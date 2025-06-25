import openai
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
import os
import random
import re

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

openai.api_key = os.getenv("OPENAI_API_KEY")
MODEL_ENGINE = "gpt-3.5-turbo"

SITUATIONS = [
  {
    "id": 11,
    "description": "Монтаж розеток та дрібна електрика",
    "requirements": "компактний, акумуляторний шуруповерт із точною регуляцією",
    "correct_model": "CD-201HBC",
    "wrong_models": ["CD-12QX", "CD-200BC", "CD-218Q"],
    "hints": [
      "Я використовую шуруповерт для встановлення розеток і підключення дрібної електрики",
      "Потрібно щось дуже точне, щоб не зірвати різьбу",
      "Часто працюю у вузьких нішах",
      "Головне — компактність і контроль обертів",
      "Потужність не головне, важлива точність"
    ]
  },
  {
    "id": 12,
    "description": "Установка меблів у салоні краси",
    "requirements": "акумуляторний, легкий шуруповерт із кейсом",
    "correct_model": "CD-201HBC",
    "wrong_models": ["CD-12QX", "CD-200BC", "CD-218Q"],
    "hints": [
      "Я майстер, встановлюю меблі в салонах — клієнти дивляться на інструмент",
      "Хочу, щоб шуруповерт виглядав охайно",
      "Кейс — це зручно для транспортування",
      "Бажано, щоб був легкий і не шумний",
      "Не потрібна велика потужність, але важлива акуратність"
    ]
  },
  {
    "id": 13,
    "description": "Робота з ПВХ-панелями та легкими матеріалами",
    "requirements": "акумуляторний шуруповерт з мінімальною вагою та плавним запуском",
    "correct_model": "CD-201HBC",
    "wrong_models": ["CD-12QX", "CD-200BC", "CD-218Q"],
    "hints": [
      "Я кріплю ПВХ-панелі, які легко пошкодити",
      "Шуруповерт має бути дуже акуратним",
      "Мінімальна вага — це ключовий фактор",
      "Плавний пуск — обов’язково",
      "Дуже чутливі матеріали — потрібен контроль"
    ]
  },
  {
    "id": 14,
    "description": "Шуруповерт для автосервісу",
    "requirements": "надійний, з LED-підсвіткою, акумулятор на довгий час",
    "correct_model": "CD-201HBC",
    "wrong_models": ["CD-12QX", "CD-200BC", "CD-218Q"],
    "hints": [
      "Я використовую інструмент у моторному відсіку",
      "Часто темно — тому потрібна підсвітка",
      "Іноді потрібно крутити металеві панелі — має тягнути",
      "Зручно, коли акумулятор тримає довго",
      "Шуруповерт повинен бути витривалим"
    ]
  }
]

TOOL_MODELS = [
    "CD-12QX",
    "CD-200BC",
    "CD-201HBC",
    "CD-218Q"
]

UNACCEPTABLE_BEHAVIOR_PROMPT = """
Якщо користувач пише матюки та слова, які є недопустими при спілкуванні з клієнтами, 
ти маєш право завершити діалог. Приклад відповіді:
"я вас не зрозумів"
Після цього заверши діалог.
"""
RELEVANT_KEYWORDS = [
    "роб", "завдан", "акумулятор", "діамет", "метал", "задач", "мережев", "прац", "як", "чому", "чи", "який", "яка", "яке",
    "дерево", "бетон", "насадки", "режим", "крутний", "момент", "потужн", "прац", "компак", "свер"
]

def is_relevant_question(text):
    return any(keyword in text for keyword in RELEVANT_KEYWORDS)

def is_question(message):
    return "?" in message or message.strip().lower().startswith(("прац", "як", "чому", "чи", "який", "яка", "яке", "роб", "завдан", "акумулятор", "діамет", "метал", "задач", "мережев",
    "дерево", "матер", "насадки", "режим", "крутний", "момент", "потужн", "буд", "свер"))

def init_conversation():
    selected_situation = random.choice(SITUATIONS)
    session['situation'] = selected_situation
    session['current_situation_id'] = selected_situation["id"]
    session['available_models'] = TOOL_MODELS  # Показуємо всі
    session['stage'] = 1
    session['chat_active'] = True
    session['message_count'] = 0
    session['wrong_model_attempts'] = 0 
    session['question_count'] = 0

    system_prompt = f"""
    Ти — віртуальний **клієнт магазину**, який **прийшов купити шуруповерт**.  
    Твоя **єдина мета** — **отримати потрібну інформацію для покупки** згідно твоєї ситуації.
    Не висвітлюй ситуацію повністю. Користувач ставить питання – ти **відповідаєш**. 
    Ти **не є консультантом**, **не допомагаєш** користувачу, **не пропонуєш моделі**, **не ставиш зустрічних запитань**.
    Ти не є консультантом. Ти клієнт, який хоче дізнатися все необхідне про інструмент, щоби прийняти рішення про покупку.  
    Ти уточнюєш деталі, висловлюєш свої вимоги. 

    Твоя ситуація: {selected_situation['description']}
    Твої потреби: {selected_situation['requirements']}

    {UNACCEPTABLE_BEHAVIOR_PROMPT}

    Поведінка:
    - Якщо користувач грубий або використовує лайливу лексику — завершуй діалог фразою "Я Вас не зрозумів"
    - В іншому випадку — задавай додаткові запитання або висловлюй свою думку.

    Починай розмову нейтрально:  
    "Добрий день, мені потрібен шуруповерт."
    """

    return [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": "Добрий день, мені потрібен шуруповерт."}
    ]

@app.route('/')
def home():
    if "unique_questions" not in session:
        session["unique_questions"] = []
    return render_template('index.html')

@app.route('/start_chat')
def start_chat():
    session['history'] = init_conversation()
    # Якщо треба, скинь інші параметри
    session["stage"] = 1
    session["question_count"] = 0
    session["model"] = None
    session["chat_active"] = True
    session["unique_questions"] = []
    return jsonify({"reply": session['history'][1]['content']})

@app.route("/restart-chat", methods=["POST"])
def restart_chat():
    keys_to_clear = ["history", "stage", "question_count", "model", "chat_active", "unique_questions", "misunderstood_count", "available_models"]
    for key in keys_to_clear:
        session.pop(key, None)
    return jsonify({"message": "Сесію скинуто."})

def match_model(user_input, available_models):
    return user_input.strip().upper() in [m.strip().upper() for m in available_models]

@app.route("/chat", methods=["POST"])
def chat():
    print("Доступні моделі для вибору:", session.get("available_models"))
    user_input = request.json.get("message", "").strip()

    session.setdefault("misunderstood_count", 0)
    session.setdefault("objection_round", 1)

    if "history" not in session or not session["history"]:
        session["history"] = init_conversation()
        session["stage"] = 1
        session["question_count"] = 0
        session["model"] = None
        session["chat_active"] = True
        session["unique_questions"] = []
        session["misunderstood_count"] = 0
        session["wrong_model_attempts"] = 0
        session["user_answers"] = {}

    # --- Обробка етапу вибору моделі ---
    if session["stage"] == 2:
        user_model = re.sub(r'[^A-Z0-9-]', '', user_input.upper())
        matched_models = [m for m in session["available_models"] if user_model in m.upper()]
        index = session.get('current_question_index', 0)

        if not matched_models:
            session["wrong_model_attempts"] += 1
            if session["wrong_model_attempts"] >= 2:
                session["chat_active"] = False
                return jsonify({
                    "reply": "Ви двічі ввели некоректну модель. Завершую діалог.",
                    "chat_ended": True,
                    "show_restart_button": True
                })
            return jsonify({
                "reply": f"Ви обрали «{user_input}», але цієї моделі немає в списку. Спробуйте ще раз.",
                "chat_ended": False,
                "show_models": True,
                "models": session["available_models"],
                "attempts_left": 2 - session["wrong_model_attempts"]
            })

        user_model = matched_models[0].upper()
        current_situation = next((s for s in SITUATIONS if s["id"] == session.get("current_situation_id")), None)
        if not current_situation:
            return jsonify({"reply": "Помилка: ситуація не знайдена", "chat_ended": True})

        correct_model = current_situation["correct_model"].upper()

        if user_model == correct_model:
            session["model"] = user_model
            session["stage"] = 3
            session["current_question_index"] = 0
            session["user_answers"] = {}

            prompt = f"""Ти клієнт, який обрав шуруповерт {user_model} для {session['situation']['description']}.
            Згенеруй 3 питання про **крутний момент**, **будову** та функції цього шуруповерта."""

            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Ти — клієнт, який має задати уточнюючі запитання про модель інструмента."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.6,
                    max_tokens=200
                )
                content = response.choices[0].message.get("content", "")
                questions = [line.strip(" 1234567890.-") for line in content.split('\n') if line.strip()]
                session["generated_questions"] = questions
                session.modified = True

                first_question = questions[0] if questions else "Яке перше ваше питання про цю модель?"

                return jsonify({
                    "reply": f"Добре, модель {user_model} мені підходить. Зараз задам кілька уточнюючих питань по черзі.\n\n{first_question}",
                    "chat_ended": False,
                    "stage": 3
                })
            except Exception as e:
                return jsonify({
                    "reply": "Вибачте, сталася помилка при генерації питань. Спробуйте ще раз.",
                    "chat_ended": False
                })

        else:
            session["wrong_model_attempts"] += 1
            if session["wrong_model_attempts"] >= 2:
                session["chat_active"] = False
                return jsonify({
                        "reply": "На жаль, ви двічі обрали неправильну модель. Завершую діалог.",
                        "show_restart_button": True,
                        "chat_ended": True
                    })

    elif session["stage"] == 3:
        if 'generated_questions' not in session or not session['generated_questions']:
            return jsonify({
                "reply": "Питання не знайдені. Давайте почнемо спочатку.",
                "chat_ended": True,
                "show_restart_button": True
            })

        index = session.get('current_question_index', 0)
        current_question = session['generated_questions'][index]

        # GPT-перевірка: чи по темі відповідь
        gpt_prompt = f"Питання: '{current_question}'\nВідповідь: '{user_input}'\n\nЧи стосується ця відповідь суті питання? Відповідай тільки 'так' або 'ні'."

        try:
            validation = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ти перевіряєш відповідність відповіді суті питання. Відповідай лише 'так' або 'ні'."},
                    {"role": "user", "content": gpt_prompt}
                ],
                temperature=0,
                max_tokens=50
            )
            is_relevant = validation.choices[0].message["content"].strip().lower()

            if is_relevant != "так":
                session["off_topic_count"] = session.get("off_topic_count", 0) + 1
                if session["off_topic_count"] >= 2:
                    session["chat_active"] = False
                    return jsonify({
                        "reply": "Ви двічі надали відповідь не по темі. Діалог завершено.",
                        "chat_ended": True,
                        "show_restart_button": True
                    })
                else:
                    return jsonify({
                        "reply": f"Здається, ця відповідь не зовсім по темі. {current_question}",
                        "chat_ended": False
                    })

            # Якщо відповідь по темі — скидаємо лічильник
            session["off_topic_count"] = 0
            session.setdefault('user_answers', {})[current_question] = user_input
            session['current_question_index'] += 1

            if session['current_question_index'] < len(session['generated_questions']):
                next_question = session['generated_questions'][session['current_question_index']]
                return jsonify({
                    "reply": next_question,
                    "chat_ended": False
                })
            else:
                session["stage"] = 4
                session["chat_active"] = True
                objections = [
                    "Мені здається, це трохи дорогувато.",
                    "А це точно не якась китайська модель?",
                    "Ваша гарантія точно працює?",
                    "Я бачив в інтернеті дешевше."
                ]
                chosen_objection = random.choice(objections)
                session["current_objection"] = chosen_objection
                return jsonify({
                    "reply": f"Хм... {chosen_objection}",
                    "chat_ended": False,
                    "stage": 4
                })

        except Exception as e:
            return jsonify({
                "reply": "Виникла помилка при перевірці відповіді. Спробуйте ще раз.",
                "chat_ended": False
            })

    # --- Обробка заперечення (stage 4) ---
    elif session["stage"] == 4:
        objection = session.get("current_objection", "Заперечення")
        seller_reply = user_input

    # --- Перший раунд: GPT генерує уточнення або сумнів ---
        if session["objection_round"] == 1:
            gpt_prompt = f"Клієнт сказав: '{objection}'. Продавець відповів: '{seller_reply}'. Напиши коротку відповідь клієнта, яка містить сумнів або уточнення, без остаточного рішення."

            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Ти — клієнт магазину інструментів. Твоя мета — сформулювати ввічливий сумнів або уточнення після відповіді продавця на заперечення."},
                        {"role": "user", "content": gpt_prompt}
                    ],
                    temperature=0.5,
                    max_tokens=100
                )

                reply = response.choices[0].message["content"].strip()
                session["objection_round"] = 2
                session["last_seller_reply"] = seller_reply

                return jsonify({
                    "reply": reply,
                    "chat_ended": False
                })
            except Exception as e:
                return jsonify({
                    "reply": "Помилка при формуванні уточнення. Спробуйте ще раз.",
                    "chat_ended": False
                })

    # --- Другий раунд: GPT оцінює остаточно ---
        elif session["objection_round"] == 2:
            seller_reply_full = session["last_seller_reply"] + " " + seller_reply
            gpt_prompt = (
                f"Клієнт сказав: '{objection}'. Продавець відповів: '{seller_reply_full}'. "
                "Ти — клієнт, який висловив заперечення. Якщо продавець відповів логічно, аргументовано і хоча б частково розвіяв сумнів — "
                "напиши лише слово «переконливо». Якщо відповідь нечітка або не містить нічого корисного — напиши «непереконливо». "
            )

            try:
                result = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": (
                            "Ти — клієнт, який висловив заперечення. Якщо продавець відповів логічно, аргументовано "
                            "Якщо відповідь містить хоч один вагомий аргумент — вважай її переконливою. Навіть якщо аргумент простий, але логічний, напиши «переконливо»."
                            "Якщо відповідь зовсім не відповідає на заперечення, напиши «непереконливо»."
                        )},
                        {"role": "user", "content": gpt_prompt}
                    ],
                    temperature=0.6,
                    max_tokens=40
                )

                rating = result.choices[0].message["content"].strip().lower()
                print(f"Оцінка GPT: '{rating}'")  # Для дебагу

                session["chat_active"] = False
                session["objection_round"] = 1  # обнуляємо для наступного запуску

                if "переконливо" in rating:
                    reply = "Дякую, ви мене переконали! Я готовий зробити покупку."
                else:
                    reply = "На жаль, ви мене не переконали. Завершую діалог."

                return jsonify({
                    "reply": reply,
                    "chat_ended": True,
                    "show_restart_button": True
                })

            except Exception as e:
                return jsonify({
                    "reply": "Сталася помилка при оцінці відповіді. Спробуйте ще раз.",
                    "chat_ended": False
                })


    # --- Стандартна логіка для stage 1 ---
    session["history"].append({"role": "user", "content": user_input})
    session["history"] = [session["history"][0]] + session["history"][-8:]

    try:
        if session["stage"] == 1 and is_question(user_input):
            normalized = user_input.lower()
            if normalized not in set(session["unique_questions"]) and is_relevant_question(normalized):
                session["unique_questions"].append(normalized)
                session["question_count"] += 1

        response = openai.ChatCompletion.create(
            model=MODEL_ENGINE,
            messages=session["history"],
            temperature=0.3,
            max_tokens=300
        )
        assistant_reply = response.choices[0].message["content"]
        session["history"].append({"role": "assistant", "content": assistant_reply})

        if "я вас не зрозумів" in assistant_reply.lower():
            session["misunderstood_count"] += 1
            if session["misunderstood_count"] >= 3:
                keys_to_clear = [
                    "history", "stage", "question_count", "model", "chat_active",
                    "unique_questions", "misunderstood_count", "wrong_model_attempts",
                    "user_answers", "generated_questions", "current_question_index"
                ]
                for key in keys_to_clear:
                    session.pop(key, None)

                return jsonify({
                    "reply": "Клієнт Вас не зрозумів. Спробуйте знову!",
                    "chat_ended": True,
                    "show_restart_button": True
                })
        else:
            session["misunderstood_count"] = 0

        show_models = False
        model_message = None
        if session["stage"] == 1 and session["question_count"] >= 5:
            session["stage"] = 2
            show_models = True
            model_message = "Оберіть одну з цих моделей:"

        return jsonify({
            "reply": assistant_reply,
            "chat_ended": False,
            "show_models": show_models,
            "models": session["available_models"],
            "second_message": model_message,
            "question_progress": session["question_count"],
            "stage": session["stage"]
        })

    except Exception as e:
        return jsonify({
            "reply": "Виникла помилка при генерації відповіді. Спробуйте ще раз.",
            "error": str(e)
        }), 500
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)