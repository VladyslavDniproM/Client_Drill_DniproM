from flask import Blueprint, request, jsonify, session

auth_bp = Blueprint("auth", __name__)

@auth_bp.route('/authenticate', methods=['POST'])
def authenticate():
    seller_name = request.json.get("seller_name", "").strip()
    selected_category = request.json.get("category", "")
    if not seller_name:
        return jsonify({"error": "Будь ласка, введіть ваше ПІБ"}), 400

    session['seller_name'] = seller_name
    session['category'] = selected_category
    session.modified = True
    return jsonify({"success": True, "message": f"Вітаємо, {seller_name}!"})
