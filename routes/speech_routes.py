import random
from flask import Blueprint, request, jsonify, session
import os, tempfile
from config import client

speech_bp = Blueprint("speech", __name__)

# 🎤 Speech-to-Text (розпізнавання)
@speech_bp.route("/speech-to-text", methods=["POST"])
def speech_to_text():
    if "file" not in request.files:
        return jsonify({"error": "Файл не надісланий"}), 400

    audio_file = request.files["file"]

    try:
        # Визначаємо розширення по імені файлу
        ext = ".webm"
        filename = audio_file.filename.lower()
        if filename.endswith(".m4a") or filename.endswith(".mp4"):
            ext = ".mp4"
        elif filename.endswith(".wav"):
            ext = ".wav"

        # Тимчасово зберігаємо у правильному форматі
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            audio_file.save(tmp.name)
            with open(tmp.name, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe",
                    file=f,
                    prompt="Користувач говорить лише українською мовою"
                )
        os.unlink(tmp.name)

        text = transcript.text.strip()
        return jsonify({"text": text})

    except Exception as e:
        print(f"[STT ERROR] {str(e)}")
        return jsonify({"error": "Помилка розпізнавання"}), 500


# 🔊 Text-to-Speech (озвучка)
# 🔊 Text-to-Speech (озвучка)
@speech_bp.route("/speak", methods=["POST"])
def speak():
    text = request.json.get("text", "").strip()
    if not text:
        return jsonify({"error": "Порожній текст"}), 400
    
    # Перевіряємо, чи це exam категорія
    category = session.get("category")
    if category != "exam":
        return jsonify({"error": "Озвучка доступна тільки в режимі екзамену"}), 403
    
    # Отримуємо ID клієнта
    client_id = session.get("current_situation_id")
    
    # АКТУАЛЬНІ ГОЛОСИ (підтримувані OpenAI)
    FEMALE_VOICES = ["nova", "shimmer", "fable", "verse", "coral"]
    MALE_VOICES = ["alloy", "echo", "onyx", "sage"]
    FEMALE_IDS = {3, 8, 20, 34, 35, 46, 47, 49, 58, 59, 61}

    # Якщо голос ще не визначений для цієї сесії - вибираємо його
    if "voice" not in session:
        # Визначаємо голос на основі ID клієнта
        if client_id in FEMALE_IDS:
            voice = random.choice(FEMALE_VOICES)
        else:
            voice = random.choice(MALE_VOICES)
        
        # Зберігаємо голос у сесії для подальшого використання
        session["voice"] = voice
        print(f"[TTS] Обрано голос: {voice} для клієнта ID: {client_id} (exam режим)")
    else:
        # Використовуємо вже збережений голос
        voice = session["voice"]
        print(f"[TTS] Використовуємо збережений голос: {voice} (exam режим)")

    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp.write(response.read())
            tmp_path = tmp.name
        with open(tmp_path, "rb") as f:
            audio_data = f.read()
        os.unlink(tmp_path)
        return audio_data, 200, {
            "Content-Type": "audio/mpeg",
            "Content-Disposition": f"inline; filename={voice}.mp3"
        }
    except Exception as e:
        print(f"[TTS ERROR] {str(e)}")
        return jsonify({"error": "Помилка генерації аудіо"}), 500
