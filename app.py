import openai
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from datetime import datetime
import os
import random
import re
import smtplib
from email.mime.text import MIMEText
from flask_session import Session

app = Flask(__name__)

app.config['SESSION_TYPE'] = 'filesystem'  # Зберігаємо сесії на файловій системі
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
Session(app)

load_dotenv()

app.secret_key = os.getenv("FLASK_SECRET_KEY", "віртуальнийклієнт")
openai.api_key = os.getenv("OPENAI_API_KEY")
MODEL_ENGINE = "gpt-3.5-turbo"

SITUATIONS = [
    {
        "id": 1,
        "description": "шуруповерт для збірки меблів",
        "requirements": "легкий, зручний шуруповерт з хорошою ергономікою для тривалої роботи",
        "avatar": "id13.png",
        "behavior": "ставить професійні твердження",
        "correct_models": ["CD-12QX", "CD-12CX", "CD-12BC"],
        "wrong_models": ["CD-200BCULTRA", "CD-201HBC", "CD-218Q", "CD-200BCCOMPACT"],
        "hints": [
        "Мені потрібен саме 12V шуруповерт",
        "Збираю шафи й кухні, часто прямо у клієнта",
        "Тримаю інструмент у руках по кілька годин",
        "Важливо, щоб рука не втомлювалася",
        "Комфорт важливіший за потужність"
        ]
    },
    {
        "id": 2,
        "description": "шуруповерт для домашнього ремонту",
        "requirements": "недорогий та компактний шуруповерт для побутових задач",
        "avatar": "id8.png",
        "behavior": "агресивно відповідає",
        "correct_models": ["CD-12QX", "CD-12CX", "CD-12BC"],
        "wrong_models": ["CD-200BCULTRA", "CD-201HBC", "CD-218Q", "CD-200BCCOMPACT"],
        "hints": [
        "Шукаю 12V шуруповерт для дому",
        "Іноді треба повісити полицю або зібрати комод",
        "Не хочу переплачувати за потужність",
        "Ціную компактність і зручність",
        "Бюджет до 2000 грн"
        ]
    },
    {
        "id": 3,
        "description": "подарунок татові – шуруповерт",
        "requirements": "компактний, простий у використанні шуруповерт для базових робіт",
        "avatar": "id9.png",
        "behavior": "спокійно відповідає",
        "correct_models": ["CD-12QX", "CD-12CX", "CD-12BC"],
        "wrong_models": ["CD-200BCULTRA", "CD-201HBC", "CD-218Q", "CD-200BCCOMPACT"],
        "hints": [
        "Шукаю 12V шуруповерт як подарунок",
        "Батько іноді щось підкручує вдома або в гаражі",
        "Йому потрібен простий та надійний інструмент",
        "Без складних налаштувань",
        "Головне — щоб був легкий і зрозумілий"
        ]
    },
    {
        "id": 4,
        "description": "шуруповерт для ремонту електроніки, робота з дрібними кріпленнями ",
        "requirements": "максимальний контроль обертів і точність",
        "avatar": "id3.png",
        "behavior": "любить жарти",
        "correct_models": ["CD-12QX", "CD-12CX", "CD-12BC", "CD-218Q"],
        "wrong_models": ["CD-200BCULTRA", "CD-201HBC", "CD-200BCCOMPACT"],
        "hints": [
        "Мені точно потрібен 12V шуруповерт",
        "Працюю з дрібними гвинтами й електронікою",
        "Важлива точність і контроль, щоб нічого не зіпсувати",
        "Сильною потужністю можна нашкодити",
        "Працюю у вузьких місцях"
        ]
    },
    {
        "id": 5,
        "description": "КШМ для різання, шліфування та зачистки",
        "requirements": "мережева болгарка, висока потужність і зручність у роботі",
        "avatar": "6.png",
        "behavior": "переважно спокійний, іноді схильний до експериментів",
        "correct_models": ["GS-140SE", "GL-160SE", "GL-145S"],
        "wrong_models": ["GS-98", "GS-100S", "CG-12BC", "GL-125S", "DGA-201"],
        "hints": [
        "Мені точно потрібна мережева болгарка для шліфування металу",
        "Працюю з металом та шліфую великі поверхні",
        "Важлива висока потужність, продуктивність і надійність",
        "Треба болгарка на 125 мм діаметр диску",
        "Хочу надійно контролювати інструмент"
        ]
    },
    {
        "id": 6,
        "description": "болгарка для різки металу та арматури",
        "requirements": "маленька мережева болгарка, зручна рукоятка, регулювання обертів",
        "avatar": "id7.png",
        "behavior": "акуратний у роботі, але іноді потребує високої продуктивності",
        "correct_models": ["GS-98", "GS-100S"],
        "wrong_models": ["CG-12BC", "DGA-201", "GS-140SE", "GL-160SE", "GL-125S"],
        "hints": [
            "Потрібен інструмент для чистової обробки металу",
            "Важливо, щоб болгарка була компактна та зручна",
            "Працюю з тонким металом, тому потужність може бути невеликою",
            "Потрібна коротка ручка",
            "Диск 125 мм – ідеальний розмір для моїх задач"
        ]
    },
    {
        "id": 7,
        "description": "болгарка з регулятором для ремонтних робіт",
        "requirements": "надійна, потужна, з підтримкою обертів",
        "avatar": "id10.png",
        "behavior": "інтенсивне використання, але з дотриманням техніки безпеки",
        "correct_models": ["GS-140SE"],
        "wrong_models": ["GS-98", "GS-100S", "CG-12BC", "GL-125S", "DGA-201", "GL-160SE"],
        "hints": [
            "Часто ріжу арматуру, потрібна стійкість до навантажень",
            "Потрібна модель мережева з великою потужністю",
            "Важливо, щоб не перегрівалася при тривалій роботі",
            "125 мм діаметр диску - мені підходить",
            "Розглядаю моделі із короткою ручкою"
        ]
    },
    {
        "id": 8,
        "description": "проста болгарка додому",
        "requirements": "здатна виконувати прості завдання без жодних проблем",
        "avatar": "id1.png",
        "behavior": "дідусь",
        "correct_models": ["GS-98", "GS-100S", "GL-125S"],
        "wrong_models": ["CG-12BC", "DGA-201", "GS-140SE", "GL-160SE"],
        "hints": [
            "Шліфую зварні шви, ріжу арматуру в гаражі",
            "Треба недорога модель",
            "Краще з довгою ручкою, бо руки вже трохи не тримають",
            "125 мм діаметр диску ідеально підійде"
        ]
    },
    {
        "id": 9,
        "description": "акумуляторна болгарка для роботи під машиною",
        "requirements": "маленька акумуляторна болгарка для вузькоспеціалізованих завдань",
        "avatar": "id2.png",
        "behavior": "експерт з автомобілів",
        "correct_models": ["DGA-201", "CG-12BC"],
        "wrong_models": ["GS-98", "GS-100S", "GL-125S", "GS-140SE", "GL-160SE"],
        "hints": [
            "Потрібен інструмент максимально зручний та компактний",
            "працюю під машиною, важлива мобільність",
            "потрібен інструмент із короткою ручкою",
            "працюю лише з металом товщинами до 4 мм"
        ]
    },
    {
        "id": 10,
        "description": "легкий перфоратор для домашнього використання",
        "requirements": "компактний та недорогий перфоратор для роботи по дому",
        "avatar": "id5.png",
        "behavior": "красивий клієнт",
        "correct_models": ["DHR-200", "DHR-202BC"],
        "wrong_models": ["BH-30", "BH-20", "RH-16"],
        "hints": [
            "Шукаю перфоратор для нечастого домашнього використання",
            "Потрібно іноді просверлити отвір у стіні",
            "Важливо, щоб був легкий і не займав багато місця",
            "Не потрібен потужний професійний інструмент",
            "Бюджет до 3000 грн"
        ]
    },
    {
        "id": 11,
        "description": "перфоратор для дрібного ремонту",
        "requirements": "акумуляторний перфоратор з режимом удару",
        "avatar": "id4.png",
        "behavior": "заляканий клієнт",
        "correct_models": ["DHR-201BC"],
        "wrong_models": ["RH-100", "BH-14S", "BH-30", "RH-12Q", "RH-16"],
        "hints": [
            "Потрібен перфоратор для дрібних ремонтних робіт",
            "Важливо мати режим руйнування для демонтажних робіт",
            "Шукаю безщітковий двигун для довговічності",
            "Потрібна балансована потужність",
            "Бюджет до 4000 грн"
        ]
    },
    {
        "id": 12,
        "description": "перфоратор для регулярного використання",
        "requirements": "потужний та зручний перфоратор для частого використання",
        "avatar": "id12.png",
        "behavior": "клієнт-задрот",
        "correct_models": ["DHR-202BC", "DHR-201BC"],
        "wrong_models": ["DHR-200", "RH-100", "BH-30", "RH-12Q", "RH-16"],
        "hints": [
            "Шукаю перфоратор для регулярних ремонтних робіт",
            "Важлива антивібраційна система для комфортної роботи",
            "Потрібна більша ударна сила ніж у базових моделей",
            "Бочкова конструкція для кращого балансу",
            "Готовий заплатити за якість"
        ]
    },
    {
        "id": 13,
        "description": "бюджетний прямий перфоратор",
        "requirements": "недорогий та надійний прямий перфоратор",
        "avatar": "id13.png",
        "behavior": "смішний клієнт",
        "correct_models": ["RH-100", "RH-12Q"],
        "wrong_models": ["DHR-202BC", "BH-20", "BH-30", "DHR-200", "BH-14S"],
        "hints": [
            "Потрібен простий і надійний перфоратор",
            "Важливо мати хорошу ударну силу за доступну ціну",
            "Кейс у комплекті - великий плюс",
            "Не потрібні додаткові функції",
            "Бюджет до 4500 грн"
        ]
    },
    {
        "id": 14,
        "description": "універсальний прямий перфоратор",
        "requirements": "перфоратор з додатковими можливостями для різних задач",
        "avatar": "id14.png",
        "behavior": "клієнт-слюсар",
        "correct_models": ["RH-12Q"],
        "wrong_models": ["RH-100", "DHR-200", "BH-14S", "BH-30", "RH-16"],
        "hints": [
            "Шукаю перфоратор, який може і сверлити, і працювати як перфоратор",
            "Додатковий патрон для свердел - важлива функція",
            "Потрібна гарна ударна сила",
            "Хочу щоб йшов у кейсі",
            "Готовий заплатити за додаткові можливості"
        ]
    },
    {
        "id": 15,
        "description": "професійний прямий перфоратор",
        "requirements": "найпотужніший прямий перфоратор для складних задач",
        "avatar": "id15.png",
        "behavior": "програміст",
        "correct_models": ["RH-16"],
        "wrong_models": ["DHR-200", "RH-100", "DHR-201BC", "BH-14S", "RH-12Q"],
        "hints": [
            "Потрібен найпотужніший прямий перфоратор",
            "Виконую професійні ремонтні роботи",
            "Важлива максимальна ударна сила",
            "Кейс у комплекті - обов'язково",
            "Ціна не головний критерій"
        ]
    },
    {
        "id": 16,
        "description": "універсальний бочковий перфоратор",
        "requirements": "балансований перфоратор для різних видів робіт",
        "avatar": "id10.png",
        "behavior": "людина-настрій",
        "correct_models": ["BH-14S", "BH-20"],
        "wrong_models": ["DHR-200", "RH-100", "BH-30", "RH-100"],
        "hints": [
            "Шукаю універсальний перфоратор для різних задач",
            "Важлива антивібраційна система",
            "Потрібен окремий регулятор обертів",
            "Бочкова конструкція для зручності",
            "Готовий заплатити за якість"
        ]
    },
    {
        "id": 17,
        "description": "потужний професійний перфоратор",
        "requirements": "перфоратор для інтенсивного професійного використання",
        "avatar": "id1.png",
        "behavior": "клієнт-професіонал",
        "correct_models": ["BH-20", "BH-30"],
        "wrong_models": ["DHR-200", "RH-100", "DHR-201BC", "RH-16"],
        "hints": [
            "Потрібен професійний інструмент для важких робіт",
            "Важливі додаткові функції як індикація зносу",
            "Потрібна висока ударна сила",
            "Виконую роботи щодня",
            "Ціна виправдана якістю"
        ]
    },
    {
        "id": 18,
        "description": "найпотужніший перфоратор для спецзавдань",
        "requirements": "перфоратор для найскладніших професійних задач",
        "avatar": "id2.png",
        "behavior": "клієнт-комунальник",
        "correct_models": ["BH-30"],
        "wrong_models": ["DHR-200", "RH-100", "DHR-201BC"],
        "hints": [
            "Потрібен найпотужніший перфоратор на ринку",
            "Виконую спеціальні професійні завдання",
            "Важливий патрон SDSMAX для важких навантажень",
            "Потрібна максимальна ударна сила",
            "Ціна не головне - потрібна продуктивність"
        ]
    },
    {
        "id": 19,
        "description": "потрібен компактний інвертор для роботи в тісних умовах",
        "requirements": "малий та легкий зварювальний апарат для періодичного використання",
        "avatar": "id11.png",
        "behavior": "клієнт-ремонтник",
        "correct_models": ["SAB-14DMINI"],
        "wrong_models": ["SAB-15DX", "M-16PW", "SAB-17DX", "M-20D"],
        "hints": [
            "Потрібен найменший інвертор для роботи в обмежених просторах",
            "Важливо, щоб була функція HOT START для легкого підпалу електрода",
            "Працюю з електродами до 4 мм",
            "Не потрібні додаткові функції, головне — компактність",
            "Потрібен недорогий варіант для нерегулярного використання"
        ]
    },
    {
        "id": 20,
        "description": "потрібен універсальний інвертор для різних видів зварювання",
        "requirements": "апарат з TIG-LIFT та зручним функціоналом",
        "avatar": "id16.png",
        "behavior": "клієнт-майстер на виробництві",
        "correct_models": ["SAB-15DX", "SAB-17DX"],
        "wrong_models": ["SAB-14DMINI", "M-18D", "M-20D", "M-16PW"],
        "hints": [
            "Потрібен інвертор із режимом TIG-LIFT для аргонного зварювання",
            "Важливі всі базові функції для комфортної роботи",
            "Працюю з різними типами металів",
            "Не потрібна максимальна потужність, головне — універсальність",
            "В комплекті повинні бути кабелі"
        ]
    },
    {
        "id": 21,
        "description": "потрібен надійний інвертор для роботи при низькій напрузі",
        "requirements": "апарат, який працює від 140 В і має хороший захист",
        "avatar": "id17.png",
        "behavior": "клієнт-електрик у сільській місцевості",
        "correct_models": ["M-16PW"],
        "wrong_models": ["SAB-14DMINI", "SAB-17DX", "M-18D", "M-20D"],
        "hints": [
            "Часто працюю там, де нестабільна напруга (низька або коливається)",
            "Потрібен яскравий дисплей для роботи на сонці",
            "Важлива захищеність від перегріву та перевантажень",
            "Працюю електродами до 4 мм",
            "Не потрібні складні функції, головне — стабільність"
        ]
    },
    {
        "id": 22,
        "description": "потрібен професійний інвертор для важких завдань",
        "requirements": "апарат для тривалої роботи з товстими металами",
        "avatar": "id18.png",
        "behavior": "клієнт-зварник на будівництві",
        "correct_models": ["SAB-17DX", "M-18D", "M-20D"],
        "wrong_models": ["SAB-14DMINI", "M-16PW", "SAB-15DX"],
        "hints": [
            "Потрібно варити електродами до 5 мм",
            "Важливий режим TIG-LIFT для якісного аргонного зварювання",
            "Працюю з товстими металами (5+ мм)",
            "Потрібна надійність при тривалому використанні",
            "Готовий платити за професійний інструмент"
        ]
    },
    {
        "id": 23,
        "description": "потрібен довговічний інвертор з гарантією",
        "requirements": "надійний апарат без зайвих функцій",
        "avatar": "id19.png",
        "behavior": "клієнт-бригадир будівельної компанії",
        "correct_models": ["M-18D"],
        "wrong_models": ["SAB-15DX", "M-20D", "SAB-17DX", "M-16PW"],
        "hints": [
            "Потрібна гарантія 5+ років",
            "Працюю переважно електродами до 5 мм",
            "Не потрібні TIG-LIFT та VRD",
            "Шукаю баланс між ціною та надійністю",
            "Інструмент повинен витримувати щоденне навантаження"
        ]
    },
    {
        "id": 24,
        "description": "потрібен найпотужніший інвертор для важких металів",
        "requirements": "апарат для зварювання товстих конструкцій (10+ мм)",
        "avatar": "id20.png",
        "behavior": "клієнт-інженер на металургійному підприємстві",
        "correct_models": ["M-20D", "M-18D"],
        "wrong_models": ["SAB-14DMINI", "M-16PW", "M-18D"],
        "hints": [
            "Потрібно варити метали товщиною понад 10 мм",
            "Важливий широкий дисплей для точних налаштувань",
            "Потрібна максимальна потужність",
            "Готовий платити за професійне обладнання",
            "В комплекті повинні бути кабелі"
        ]
    }
]

TOOL_MODELS = [
    "CD-12QX",
    "CD-200BCULTRA",
    "CD-201HBC",
    "CD-218Q",
    "CD-200BCCOMPACT",
    "CD-12CX",
    "CD-12BC",
    "GS-140SE",
    "GL-160SE",
    "GS-98",
    "GS-100S",
    "GL-145S",
    "GS-120S",
    "GL-240",
    "CG-12BC",
    "GL-125S",
    "DGA-201",
    "DHR-200",
    "DHR-201BC",
    "DHR-202BC",
    "RH-100",
    "RH-12Q",
    "RH-16",
    "BH-14S",
    "BH-20",
    "BH-30",
    "SAB-14DMINI",
    "SAB-15DX",
    "M-16PW",
    "SAB-17DX",
    "M-18D",
    "M-20D"
]

UNACCEPTABLE_BEHAVIOR_PROMPT = """
Якщо користувач пише матюки та слова, які є недопустими при спілкуванні з клієнтами, 
ти маєш право завершити діалог. Приклад відповіді:
"Ем...
"""

def is_question(message):
    return "?" in message or message.strip().lower().startswith((
        "прац", "як", "чому", "чи", "який", "яка", "яке", "роб",
        "завдан", "акумулятор", "діамет", "метал", "задач", "мережев",
        "дерево", "матер", "насадки", "режим", "крутний", "момент",
        "потужн", "буд", "свер"
    ))

def send_email_report(subject, body, to_email):
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = os.getenv('EMAIL_ADDRESS')
    msg['To'] = to_email

    try:
        with smtplib.SMTP(os.getenv('EMAIL_HOST'), int(os.getenv('EMAIL_PORT'))) as server:
            server.starttls()
            server.login(os.getenv('EMAIL_ADDRESS'), os.getenv('EMAIL_PASSWORD'))
            server.send_message(msg)
            print("[EMAIL] Звіт успішно відправлено.")
    except Exception as e:
        print(f"[EMAIL ERROR] Не вдалося надіслати лист: {str(e)}")

@app.route('/authenticate', methods=['POST'])
def authenticate():
    seller_name = request.json.get("seller_name", "").strip()
    if not seller_name:
        return jsonify({"error": "Будь ласка, введіть ваше ПІБ"}), 400
    
    session['seller_name'] = seller_name
    session.modified = True
    return jsonify({"success": True, "message": f"Вітаємо, {seller_name}! Тепер ви можете розпочати діалог."})

@app.errorhandler(500)
def internal_error(error):
    if 'seller_name' in session:
        generate_report(session)  # Зберегти звіт навіть при помилці
    return jsonify({"error": "Внутрішня помилка сервера"}), 500

def init_conversation():
    # Очистити всі попередні дані сесії
    session.clear()
    
    selected_situation = random.choice(SITUATIONS)
    session['situation'] = selected_situation
    session['current_situation_id'] = selected_situation["id"]
    session['available_models'] = TOOL_MODELS.copy()  # Використовуємо копію, щоб уникнути модифікації оригіналу
    session['stage'] = 1
    session['chat_active'] = True
    session['message_count'] = 0
    session['wrong_model_attempts'] = 0
    session['question_count'] = 0
    session['unique_questions'] = []
    session['off_topic_count'] = 0
    session['misunderstood_count'] = 0
    session['objection_round'] = 1
    session['warning_count'] = 0
    session['user_answers'] = {}
    session['question_scores'] = []
    session['model_score'] = 0
    session['total_score'] = 0
    session['seller_replies'] = []
    session['irrelevant_answers'] = 0
    session.modified = True 

    system_prompt = f"""
    Ти — віртуальний **клієнт магазину**, який **прийшов купити інструмент**.  
    Твоя **єдина мета** — **отримати потрібну інформацію для покупки** згідно твоєї ситуації.
    Не висвітлюй ситуацію повністю. Користувач ставить питання – ти **відповідаєш по одному реченню**. 
    Ти **не є консультантом**, **не допомагаєш** користувачу, **не пропонуєш моделі**, **не ставиш зустрічних запитань**.
    Ти не є консультантом. Ти клієнт, який хоче дізнатися все необхідне про інструмент, щоби прийняти рішення про покупку.  
    Ти уточнюєш деталі, висловлюєш свої вимоги.
    **Ніколи не грай роль продавця**.

    Твоя ситуація: {selected_situation['description']}
    Твої потреби: {selected_situation['requirements']}
    **Поведінка**: {selected_situation.get('behavior')}

    {UNACCEPTABLE_BEHAVIOR_PROMPT}

    Поведінка:
    - Якщо користувач грубий або використовує лайливу лексику — завершуй діалог фразою "Я Вас не зрозумів"
    - В іншому випадку — задавай додаткові запитання або висловлюй свою думку.

    Починай розмову нейтрально:  
    "Добрий день, мені потрібен інструмент."
    """
    return [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": f"Добрий день, мені потрібен {session['situation']['description']}"}
    ]

def is_relevant_question_gpt(question, situation_description):
    prompt = f"""
Ти — клієнт, який обирає інструмент.

Оціни, чи стосується це питання вибору відповідного інструменту в контексті описаної ситуації.

Ситуація: "{situation_description}"

Критерії релевантності:
- Питання допомагає краще зрозуміти потреби, вимоги чи обмеження ситуації
- Воно стосується технічних параметрів, функцій, сумісності або застосування інструменту
- Або воно уточнює умови, в яких буде використовуватись інструмент

Відповідай лише "так" або "ні". Питання: "{question}"
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # або gpt-3.5-turbo, якщо треба
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=10,
        )
        answer = response.choices[0].message["content"].strip().lower()
        print(f"[DEBUG] Відповідь GPT: {answer}")
        return "так" in answer
    except Exception as e:
        print(f"Помилка: {str(e)}")
        return False

def match_model(user_input, available_models):7
    user_model = re.sub(r'[^A-Z0-9-]', '', user_input.upper())
    matched_models = [m for m in available_models if user_model in m.upper()]
    
    if not matched_models:
        return None  # Модель не знайдена
    
    return matched_models[0]

@app.route('/')
def home():
    instance_id = request.args.get('instance', 'default_value')
    if instance_id:
        session['instance_id'] = instance_id  # Зберігаємо ID інстансу в сесії
        return jsonify({"message": f"Instance ID is: {instance_id}"})  # Повертаємо відповідь
    else:
        return jsonify({"error": "Instance ID is missing."}), 400 


@app.route('/start_chat')
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

@app.route("/restart-chat", methods=["POST"])
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

@app.route("/show_models", methods=["POST"])
def show_models():
    # Отримуємо поточну ситуацію
    current_situation = session.get("situation")
    
    # Отримуємо правильні і неправильні моделі з поточної ситуації
    correct_models = current_situation["correct_models"]
    wrong_models = current_situation["wrong_models"]
    
    # Фільтруємо доступні моделі на основі ситуації
    available_models = correct_models + wrong_models

    session["stage"] = 2  # Переконуємось, що ми на правильному етапі для вибору моделі

    return jsonify({
        "models": available_models,
        "stage": 2
    })

def generate_report(session_data):
    seller_name = session_data.get('seller_name') or 'Невідомий продавець'
    total_score = session_data.get('total_score', 0)
    max_score = 20  # або інше значення з вашого коду
    
    report_lines = [
        f"Звіт про діалог продавця: {seller_name}",
        f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Оцінка: {total_score}/{max_score}",
        "\nДіалог:",
    ]
    
    # Додати всі репліки діалогу
    for message in session_data.get('conversation_log', []):
        role = "Клієнт" if message['role'] == 'assistant' else "Продавець"
        report_lines.append(f"{role} ({message['timestamp']}): {message['message']}")
    
    # Додати результати оцінювання
    report_lines.extend([
        "\nРезультати:",
        f"- Оцінка за модель: {session_data.get('model_score', 0)}/4",
        f"- Оцінка за питання: {sum(q['score'] for q in session_data.get('question_scores', []))}/5",
        f"- Оцінка за відповіді: {sum(a['score'] for a in session_data.get('user_answers', {}).values())}/6",
        f"- Оцінка за заперечення: {session_data.get('objection_score', 0)}/5"
    ])
    
    return "\n".join(report_lines)

@app.after_request
def apply_caching(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Set-Cookie"] = "SameSite=None; Secure"  # Дозволяє сесію через iframe
    return response

@app.after_request
def set_security_headers(response):
    # Налаштування для iframe
    response.headers['Content-Security-Policy'] = "frame-ancestors https://ako.dnipro-m.ua;"
    response.headers['X-Frame-Options'] = 'ALLOW-FROM https://ako.dnipro-m.ua'
    
    # Додаткові заголовки безпеки
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    
    # Куки для iframe
    response.headers.add('Set-Cookie', 'SameSite=None; Secure')
    
    return response

@app.route("/chat", methods=["POST"])
def chat():
    instance_id = request.json.get('instance') or session.get('instance_id')
    if not instance_id:
        return jsonify({"error": "Instance ID missing"}), 400

    data = request.get_json()
    instance_id = data.get('instance') or session.get('instance_id')
    if not instance_id:
        return jsonify({"error": "Instance ID required"}), 400

    # Ініціалізація всіх критичних змінних сесії
    session.setdefault('conversation_log', [])
    session.setdefault('seller_name', request.json.get("seller_name", "Невідомий продавець"))
    session.setdefault('stage', 1)
    session.setdefault('misunderstood_count', 0)
    session.setdefault('objection_round', 1)
    session.setdefault('question_scores', [])
    session.setdefault('user_answers', {})
    session.setdefault('seller_replies', [])
    session.setdefault('available_models', [])
    session.setdefault('history', init_conversation() if 'history' not in session else session['history'])

    user_input = request.json.get("message", "").strip()
    print(f"[DEBUG] Поточний стан сесії: {list(session.keys())}")
    print(f"[DEBUG] Користувач написав: {user_input}")
    print(f"[DEBUG] Поточна стадія: {session['stage']}")

    # Запис повідомлення в лог
    try:
        session['conversation_log'].append({
            'role': 'user',
            'message': user_input,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        session.modified = True
        print(f"[DEBUG] Оновлений conversation_log: {session['conversation_log'][-1]}")
    except Exception as e:
        print(f"[ERROR] Помилка запису в conversation_log: {str(e)}")
        session['conversation_log'] = [{
            'role': 'user', 
            'message': user_input,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }]

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
        # Перевірка на нерелевантні питання
        if not is_relevant_question_gpt(user_input, session["situation"]["description"]):
            print(f"[SCORE] Нерелевантне питання: 0 балів | Поточний рахунок: {session.get('total_score', 0)}")
            session["misunderstood_count"] += 1
            session["question_scores"].append({"question": user_input, "score": 0})
            
            # Збільшуємо загальний лічильник питань, навіть якщо питання нерелевантне
            session["question_count"] += 1

            if session["misunderstood_count"] >= 3:
                session["chat_active"] = False
                # Генерація звіту та збереження його в змінну report_content
                report_content = generate_report(session)  # Зберегти звіт навіть при помилці
                send_email_report(
                    subject=f"Звіт про діалог — {session.get('seller_name', 'Продавець')}",
                    body=report_content,  # Використовуємо згенерований звіт
                    to_email="voloshchenko2014@gmail.com"
                )
                return jsonify({
                    "reply": "Ви поставили декілька нерелевантних питань. Діалог завершено.",
                    "chat_ended": True,
                    "show_restart_button": True
                })
            return jsonify({
                "reply": "Ваше питання не стосується вибору інструменту. Спробуйте інше питання.",
                "chat_ended": False,
                "question_progress": session["question_count"]
            })

        # Обробка релевантних питань
        is_duplicate = user_input.lower() in [q.lower() for q in session["unique_questions"]]
        question_score = 1 if not is_duplicate else 0
        print(f"[SCORE] {'Нове' if not is_duplicate else 'Повторне'} питання: +{question_score} бал(и)")
        
        if not is_duplicate:
            session["unique_questions"].append(user_input)

        session["question_scores"].append({
            "question": user_input,
            "score": question_score
        })
        
        # Збільшуємо загальний лічильник питань за кожне питання
        session["question_count"] += 1

        current_questions_score = sum(q["score"] for q in session["question_scores"])
        max_questions_score = 5  # Тепер рахуються всі питання, не тільки правильні
        print(f"[SCORE] Загальний бал за питання: {current_questions_score}/{max_questions_score}")

        # Обмеження кількості питань (максимум 5)
        if session["question_count"] >= 7:
            session["stage"] = 2
            return jsonify({
                "reply": "Я відповів на достатньо питань. Тепер ви можете запропонувати мені модель інструменту.",
                "chat_ended": False,
                "stage": 2,
                "show_model_button": True
            })

        # Генерація відповіді GPT
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Додати повідомлення користувача до history і до conversation_log
        session["history"].append({"role": "user", "content": user_input})
        session['conversation_log'].append({
            'role': 'user',
            'message': user_input,
            'timestamp': now
        })

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=session["history"][-20:],
                temperature=0.5,
                max_tokens=150
            )
            answer = response.choices[0].message["content"].strip()

            # Додати відповідь GPT до history і до conversation_log
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
                "show_model_button": session["question_count"] >= 3
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
                "model_chosen": False  # Додайте цей прапорець
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
        partially_correct_models = [model.upper() for model in current_situation.get("partially_correct_models", [])]

        # Оцінка моделі
        if user_model in correct_models:
            session["model_score"] = 4
            print(f"[SCORE] Правильна модель: +2 бали")
        elif user_model in partially_correct_models:
            session["model_score"] = 1
            print(f"[SCORE] Частково правильна модель: +1 бал")
        else:
            session["model_score"] = 0
            print(f"[SCORE] Неправильна модель: 0 балів")

            # Оновлений вивід для переходу на stage 3
            print(f"[SCORE] Поточний бал за модель: {session['model_score']}/2")
            print(f"[SCORE] Загальний бал: {session.get('total_score', 0) + session['model_score']}")

        # Переходь на stage 3 після оцінки моделі
        session["model"] = user_model
        session["stage"] = 3
        session["current_question_index"] = 0
        session["user_answers"] = {}

        # Генерація уточнюючих питань
        prompt = f"""Ти клієнт, який обрав інструмент {user_model} для {session['situation']['description']}.\n
        Згенеруй 3 питання про **характеристики**, **зовнішню будову** та функції цього інструменту."""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ти — клієнт, який має задати уточнюючі запитання про модель інструмента."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=400
            )
            content = response.choices[0].message.get("content", "")
            questions = [line.strip(" 1234567890.-") for line in content.split('\n') if line.strip()]
            session["generated_questions"] = questions
            
            session["history"].append({"role": "user", "content": user_input})
            first_question = questions[0] if questions else "Яке перше ваше питання про цю модель?"
            session["history"].append({"role": "assistant", "content": first_question})

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

        # Оцінка відповіді
        gpt_prompt = f"""
Оціни відповідь користувача на питання.
Питання: "{current_question}"
Відповідь: "{user_input}"

Оціни відповідь продавця за цією шкалою:

2 — відповідь містить **характеристику** і пояснення, що вона означає або як допомагає клієнту
1 — відповідь містить **лише характеристику**
0 — відповідь **не по темі** або **занадто загальна**

Відповідай лише цифрою: 0, 1 або 2.
"""
        try:
            evaluation = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ти оцінюєш відповідь на запитання. Відповідай лише числом: 0, 1 або 2."},
                    {"role": "user", "content": gpt_prompt}
                ],
                temperature=0,
                max_tokens=10
            )
            score = int(evaluation.choices[0].message["content"].strip() or 0)
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
            current_answers_score = sum(a["score"] for a in session["user_answers"].values())
            max_answers_score = 3 * 2  # 3 питання по 2 бали
            print(f"[SCORE] Загальний бал за відповіді: {current_answers_score}/{max_answers_score}")

            session['current_question_index'] += 1

            # Перехід до наступного питання
            if session['current_question_index'] < len(session['generated_questions']):
                next_question = session['generated_questions'][session['current_question_index']]
                session["history"].append({"role": "assistant", "content": next_question})
                session.modified = True

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

                objections = [
                    "Мені здається, це трохи дорогувато.",
                    "Ваша гарантія точно працює?",
                    "Я бачив в інтернеті дешевше.",
                    "Чому в комплекті так мало насадок?",
                    "Я чув, що ця модель швидко ламається.",
                    "У іншому магазині така ж модель, але зі знижкою.",
                    "Це остання модель чи вже застаріла?",
                    "А де виробляють цей інструмент?",
                    "Я чув погані відгуки про цю модель.",
                    "А якщо мені не сподобається - можна повернути?"
                ]
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

        if current_round <= 2:
            try:
                history = "\n".join([f"Раунд {i+1}: {reply}" for i, reply in enumerate(session["seller_replies"])])
                gpt_prompt = f"""
    Ти — клієнт, який має заперечення: "{objection}".

    Ось як продавець відповідав до цього моменту:
    {history}

    Відповідай як реалістичний клієнт. Реагуй природно на останню репліку продавця: "{seller_reply}".
    Підтримуй контекст заперечення. Будь конкретним, відповідай одним-двома реченнями."""
                
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Ти — клієнт у діалозі з продавцем. Відповідай чесно, логічно і згідно з контекстом заперечення."},
                        {"role": "user", "content": gpt_prompt}
                    ],
                    temperature=0.6,
                    max_tokens=200
                )
                reply = response.choices[0].message["content"].strip()
                session["objection_round"] += 1
                session.modified = True

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
    - "переконливо" — якщо є **1 або більше сильні аргументи** – 5 балів
    - "частково переконливо" — якщо є **2 слабких аргументи** – 3 бали
    - "непереконливо" — якщо **немає** жодного аргументу або відповідь не по темі – 0 балів

    Відповідай одним словом: "переконливо", "частково переконливо" або "непереконливо". Не додавай пояснень.
    """
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Ти — експерт з оцінки комунікацій. Будь об'єктивним."},
                        {"role": "user", "content": evaluation_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=50
                )
                raw_rating = response.choices[0].message["content"].strip().lower()

                # Витягнути перше зі слів: переконливо, частково переконливо, непереконливо
                match = re.search(r"(переконливо|частково переконливо|непереконливо)", raw_rating)
                rating = match.group(1) if match else "непереконливо"
                
                if rating == "переконливо":
                    objection_score = 5
                elif rating == "частково переконливо":
                    objection_score = 3
                elif rating == "непереконливо":
                    objection_score = 0
                else:
                    objection_score = 0

                print(f"[SCORE] Оцінка аргументів: {rating} ({objection_score}/5 балів)")

                model_score = session.get("model_score", 0)
                questions_score = sum(q["score"] for q in session.get("question_scores", []))
                answers_score = sum(a["score"] for a in session.get("user_answers", {}).values())
                total_score = model_score + questions_score + answers_score + objection_score
                max_score = 5 + 4 + 6 + 5

                print("\n=== ФІНАЛЬНИЙ РАХУНОК ===")
                print(f"[SCORE] За модель: {model_score}/4")
                print(f"[SCORE] За питання: {questions_score}/5")
                print(f"[SCORE] За відповіді: {answers_score}/6")
                print(f"[SCORE] За заперечення: {objection_score}/5")
                print(f"[SCORE] ЗАГАЛЬНИЙ БАЛ: {total_score}/20")

                if total_score >= max_score * 0.8:
                    feedback = "🔝 Чудово! Ви дуже впевнено провели клієнта до покупки."
                elif total_score >= max_score * 0.6:
                    feedback = "👍 Ваші відповіді були хорошими, але є над чим попрацювати."
                else:
                    feedback = "⚠️ Є недоліки в підході до клієнта. Рекомендується додаткове навчання."

                if rating == "переконливо":
                    reply = "Вітаю, Ви успішно проконсультували клієнта."
                elif rating == "частково переконливо":
                    reply = "Клієнта було проконсультовано, але допущені помилки, що завадили набрати максимальну кількість балів."
                else:
                    reply = "Клієнт незадоволений консультацією."

                full_reply = f"{reply}\n\n📊 Ваша оцінка: {total_score}/{max_score}\n{feedback}"

                # Збереження звіту
                session["total_score"] = total_score
                report_content = generate_report(dict(session))
                report_filename = f"report_{session.get('seller_name', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                
                # Створення папки reports, якщо її немає
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
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)