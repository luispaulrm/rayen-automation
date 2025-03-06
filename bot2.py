import requests
from flask import Flask, request

TOKEN = "7247621163:AAE2620h3cNDn-Pbt5gxgENQWqG5DTPD294"
WEBHOOK_URL = "https://rayenbot.onrender.com/webhook"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

def set_webhook():
    url = f"{TELEGRAM_API_URL}/setWebhook?url={WEBHOOK_URL}"
    response = requests.get(url)
    print("Webhook configurado:", response.json())

@app.route("/", methods=["GET", "HEAD"])
def index():
    return "OK", 200

@app.route("/webhook", methods=["POST"])
def recibir_actualizacion():
    datos = request.json
    if "message" in datos:
        chat_id = datos["message"]["chat"]["id"]
        mensaje = datos["message"].get("text", "")
        
        if mensaje.lower() == "/start":
            enviar_mensaje(chat_id, f"Hola, tu chat ID es: {chat_id}")
        else:
            enviar_mensaje(chat_id, "No entiendo el mensaje. Usa /start para obtener tu ID.")
    return "OK", 200

def enviar_mensaje(chat_id, mensaje):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensaje}
    requests.post(url, json=payload)

@app.route("/health")
def health_check():
    return "OK", 200

# En Render, configuras:
# Start Command: gunicorn CHAITDGTELEGRAM:app --bind 0.0.0.0:$PORT
# (asumiendo que este archivo se llama CHAITDGTELEGRAM.py)
if __name__ == "__main__":
    # Solo para que se ejecute al hacer 'python CHAITDGTELEGRAM.py' local:
    set_webhook()
    # No hagas app.run(...) porque Gunicorn se encarga en producción
