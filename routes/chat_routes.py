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
        session.pop("user_selected_model", None)
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
            session["user_selected_model"] = model_name.upper()  # Зберігаємо обрану модель
            return jsonify({
                "reply": f"Так, оце модель {model_name}. А можна взяти її в руки?",
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

        current_question = f"question_{session.get('question_count', 0) + 1}"

        session["user_answers"][current_question] = {
            "answer": user_input,
            "score": final_score,          # 🔴 ОБОВʼЯЗКОВО
            "comment": question_comment    # (необов'язково)
        }
        
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

        if "conversation_log" not in session:
            session["conversation_log"] = []

        user_model = re.sub(r'[^A-Z0-9-]', '', user_input.upper())
        matched_models = [m for m in session["available_models"] if user_model in m.upper()]

        # Лог користувача
        session["history"].append({"role": "user", "content": user_input})
        session["conversation_log"].append({
            "role": "user",
            "message": user_input,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        if not matched_models:
            session["model_score"] = 0
            session["wrong_model_attempts"] += 1
            session["stage"] = 3

            reply_text = "Ця модель не підходить для моїх потреб. Давайте продовжимо."

            session["conversation_log"].append({
                "role": "assistant",
                "message": reply_text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            return jsonify({
                "reply": reply_text,
                "chat_ended": False,
                "stage": 3,
                "model_chosen": False
            })

        user_model = matched_models[0].upper()

        current_situation = next(
            (s for s in SITUATIONS if s["id"] == session.get("current_situation_id")),
            None
        )

        if not current_situation:
            reply_text = "Помилка: ситуація не знайдена."

            session["conversation_log"].append({
                "role": "assistant",
                "message": reply_text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            return jsonify({
                "reply": reply_text,
                "chat_ended": True,
                "show_restart_button": True
            })

        correct_models = [m.upper() for m in current_situation["correct_models"]]

        session["model_score"] = 6 if user_model in correct_models else 0
        session["model"] = user_model
        session["stage"] = 3
        session["current_question_index"] = 0
        session["user_answers"] = {}
        session["clarification_attempts"] = 0

        # --- Генерація питань ---
        prompt = f"""
        Ти клієнт, який обрав інструмент {user_model} для {session['situation']['description']}.
        Згенеруй 5 природних запитань.
        НЕ питай про вагу та розміри.
        """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ти клієнт у магазині інструментів."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=400
        )

        content = response.choices[0].message.content or ""
        questions = [q.strip(" 1234567890.-") for q in content.split('\n') if q.strip()]
        session["generated_questions"] = questions

        first_question = questions[0] if questions else "Розкажіть про цю модель."
        reply_text = f"Добре, {user_model} виглядає непогано.\n\n{first_question}"

        session["conversation_log"].append({
            "role": "assistant",
            "message": reply_text,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        return jsonify({
            "reply": reply_text,
            "chat_ended": False,
            "stage": 3
        })

    elif session["stage"] == 3:

        if 'generated_questions' not in session:
            return jsonify({
                "reply": "Питання не знайдені. Почнемо спочатку.",
                "chat_ended": True,
                "show_restart_button": True
            })

        # Ініціалізація
        if "conversation_log" not in session:
            session["conversation_log"] = []
        if "user_answers" not in session:
            session["user_answers"] = {}

        index = session.get('current_question_index', 0)
        current_question = session['generated_questions'][index]
        user_input_text = user_input.strip()

        # =====================================================
        # 🔹 Обробка образ та нецензури
        # =====================================================
        insults = ["придурок", "дурень", "ідіот", "дебіл"]
        if any(word in user_input_text.lower() for word in insults):
            return jsonify({
                "reply": "З таким ставленням я, мабуть, звернуся в інший магазин.",
                "chat_ended": True,
                "show_restart_button": True
            })

        # =====================================================
        # 🔹 Класифікація повідомлення
        # =====================================================
        msg_type = None
        text = user_input_text.lower()
        if "?" in text or text.startswith(("що", "чому", "яке", "яка", "які", "як", "навіщо", "в якому")):
            msg_type = "QUESTION"
        elif text in ["не знаю", "не розумію", "важко сказати", "я хз", "без поняття"]:
            msg_type = "CONFUSED"
        else:
            classification_prompt = f"""
            Поточне питання клієнта: "{current_question}"
            Повідомлення продавця: "{user_input_text}"

            Визнач тип:
            ANSWER — відповідь на питання
            QUESTION — продавець ставить зустрічне питання
            CONFUSED — продавець не знає або не розуміє
            IRRELEVANT — образи або не по темі

            Відповідай одним словом.
            """
            classification = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": classification_prompt}],
                temperature=0,
                max_tokens=10
            )
            msg_type = classification.choices[0].message.content.strip().upper()

        print(f"[DEBUG] msg_type = {msg_type}")

        # =====================================================
        # 🔹 QUESTION
        # =====================================================
        if msg_type == "QUESTION":
            # Зберігаємо відповідь користувача
            session["user_answers"][current_question] = {"answer": user_input_text}

            answer_prompt = f"""
            Ти покупець у магазині інструментів.
            Коротко відповідай на питання продавця:
            "{user_input_text}"
            Не вигадуй технічні характеристики. Відповідай простою мовою.
            """
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": answer_prompt}],
                temperature=0.7,
                max_tokens=120
            )
            bot_answer = response.choices[0].message.content.strip()

            reply_text = f"{bot_answer}\n\nА тепер скажіть, будь ласка: {current_question}"

            session["conversation_log"].append({
                "role": "assistant",
                "message": reply_text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            return jsonify({
                "reply": reply_text,
                "chat_ended": False
            })

        # =====================================================
        # 🔹 CONFUSED
        # =====================================================
        elif msg_type == "CONFUSED":
            # Зберігаємо відповідь користувача
            session["user_answers"][current_question] = {"answer": user_input_text}

            attempts = session.get("confused_attempts", 0)
            if attempts == 0:
                simplify_prompt = f"""
                Переформулюй питання простіше і зрозуміліше.
                Питання: "{current_question}"
                Говори як звичайний покупець.
                """
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": simplify_prompt}],
                    temperature=0.7,
                    max_tokens=120
                )
                simpler_question = response.choices[0].message.content.strip()
                session["confused_attempts"] = 1

                reply_text = f"Можливо, я не зовсім зрозуміло сказав.\n\n{simpler_question}"

                session["conversation_log"].append({
                    "role": "assistant",
                    "message": reply_text,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                return jsonify({
                    "reply": reply_text,
                    "chat_ended": False
                })
            else:
                session["confused_attempts"] = 0
                session['current_question_index'] += 1
                if session['current_question_index'] < len(session['generated_questions']):
                    next_question = session['generated_questions'][session['current_question_index']]
                    reply_text = f"Добре, зрозуміло.\n\n{next_question}"

                    session["conversation_log"].append({
                        "role": "assistant",
                        "message": reply_text,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })

                    return jsonify({
                        "reply": reply_text,
                        "chat_ended": False
                    })

                # Переходимо на Stage 4
                session["stage"] = 4
                category = session.get("current_category", "default")
                objections = CATEGORY_OBJECTIONS.get(category, CATEGORY_OBJECTIONS["default"])
                session["current_objection"] = random.choice(objections)

                reply_text = f"Зрозуміло.\n\nХм... {session['current_objection']}"

                session["conversation_log"].append({
                    "role": "assistant",
                    "message": reply_text,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                return jsonify({
                    "reply": reply_text,
                    "chat_ended": False,
                    "stage": 4
                })

        # =====================================================
        # 🔹 IRRELEVANT
        # =====================================================
        elif msg_type == "IRRELEVANT":
            # Зберігаємо відповідь користувача
            session["user_answers"][current_question] = {"answer": user_input_text}

            reply_text = f"Вибачте, але мені важливо це зрозуміти.\n\n{current_question}"

            session["conversation_log"].append({
                "role": "assistant",
                "message": reply_text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            return jsonify({
                "reply": reply_text,
                "chat_ended": False
            })

        # =====================================================
        # 🔹 ANSWER
        # =====================================================
        elif msg_type == "ANSWER":
            # Зберігаємо відповідь користувача
            session["user_answers"][current_question] = {"answer": user_input_text}

            final_score = 0
            question_comment = "Коментар недоступний"

            evaluation_prompt = f"""
            Питання: "{current_question}"
            Відповідь: "{user_input_text}"

            2 — характеристика + користь
            1 — лише характеристика
            0 — не по темі

            Відповідай тільки числом і дай короткий коментар:
            ОЦІНКА: X
            КОМЕНТАР: <короткий коментар>
            """

            evaluation = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": evaluation_prompt}],
                temperature=0,
                max_tokens=100
            )

            stage3_text = evaluation.choices[0].message.content.strip()

            score_match = re.search(r"ОЦІНКА:\s*(\d)", stage3_text)
            comment_match = re.search(r"КОМЕНТАР:\s*(.+)", stage3_text)
            final_score = int(score_match.group(1)) if score_match else 0
            question_comment = comment_match.group(1).strip() if comment_match else "Коментар недоступний"

            # --- Зберігаємо оцінку та коментар
            session["user_answers"][current_question]["score_text"] = stage3_text
            session["user_answers"][current_question]["score"] = final_score
            session["user_answers"][current_question]["comment"] = question_comment

            # --- Формуємо тост-підказку ---
            feedback_toast = None
            if session.get('show_hints', True):
                if final_score == 0:
                    feedback_toast = "❌ Відповідь не пояснює вигоди. Спробуйте зв'язати характеристики з користю."
                elif final_score == 1:
                    feedback_toast = "⚠️ Частково правильно. Додайте приклади або поясніть користь."
                elif final_score == 2:
                    feedback_toast = "✅ Чудово! Відповідь повністю пояснює вигоду для клієнта."

            # --- Наступне питання ---
            session["confused_attempts"] = 0
            session['current_question_index'] += 1

            if session['current_question_index'] < len(session['generated_questions']):
                next_question = session['generated_questions'][session['current_question_index']]
                reply_text = next_question

                session["conversation_log"].append({
                    "role": "assistant",
                    "message": reply_text,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                return jsonify({
                    "reply": reply_text,
                    "chat_ended": False,
                    "question_feedback": feedback_toast,
                    "question_score": final_score
                })

            # --- Stage 4 ---
            session["stage"] = 4
            answers_score = min(
                sum(a.get("score", 0) for a in session.get("user_answers", {}).values()),
                10
            )

            if answers_score >= 5:
                feedback = "Класно презентуєте."
            elif answers_score >= 3:
                feedback = "Окей, прикольно."
            else:
                feedback = "Зрозуміло."

            category = session.get("current_category", "default")
            objections = CATEGORY_OBJECTIONS.get(category, CATEGORY_OBJECTIONS["default"])
            session["current_objection"] = random.choice(objections)

            reply_text = f"{feedback}\n\nХм... {session['current_objection']}"

            session["conversation_log"].append({
                "role": "assistant",
                "message": reply_text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            return jsonify({
                "reply": reply_text,
                "chat_ended": False,
                "stage": 4,
                "question_feedback": feedback_toast,
                "question_score": final_score
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
    Підтримуй контекст заперечення. Твоя відповідь повинна складатися з одного-двох речень. Не повторюйся.
    Намагайся висловити свій сумнів природньо, можеш навіть агресивно чи ввічливо, обережно чи не дуже."""
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Ти — клієнт у діалозі з продавцем. Відповідай чесно, логічно і згідно з контекстом заперечення. Твоя відповідь повинна складатися рівно з одного речення (10–15 слів). Не повторюйся."},
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
                        answers_text += f"   Оцінка: {re.search(r'ОЦІНКА:\s*(\d)', answer_data['score_text']).group(1)}/2\n"
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

                    ПРОАНАЛІЗУЙ відповіді продавця та бал від 0 до 6 за таким критерієм:

                    1 бал – дуже слабке відпрацювання заперечення
                    2 бали – слабке відпрацювання заперечення
                    3 бали – не дуже точне відпрацювання заперечення
                    4 бали – середнє відпрацювання заперечення
                    5 балів – гарне відпрацювання заперечення
                    6 балів – ідеальне відпрацювання заперечення

                    ФОРМАТ ВІДПОВІДІ ОБОВ'ЯЗКОВО ТАКИЙ:
                    АНАЛІЗ_ЗАПЕРЕЧЕННЯ: [детальний аналіз за критеріями, але їх не згадуй – два-три речення]
                    ПОРАДИ_ЗАПЕРЕЧЕННЯ: [2-3 конкретні рекомендації – два-три речення]
                    ЗАГАЛЬНІ_БАЛИ: [число від 0 до 6]
                    """
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "Ти — експерт з оцінки комунікацій. Повертай тільки цілі числа від 0 до 6. Будь об'єктивним та конструктивним."},
                            {"role": "user", "content": evaluation_prompt}
                        ],
                        temperature=0.3,
                        max_tokens=700
                    )
                    evaluation_text = response.choices[0].message.content.strip()

                    print(f"[DEBUG] Відповідь GPT для заперечень: {evaluation_text}")

                    # Парсинг відповіді для stage 4 - СПРОЩЕНИЙ ТА НАДІЙНИЙ ВАРІАНТ
                    objection_score = 0  # значення за замовчуванням

                    # Спробуємо знайти число 0-6 різними способами
                    score_match = re.search(r"ЗАГАЛЬНІ_БАЛИ:\s*(\d+)", evaluation_text)
                    if score_match:
                        objection_score = int(score_match.group(1))
                        print(f"[SCORE] Отримано {objection_score} балів за заперечення (парсинг з ЗАГАЛЬНІ_БАЛИ)")

                    # Якщо не знайшли, шукаємо інші варіанти
                    if objection_score == 0:
                        # Шукаємо число 0-6 у всьому тексті
                        all_numbers = re.findall(r'\b([0-6])\b', evaluation_text)
                        if all_numbers:
                            # Беремо останнє знайдене число 0-6
                            for num in reversed(all_numbers):
                                if 0 <= int(num) <= 6:
                                    objection_score = int(num)
                                    print(f"[SCORE] Отримано {objection_score} балів за заперечення (знайдено в тексті)")
                                    break

                    # 🔴 ГАРАНТОВАНЕ ОБМЕЖЕННЯ 0-6
                    if objection_score > 6:
                        print(f"[WARNING] GPT повернув {objection_score} балів. Обмежуємо до 6")
                        objection_score = 6
                    elif objection_score < 0:
                        objection_score = 0

                    # Якщо все ще 0, спробуємо оцінити якість тексту
                    if objection_score == 0:
                        # Простий аналіз якості на основі ключових слів
                        positive_keywords = ["переконали", "переконливо", "аргументи", "відповів", "пояснив", "зрозуміло", "логічно"]
                        negative_keywords = ["не відповів", "незрозуміло", "непереконливо", "недостатньо", "погано", "слабко"]
                        
                        positive_count = sum(1 for word in positive_keywords if word in evaluation_text.lower())
                        negative_count = sum(1 for word in negative_keywords if word in evaluation_text.lower())
                        
                        if positive_count > negative_count:
                            objection_score = 4  # середній бал
                            print(f"[SCORE] Призначено {objection_score} балів на основі ключових слів")
                        elif positive_count == negative_count:
                            objection_score = 2  # низький бал
                        else:
                            objection_score = 0  # дуже низький бал

                    print(f"[SCORE] Фінальна оцінка аргументів: {objection_score}/6 балів")

                    analysis_match = re.search(r"АНАЛІЗ_ЗАПЕРЕЧЕННЯ:\s*(.+?)(?=ПОРАДИ_ЗАПЕРЕЧЕННЯ:|$)", evaluation_text, re.DOTALL)
                    advice_match = re.search(r"ПОРАДИ_ЗАПЕРЕЧЕННЯ:\s*(.+)", evaluation_text, re.DOTALL)

                    stage4_analysis = analysis_match.group(1).strip() if analysis_match else "Аналіз недоступний"
                    stage4_advice = advice_match.group(1).strip() if advice_match else "Поради недоступні"

                    # Фінальна репліка клієнта на основі балів
                    if objection_score >= 6:
                        client_final_reply = "Чудово! Ви мене повністю переконали. Пакуйте!"
                    elif objection_score >= 5:
                        client_final_reply = "Добре, ви мене переконали. Пакуйте!"
                    elif objection_score >= 4:
                        client_final_reply = "Гаразд, беру. Пакуйте!"
                    elif objection_score >= 3:
                        client_final_reply = "Ну що ж, давайте. Пакуйте."
                    elif objection_score >= 2:
                        client_final_reply = "Ой, ладно, пакуйте. Але я ще сумніваюся."
                    elif objection_score >= 1:
                        client_final_reply = "Дякую, але я ще подумаю. Можливо, зателефоную."
                    else:
                        client_final_reply = "Дякую, я ще подумаю. До побачення."

                    session['objection_score'] = objection_score

                    print(f"[STAGE1_ANALYSIS] Аналіз виявлення потреб: {stage1_analysis}")
                    print(f"[STAGE3_ANALYSIS] Аналіз презентації: {stage3_analysis}")
                    print(f"[STAGE4_ANALYSIS] Аналіз заперечень: {stage4_analysis}")

                    # Додаємо фінальну репліку клієнта до логу
                    session['conversation_log'].append({
                        'role': 'assistant',
                        'message': client_final_reply,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })

                    # Розрахунок загального балу - ТЕПЕР МАКСИМУМ 30 БАЛІВ
                    model_score = min(session.get("model_score", 0), 6)  # обмежуємо 6
                    questions_score = min(sum(q["score"] for q in session.get("question_scores", [])), 8)  # обмежуємо 8
                    answers_score = min(sum(a.get("score", 0) for a in session.get("user_answers", {}).values()), 10)  # обмежуємо 10
                    objection_score = min(session.get('objection_score', 0), 6)  # обмежуємо 6
                    total_score = model_score + questions_score + answers_score + objection_score

                    print("\n=== ФІНАЛЬНИЙ РАХУНОК ===")
                    print(f"[SCORE] За модель: {model_score}/6")
                    print(f"[SCORE] За питання: {questions_score}/8")
                    print(f"[SCORE] За відповіді: {answers_score}/10")
                    print(f"[SCORE] За заперечення: {objection_score}/6")
                    print(f"[SCORE] ЗАГАЛЬНИЙ БАЛ: {total_score}/30")

                    if total_score >= 26:
                        summary_label = "🟢 Чудова консультація."
                    elif total_score >= 22:
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