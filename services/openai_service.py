from config import client, MODEL_ENGINE
import re, random
from data.models import FEMALE_IDS, FEMALE_VOICES, MALE_VOICES

def evaluate_question(question, situation_description):
    prompt = f"""
Ти — клієнт, який обирає інструмент в магазині електроінструментів. Оціни питання за критеріями:

Ситуація: "{situation_description}"
Питання: "{question}"

Критерії оцінки (відповідь лише цифрою):
2 - якщо питання чітко стосується вибору інструменту **(технічні параметри, будова, сфера застосування, сумісність, застосування)**
1 - якщо питання частково стосується теми роботи інструменту, характеристик тощо
0 - якщо питання не стосується вибору інструменту (соціальне, про компанію тощо)

**Важливо: це мають бути питання коректні, без матюків та слів, що стосуються грошей, матеріалього становища.**

Відповідь має бути лише однією цифрою (0, 1 або 2) без жодних додаткових слів.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=2,
        )
        score = response.choices[0].message.content.strip()
        if score.isdigit():
            return min(max(int(score), 0), 2)
        return 0
    except Exception as e:
        print(f"Помилка при оцінці питання: {str(e)}")
        return 0

def match_model(user_input, available_models):
    user_model = re.sub(r'[^A-Z0-9-]', '', user_input.upper())
    matched_models = [m for m in available_models if user_model in m.upper()]
    
    if not matched_models:
        return None  # Модель не знайдена
    
    return matched_models[0]

def assign_voice_for_situation(situation_id):
    """Визначаємо голос для ситуації один раз"""
    if situation_id in FEMALE_IDS:
        return random.choice(FEMALE_VOICES)
    else:
        return random.choice(MALE_VOICES)