import os
import requests
import time
from flask import Flask, request
from threading import Thread
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Obtener variables de entorno
TOKEN = os.environ.get("TOKEN", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://rayenbot4.onrender.com/webhook")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"
HEALTH_CHECK_INTERVAL = 300  # 5 minutos en segundos
RETRY_INTERVAL = 60  # 1 minuto en segundos para reintentos

app = Flask(__name__)

# Función para configurar o verificar el webhook
def set_webhook():
    while True:
        try:
            url = f"{TELEGRAM_API_URL}/setWebhook?url={WEBHOOK_URL}"
            response = requests.get(url, timeout=10)
            result = response.json()
            if result.get("ok"):
                logger.info(f"Webhook configurado correctamente: {result}")
            else:
                logger.warning(f"Error configurando webhook: {result}")
        except Exception as e:
            logger.error(f"Error al configurar webhook: {e}")
        time.sleep(3600)  # Reintentar cada hora

# Función para mantener la instancia activa
def keep_alive():
    while True:
        try:
            logger.info("🔄 Manteniendo instancia activa con solicitud interna...")
            # Hacer una solicitud al endpoint de salud para simular actividad
            requests.get(f"{WEBHOOK_URL}/health", timeout=10)
            # Opcional: registrar un log para forzar actividad
            logger.info("Actividad interna registrada")
        except Exception as e:
            logger.error(f"Error en keep_alive: {e}")
        time.sleep(HEALTH_CHECK_INTERVAL)  # Cada 5 minutos

# Función para reintentar tras suspensión
def retry_on_sleep():
    while True:
        try:
            # Verificar si la instancia está activa enviando una solicitud a sí misma
            response = requests.get(WEBHOOK_URL, timeout=10)
            if response.status_code != 200:
                logger.warning("Instancia parece estar dormida. Intentando reiniciar...")
                # Aquí no podemos reiniciar directamente, pero notificamos
                notify_sleep()
        except Exception as e:
            logger.error(f"Error en retry_on_sleep: {e}")
        time.sleep(RETRY_INTERVAL)  # Revisar cada minuto

# Notificar vía Telegram si el servicio se duerme
def notify_sleep():
    try:
        chat_id = "TU_CHAT_ID_AQUI"  # Reemplaza con un CHAT_ID donde quieras recibir notificaciones
        mensaje = "⚠️ El servicio en Render se ha dormido. Por favor, realiza un deploy manual o espera a que se reactive."
        payload = {"chat_id": chat_id, "text": mensaje}
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload, timeout=10)
        logger.warning(f"Notificación enviada a Telegram: {mensaje}")
    except Exception as e:
        logger.error(f"Error al enviar notificación de sueño: {e}")

# Iniciar los hilos
Thread(target=set_webhook, daemon=True).start()
Thread(target=keep_alive, daemon=True).start()
Thread(target=retry_on_sleep, daemon=True).start()

@app.route("/", methods=["GET", "HEAD"])
def index():
    logger.info("Ping recibido en /")
    return "OK", 200

@app.route("/webhook", methods=["POST", "GET"])
def recibir_actualizacion():
    logger.info(f"Solicitud recibida en /webhook: {request.method}")
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
            logger.error(f"Error procesando mensaje: {e}")
            return "Error", 500
    elif request.method == "GET":
        logger.info("Ping recibido en /webhook")
        return "Bot is alive!", 200

def enviar_mensaje(chat_id, mensaje):
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensaje}
        response = requests.post(url, json=payload, timeout=10)
        logger.info(f"Mensaje enviado: {response.json()}")
    except Exception as e:
        logger.error(f"Error enviando mensaje: {e}")

@app.route("/health", methods=["GET"])
def health_check():
    logger.info("Chequeo de salud recibido")
    return "OK", 200

if __name__ == "__main__":
    # Ejecutar el servidor en el puerto esperado por Render (8080)
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
