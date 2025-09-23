from flask import Blueprint, jsonify, session
from services.report_service import generate_report

misc_bp = Blueprint("misc", __name__)

@misc_bp.app_errorhandler(500)
def internal_error(error):
    if 'seller_name' in session:
        generate_report(session)  # Зберегти звіт навіть при помилці
    return jsonify({"error": "Внутрішня помилка сервера"}), 500

@misc_bp.after_app_request
def allow_iframe(response):
    # Дозволяємо вбудовування в iframe тільки з ako.dnipro-m.ua
    response.headers['X-Frame-Options'] = 'https://ako.dnipro-m.ua/'
    return response
