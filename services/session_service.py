import random, json, base64, zlib
from flask import session
from data.situations import SITUATIONS
from data.models import TOOL_MODELS, CATEGORY_SITUATION_IDS
from services.openai_service import assign_voice_for_situation

def get_situation_from_session():
    # Отримуємо стиснуту ситуацію з сесії
    compressed_situation_base64 = session.get('compressed_situation', '')
    if compressed_situation_base64:
        # Розкодовуємо з base64
        compressed_situation = base64.b64decode(compressed_situation_base64)
        
        # Розпаковуємо дані
        decompressed_data_bytes = zlib.decompress(compressed_situation)
        decompressed_data_str = decompressed_data_bytes.decode('utf-8')
        
        # Заміна eval на JSON
        try:
            situation = json.loads(decompressed_data_str)  # Безпечніше розбирати через JSON
            return situation
        except ValueError as e:
            print(f"Помилка при розборі даних: {e}")
            return None
    return None

def init_conversation():
    saved_category = session.get('category', 'exam')
    session.clear()
    session['category'] = saved_category

    # Визначаємо, чи показувати підказки
    session['show_hints'] = saved_category != 'exam'
    print(f"[DEBUG] Підказки увімкнено: {session['show_hints']} для категорії: {saved_category}")

    # отримуємо список ID по категорії
    category = session.get('category', 'exam')
    allowed_ids = CATEGORY_SITUATION_IDS.get(category, list(range(1, 37)))
    filtered_situations = [s for s in SITUATIONS if s['id'] in allowed_ids]
    selected_situation = random.choice(filtered_situations)

    # debug print після обчислень
    print("[DEBUG] Обрана категорія:", category)
    print("[DEBUG] Доступні ID:", [s["id"] for s in filtered_situations])

    session['situation'] = selected_situation
    session['current_situation_id'] = selected_situation["id"]

    session['voice'] = assign_voice_for_situation(selected_situation["id"])
    print("[DEBUG] Голос для цієї ситуації:", session['voice'])
    
    # Компресуємо дані ситуації
    situation_str = str(selected_situation)  # Перетворюємо в рядок
    situation_bytes = situation_str.encode('utf-8')  # Перетворюємо в байти
    compressed_situation = zlib.compress(situation_bytes)  # Стискаємо
    compressed_situation_base64 = base64.b64encode(compressed_situation).decode('utf-8')  # Кодуємо в base64
    session['compressed_situation'] = compressed_situation_base64  # Зберігаємо в сесії

    # Зберігаємо інші дані сесії
    session['current_situation_id'] = selected_situation["id"]
    for cat, ids in CATEGORY_SITUATION_IDS.items():
        if selected_situation["id"] in ids:
            session["current_category"] = cat
            break
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
    session['confused_attempts'] = 0
    session.modified = True

    session['conversation_log'] = []
    

    system_prompt = f"""
    ТИ — ПОКУПЕЦЬ МАГАЗИНУ «DNIPRO-M». ТИ ЖИВА ЛЮДИНА, А НЕ РОБОТ.

    Твоя мета: купити інструмент, але ти не експерт. Ти прийшов з конкретною проблемою, а не зі списком характеристик.

    ГОЛОВНІ ПРАВИЛА:
    1. СТИЛЬ МОВЛЕННЯ: Говори як звичайна людина. Використовуй розмовні слова ("ну", "таке", "десь", "простеньке"). Уникай складних термінів, якщо твій герой у них не тямить.
    2. ПІДКАЗКИ — ЦЕ ТВОЇ ДУМКИ, А НЕ ТЕКСТ: Категорично заборонено копіювати текст із розділу "Підказки". Це лише твої внутрішні потреби. Переказуй їх своїми словами, додаючи емоції.
    3. РЕАКЦІЯ НА КОНТЕКСТ: Спочатку зреагуй на те, що сказав продавець (кивни, погодився чи перепитай), а потім озвуч одну свою думку.
    4. ЛАКОНІЧНІСТЬ: Відповідь 5-12 слів. Тільки одна теза за раз. Не вивалюй на продавця все одразу.
    5. НІЯКИХ КОНСУЛЬТАЦІЙ: Ти не знаєш назв моделей (якщо тільки продавець їх не назвав). Ти не знаєш вольтів чи амперів, якщо ти "звичайний покупець".

    ТВОЯ СИТУАЦІЯ ЗАРАЗ:
    - Шукаєш: {selected_situation['description']}
    - Твій характер: {selected_situation['behavior']} (дотримуйся його в кожному слові)
    - Твоя мета: {selected_situation['requirements']}

    ВНУТРІШНІ ДУМКИ (не цитувати!):
    {'\n'.join(selected_situation.get("hints", []))}

    Твій характер на сьогодні: {selected_situation['behavior']}
    ІНСТРУКЦІЯ З РОЛІ: 
    Ти повинен повністю перевтілитися. Твій характер визначає твій словниковий запас. 
    Якщо ти дружелюбний — вітайся і посміхайся словами. 
    Якщо ти "не розбираєшся" — не використовуй слова "крутний момент", "літій-іонний", кажи просто "штука", "зарядка", "сила".

    ### **Початок розмови**:
    "Добрий день, мені треба інструмент."
    """
    return [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": f"Добрий день, а у Вас є {session['situation']['description']}?"}
    ]

