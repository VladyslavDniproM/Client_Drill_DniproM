from datetime import datetime
import smtplib, os
from email.mime.text import MIMEText

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
