import requests
from flask import Flask, request
import os

# Configuración del bot
TOKEN = os.environ.get("TOKEN")  # Leer el token desde las variables de entorno
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # Leer la URL del webhook desde las variables de entorno
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

# Función para configurar el webhook automáticamente
def set_webhook():
    # Asegúrate de que WEBHOOK_URL empiece por https:// y termine con /webhook
    url = f"{TELEGRAM_API_URL}/setWebhook?url={WEBHOOK_URL}"
    response = requests.get(url)
    print("Webhook configurado:", response.json())

# Ruta raíz: evita el 404 en HEAD /
@app.route("/", methods=["GET", "HEAD"])
def index():
    return "OK", 200

# Ruta para recibir mensajes de Telegram
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

# Función para enviar mensajes a Telegram
def enviar_mensaje(chat_id, mensaje):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensaje}
    requests.post(url, json=payload)

# Ruta de salud para mantener activo el bot en Render (opcional)
@app.route("/health")
def health_check():
    return "OK", 200

# Al iniciar, configura el webhook
# IMPORTANTE: No ejecutar app.run(...) cuando usemos gunicorn
if __name__ == "__main__":
    set_webhook()
    # Si necesitas probar localmente, podrías hacerlo con:
    # app.run(host="0.0.0.0", port=5000, debug=True)
