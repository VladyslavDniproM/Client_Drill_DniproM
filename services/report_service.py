from datetime import datetime
import os
import json
import io
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.http import MediaInMemoryUpload

def update_google_sheets(session_data):
    """Записує статистику в єдину Google Таблицю"""
    try:
        # Отримуємо credentials
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json')
        elif os.getenv('GMAIL_CREDENTIALS_JSON'):
            creds_json = os.getenv('GMAIL_CREDENTIALS_JSON')
            creds_dict = json.loads(creds_json)
            creds = Credentials.from_authorized_user_info(creds_dict)
        else:
            print("[SHEETS ERROR] Не знайдено Google credentials")
            return False
        
        # Оновлюємо токен якщо потрібно
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        
        # Створюємо сервіси
        drive_service = build('drive', 'v3', credentials=creds)
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        # ID папки
        FOLDER_ID = '1vU_AH8bQspbT4Viw7EoMoCObrFWqcV3d'
        
        # Назва таблиці (постійна)
        spreadsheet_name = "ЗВІТИ ПРОДАЖІВ"
        
        # Перевіряємо, чи вже існує таблиця
        query = f"name='{spreadsheet_name}' and '{FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
        results = drive_service.files().list(q=query).execute()
        files = results.get('files', [])
        
        if files:
            # Використовуємо існуючу таблицю
            SPREADSHEET_ID = files[0]['id']
            print(f"[SHEETS] Використовуємо існуючу таблицю: {spreadsheet_name}")
        else:
            # Створюємо нову таблицю
            spreadsheet_body = {
                'properties': {
                    'title': spreadsheet_name
                },
                'sheets': [
                    {
                        'properties': {
                            'title': 'Звіти',
                            'gridProperties': {
                                'rowCount': 1000,
                                'columnCount': 8
                            }
                        }
                    }
                ]
            }
            
            spreadsheet = sheets_service.spreadsheets().create(body=spreadsheet_body).execute()
            SPREADSHEET_ID = spreadsheet['spreadsheetId']
            
            # Переміщуємо таблицю в потрібну папку
            drive_service.files().update(
                fileId=SPREADSHEET_ID,
                addParents=FOLDER_ID,
                fields='id, parents'
            ).execute()
            
            print(f"[SHEETS] Створено нову таблицю: {spreadsheet_name}")
        
        # Підготовка даних
        seller_name = session_data.get('seller_name', 'Невідомий')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        selected_category = session_data.get('category', 'Не вказано')
        
        # Розрахунок балів
        model_score = session_data.get('model_score', 0)
        questions_score = min(sum(q['score'] for q in session_data.get('question_scores', [])), 8)
        answers_score = min(sum(a['score'] for a in session_data.get('user_answers', {}).values()), 10)
        objection_score = session_data.get('objection_score', 0)
        total_score = model_score + questions_score + answers_score + objection_score
        
        # Дані для запису
        row_data = [
            timestamp,
            seller_name,
            selected_category,
            total_score,
            model_score,
            questions_score,
            answers_score,
            objection_score
        ]
        
        # Шапка таблиці
        headers = ['Дата', 'Продавець', 'Категорія', 'Загальний бал', 'Бал за модель', 'Бал за питання', 'Бал за відповіді', 'Бал за заперечення']
        
        # Перевіряємо, чи є шапка
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="A1:H1"
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            # Додаємо шапку
            header_body = {'values': [headers]}
            sheets_service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range="A1",
                valueInputOption="RAW",
                body=header_body
            ).execute()
            print("[SHEETS] Додано шапку таблиці")
        
        # Знаходимо вільний рядок
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="A:A"
        ).execute()
        
        values = result.get('values', [])
        next_row = len(values) + 1
        
        # Записуємо дані
        body = {'values': [row_data]}
        sheets_service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"A{next_row}",
            valueInputOption="RAW",
            body=body
        ).execute()
        
        print(f"[SHEETS] Статистику успішно додано до таблиці '{spreadsheet_name}', рядок {next_row}")
        print(f"[SHEETS] Посилання на таблицю: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")
        return True
        
    except Exception as e:
        print(f"[SHEETS ERROR] Не вдалося оновити таблицю: {str(e)}")
        return False

def generate_report(session_data):
    seller_name = session_data.get('seller_name') or 'Невідомий продавець'
    selected_category = session_data.get('category', 'Не вказано')

    model_score = session_data.get('model_score', 0)
    questions_score = min(sum(q['score'] for q in session_data.get('question_scores', [])), 8)
    answers_score = min(sum(a['score'] for a in session_data.get('user_answers', {}).values()), 10)
    objection_score = session_data.get('objection_score', 0)
    total_score = model_score + questions_score + answers_score + objection_score
    max_score = 30
    
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
        f"- Оцінка за модель: {session_data.get('model_score', 0)}/4",  # Змінити з 6 на 4
        f"- Оцінка за питання: {questions_score}/8",
        f"- Оцінка за відповіді: {sum(a['score'] for a in session_data.get('user_answers', {}).values())}/10",  # Змінити з 6 на 10
        f"- Оцінка за заперечення: {session_data.get('objection_score', 0)}/8"  # Змінити з 10 на 8
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