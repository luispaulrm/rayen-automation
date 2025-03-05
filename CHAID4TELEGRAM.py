import requests
from flask import Flask, request

# CONFIGURACIÓN DEL BOT
TOKEN = "7247621163:AAE2620h3cNDn-Pbt5gxgENQWqG5DTPD294"
WEBHOOK_URL = "https://e6f3-191-127-246-185.ngrok-free.app"  # Reemplaza con tu URL de ngrok

# URL de la API de Telegram
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

# INICIAR SERVIDOR FLASK
app = Flask(__name__)

# ✅ FUNCIÓN PARA ENVIAR MENSAJES A TELEGRAM
def enviar_mensaje(chat_id, mensaje):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensaje}
    requests.post(url, json=payload)

# ✅ WEBHOOK PARA RECIBIR MENSAJES DE TELEGRAM
@app.route("/webhook", methods=["POST"])
def recibir_actualizacion():
    datos = request.json
    if "message" in datos:
        chat_id = datos["message"]["chat"]["id"]
        mensaje = datos["message"].get("text", "")

        # Si el usuario escribe /start, envía su chat_id
        if mensaje == "/start":
            enviar_mensaje(chat_id, f"Hola, tu chat ID es: {chat_id}")

        # Si el usuario envía otro mensaje, responde de forma genérica
        else:
            enviar_mensaje(chat_id, "¡Hola! Soy un bot de notificaciones, te notificaré tus pacientes de Rayen.")

    return "OK", 200

# ✅ FUNCIÓN PARA CONFIGURAR EL WEBHOOK EN TELEGRAM
def configurar_webhook():
    url = f"{TELEGRAM_API_URL}/setWebhook?url={WEBHOOK_URL}/webhook"
    response = requests.get(url)
    print("📡 Webhook configurado:", response.json())

if __name__ == "__main__":
    configurar_webhook()  # Configura el Webhook al iniciar
    app.run(host="0.0.0.0", port=5000, debug=True)  # Inicia Flask
