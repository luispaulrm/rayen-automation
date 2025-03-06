import os
import requests
from flask import Flask, request

# Lee TOKEN y WEBHOOK_URL de las variables de entorno
# (en Render, las defines en la sección "Environment")
TOKEN = os.environ.get("TOKEN", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

# Construye la URL base de la API de Telegram
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

def set_webhook():
    """
    Configura el webhook en Telegram apuntando a WEBHOOK_URL.
    Debe llamarse en algún momento (ej: al inicio).
    """
    url = f"{TELEGRAM_API_URL}/setWebhook?url={WEBHOOK_URL}"
    response = requests.get(url)
    print("Webhook configurado:", response.json())

@app.route("/", methods=["GET", "HEAD"])
def index():
    """
    Ruta raíz para devolver OK y así evitar 404 en HEAD /
    """
    return "OK", 200

@app.route("/webhook", methods=["POST"])
def recibir_actualizacion():
    """
    Aquí Telegram enviará los mensajes:
    - Extraemos chat_id y texto.
    - Respondemos acorde.
    """
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
    """
    Envía texto a Telegram usando la API del bot.
    """
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensaje}
    requests.post(url, json=payload)

@app.route("/health")
def health_check():
    """
    Ruta opcional para ver si la app está viva en Render.
    """
    return "OK", 200

if __name__ == "__main__":
    # Llama a set_webhook() solo si ejecutas este archivo con "python <archivo.py>" localmente
    # En Render, estarás usando gunicorn, y el "app.run()" no se utiliza.
    set_webhook()
    # app.run(host="0.0.0.0", port=5000, debug=True)  # Solo para pruebas locales
