from flask import Blueprint, request, jsonify, render_template, session
from datetime import datetime
import random, re, os
from config import client
from services.session_service import init_conversation, get_situation_from_session
from services.report_service import generate_report, save_report_to_drive
from services.openai_service import evaluate_question
from data.situations import SITUATIONS
from data.models import TOOL_MODELS
from data.objections import CATEGORY_OBJECTIONS

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/")
def home():
    if "unique_questions" not in session:
        session["unique_questions"] = []
    return render_template('index.html')

@chat_bp.route("/restart-chat")
def restart_chat():
    keys_to_clear = [
        "history", "stage", "question_count", "model", "chat_active",
        "unique_questions", "misunderstood_count", "available_models",
        "wrong_model_attempts", "user_answers", "off_topic_count",
        "objection_round", "generated_questions", "current_question_index",
        "current_situation_id", "situation", "last_seller_reply",
        "current_objection", "hint_shown", "question_scores", "model_score", "total_score", "seller_replies"
    ]
    for key in keys_to_clear:
        session.pop(key, None)
    return jsonify({"message": "Сесію скинуто."})

@chat_bp.route("/start_chat")
def start_chat():
    session['history'] = init_conversation()
    # Якщо треба, скинь інші параметри
    session["stage"] = 1
    session["question_count"] = 0
    session["model"] = None
    session["chat_active"] = True
    session["unique_questions"] = []

    return jsonify({
        "reply": session['history'][1]['content'],
        "avatar": session["situation"].get("avatar", "clientpes.png")
    })

@chat_bp.route("/chat", methods=["POST"])
def chat():
    print("Доступні моделі для вибору:", session.get("available_models"))
    user_input = request.json.get("message", "").strip()

    print(f"[DEBUG] Користувач написав: {user_input}")
    print(f"[DEBUG] Поточна стадія: {session.get('stage')}")

    # Ініціалізація змінних сесії
    session.setdefault("misunderstood_count", 0)
    session.setdefault("objection_round", 1)
    session.setdefault("question_scores", [])
    session.setdefault("user_answers", {})
    session.setdefault("seller_replies", [])

    if 'conversation_log' not in session:
        session['conversation_log'] = []
    
    if 'seller_name' not in session:
        seller_name = request.json.get("seller_name")
        if seller_name:
            session['seller_name'] = seller_name

    # Використовуємо setdefault для conversation_log, щоб уникнути помилок KeyError
    session.setdefault('conversation_log', [])

    if "history" not in session or not session["history"]:
        session["history"] = init_conversation()
        session["stage"] = 1
        session["question_count"] = 0
        session["model"] = None
        session["chat_active"] = True
        session["unique_questions"] = []
        session["misunderstood_count"] = 0
        session["wrong_model_attempts"] = 0
        session["model_score"] = 0
        session["total_score"] = 0
        session["objection_round"] = 1

    if session["stage"] == 1:
        # --- Перевірка, чи користувач вибрав модель ---
        if user_input.lower().startswith("обираю модель:"):
            model_name = user_input.split(":", 1)[1].strip()
            session["stage"] = 2
            return jsonify({
                "reply": f"Ви обрали модель: {model_name}. Переходимо до перевірки...",
                "chat_ended": False,
                "stage": 2,
                "chosen_model": model_name
            })

        # --- Оцінка питання ---
        question_score = evaluate_question(user_input, session["situation"]["description"])
        
        # Перевірка на дублікати
        is_duplicate = user_input.lower() in [q.lower() for q in session["unique_questions"]]
        if is_duplicate:
            question_score = max(0, question_score - 1)
            print(f"[SCORE] Повторне питання: оцінка знижена до {question_score} балів")
        
        print(f"[SCORE] Оцінка питання: {question_score} бал(и) | Поточний рахунок: {session.get('total_score', 0)}")
        
        # 🔴 ПОКРАЩЕНА ОЦІНКА З АНАЛІЗОМ ДЛЯ МАЙБУТНЬОГО ЗВІТУ
        stage1_prompt = f"""
    Питання продавця або відповідь: "{user_input}"
    Ситуація клієнта: {session["situation"]["description"]}

    Оціни якість питання за шкалою:
    2 - відповідь виявляє потребу або допомагає клієнтові зорієнтуватись у товарі
    1 - відповідь не виявляє потребу, але сформульована неправильно або некоректно
    0 - відповідь не стосується ситуації чи є агресивною

    Також проаналізуй якість питання для майбутнього детального звіту.
    """
        
        stage1_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ти оцінюєш якість питань продавця для виявлення потреб клієнта. Використовуй вказаний формат."},
                {"role": "user", "content": stage1_prompt}
            ],
            temperature=0,
            max_tokens=200
        )
        stage1_text = stage1_response.choices[0].message.content.strip()
        
        # Парсинг відповіді
        score_match = re.search(r"ОЦІНКА:\s*(\d)", stage1_text)
        comment_match = re.search(r"КОМЕНТАР:\s*(.+)", stage1_text)
        
        analyzed_score = int(score_match.group(1)) if score_match else question_score
        question_comment = comment_match.group(1).strip() if comment_match else "Коментар недоступний"
        
        # Використовуємо аналізовану оцінку
        final_score = analyzed_score
        
        print(f"[SCORE] Аналізована оцінка питання: {final_score}/2 балів")
        print(f"[COMMENT] Коментар: {question_comment}")

        # ДОДАЄМО ЗВОРОТНИЙ ЗВ'ЯЗОК ДЛЯ КОРИСТУВАЧА (ТІЛЬКИ ЯКЩО НЕ EXAM)
        feedback_message = None
        if session.get('show_hints', True):
            if final_score == 0:
                feedback_message = "❌ Це неправильне питання або відповідь. Враховуйте, що на цьому етапі потрібно ставити питання про роботи або досвід користувача з інструментом."
            elif final_score == 1:
                feedback_message = "⚠️ Питання або відповідь зарахована, але потрібно краще її сформулювати. Не спішіть, у Вас є час подумати та висловитись краще."
            elif final_score == 2:
                feedback_message = "✅ Відмінне питання або відповідь! Воно допомагає зрозуміти потреби клієнта."
            
            # Якщо питання дублюється
            if is_duplicate and final_score > 0:
                feedback_message = "🔄 Ви вже ставили схоже питання. Спробуйте задати інше."
        
        # 🔴 ЗБЕРІГАЄМО ПИТАННЯ З КОМЕНТАРЕМ ДЛЯ МАЙБУТНЬОГО АНАЛІЗУ
        session["question_scores"].append({
            "question": user_input,
            "score": final_score,
            "comment": question_comment,  # 🔴 ДОДАЄМО КОМЕНТАР ДЛЯ АНАЛІЗУ
            "is_duplicate": is_duplicate
        })
        
        session["question_count"] += 1
        
        if final_score == 0:
            session["misunderstood_count"] += 1
        
        if not is_duplicate and final_score > 0:
            session["unique_questions"].append(user_input)
        
        # Бонус
        perfect_questions = sum(1 for q in session["question_scores"] if q["score"] == 2)
        if perfect_questions >= 3 and "bonus_added" not in session:
            session["total_score"] = min(session.get("total_score", 0) + 2, 8)
            session["bonus_added"] = True
            print(f"[SCORE] Бонус +2 бали за 3 коректних запитання")
        
        # Перевірка на занадто багато неправильних питань
        if session["misunderstood_count"] >= 3:
            session["chat_active"] = False
            report_content = generate_report(session)
            success = save_report_to_drive(session)
            if success:
                print("[DRIVE] Звіт успішно збережено на Google Drive")
            else:
                print("[DRIVE] Помилка збереження звіту")
            return jsonify({
                "reply": "Ви поставили декілька некоректних питань. Діалог завершено.",
                "chat_ended": True,
                "show_restart_button": True
            })
        
        # Якщо питання отримало 0 балів - повертаємо feedback без виклику AI
        if final_score == 0:
            return jsonify({
                "reply": "Навіть не знаю, що Вам відповісти... Повторіть питання, будь ласка!",
                "chat_ended": False,
                "question_progress": session["question_count"],
                "question_feedback": feedback_message
            })
        
        current_questions_score = sum(q["score"] for q in session["question_scores"])
        current_questions_score = min(current_questions_score, 8)
        print(f"[SCORE] Загальний бал за питання: {current_questions_score}/8")
        
        # Додаємо питання до історії
        session["history"].append({"role": "user", "content": user_input})
        session['conversation_log'].append({
            'role': 'user',
            'message': user_input,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=session["history"][-20:],
                temperature=0.5,
                max_tokens=400
            )
            answer = response.choices[0].message.content.strip()

            session["history"].append({"role": "assistant", "content": answer})
            session['conversation_log'].append({
                'role': 'assistant',
                'message': answer,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            return jsonify({
                "reply": answer,
                "chat_ended": False,
                "stage": 1,
                "question_progress": session["question_count"],
                "show_model_button": session["question_count"] >= 1,
                "question_feedback": feedback_message,
                "question_score": final_score
            })
            
        except Exception as e:
            return jsonify({
                "reply": "Вибачте, сталася помилка при відповіді. Спробуйте ще раз.",
                "chat_ended": False,
                "question_feedback": feedback_message
            })

    # --- Stage 2: Вибір моделі ---
    elif session["stage"] == 2:
        user_model = re.sub(r'[^A-Z0-9-]', '', user_input.upper())
        matched_models = [m for m in session["available_models"] if user_model in m.upper()]

        if not matched_models:
            session["model_score"] = 0
            session["wrong_model_attempts"] += 1
            session["stage"] = 3

            # ПІДКАЗКА ДЛЯ НЕПРАВИЛЬНОГО ВИБОРУ МОДЕЛІ
            model_feedback = None
            if session.get('show_hints', True):
                model_feedback = "❌ Ви обрали неправильну модель інструменту. Наступного разу краще виявляйте потребу – ставте більше запитань."

            return jsonify({
                "reply": "Ця модель не підходить для моїх потреб. Давайте продовжимо.",
                "chat_ended": False,
                "stage": 3,
                "model_chosen": False,
                "model_feedback": model_feedback
            })

        user_model = matched_models[0].upper()
        current_situation = next((s for s in SITUATIONS if s["id"] == session.get("current_situation_id")), None)
        if not current_situation:
            return jsonify({
                "reply": "Помилка: ситуація не знайдена.",
                "chat_ended": True,
                "show_restart_button": True
            })

        correct_models = [model.upper() for model in current_situation["correct_models"]]

        # Оцінка моделі
        if user_model in correct_models:
            session["model_score"] = 4  # Максимум 4 балів за правильний вибір
            print(f"[SCORE] Правильна модель: +4 балів")

            model_feedback = None
            if session.get('show_hints', True):
                model_feedback = "✅ Чудовий вибір, це означає, що ви правильно виявили потребу клієнта!"
        else:
            session["model_score"] = 0
            print(f"[SCORE] Неправильна модель: 0 балів")

            model_feedback = None
            if session.get('show_hints', True):
                model_feedback = "❌ Ви обрали неправильну модель інструменту. У подальшому – краще виявляйте потребу клієнта."

            # Оновлений вивід для переходу на stage 3
            print(f"[SCORE] Поточний бал за модель: {session['model_score']}/4")
            print(f"[SCORE] Загальний бал: {session.get('total_score', 0) + session['model_score']}")

        # Переходь на stage 3 після оцінки моделі
        session["model"] = user_model
        session["stage"] = 3
        session["current_question_index"] = 0
        session["user_answers"] = {}

        # Генерація уточнюючих питань
        prompt = f"""Ти клієнт, який обрав інструмент {user_model} для {session['situation']['description']}.\n
        Згенеруй 5 питань про **задачі моделі**, **характеристику**, **зовнішню будову**, вартість інструменту та витратні матеріали до САМЕ ЦЬОГО ІНСТРУМЕНТУ.. **НІКОЛИ НЕ ПИТАЙ ЗА РОЗМІРИ ТА ВАГУ ІНСТРУМЕНТУ**. 
        
        Питання став, використовуючи різні початки:

    - А мене цікавить...
    - А ще хотів би знати... 
    - А розкажіть детальніше...
    - А мене також цікавить...
    - А останнє питання - ...
    - А скажіть, будь ласка...
    - А ще мене цікавить...
    - А не могли б ви розповісти...
        
        """

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ти — клієнт, який має задати уточнюючі запитання про модель інструмента."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=400
            )
            content = response.choices[0].message.content or ""
            questions = [line.strip(" 1234567890.-") for line in content.split('\n') if line.strip()]
            session["generated_questions"] = questions
            
            session["history"].append({"role": "user", "content": user_input})
            first_question = questions[0] if questions else "Яке перше ваше питання про цю модель?"
            session["history"].append({"role": "assistant", "content": first_question})

            session['conversation_log'].append({
                'role': 'user',
                'message': user_input,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            session['conversation_log'].append({
                'role': 'assistant',
                'message': f"Добре, {user_model} виглядає непогано.",
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            session.modified = True

            return jsonify({
                "reply": f"Добре, наче виглядає непогано. \n\n{first_question}",
                "chat_ended": False,
                "stage": 3,
                "model_feedback": model_feedback
            })
        except Exception as e:
            return jsonify({
                "reply": "Вибачте, сталася помилка при генерації питань. Спробуйте ще раз.",
                "chat_ended": False,
                "model_feedback": model_feedback
            })

    # --- Stage 3: Уточнюючі питання ---
    elif session["stage"] == 3:
        if 'generated_questions' not in session:
            return jsonify({
                "reply": "Питання не знайдені. Давайте почнемо спочатку.",
                "chat_ended": True,
                "show_restart_button": True
            })

        index = session.get('current_question_index', 0)
        current_question = session['generated_questions'][index]

        session["history"].append({"role": "user", "content": user_input})

        session['conversation_log'].append({
            'role': 'user',
            'message': user_input,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        # 🔴 ПОКРАЩЕНА ОЦІНКА З АНАЛІЗОМ ДЛЯ МАЙБУТНЬОГО ЗВІТУ
        gpt_prompt = f"""
    Питання клієнта: "{current_question}"
    Відповідь продавця: "{user_input}"

    Оціни відповідь за шкалою:
    2 - характеристика та є пояснення, що вона означає або яку користь несе клієнтові
    1 - просто наявна характеристика  
    0 - відповідь не по темі або загальна

    Також проаналізуй якість відповіді для майбутнього детального звіту.

    ФОРМАТ ВІДПОВІДІ:
    ОЦІНКА: [0/1/2]
    КОМЕНТАР: [короткий коментар про якість відповіді]
    """
        try:
            evaluation = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ти оцінюєш відповіді продавця. Використовуй вказаний формат."},
                    {"role": "user", "content": gpt_prompt}
                ],
                temperature=0,
                max_tokens=300
            )
            evaluation_text = evaluation.choices[0].message.content.strip()
            
            # Парсинг відповіді
            score_match = re.search(r"ОЦІНКА:\s*(\d)", evaluation_text)
            comment_match = re.search(r"КОМЕНТАР:\s*(.+)", evaluation_text)
            
            score = int(score_match.group(1)) if score_match else 0
            comment = comment_match.group(1).strip() if comment_match else "Коментар недоступний"
            
            print(f"[SCORE] Відповідь на питання {session['current_question_index']+1}: {score}/2 балів")
            print(f"[COMMENT] Коментар: {comment}")

            # 🔴 ДОДАЄМО ПІДКАЗКИ ДЛЯ STAGE 3
            answer_feedback = None
            if session.get('show_hints', True):
                if score == 0:
                    answer_feedback = "❌ Ваша відповідь не по темі або занадто загальна. Надайте конкретну характеристику та поясніть, як вона допомагає клієнту."
                elif score == 1:
                    answer_feedback = "⚠️ Ви надали характеристику, але не пояснили переваги. Розкажіть, як це допоможе клієнту у його задачі."
                elif score == 2:
                    answer_feedback = "✅ Відмінна відповідь! Ви надали характеристику та пояснили її перевагу."

            # 🔴 ЗБЕРІГАЄМО ВІДПОВІДЬ З КОМЕНТАРЕМ ДЛЯ МАЙБУТНЬОГО АНАЛІЗУ
            session["user_answers"][current_question] = {
                "answer": user_input,
                "score": score,
                "comment": comment  # 🔴 ДОДАЄМО КОМЕНТАР ДЛЯ АНАЛІЗУ
            }

            # 🔴 Лічильник двох поспіль нерелевантних відповідей
            if score == 0:
                session['irrelevant_answers'] = session.get('irrelevant_answers', 0) + 1
            else:
                session['irrelevant_answers'] = 0

            if session['irrelevant_answers'] >= 2:
                session['chat_active'] = False
                report_content = generate_report(session)
                success = save_report_to_drive(session)
                if success:
                    print("[DRIVE] Звіт успішно збережено на Google Drive")
                else:
                    print("[DRIVE] Помилка збереження звіту")
                    
                return jsonify({
                    "reply": "Вибачте, я не отримав потрібної інформації. Я, мабуть, піду в інший магазин.",
                    "chat_ended": True,
                    "show_restart_button": True
                })

            # Продовжуємо діалог
            raw_score = sum(a["score"] for a in session["user_answers"].values())
            current_answers_score = min(raw_score, 10)
            print(f"[SCORE] Загальний бал за відповіді: {current_answers_score}/10")

            session['current_question_index'] += 1

            # Перехід до наступного питання
            if session['current_question_index'] < len(session['generated_questions']):
                next_question = session['generated_questions'][session['current_question_index']]
                session["history"].append({"role": "assistant", "content": next_question})
                session.modified = True

                session['conversation_log'].append({
                    'role': 'assistant',
                    'message': next_question,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                return jsonify({
                    "reply": next_question,
                    "chat_ended": False,
                    "answer_feedback": answer_feedback,
                    "current_score": score
                })
            else:
                # Перехід до Stage 4 (заперечення)
                session["stage"] = 4
                answers_score = sum(a["score"] for a in session["user_answers"].values())

                if answers_score >= 5:
                    feedback = "Класно презентуєте."
                elif answers_score >= 3:
                    feedback = "Окей, прикольно."
                else:
                    feedback = "Зрозуміло."

                category = session.get("current_category", "default")
                objections = CATEGORY_OBJECTIONS.get(category, CATEGORY_OBJECTIONS["default"])
                session["current_objection"] = random.choice(objections)
                session["objection_round"] = 1

                final_reply = f"{feedback}\n\nХм... {session['current_objection']}"
                session["history"].append({"role": "assistant", "content": final_reply})
                session['conversation_log'].append({
                    'role': 'assistant',
                    'message': final_reply,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                
                session.modified = True

                return jsonify({
                    "reply": f"{feedback}\n\nХм... {session['current_objection']}",
                    "chat_ended": False,
                    "stage": 4,
                    "answer_feedback": answer_feedback,
                    "answers_summary": f"Загальний бал за відповіді: {min(answers_score, 6)}/6"
                })
        except Exception as e:
            return jsonify({
                "reply": "Виникла помилка при оцінюванні відповіді. Спробуйте ще раз.",
                "chat_ended": False
            })

    # --- Stage 4: Обробка заперечень ---
    elif session["stage"] == 4:
        objection = session.get("current_objection", "Заперечення")
        seller_reply = user_input
        session["seller_replies"].append(seller_reply)
        current_round = session.get("objection_round", 1)

        # Додаємо репліку продавця до логу ТІЛЬКИ ОДИН РАЗ
        session['conversation_log'].append({
            'role': 'user',
            'message': seller_reply,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        if current_round <= 1:
            try:
                history = "\n".join([f"Раунд {i+1}: {reply}" for i, reply in enumerate(session["seller_replies"])])
                gpt_prompt = f"""
    Ти — клієнт, який має заперечення: "{objection}".

    Ось як продавець відповідав до цього моменту:
    {history}

    Відповідай як реалістичний клієнт. Реагуй природно на останню репліку продавця: "{seller_reply}".
    Підтримуй контекст заперечення. Твоя відповідь повинна складатися з одного-двох речень. Не повторюйся."""
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Ти — клієнт у діалозі з продавцем. Відповідай чесно, логічно і згідно з контекстом заперечення. Твоя відповідь повинна складатися рівно з одного речення (5–15 слів). Не повторюйся."},
                        {"role": "user", "content": gpt_prompt}
                    ],
                    temperature=0.6,
                    max_tokens=300
                )
                reply = response.choices[0].message.content
                session["objection_round"] += 1
                session.modified = True

                session['conversation_log'].append({
                    'role': 'assistant',
                    'message': reply,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                # 🔴 ДОДАЄМО ПІДКАЗКУ ДЛЯ STAGE 4
                objection_feedback = None
                if session.get('show_hints', True):
                    objection_feedback = "💡 Ви на шляху до розв'язання заперечення! Намагайтесь надавати конкретні аргументи та приклади."

                return jsonify({
                    "reply": reply,
                    "chat_ended": False,
                    "current_round": session["objection_round"],
                    "objection_feedback": objection_feedback
                })
            except Exception as e:
                return jsonify({
                    "reply": "Вибачте, сталася помилка під час відповіді. Спробуйте ще раз.",
                    "chat_ended": False
                })

        elif current_round == 2:
            try:
                if not session.get("seller_replies"):
                    return jsonify({
                        "reply": "Помилка: відсутні відповіді для оцінювання.",
                        "chat_ended": True,
                        "show_restart_button": True
                    })

                full_history = "\n".join([f"Раунд {i+1}: {reply}" for i, reply in enumerate(session["seller_replies"])])
                
                # 🔴 АНАЛІЗ ДЛЯ STAGE 1 - ВИЯВЛЕННЯ ПОТРЕБ
                stage1_analysis = "Інформація про етап виявлення потреб недоступна"
                stage1_advice = "Рекомендації відсутні"

                question_scores = session.get("question_scores", [])
                if question_scores:
                    # Формуємо текст для аналізу
                    questions_text = ""
                    for i, q_data in enumerate(question_scores, 1):
                        questions_text += f"{i}. Питання: {q_data['question']}\n"
                        questions_text += f"   Оцінка: {q_data['score']}/2\n"
                        if q_data.get('comment'):
                            questions_text += f"   Коментар: {q_data['comment']}\n"
                        if q_data.get('is_duplicate'):
                            questions_text += f"   ⚠️ Дублікат\n"
                        questions_text += "\n"
                    
                    stage1_prompt = f"""
    Проаналізуй питання, які ставив продавець для виявлення потреб клієнта:

    {questions_text}

    Оціни якість виявлення потреб за критеріями:
    1. Відповідність ситуації клієнта
    2. Здатність виявити реальні потреби
    3. Уникання дублювань

    Надай короткий аналіз та 2-3 конкретні поради для покращення навичок виявлення потреб.

    ФОРМАТ:
    АНАЛІЗ_ВИЯВЛЕННЯ_ПОТРЕБ: [короткий аналіз якості питань – два-три речення]
    ПОРАДИ_ВИЯВЛЕННЯ_ПОТРЕБ: [конкретні рекомендації – два-три речення]
    """
                    
                    stage1_response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "Ти — експерт з виявлення потреб клієнтів та комунікацій."},
                            {"role": "user", "content": stage1_prompt}
                        ],
                        temperature=0.3,
                        max_tokens=400
                    )
                    stage1_text = stage1_response.choices[0].message.content.strip()
                    
                    # Парсинг відповіді для stage 1
                    analysis_match = re.search(r"АНАЛІЗ_ВИЯВЛЕННЯ_ПОТРЕБ:\s*(.+?)(?=ПОРАДИ_ВИЯВЛЕННЯ_ПОТРЕБ:|$)", stage1_text, re.DOTALL)
                    advice_match = re.search(r"ПОРАДИ_ВИЯВЛЕННЯ_ПОТРЕБ:\s*(.+)", stage1_text, re.DOTALL)
                    
                    stage1_analysis = analysis_match.group(1).strip() if analysis_match else "Аналіз виявлення потреб недоступний"
                    stage1_advice = advice_match.group(1).strip() if advice_match else "Рекомендації відсутні"

                # 🔴 АНАЛІЗ ДЛЯ STAGE 3 - ПРЕЗЕНТАЦІЯ МОДЕЛІ
                stage3_analysis = "Інформація про етап презентації недоступна"
                stage3_advice = "Рекомендації відсутні"
                
                user_answers = session.get("user_answers", {})
                if user_answers:
                    # Формуємо текст для аналізу
                    answers_text = ""
                    for i, (question, answer_data) in enumerate(user_answers.items(), 1):
                        answers_text += f"{i}. Питання: {question}\n"
                        answers_text += f"   Відповідь: {answer_data['answer']}\n"
                        answers_text += f"   Оцінка: {answer_data['score']}/2\n"
                        if answer_data.get('comment'):
                            answers_text += f"   Коментар: {answer_data['comment']}\n"
                        answers_text += "\n"
                    
                    stage3_prompt = f"""
    Проаналізуй відповіді продавця на технічні питання клієнта про модель інструменту:

    {answers_text}

    Оціни якість презентації за критеріями:
    1. Чи є характеристика та є пояснення, що вона означає або яку користь несе клієнтові
    2. Чи зрозуміло сформульована думка

    Надай короткий аналіз та 2-3 конкретні поради для покращення презентаційних навичок.

    ФОРМАТ:
    АНАЛІЗ_ПРЕЗЕНТАЦІЇ: [короткий аналіз якості презентації – два-три речення]
    ПОРАДИ_ПРЕЗЕНТАЦІЇ: [конкретні рекомендації – два-три речення]
    """
                    
                    stage3_response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "Ти — експерт з презентаційних навичок та комунікацій."},
                            {"role": "user", "content": stage3_prompt}
                        ],
                        temperature=0.3,
                        max_tokens=700
                    )
                    stage3_text = stage3_response.choices[0].message.content.strip()
                    
                    # Парсинг відповіді для stage 3
                    analysis_match = re.search(r"АНАЛІЗ_ПРЕЗЕНТАЦІЇ:\s*(.+?)(?=ПОРАДИ_ПРЕЗЕНТАЦІЇ:|$)", stage3_text, re.DOTALL)
                    advice_match = re.search(r"ПОРАДИ_ПРЕЗЕНТАЦІЇ:\s*(.+)", stage3_text, re.DOTALL)
                    
                    stage3_analysis = analysis_match.group(1).strip() if analysis_match else "Аналіз презентації недоступний"
                    stage3_advice = advice_match.group(1).strip() if advice_match else "Рекомендації відсутні"

                # 🔴 ОЦІНКА ДЛЯ STAGE 4 - ЗАПЕРЕЧЕННЯ
                evaluation_prompt = f"""
Ти — експерт з продажів, який оцінює ефективність роботи з запереченнями.

ЗАПЕРЕЧЕННЯ КЛІЄНТА: "{objection}"

ВІДПОВІДІ ПРОДАВЦЯ (по раундах):
{full_history}

ПРОАНАЛІЗУЙ відповіді продавця за такими критеріями та ВКАЖИ БАЛИ для кожного, але НЕ ВКАЗУЙ ЦІ КРИТЕРІЇ У ФІНАЛЬНОМУ ЗВІТІ:
1. Відповідність запереченню (0-2 бали): Чи відповідає продавець безпосередньо на заперечення?
2. Аргументація (0-2 бали): Чи наводить конкретні переваги, факти, приклади?
3. Емпатія та розуміння (0-2 бали): Чи виявляє розуміння проблеми клієнта?
4. Закриття (0-2 бали): Чи пропонує рішення або переводить до покупки?

ФОРМАТ ВІДПОВІДІ:
АНАЛІЗ_ЗАПЕРЕЧЕННЯ: [детальний аналіз за критеріями, але їх не згадуй – два-три речення]
ПОРАДИ_ЗАПЕРЕЧЕННЯ: [2-3 конкретні рекомендації – два-три речення]
ЗАГАЛЬНІ_БАЛИ: [сума балів від 0 до 8]
"""
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Ти — експерт з оцінки комунікацій. Будь об'єктивним та конструктивним."},
                        {"role": "user", "content": evaluation_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=700
                )
                evaluation_text = response.choices[0].message.content.strip()

                print(f"[DEBUG] Відповідь GPT для заперечень: {evaluation_text}")

                # Парсинг відповіді для stage 4
                score_match = re.search(r"ЗАГАЛЬНІ_БАЛИ:\s*(\d+)", evaluation_text)
                analysis_match = re.search(r"АНАЛІЗ_ЗАПЕРЕЧЕННЯ:\s*(.+?)(?=ПОРАДИ_ЗАПЕРЕЧЕННЯ:|$)", evaluation_text, re.DOTALL)
                advice_match = re.search(r"ПОРАДИ_ЗАПЕРЕЧЕННЯ:\s*(.+)", evaluation_text, re.DOTALL)

                # Отримуємо числові бали
                if score_match:
                    objection_score = int(score_match.group(1))
                    # Обмежуємо максимум 8 балами
                    objection_score = min(objection_score, 8)
                    print(f"[SCORE] Отримано {objection_score}/8 балів за заперечення")
                else:
                    # Альтернативний парсинг - шукаємо бали в тексті аналізу
                    total_score = 0
                    criteria_patterns = [
                        r"Відповідність запереченню.*?(\d+) бал",
                        r"Аргументація.*?(\d+) бал", 
                        r"Емпатія.*?(\d+) бал",
                        r"Закриття.*?(\d+) бал"
                    ]
                    
                    for pattern in criteria_patterns:
                        match = re.search(pattern, evaluation_text, re.IGNORECASE)
                        if match:
                            total_score += int(match.group(1))
                    
                    objection_score = min(total_score, 8)
                    print(f"[SCORE] Підраховано {objection_score}/8 балів за заперечення з аналізу")

                stage4_analysis = analysis_match.group(1).strip() if analysis_match else "Аналіз недоступний"
                stage4_advice = advice_match.group(1).strip() if advice_match else "Поради недоступні"

                # Фінальна репліка клієнта на основі балів
                if objection_score >= 7:
                    client_final_reply = "Добре, ви мене переконали. Пакуйте!"
                elif objection_score >= 5:
                    client_final_reply = "Гаразд, беру. Пакуйте!"
                elif objection_score >= 3:
                    client_final_reply = "Ну що ж, давайте. Пакуйте."
                elif objection_score >= 1:
                    client_final_reply = "Ой, ладно, пакуйте. Але я ще сумніваюся."
                else:
                    client_final_reply = "Дякую, я ще подумаю. До побачення."

                session['objection_score'] = objection_score

                print(f"[SCORE] Оцінка аргументів: {objection_score}/8 балів")
                print(f"[STAGE1_ANALYSIS] Аналіз виявлення потреб: {stage1_analysis}")
                print(f"[STAGE3_ANALYSIS] Аналіз презентації: {stage3_analysis}")
                print(f"[STAGE4_ANALYSIS] Аналіз заперечень: {stage4_analysis}")

                # Додаємо фінальну репліку клієнта до логу
                session['conversation_log'].append({
                    'role': 'assistant',
                    'message': client_final_reply,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                # Розрахунок загального балу
                model_score = session.get("model_score", 0)
                questions_score = min(sum(q["score"] for q in session.get("question_scores", [])), 8)
                answers_score = min(sum(a["score"] for a in session.get("user_answers", {}).values()), 10)
                objection_score = session.get('objection_score', 0)
                total_score = model_score + questions_score + answers_score + objection_score

                print("\n=== ФІНАЛЬНИЙ РАХУНОК ===")
                print(f"[SCORE] За модель: {model_score}/4")
                print(f"[SCORE] За питання: {questions_score}/8")
                print(f"[SCORE] За відповіді: {answers_score}/10")
                print(f"[SCORE] За заперечення: {objection_score}/8")
                print(f"[SCORE] ЗАГАЛЬНИЙ БАЛ: {total_score}/30")

                if total_score >= 24:
                    summary_label = "🟢 Чудова консультація."
                elif total_score >= 16:
                    summary_label = "🟡 Задовільна консультація."
                else:
                    summary_label = "🔴 Незадовільна консультація."

                # 🔴 ФОРМУЄМО ДЕТАЛЬНИЙ ЗВІТ З ОКРЕМИМИ БЛОКАМИ
                detailed_report = {
                    "model_score": model_score,
                    "questions_score": questions_score,
                    "answers_score": answers_score,
                    "objection_score": objection_score,
                    "total_score": total_score,
                    "summary_label": summary_label,
                    "client_final_reply": client_final_reply,
                    
                    # 🔴 ОКРЕМІ БЛОКИ ДЛЯ КОЖНОГО ЕТАПУ
                    "stage1_analysis": stage1_analysis,
                    "stage1_advice": stage1_advice,
                    "stage3_analysis": stage3_analysis,
                    "stage3_advice": stage3_advice,
                    "stage4_analysis": stage4_analysis,
                    "stage4_advice": stage4_advice
                }

                # Формуємо відповідь
                response_data = {
                    "reply": client_final_reply,
                    "detailed_report": detailed_report,
                    "chat_ended": True,
                    "show_restart_button": True,
                    "report_filename": f"report_{session.get('seller_name', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                }

                # Зберігаємо звіт
                drive_success = save_report_to_drive(session)
                if drive_success:
                    print("[DRIVE] Звіт успішно збережено на Google Drive")
                else:
                    print("[DRIVE] Помилка збереження звіту")

                # Очищаємо сесію після формування відповіді
                session.clear()
                session.modified = True

                return jsonify(response_data)
                
            except Exception as e:
                print(f"Помилка при оцінюванні: {str(e)}")
                return jsonify({
                    "reply": "Вибачте, не вдалося обробити відповідь. Давайте спробуємо ще раз?",
                    "chat_ended": False
                })
            
@chat_bp.route("/show_models", methods=["POST"])
def show_models():
    # Отримуємо поточну ситуацію
    current_situation = session.get("situation")
    
    # Отримуємо правильні і неправильні моделі з поточної ситуації
    correct_models = current_situation["correct_models"]
    wrong_models = current_situation["wrong_models"]
    
    # Фільтруємо доступні моделі на основі ситуації
    available_models = correct_models + wrong_models

    session["stage"] = 2  # Переконуємось, що ми на правильному етапі для вибору моделі
    session["available_models"] = available_models

    return jsonify({
        "models": available_models,
        "stage": 2
    })