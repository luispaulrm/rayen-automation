import os
import requests
import time
from flask import Flask, request
from threading import Thread
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://notirayen2.onrender.com/webhook")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

HEALTH_CHECK_INTERVAL = 120
RETRY_INTERVAL = 60
NOTIFICATION_INTERVAL = 12 * 60 * 60

app = Flask(__name__)

# Estados
user_states = {}  # {chat_id: {"paused": False, "stopped": False}}
last_notification_time = None

# Estado de control remoto
control_state = "reanudar"

def set_webhook():
    while True:
        try:
            url = f"{TELEGRAM_API_URL}/setWebhook?url={WEBHOOK_URL}"
            r = requests.get(url, timeout=10)
            result = r.json()
            if result.get("ok"):
                logger.info(f"Webhook configurado correctamente: {result}")
            else:
                logger.warning(f"Error configurando webhook: {result}")
        except Exception as e:
            logger.error(f"Error al configurar webhook: {e}")
        time.sleep(3600)

def keep_alive():
    while True:
        try:
            logger.info("🔄 Manteniendo instancia activa con solicitud interna...")
            health_url = "https://notirayen2.onrender.com/health"
            requests.get(health_url, timeout=10)
            logger.info("Actividad interna registrada")
        except Exception as e:
            logger.error(f"Error en keep_alive: {e}")
        time.sleep(HEALTH_CHECK_INTERVAL)

def retry_on_sleep():
    global last_notification_time
    while True:
        try:
            resp = requests.get(WEBHOOK_URL, timeout=10)
            if resp.status_code != 200:
                current_time = time.time()
                if last_notification_time is None or (current_time - last_notification_time >= NOTIFICATION_INTERVAL):
                    logger.warning("Instancia parece estar dormida. Intentando reiniciar...")
                    notify_sleep()
                    last_notification_time = current_time
        except Exception as e:
            logger.error(f"Error en retry_on_sleep: {e}")
        time.sleep(RETRY_INTERVAL)

def notify_sleep():
    try:
        chat_id = "7294987620"  # Ajusta con tu chat ID de alerta
        mensaje = "⚠️ El servicio en Render se ha dormido. Por favor, realiza un deploy manual."
        payload = {"chat_id": chat_id, "text": mensaje}
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload, timeout=10)
        logger.warning(f"Notificación enviada a Telegram: {mensaje}")
    except Exception as e:
        logger.error(f"Error al enviar notificación de sueño: {e}")

def enviar_mensaje(chat_id, texto):
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        payload = {"chat_id": chat_id, "text": texto}
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            logger.info(f"Mensaje enviado a {chat_id}: {r.json()}")
        else:
            logger.error(f"Fallo al enviar mensaje a {chat_id}: {r.status_code} - {r.text}")
    except Exception as e:
        logger.error(f"Error enviando mensaje a {chat_id}: {e}")

# NUEVO: función para enviar el botón "Ver Comandos"
def enviar_boton_menu(chat_id):
    """
    Envía un botón Inline Keyboard (texto: "Ver comandos").
    Al hacer clic, el bot recibirá un callback_query con data="ver_comandos".
    """
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "Ver comandos",
                    "callback_data": "ver_comandos"
                }
            ]
        ]
    }
    payload = {
        "chat_id": chat_id,
        "text": "Haz clic en el botón para ver los comandos disponibles:",
        "reply_markup": keyboard
    }
    url = f"{TELEGRAM_API_URL}/sendMessage"
    requests.post(url, json=payload, timeout=10)

# Rutas para control remoto
@app.route("/control", methods=["GET"])
def get_control():
    return {"estado": control_state}, 200

@app.route("/control", methods=["POST"])
def set_control():
    global control_state
    try:
        data = request.json
        nuevo_estado = data.get("estado", "").lower()
        if nuevo_estado in ["pausado", "reanudar", "detener"]:
            control_state = nuevo_estado
            logger.info(f"Control actualizado: {control_state}")
            return {"ok": True, "estado": control_state}, 200
        else:
            return {"ok": False, "error": "estado inválido"}, 400
    except Exception as e:
        logger.error(f"Error actualizando control: {e}")
        return {"ok": False, "error": str(e)}, 500

@app.route("/", methods=["GET", "HEAD"])
def index():
    logger.info("Ping recibido en /")
    return "OK", 200

@app.route("/webhook", methods=["POST", "GET"])
def recibir_webhook():
    logger.info(f"Solicitud recibida en /webhook: {request.method}")
    if request.method == "POST":
        try:
            datos = request.json
            logger.info(f"Datos recibidos: {datos}")

            # 1) Manejo de callback_query (cuando el usuario hace clic en un botón)
            if "callback_query" in datos:
                cb = datos["callback_query"]
                cb_chat_id = cb["message"]["chat"]["id"]
                cb_data = cb.get("data", "")

                # Responder a la callback, para eliminar el “relojito” en la interfaz
                answer_url = f"{TELEGRAM_API_URL}/answerCallbackQuery"
                requests.post(answer_url, json={"callback_query_id": cb["id"]}, timeout=10)

                if cb_data == "ver_comandos":
                    # Devuelve la lista de comandos en un mensaje
                    enviar_mensaje(cb_chat_id, "ℹ️ Comandos disponibles: /start, /pausar, /reanudar, /estado, /detener")
                return "OK", 200

            # 2) Manejo de message normal
            if "message" in datos:
                chat_id = str(datos["message"]["chat"]["id"])
                mensaje = datos["message"].get("text", "").lower()

                # Asegúrate de que el usuario tenga un estado en user_states
                if chat_id not in user_states:
                    user_states[chat_id] = {"paused": False, "stopped": False}

                if mensaje == "/start":
                    # En vez de mandar "Hola tu chat ID...", ahora enviamos el botón "Ver comandos"
                    enviar_boton_menu(chat_id)

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
                    # Texto cuando no coincide con ninguno
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

Thread(target=set_webhook, daemon=True).start()
Thread(target=keep_alive, daemon=True).start()
Thread(target=retry_on_sleep, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


