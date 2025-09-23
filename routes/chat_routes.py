from flask import Blueprint, request, jsonify, render_template, session
from datetime import datetime
import random, re, os
from config import client
from services.session_service import init_conversation, get_situation_from_session
from services.report_service import generate_report, send_email_report
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

        # --- Stage 1: Питання клієнта ---
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

        # --- Далі йде твоя логіка оцінки питання ---
        question_score = evaluate_question(user_input, session["situation"]["description"])
        
        # Перевірка на дублікати
        is_duplicate = user_input.lower() in [q.lower() for q in session["unique_questions"]]
        if is_duplicate:
            question_score = max(0, question_score - 1)
            print(f"[SCORE] Повторне питання: оцінка знижена до {question_score} балів")
        
        print(f"[SCORE] Оцінка питання: {question_score} бал(и) | Поточний рахунок: {session.get('total_score', 0)}")
        
        session["question_scores"].append({
            "question": user_input,
            "score": question_score
        })
        
        session["question_count"] += 1
        
        if question_score == 0:
            session["misunderstood_count"] += 1
        
        if not is_duplicate and question_score > 0:
            session["unique_questions"].append(user_input)
        
        # Бонус
        perfect_questions = sum(1 for q in session["question_scores"] if q["score"] == 2)
        if perfect_questions >= 3 and "bonus_added" not in session:
            session["total_score"] = min(session.get("total_score", 0) + 2, 8)
            session["bonus_added"] = True
            print(f"[SCORE] Бонус +2 бали за 3 коректних запитання")
        
        if session["misunderstood_count"] >= 3:
            session["chat_active"] = False
            report_content = generate_report(session)
            send_email_report(
                subject=f"Звіт про діалог — {session.get('seller_name', 'Продавець')}",
                body=report_content,
                to_email="voloshchenko2014@gmail.com"
            )
            return jsonify({
                "reply": "Ви поставили декілька некоректних питань. Діалог завершено.",
                "chat_ended": True,
                "show_restart_button": True
            })
        
        if question_score == 0:
            return jsonify({
                "reply": "Ваше питання не стосується вибору інструменту. Спробуйте інше питання.",
                "chat_ended": False,
                "question_progress": session["question_count"]
            })
        
        current_questions_score = sum(q["score"] for q in session["question_scores"])
        current_questions_score = min(current_questions_score, 8)
        print(f"[SCORE] Загальний бал за питання: {current_questions_score}/8")
        
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
                max_tokens=150
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
                "show_model_button": session["question_count"] >= 1
            })
        except Exception as e:
            return jsonify({
                "reply": "Вибачте, сталася помилка при відповіді. Спробуйте ще раз.",
                "chat_ended": False
            })

    # --- Stage 2: Вибір моделі ---
    elif session["stage"] == 2:
        user_model = re.sub(r'[^A-Z0-9-]', '', user_input.upper())
        matched_models = [m for m in session["available_models"] if user_model in m.upper()]

        if not matched_models:
            session["model_score"] = 0
            session["wrong_model_attempts"] += 1
            session["stage"] = 3
            return jsonify({
                "reply": "Ця модель не підходить для моїх потреб. Давайте продовжимо.",
                "chat_ended": False,
                "stage": 3,
                "model_chosen": False
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
            session["model_score"] = 6  # Максимум 6 балів за правильний вибір
            print(f"[SCORE] Правильна модель: +6 балів")
        else:
            session["model_score"] = 0
            print(f"[SCORE] Неправильна модель: 0 балів")

            # Оновлений вивід для переходу на stage 3
            print(f"[SCORE] Поточний бал за модель: {session['model_score']}/6")
            print(f"[SCORE] Загальний бал: {session.get('total_score', 0) + session['model_score']}")

        # Переходь на stage 3 після оцінки моделі
        session["model"] = user_model
        session["stage"] = 3
        session["current_question_index"] = 0
        session["user_answers"] = {}

        # Генерація уточнюючих питань
        prompt = f"""Ти клієнт, який обрав інструмент {user_model} для {session['situation']['description']}.\n
        Згенеруй 5 питань про **характеристики**, **зовнішню будову**, **функції цього інструменту**, додаткові витратні матеріали до інструменту. Питання має бути в одне речення."""

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
                'message': f"Добре, {user_model} виглядає непогано. А таке питання:\n\n{first_question}",
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            session.modified = True

            return jsonify({
                "reply": f"Добре, {user_model} виглядає непогано. А таке питання:\n\n{first_question}",
                "chat_ended": False,
                "stage": 3
            })
        except Exception as e:
            return jsonify({
                "reply": "Вибачте, сталася помилка при генерації питань. Спробуйте ще раз.",
                "chat_ended": False
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

        # Оцінка відповіді
        gpt_prompt = f"""
Оціни відповідь користувача на питання.
Питання: "{current_question}"
Відповідь: "{user_input}"

Оціни відповідь продавця за цією шкалою:

2 — відповідь містить **характеристику** і перевагу: що вона означає або як допомагає клієнту у задачі
1 — відповідь містить **лише характеристику** без жодного пояснення, без жодного коментаря
0 — відповідь **не по темі** або **занадто загальна**

Відповідай лише цифрою: 0, 1 або 2.
"""
        try:
            evaluation = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ти оцінюєш відповідь на запитання. Відповідай лише числом: 0, 1 або 2."},
                    {"role": "user", "content": gpt_prompt}
                ],
                temperature=0,
                max_tokens=10
            )
            score_text = evaluation.choices[0].message.content.strip()
            try:
                score = int(score_text)
            except ValueError:
                score = 0
            print(f"[SCORE] Відповідь на питання {session['current_question_index']+1}: {score}/2 балів")

            # Зберігаємо відповідь
            session["user_answers"][current_question] = {
                "answer": user_input,
                "score": score
            }

            # 🔴 Лічильник двох поспіль нерелевантних відповідей
            if score == 0:
                session['irrelevant_answers'] = session.get('irrelevant_answers', 0) + 1
            else:
                session['irrelevant_answers'] = 0  # скидаємо лічильник при нормальній відповіді

            if session['irrelevant_answers'] >= 2:
                session['chat_active'] = False
                report_content = generate_report(session)  # Зберегти звіт навіть при помилці
                send_email_report(
                    subject=f"Звіт про діалог — {session.get('seller_name', 'Продавець')}",
                    body=report_content,
                    to_email="voloshchenko2014@gmail.com"
                )
                return jsonify({
                    "reply": "Вибачте, я не отримав потрібної інформації. Я, мабуть, піду в інший магазин.",
                    "chat_ended": True,
                    "show_restart_button": True
                })

            # Продовжуємо діалог
            raw_score = sum(a["score"] for a in session["user_answers"].values())
            max_answers_score = len(session["generated_questions"]) * 2
            current_answers_score = min(raw_score, 6)
            print(f"[SCORE] Загальний бал за відповіді: {current_answers_score}/6")

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
                    "chat_ended": False
                })
            else:
                # Перехід до Stage 4 (заперечення)
                session["stage"] = 4
                answers_score = sum(a["score"] for a in session["user_answers"].values())

                if answers_score >= 5:
                    feedback = "Гарний інструмент."
                elif answers_score >= 3:
                    feedback = "Інструмент непоганий."
                else:
                    feedback = "Зрозуміло."

                category = session.get("current_category", "default")
                objections = CATEGORY_OBJECTIONS.get(category, CATEGORY_OBJECTIONS["default"])
                session["current_objection"] = random.choice(objections)
                session["objection_round"] = 1

                final_reply = f"{feedback}\n\nХм... {session['current_objection']}"
                session["history"].append({"role": "assistant", "content": final_reply})
                session.modified = True

                return jsonify({
                    "reply": f"{feedback}\n\nХм... {session['current_objection']}",
                    "chat_ended": False,
                    "stage": 4
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

        if current_round <= 2:
            try:
                history = "\n".join([f"Раунд {i+1}: {reply}" for i, reply in enumerate(session["seller_replies"])])
                gpt_prompt = f"""
    Ти — клієнт, який має заперечення: "{objection}".

    Ось як продавець відповідав до цього моменту:
    {history}

    Відповідай як реалістичний клієнт. Реагуй природно на останню репліку продавця: "{seller_reply}".
    Підтримуй контекст заперечення. Твоя відповідь повинна складатися рівно з одного речення. Не повторюйся."""
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Ти — клієнт у діалозі з продавцем. Відповідай чесно, логічно і згідно з контекстом заперечення. Твоя відповідь повинна складатися рівно з одного речення. Не повторюйся."},
                        {"role": "user", "content": gpt_prompt}
                    ],
                    temperature=0.6,
                    max_tokens=50
                )
                reply = response.choices[0].message.content
                session["objection_round"] += 1
                session.modified = True

                session['conversation_log'].append({
                    'role': 'user',
                    'message': seller_reply,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                session['conversation_log'].append({
                    'role': 'assistant',
                    'message': reply,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                return jsonify({
                    "reply": reply,
                    "chat_ended": False,
                    "current_round": session["objection_round"]
                })
            except Exception as e:
                return jsonify({
                    "reply": "Вибачте, сталася помилка під час відповіді. Спробуйте ще раз.",
                    "chat_ended": False
                })

        elif current_round == 3:
            try:
                if not session.get("seller_replies"):
                    return jsonify({
                        "reply": "Помилка: відсутні відповіді для оцінювання.",
                        "chat_ended": True,
                        "show_restart_button": True
                    })

                full_history = "\n".join([f"Раунд {i+1}: {reply}" for i, reply in enumerate(session["seller_replies"])])
                evaluation_prompt = f"""
    Ти — експерт з продажів, який оцінює відповіді продавця на заперечення клієнта.

    Заперечення клієнта: "{objection}"

    Ось відповіді продавця (по раундах):
    {full_history}

    Проаналізуй відповіді продавця за 4 критеріями:
    1. Чіткість аргументів
    2. Відповідність запереченню
    3. Наявність доказів, прикладів або логіки
    4. Логічна послідовність і побудова

    Аргумент — це чітке пояснення з доказом, прикладом або логікою, яке прямо стосується заперечення.

    🔻 Оціни рівень переконливості за шкалою:
    - "переконливо" — якщо **аргументи є чіткими та логічними** 
    - "частково переконливо" — якщо **аргументи слабкі, але відповідають на запит** 
    - "непереконливо" — якщо **немає** жодного аргументу або відповідь не по темі

    Відповідай одним словом: "переконливо", "частково переконливо" або "непереконливо". Не додавай пояснень.
    """
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Ти — експерт з оцінки комунікацій. Будь об'єктивним."},
                        {"role": "user", "content": evaluation_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=50
                )
                raw_rating = response.choices[0].message.content.strip().lower()

                # Витягнути перше зі слів: переконливо, частково переконливо, непереконливо
                match = re.search(r"(переконливо|частково переконливо|непереконливо)", raw_rating)
                rating = match.group(1) if match else "непереконливо"
                
                if rating == "переконливо":
                    objection_score = 10
                    reply = "Клієнта проконсультовано."
                elif rating == "частково переконливо":
                    objection_score = 5
                    reply = "Клієнта проконсультовано."
                elif rating == "непереконливо":
                    objection_score = 0
                    reply = "Клієнт незадоволений консультацією."
                else:
                    objection_score = 0
                    reply = "Клієнт незадоволений консультацією."  # fallback

                session['objection_score'] = objection_score

                print(f"[SCORE] Оцінка аргументів: {rating} ({objection_score} балів)")

                # Додаємо фінальну відповідь системи
                session['conversation_log'].append({
                    'role': 'assistant',
                    'message': reply,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                model_score = session.get("model_score", 0)
                questions_score = sum(q["score"] for q in session.get("question_scores", []))
                answers_score = sum(a["score"] for a in session.get("user_answers", {}).values())
                objection_score = session.get('objection_score', 0)
                total_score = model_score + questions_score + answers_score + objection_score
                max_score = 8 + 6 + 6 + 10

                print("\n=== ФІНАЛЬНИЙ РАХУНОК ===")
                print(f"[SCORE] За модель: {model_score}/6")
                print(f"[SCORE] За питання: {questions_score}/8")
                print(f"[SCORE] За відповіді: {answers_score}/6")
                print(f"[SCORE] За заперечення: {objection_score}/10")
                print(f"[SCORE] ЗАГАЛЬНИЙ БАЛ: {total_score}/30")

                if total_score >= 24:
                    summary_label = "🟢 Чудова консультація."
                elif total_score >= 20:
                    summary_label = "🟡 Задовільна консультація."
                else:
                    summary_label = "🔴 Незадовільна консультація."

                full_reply = f"{reply}\n\n📊 Результат: {summary_label}"

                # Збереження звіту
                session["total_score"] = total_score
                report_content = generate_report(dict(session))
                report_filename = f"report_{session.get('seller_name', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                
                os.makedirs('reports', exist_ok=True)
                
                send_email_report(
                    subject=f"Звіт про діалог — {session.get('seller_name', 'Продавець')}",
                    body=report_content,
                    to_email="voloshchenko2014@gmail.com"
                )

                session.clear()
                session.modified = True

                return jsonify({
                    "reply": f"{full_reply}\n\nЗвіт збережено для вашого тренера.",
                    "chat_ended": True,
                    "show_restart_button": True,
                    "report_filename": report_filename
                })
            
            except Exception as e:
                print(f"Помилка при оцінюванні: {str(e)}")
                return jsonify({
                    "reply": "Вибачте, не вдалося обробити відповідь. Давайте спробуємо ще раз?",
                    "chat_ended": False
                })

    return jsonify({
        "reply": "Виникла непередбачена помилка. Спробуйте ще раз.",
        "chat_ended": True,
        "show_restart_button": True
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