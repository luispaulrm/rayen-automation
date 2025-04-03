import os
import requests
import time
from flask import Flask, request, send_file
from threading import Thread
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN", "TU_TOKEN_AQUÍ")  # Configura el token en Render
WEBHOOK_URL = "https://notirayen2.onrender.com/webhook"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

HEALTH_CHECK_INTERVAL = 120
RETRY_INTERVAL = 60
NOTIFICATION_INTERVAL = 12 * 60 * 60

app = Flask(__name__)

# Almacenamiento de estados y comandos
user_states = {}  # {chat_id: {"paused": False, "stopped": False}}
instance_commands = {}  # {instance_id: [{"chat_id": chat_id, "command": command}]}
last_notification_time = None

# -----------------------------
# Funciones de Telegram
# -----------------------------
def enviar_mensaje_telegram(chat_id, texto):
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            logger.info(f"Mensaje enviado a {chat_id}: {texto}")
        else:
            logger.error(f"Fallo al enviar mensaje: {r.text}")
    except Exception as e:
        logger.error(f"Error enviando mensaje: {e}")

def enviar_mensaje_con_botones(chat_id, mensaje, opciones):
    keyboard = {"inline_keyboard": [opciones]}
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensaje, "reply_markup": keyboard, "parse_mode": "Markdown"}
    requests.post(url, json=payload, timeout=10)

# -----------------------------
# Funciones de mantenimiento
# -----------------------------
def set_webhook():
    url = f"{TELEGRAM_API_URL}/setWebhook?url={WEBHOOK_URL}"
    resp = requests.get(url, timeout=10)
    if resp.json().get("ok"):
        logger.info("Webhook configurado correctamente")
    else:
        logger.warning(f"Error configurando webhook: {resp.text}")

def keep_alive():
    while True:
        requests.get("https://notirayen2.onrender.com/health", timeout=10)
        time.sleep(HEALTH_CHECK_INTERVAL)

def retry_on_sleep():
    global last_notification_time
    while True:
        resp = requests.get(WEBHOOK_URL, timeout=10)
        if resp.status_code != 200 and (last_notification_time is None or (time.time() - last_notification_time >= NOTIFICATION_INTERVAL)):
            enviar_mensaje_telegram("7294987620", "⚠️ El servicio en Render se ha dormido.")
            last_notification_time = time.time()
        time.sleep(RETRY_INTERVAL)

# -----------------------------
# Rutas Flask
# -----------------------------
@app.route("/", methods=["GET", "HEAD"])
def index():
    return "OK", 200

@app.route("/webhook", methods=["POST"])
def recibir_webhook():
    datos = request.json
    if "callback_query" in datos:
        cb = datos["callback_query"]
        chat_id = str(cb["message"]["chat"]["id"])
        cb_data = cb.get("data", "")
        requests.post(f"{TELEGRAM_API_URL}/answerCallbackQuery", json={"callback_query_id": cb["id"]}, timeout=10)
        
        if cb_data.startswith("ina:") or cb_data.startswith("nina:"):
            parts = cb_data.split(":")
            instance_id = parts[1]
            action = parts[0]
            datos_paciente = parts[2]
            if instance_id not in instance_commands:
                instance_commands[instance_id] = []
            instance_commands[instance_id].append({"chat_id": chat_id, "command": f"{action}:{datos_paciente}"})
            enviar_mensaje_telegram(chat_id, f"Procesando {action} para {datos_paciente} en instancia {instance_id}")
        return "OK", 200

    if "message" in datos:
        chat_id = str(datos["message"]["chat"]["id"])
        mensaje = datos["message"].get("text", "").lower()
        
        if chat_id not in user_states:
            user_states[chat_id] = {"paused": False, "stopped": False}
        
        if mensaje.startswith("/"):
            if mensaje == "/start":
                enviar_mensaje_telegram(chat_id, f"Hola, tu chat ID es: {chat_id}\nComandos: /pausar, /reanudar, /estado, /detener, /mostrar_jornada, /localizar_inasistentes")
            else:
                for instance_id in instance_commands.keys():
                    instance_commands[instance_id].append({"chat_id": chat_id, "command": mensaje})
                enviar_mensaje_telegram(chat_id, f"Comando {mensaje} enviado a todas las instancias.")
        return "OK", 200
    return "OK", 200

@app.route("/notify", methods=["POST"])
def recibir_notificacion():
    data = request.json
    chat_id = data["chat_id"]
    message = data["message"]
    instance_id = data["instance_id"]
    _send_all = data.get("_send_all", False)
    enviar_mensaje_telegram(chat_id, f"[Instancia {instance_id}] {message}")
    if chat_id == CHAT_ID and not _send_all and CHAT_ID2:
        enviar_mensaje_telegram(CHAT_ID2, f"[Instancia {instance_id}] {message}")
    return {"ok": True}, 200

@app.route("/notify_with_buttons", methods=["POST"])
def recibir_notificacion_con_botones():
    data = request.json
    chat_id = data["chat_id"]
    message = data["message"]
    options = data["options"]
    instance_id = data["instance_id"]
    enviar_mensaje_con_botones(chat_id, f"[Instancia {instance_id}] {message}", options)
    return {"ok": True}, 200

@app.route("/commands/<instance_id>", methods=["GET"])
def enviar_comandos(instance_id):
    if instance_id not in instance_commands:
        instance_commands[instance_id] = []
    comandos = instance_commands[instance_id]
    instance_commands[instance_id] = []  # Limpiar después de enviar
    return {"commands": comandos}, 200

@app.route("/health", methods=["GET"])
def health_check():
    return "OK", 200

# Iniciar hilos
Thread(target=set_webhook, daemon=True).start()
Thread(target=keep_alive, daemon=True).start()
Thread(target=retry_on_sleep, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
