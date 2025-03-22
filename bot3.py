import os
import requests
import time
from flask import Flask, request
from threading import Thread
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========================================================
# 1. Variables de entorno y configuración
# ========================================================
TOKEN = os.environ.get("TOKEN", "")
# Ajusta la URL a tu nuevo dominio en Render:
# Por ejemplo, si tu nueva app en Render se llama "notirayen2",
# la URL sería "https://notirayen2.onrender.com/webhook"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://notirayen2.onrender.com/webhook")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

# Intervalos
HEALTH_CHECK_INTERVAL = 120  # 2 minutos
RETRY_INTERVAL = 60          # 1 minuto
NOTIFICATION_INTERVAL = 12 * 60 * 60  # 12 horas

app = Flask(__name__)

# Estado de notificaciones por usuario
user_states = {}  # {chat_id: {"paused": False, "stopped": False}}
last_notification_time = None


# ========================================================
# 2. Función para configurar el webhook periódicamente
# ========================================================
def set_webhook():
    """
    Intenta configurar el webhook cada cierto tiempo (1 hora).
    Esto es útil por si Render se duerme y el bot se reinicia.
    """
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
        # Reintenta cada hora
        time.sleep(3600)


# ========================================================
# 3. Función para mantener la instancia activa en Render
# ========================================================
def keep_alive():
    """
    Llama cada 2 minutos a la ruta '/health' para que Render
    no ponga la app en reposo por inactividad.
    """
    while True:
        try:
            logger.info("🔄 Manteniendo instancia activa con solicitud interna...")
            # Ajusta la URL a tu nuevo dominio en Render:
            health_url = "https://notirayen2.onrender.com/health"
            requests.get(health_url, timeout=10)
            logger.info("Actividad interna registrada")
        except Exception as e:
            logger.error(f"Error en keep_alive: {e}")
        time.sleep(HEALTH_CHECK_INTERVAL)


# ========================================================
# 4. Función para verificar si la app está dormida
# ========================================================
def retry_on_sleep():
    """
    Llama a la URL base (WEBHOOK_URL) cada minuto para verificar
    si la app responde con 200. Si no, envía una notificación de
    que la instancia puede haberse dormido.
    """
    global last_notification_time
    while True:
        try:
            response = requests.get(WEBHOOK_URL, timeout=10)
            if response.status_code != 200:
                current_time = time.time()
                # Verificar si han pasado 12 horas desde la última notificación
                if last_notification_time is None or (current_time - last_notification_time >= NOTIFICATION_INTERVAL):
                    logger.warning("Instancia parece estar dormida. Intentando reiniciar...")
                    notify_sleep()
                    last_notification_time = current_time
        except Exception as e:
            logger.error(f"Error en retry_on_sleep: {e}")
        time.sleep(RETRY_INTERVAL)


# ========================================================
# 5. Notificar por Telegram si Render se duerme
# ========================================================
def notify_sleep():
    """
    Envía un aviso a un chat_id específico indicando que el servicio
    podría haberse dormido.
    """
    try:
        # Reemplaza con el chat_id donde quieras recibir alertas
        chat_id = "7294987620"
        mensaje = "⚠️ El servicio en Render se ha dormido. Por favor, realiza un deploy manual o espera a que se reactive."
        payload = {"chat_id": chat_id, "text": mensaje}
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload, timeout=10)
        logger.warning(f"Notificación enviada a Telegram: {mensaje}")
    except Exception as e:
        logger.error(f"Error al enviar notificación de sueño: {e}")


# ========================================================
# 6. Función para enviar mensajes a Telegram
# ========================================================
def enviar_mensaje(chat_id, mensaje):
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensaje}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info(f"Mensaje enviado a {chat_id}: {response.json()}")
        else:
            logger.error(f"Fallo al enviar mensaje a {chat_id}: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error enviando mensaje a {chat_id}: {e}")


# ========================================================
# 7. Iniciar los hilos en segundo plano
# ========================================================
Thread(target=set_webhook, daemon=True).start()
Thread(target=keep_alive, daemon=True).start()
Thread(target=retry_on_sleep, daemon=True).start()


# ========================================================
# 8. Rutas Flask
# ========================================================
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
            logger.info(f"Datos recibidos: {datos}")  # Depuración: mostrar datos recibidos
            if "message" in datos:
                chat_id = str(datos["message"]["chat"]["id"])
                mensaje = datos["message"].get("text", "").lower()

                # Inicializar estado para el usuario si no existe
                if chat_id not in user_states:
                    user_states[chat_id] = {"paused": False, "stopped": False}

                if mensaje == "/start":
                    logger.info(f"Procesando /start para chat_id: {chat_id}")
                    try:
                        enviar_mensaje(chat_id, f"Hola, tu chat ID es: {chat_id}")
                    except Exception as e:
                        logger.error(f"Error al enviar mensaje de /start: {e}")

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


# ========================================================
# 9. Main: iniciar la app en Render
# ========================================================
if __name__ == "__main__":
    # Render espera que la app corra en el puerto 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
