import requests
from flask import Flask, request
import os

# Configuración del bot
TOKEN = os.environ.get("TOKEN")  # Leer el token desde las variables de entorno
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # Leer la URL del webhook desde las variables de entorno
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

# Iniciar servidor Flask
app = Flask(__name__)

# Función para configurar el webhook automáticamente
def set_webhook():
    url = f"{TELEGRAM_API_URL}/setWebhook?url={WEBHOOK_URL}"
    response = requests.get(url)
    print("Webhook configurado:", response.json())

# Ruta para recibir mensajes de Telegram
@app.route("/webhook", methods=["POST"])
def recibir_actualizacion():
    datos = request.json
    if "message" in datos:
        chat_id = datos["message"]["chat"]["id"]
        mensaje = datos["message"].get("text", "")
        
        # Si el usuario envía /start, responde con su chat_id
        if mensaje.lower() == "/start":
            enviar_mensaje(chat_id, f"Hola, tu chat ID es: {chat_id}")
        else:
            enviar_mensaje(chat_id, "No entiendo el mensaje. Usa /start para obtener tu ID.")
    return "OK", 200

# Función para enviar mensajes a Telegram
def enviar_mensaje(chat_id, mensaje):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensaje}
    requests.post(url, json=payload)

# Ruta de salud para mantener activo el bot en Render
@app.route("/health")
def health_check():
    return "OK", 200

if __name__ == "__main__":
    set_webhook()  # Configura el webhook al iniciar
    PORT = int(os.environ.get("PORT", 5000))  # Usa puerto dinámico o 5000 por defecto
    app.run(host="0.0.0.0", port=PORT)