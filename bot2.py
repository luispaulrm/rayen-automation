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

# Diccionario para almacenar el estado de notificaciones por CHAT_ID
user_states = {}  # {chat_id: {"paused": False, "stopped": False}}

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
            requests.get(f"{WEBHOOK_URL}/health", timeout=10)
            logger.info("Actividad interna registrada")
        except Exception as e:
            logger.error(f"Error en keep_alive: {e}")
        time.sleep(HEALTH_CHECK_INTERVAL)  # Cada 5 minutos

# Función para reintentar tras suspensión
def retry_on_sleep():
    while True:
        try:
            response = requests.get(WEBHOOK_URL, timeout=10)
            if response.status_code != 200:
                logger.warning("Instancia parece estar dormida. Intentando reiniciar...")
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

# Función para enviar mensajes a Telegram
def enviar_mensaje(chat_id, mensaje):
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensaje}
        response = requests.post(url, json=payload, timeout=10)
        logger.info(f"Mensaje enviado a {chat_id}: {response.json()}")
    except Exception as e:
        logger.error(f"Error enviando mensaje a {chat_id}: {e}")

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
                chat_id = str(datos["message"]["chat"]["id"])
                mensaje = datos["message"].get("text", "").lower()

                # Inicializar estado para el usuario si no existe
                if chat_id not in user_states:
                    user_states[chat_id] = {"paused": False, "stopped": False}

                if mensaje == "/start":
                    enviar_mensaje(chat_id, f"Hola, tu chat ID es: {chat_id}")
                elif mensaje == "/pausar" and not user_states[chat_id]["stopped"]:
                    if user_states[chat_id]["paused"]:
                        enviar_mensaje(chat_id, "ℹ️ Las notificaciones ya están pausadas.")
                    else:
                        user_states[chat_id]["paused"] = True
                        enviar_mensaje(chat_id, "🔇 Notificaciones pausadas.")
                elif mensaje == "/reanudar" and not user_states[chat_id]["stopped"]:
                    if not user_states[chat_id]["paused"]:
                        enviar_mensaje(chat_id, "ℹ️ Las notificaciones ya están activas.")
                    else:
                        user_states[chat_id]["paused"] = False
                        enviar_mensaje(chat_id, "🔔 Notificaciones reanudadas.")
                elif mensaje == "/estado" and not user_states[chat_id]["stopped"]:
                    estado = "🔇 Pausadas" if user_states[chat_id]["paused"] else "🔔 Activas"
                    enviar_mensaje(chat_id, f"ℹ️ Estado: {estado}")
                elif mensaje == "/detener":
                    if user_states[chat_id]["stopped"]:
                        enviar_mensaje(chat_id, "ℹ️ El bot ya está detenido.")
                    else:
                        user_states[chat_id]["stopped"] = True
                        user_states[chat_id]["paused"] = False
                        enviar_mensaje(chat_id, "⛔ Bot detenido.")
                else:
                    enviar_mensaje(chat_id, "ℹ️ Comandos disponibles: /start, /pausar, /reanudar, /estado, /detener")
            return "OK", 200
        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}")
            return "Error", 500
    elif request.method == "GET":
        logger.info("Ping recibido en /webhook")
        return "Bot is alive!", 200

@app.route("/health", methods=["GET"])
def health_check():
    logger.info("Chequeo de salud recibido")
    return "OK", 200

if __name__ == "__main__":
    # Ejecutar el servidor en el puerto esperado por Render (8080)
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
