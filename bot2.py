import os
import requests
import time
from flask import Flask, request
from threading import Thread

# Obtener variables de entorno
TOKEN = os.environ.get("TOKEN", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://rayenbot4.onrender.com/webhook")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

# Función para configurar o verificar el webhook
def set_webhook():
    while True:
        try:
            url = f"{TELEGRAM_API_URL}/setWebhook?url={WEBHOOK_URL}"
            response = requests.get(url, timeout=10)
            result = response.json()
            if result.get("ok"):
                print(f"Webhook configurado correctamente: {result}")
            else:
                print(f"Error configurando webhook: {result}")
        except Exception as e:
            print(f"Error al configurar webhook: {e}")
        time.sleep(3600)  # Reintentar cada hora

# Iniciar la configuración del webhook en un hilo separado
Thread(target=set_webhook, daemon=True).start()

@app.route("/", methods=["GET", "HEAD"])
def index():
    print("Ping recibido en /")
    return "OK", 200

@app.route("/webhook", methods=["POST", "GET"])
def recibir_actualizacion():
    print(f"Solicitud recibida en /webhook: {request.method}")
    if request.method == "POST":
        try:
            datos = request.json
            if "message" in datos:
                chat_id = datos["message"]["chat"]["id"]
                mensaje = datos["message"].get("text", "").lower()
                
                if mensaje == "/start":
                    enviar_mensaje(chat_id, f"Hola, tu chat ID es: {chat_id}")
                else:
                    enviar_mensaje(chat_id, "No entiendo el mensaje. Usa /start para obtener tu ID.")
            return "OK", 200
        except Exception as e:
            print(f"Error procesando mensaje: {e}")
            return "Error", 500
    elif request.method == "GET":
        print("Ping recibido en /webhook")
        return "Bot is alive!", 200

def enviar_mensaje(chat_id, mensaje):
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensaje}
        response = requests.post(url, json=payload, timeout=10)
        print(f"Mensaje enviado: {response.json()}")
    except Exception as e:
        print(f"Error enviando mensaje: {e}")

@app.route("/health", methods=["GET"])
def health_check():
    print("Chequeo de salud recibido")
    return "OK", 200

if __name__ == "__main__":
    # Ejecutar el servidor en el puerto esperado por Render (8080)
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
