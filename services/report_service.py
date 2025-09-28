from datetime import datetime
import os
import json
import io
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.http import MediaInMemoryUpload

def generate_report(session_data):
    seller_name = session_data.get('seller_name') or 'Невідомий продавець'
    total_score = session_data.get('total_score', 0)
    max_score = 30
    selected_category = session_data.get('category', 'Не вказано')
    
    report_lines = [
        f"Звіт про діалог продавця: {seller_name}",
        f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Обрана категорія: {selected_category}",
        f"Оцінка: {total_score}/{max_score}",
        "\nДіалог:",
    ]
    
    # Додати всі репліки діалогу
    for message in session_data.get('conversation_log', []):
        if message['role'] == 'user':
            role = "Продавець"
        elif message['role'] == 'assistant':
            role = "Клієнт (бот)"
        else:
            role = message['role'].capitalize()
        report_lines.append(f"{role} ({message['timestamp']}): {message['message']}")
    
    # обчислюємо бал за питання з обмеженням максимум 8
    questions_score = min(
        sum(q['score'] for q in session_data.get('question_scores', [])), 
        8
    )

    # Додати результати оцінювання
    report_lines.extend([
        "\nРезультати:",
        f"- Оцінка за модель: {session_data.get('model_score', 0)}/6",
        f"- Оцінка за питання: {questions_score}/8",
        f"- Оцінка за відповіді: {sum(a['score'] for a in session_data.get('user_answers', {}).values())}/6",
        f"- Оцінка за заперечення: {session_data.get('objection_score', 0)}/10"
    ])
    
    return "\n".join(report_lines)

def save_report_to_drive(session_data):
    """Зберігає звіт у файл на Google Drive"""
    try:
        # Отримуємо credentials
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json')
        elif os.getenv('GMAIL_CREDENTIALS_JSON'):
            creds_json = os.getenv('GMAIL_CREDENTIALS_JSON')
            creds_dict = json.loads(creds_json)
            creds = Credentials.from_authorized_user_info(creds_dict)
        else:
            print("[DRIVE ERROR] Не знайдено Google credentials")
            return False
        
        # Оновлюємо токен якщо потрібно
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        
        # Створюємо сервіс Drive
        drive_service = build('drive', 'v3', credentials=creds)
        
        # Шукаємо папку для звітів
        folder_name = "Sales Training Reports"
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive_service.files().list(q=query, spaces='drive').execute()
        items = results.get('files', [])
        
        if not items:
            print("[DRIVE ERROR] Папка для звітів не знайдена")
            return False
        
        folder_id = items[0]['id']
        
        # Генеруємо звіт
        report_content = generate_report(session_data)
        seller_name = session_data.get('seller_name', 'Невідомий').replace('/', '-').replace('\\', '-')
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Формуємо назву файлу
        filename = f"Звіт_{seller_name}_{timestamp}.txt"
        
        # Метадані файлу
        file_metadata = {
            'name': filename,
            'parents': [folder_id],
            'mimeType': 'text/plain'
        }
        
        # Створюємо файл з текстовим контентом
        from googleapiclient.http import MediaInMemoryUpload
        media = MediaInMemoryUpload(
            report_content.encode('utf-8'),
            mimetype='text/plain'
        )
        
        # Створюємо файл
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        print(f"[DRIVE] Звіт успішно збережено на Google Drive: {filename}")
        print(f"[DRIVE] ID файлу: {file.get('id')}")
        return True
        
    except Exception as e:
        print(f"[DRIVE ERROR] Не вдалося зберегти звіт: {str(e)}")
        return False

# Застаріла функція для зворотньої сумісності
def send_email_report(subject, body, to_email):
    print("[INFO] Функція send_email_report застаріла. Використовується Google Drive")
    # Тут можна використати session_data з body, якщо потрібно
    return save_report_to_drive({"conversation_log": []})  # Мінімальні дані для збереження