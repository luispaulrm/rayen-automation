import os
import requests
from flask import Flask, request

TOKEN = os.environ.get("TOKEN", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

def set_webhook():
    url = f"{TELEGRAM_API_URL}/setWebhook?url={WEBHOOK_URL}"
    response = requests.get(url)
    print("Webhook configurado:", response.json())

# LLAMADA AL WEBHOOK FUERA DE "__main__"
set_webhook()

@app.route("/", methods=["GET", "HEAD"])
def index():
    return "OK", 200

@app.route("/webhook", methods=["POST"])
def recibir_actualizacion():
    datos = request.json
    if "message" in datos:
        chat_id = datos["message"]["chat"]["id"]
        mensaje = datos["message"].get("text", "")
        
        if mensaje and mensaje.lower() == "/start":
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

# SIN if __name__ == "__main__": set_webhook()
