from audio_to_text_whisperex.whisper_pragraf import transcribe_latest_audio
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/STT", methods=["GET"])
def stt():
    result = transcribe_latest_audio()
    # אם יש מפתח error בתשובה — החזר קוד 400 ושגיאה
    if isinstance(result, dict) and "error" in result:
        return jsonify({"error": result["error"]}), 400
    # אם הכל תקין
    return jsonify({"result": result, "message": "success"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000)
