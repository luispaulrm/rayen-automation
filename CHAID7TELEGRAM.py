from datetime import datetime, timedelta
import os
import tkinter as tk
from tkinter import messagebox
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
import time
import random
import pyttsx3
import psutil
import sys
from flask import Flask, request
import requests
from webdriver_manager.chrome import ChromeDriverManager

# Para Selenium 4+
from selenium.webdriver.chrome.service import Service

# ---------------------------------------------------------------------------
# Caducidad
# ---------------------------------------------------------------------------
FECHA_CADUCIDAD = datetime(2025, 4, 5)  # Ajusta la fecha de caducidad deseada
if datetime.now() > FECHA_CADUCIDAD:
    print("Este software ha caducado. Por favor contacte al proveedor para renovarlo.")
    sys.exit(1)

# Configuración del bot de Telegram (leer desde variables de entorno)
TOKEN = os.environ.get("TOKEN", "7247621163:AAE2620h3cNDn-Pbt5gxgENQWqG5DTPD294")  # Default si no está en entorno
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://rayenbot3.onrender.com/webhook")  # Default si no está en entorno
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Evitar múltiples instancias del script
# ---------------------------------------------------------------------------
def check_if_running():
    script_name = os.path.basename(__file__)
    count = 0
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if proc.info['name'] == 'python.exe' and script_name in proc.cmdline():
                count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    if count > 1:
        print("❌ Otra instancia del script ya está ejecutándose.")
        sys.exit(1)

check_if_running()

# ---------------------------------------------------------------------------
# Archivo de configuración y funciones de configuración
# ---------------------------------------------------------------------------
CONFIG_FILE = "config.json"

def guardar_config(usuario, contraseña, ubicacion, chat_id):
    config = {
        "credenciales": {
            "usuario": usuario,
            "contraseña": contraseña,
            "ubicacion": ubicacion,
            "telegram_chat_id": chat_id
        }
    }
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
            json.dump(config, configfile, indent=4, ensure_ascii=False)
        print(f"✅ Configuración guardada en {CONFIG_FILE}.")
    except PermissionError as pe:
        print(f"❌ No se pudo guardar {CONFIG_FILE}. Error de permisos: {pe}")
        raise
    except Exception as e:
        print(f"❌ Error al guardar {CONFIG_FILE}: {e}")
        raise

def cargar_config():
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as configfile:
            config = json.load(configfile)
            usuario = config['credenciales'].get('usuario', '').strip()
            contraseña = config['credenciales'].get('contraseña', '').strip()
            ubicacion = config['credenciales'].get('ubicacion', '').strip()
            chat_id = config['credenciales'].get('telegram_chat_id', '').strip()

            if not all([usuario, contraseña, ubicacion, chat_id]):
                print(f"⚠️ Configuración incompleta o corrupta en {CONFIG_FILE}. Se intentará eliminar.")
                eliminar_config_con_reintentos()
                return None

            return (usuario, contraseña, ubicacion, chat_id)
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"❌ Error al leer {CONFIG_FILE}: {e}. Se intentará eliminar el archivo corrupto.")
        eliminar_config_con_reintentos()
        return None
    except PermissionError as pe:
        print(f"❌ No se pudo leer {CONFIG_FILE} debido a un error de permisos: {pe}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado al leer {CONFIG_FILE}: {e}")
        return None

def eliminar_config_con_reintentos():
    if not os.path.exists(CONFIG_FILE):
        print(f"✅ El archivo {CONFIG_FILE} ya no existe.")
        return True
    max_intentos = 5
    for intento in range(max_intentos):
        try:
            os.remove(CONFIG_FILE)
            print(f"✅ Archivo {CONFIG_FILE} eliminado correctamente.")
            return True
        except PermissionError as pe:
            print(f"⚠️ Intento {intento + 1}/{max_intentos}: No se pudo eliminar {CONFIG_FILE}. Error: {pe}. Reintentando...")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Intento {intento + 1}/{max_intentos}: Error inesperado al eliminar {CONFIG_FILE}: {e}. Reintentando...")
            time.sleep(1)
    print(f"❌ No se pudo eliminar {CONFIG_FILE} después de {max_intentos} intentos.")
    return False

def mostrar_formulario():
    ventana = tk.Tk()
    ventana.title("Configuración Inicial")
    ventana.geometry("400x350")
    fuente_profesional = ("Arial", 11)
    main_frame = tk.Frame(ventana, padx=20, pady=20)
    main_frame.pack(expand=True, fill="both")
    config_data = cargar_config()

    usuario_valor = config_data[0] if config_data else ""
    contraseña_valor = config_data[1] if config_data else ""
    ubicacion_valor = config_data[2] if config_data else "cecosfeduardofrei"
    chat_id_valor = config_data[3] if config_data else ""

    def crear_campo(label_text, value, show=None, is_menu=False, options=None):
        frame = tk.Frame(main_frame)
        frame.pack(fill="x", pady=5)
        tk.Label(frame, text=label_text, font=fuente_profesional, width=15, anchor="e").pack(side=tk.LEFT, padx=5)
        if is_menu and options:
            var = tk.StringVar(value=value)
            menu = tk.OptionMenu(frame, var, *options)
            menu.config(font=fuente_profesional)
            menu.pack(side=tk.LEFT, fill="x", expand=True)
            return var
        else:
            entry = tk.Entry(frame, font=fuente_profesional, show=show)
            entry.insert(0, value)
            entry.pack(side=tk.LEFT, fill="x", expand=True)
            return entry

    ubicacion_opciones = ["cecosfeduardofrei", "cesfameduardofrei"]

    entry_usuario = crear_campo("Usuario Rayen:", usuario_valor)
    entry_contraseña = crear_campo("Contraseña:", contraseña_valor, show="*")
    ubicacion_var = crear_campo("Ubicación:", ubicacion_valor, is_menu=True, options=ubicacion_opciones)
    entry_chat_id = crear_campo("Chat ID Telegram:", chat_id_valor)

    mostrar_pass = tk.BooleanVar()
    mostrar_pass.set(False)
    check_pass = tk.Checkbutton(
        main_frame,
        text="Mostrar contraseña",
        font=fuente_profesional,
        variable=mostrar_pass,
        command=lambda: entry_contraseña.config(show="" if mostrar_pass.get() else "*")
    )
    check_pass.pack(pady=5)

    def guardar_y_cerrar():
        usuario = entry_usuario.get().strip()
        contraseña = entry_contraseña.get().strip()
        ubicacion = ubicacion_var.get()
        chat_id = entry_chat_id.get().strip()
        if not (usuario and contraseña and ubicacion and chat_id):
            messagebox.showwarning("Error", "Todos los campos son obligatorios.", parent=ventana)
            return
        try:
            guardar_config(usuario, contraseña, ubicacion, chat_id)
            messagebox.showinfo("Éxito", "Configuración guardada. El formulario se reiniciará.", parent=ventana)
            ventana.destroy()
            mostrar_formulario()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la configuración: {e}", parent=ventana)

    def borrar_config():
        if os.path.exists(CONFIG_FILE):
            if not eliminar_config_con_reintentos():
                messagebox.showerror(
                    "Error",
                    f"No se pudo eliminar {CONFIG_FILE}. Revisa los permisos o cierra otros programas que puedan estar usando el archivo.",
                    parent=ventana
                )
                return
        entry_usuario.delete(0, "end")
        entry_contraseña.delete(0, "end")
        ubicacion_var.set("cecosfeduardofrei")
        entry_chat_id.delete(0, "end")
        mostrar_pass.set(False)
        messagebox.showinfo("Borrado", "El archivo config.json ha sido borrado. Puedes guardar nuevos datos.", parent=ventana)

    def cerrar_formulario():
        ventana.destroy()
        return

    button_frame = tk.Frame(main_frame)
    button_frame.pack(pady=10)
    tk.Button(button_frame, text="Guardar", font=fuente_profesional, command=guardar_y_cerrar).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Borrar config", font=fuente_profesional, command=borrar_config).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Cerrar", font=fuente_profesional, command=cerrar_formulario).pack(side=tk.LEFT, padx=5)

    try:
        ventana.mainloop()
    except KeyboardInterrupt:
        ventana.destroy()

print("📝 Mostrando formulario de configuración...")
mostrar_formulario()
config_data = cargar_config()
if not config_data or not all(config_data):
    print("❌ No se guardó la configuración correctamente. Cierra y vuelve a intentar.")
    input("Presiona Enter para cerrar...")
    exit()

USUARIO, CONTRASEÑA, UBICACION, TELEGRAM_CHAT_ID = config_data

# ---------------------------------------------------------------------------
# Inicializar el motor de voz
# ---------------------------------------------------------------------------
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 0.9)

# ---------------------------------------------------------------------------
# Variables globales: PACIENTE_ESPECIFICO, EVENTO_ACTIVO
# ---------------------------------------------------------------------------
PACIENTE_ESPECIFICO = None
HORA_CITA_ESPECIFICA = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
EVENTO_ACTIVO = True  # <--- Importante: Declaración global

# Función para configurar el webhook automáticamente
def set_webhook():
    url = f"{TELEGRAM_API_URL}/setWebhook?url={WEBHOOK_URL}"
    response = requests.get(url)
    print("Webhook configurado:", response.json())

# Función para enviar mensajes a Telegram
def enviar_mensaje(chat_id, mensaje):
    if len(mensaje) > 4096:  # Límite de Telegram para un mensaje
        mensaje = mensaje[:4092] + "..."
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensaje}
    response = requests.post(url, json=payload)
    print("Respuesta de enviar_mensaje:", response.json())  # Depuración
    return response.status_code == 200

# Ruta para recibir mensajes de Telegram (opcional, para interacción)
@app.route("/webhook", methods=["POST"])
def recibir_actualizacion():
    datos = request.json
    print("Datos recibidos:", datos)
    if "message" in datos:
        chat_id = datos["message"]["chat"]["id"]
        mensaje = datos["message"].get("text", "").lower()
        print(f"Mensaje recibido de chat_id {chat_id}: {mensaje}")
        if mensaje == "/start":
            enviar_mensaje(chat_id, f"Hola, tu chat ID es: {chat_id}")
        else:
            enviar_mensaje(chat_id, "No entiendo el mensaje. Usa /start para obtener tu ID.")
    return "OK", 200

# Ruta de salud para mantener activo el bot en Render
@app.route("/health")
def health_check():
    return "OK", 200

def esperar_carga_pagina(driver):
    WebDriverWait(driver, 30).until(lambda d: d.execute_script("return document.readyState") == "complete")

def iniciar_navegador():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-autofill")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-save-password-bubble")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    if os.environ.get("RENDER") == "true":  # Modo headless en Render
        options.add_argument("--headless")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("prefs", {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "autofill.profile_enabled": False,
        "autofill.credit_card_enabled": False,
        "formfill.enable": False
    })

    # Usar ChromeDriverManager para descargar automáticamente
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def hacer_clic(driver, metodo, selector, usar_js=False):
    try:
        WebDriverWait(driver, 30).until(EC.invisibility_of_element_located((By.CLASS_NAME, "cache-loading")))
        elemento = WebDriverWait(driver, 60).until(EC.element_to_be_clickable((metodo, selector)))
        time.sleep(random.uniform(2.0, 4.0))
        if usar_js:
            driver.execute_script("arguments[0].click();", elemento)
        else:
            elemento.click()
    except Exception as e:
        print(f"❌ Error al hacer clic en {selector}: {e}")
        raise

def escribir_input(driver, metodo, selector, texto):
    try:
        campo = WebDriverWait(driver, 60).until(EC.presence_of_element_located((metodo, selector)))
        campo.clear()
        time.sleep(random.uniform(0.5, 1.5))
        campo.send_keys(texto)
    except Exception as e:
        print(f"❌ Error al escribir en {selector}: {e}")
        raise

def iniciar_sesion(driver):
    driver.get("https://clinico.rayenaps.cl/#/actualizar-app")
    escribir_input(driver, By.ID, "location", UBICACION)
    escribir_input(driver, By.ID, "username", USUARIO)
    escribir_input(driver, By.ID, "password", CONTRASEÑA)
    hacer_clic(driver, By.XPATH, "//button[contains(text(), 'Ingresar')]")
    print("✅ Login exitoso.")

def navegar_a_pacientes_citados(driver):
    try:
        time.sleep(5)
        esperar_carga_pagina(driver)
        hacer_clic(driver, By.CLASS_NAME, "navbar-left-icon", usar_js=True)
        esperar_carga_pagina(driver)
        hacer_clic(driver, By.XPATH, "//span[contains(text(), 'Box')]", usar_js=True)
        time.sleep(2)
        esperar_carga_pagina(driver)

        max_intentos = 3
        for intento in range(max_intentos):
            try:
                pacientes_citados = WebDriverWait(driver, 60).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Pacientes citados')]"))
                )
                driver.execute_script("arguments[0].scrollIntoView();", pacientes_citados)
                time.sleep(1)
                pacientes_citados = WebDriverWait(driver, 60).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Pacientes citados')]"))
                )
                driver.execute_script("arguments[0].click();", pacientes_citados)
                print("✅ Navegación completa.")
                break
            except StaleElementReferenceException:
                print(f"⚠️ Intento {intento + 1}/{max_intentos}: Elemento 'Pacientes citados' desactualizado. Reintentando...")
                time.sleep(2)
                if intento == max_intentos - 1:
                    raise Exception("No se pudo hacer clic en 'Pacientes citados' después de múltiples intentos.")
    except Exception as e:
        print(f"❌ Error en la navegación: {e}")
        raise

def speak_message(message):
    if os.environ.get("RENDER") != "true":  # Solo reproduce voz si no está en Render
        try:
            engine.say(message)
            engine.runAndWait()
        except Exception as e:
            print(f"⚠️ Error al reproducir mensaje en voz: {e}")
    else:
        print(f"🎙️ Voz desactivada en Render: {message}")

def detectar_llegadas(driver):
    global PACIENTE_ESPECIFICO
    pacientes = []
    try:
        print("⏳ Esperando carga completa de la página...")
        WebDriverWait(driver, 120).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        print("✅ Página cargada completamente.")

        print("🔍 Buscando tabla de pacientes con clase 'rt-table'...")
        tabla_pacientes = WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.CLASS_NAME, "rt-table"))
        )
        print("✅ Tabla encontrada con clase 'rt-table'.")

        print("🔍 Buscando contenedor 'rt-tbody' dentro de la tabla...")
        tbody = WebDriverWait(tabla_pacientes, 60).until(
            EC.presence_of_element_located((By.CLASS_NAME, "rt-tbody"))
        )
        print("✅ Contenedor 'rt-tbody' encontrado.")

        print("🔍 Buscando filas con clase 'rt-tr-group' dentro de 'rt-tbody'...")
        filas = tbody.find_elements(By.CLASS_NAME, "rt-tr-group")
        print(f"📋 Encontradas {len(filas)} filas con clase 'rt-tr-group'.")

        for fila in filas:
            try:
                subfila = fila.find_element(By.CSS_SELECTOR, ".rt-tr")
                celdas = subfila.find_elements(By.CLASS_NAME, "rt-td")
                if len(celdas) >= 8:
                    paciente = {
                        "hora_cita": celdas[0].text.strip() if celdas[0].text.strip() else "00:00",
                        "estado": celdas[1].text.strip(),
                        "nombre": celdas[2].text.strip(),
                        "tipo_cupo": celdas[3].text.strip(),
                        "llegada": celdas[4].text.strip(),
                        "llamada": celdas[5].text.strip(),
                        "razon_cita": celdas[6].text.strip(),
                        "tipo_atencion": celdas[7].text.strip()
                    }
                    pacientes.append(paciente)

                    hora_cita_str = paciente["hora_cita"]
                    if hora_cita_str and hora_cita_str.strip():
                        try:
                            hora_cita = datetime.strptime(hora_cita_str, "%H:%M").replace(
                                year=datetime.now().year, month=datetime.now().month, day=datetime.now().day
                            )
                            if hora_cita == HORA_CITA_ESPECIFICA and PACIENTE_ESPECIFICO is None:
                                PACIENTE_ESPECIFICO = paciente["nombre"]
                        except ValueError:
                            print(f"⚠️ Formato de hora inválido para paciente {paciente['nombre']}: {hora_cita_str}.")
                else:
                    print(f"⚠️ Fila ignorada, no tiene suficientes celdas: {len(celdas)}")
            except Exception as e:
                print(f"⚠️ Error al procesar fila: {e}")
                continue

    except TimeoutException as e:
        print(f"❌ No se encontró la tabla de pacientes: {e}")
        return pacientes
    except Exception as e:
        print(f"❌ Error inesperado al buscar la tabla: {e}")
        return pacientes

    if not pacientes:
        print("❌ No se encontraron pacientes en la tabla después de procesar las filas.")
    else:
        print(f"✅ Se encontraron {len(pacientes)} pacientes en la tabla.")
    return pacientes

def verificar_paciente_especifico(driver):
    global EVENTO_ACTIVO, PACIENTE_ESPECIFICO
    if EVENTO_ACTIVO and PACIENTE_ESPECIFICO:
        ahora = datetime.now()
        if ahora.hour == 12 and ahora.minute == 1 and ahora.second == 0:
            pacientes = detectar_llegadas(driver)
            registrado = False
            for paciente in pacientes:
                hora_cita_str = paciente["hora_cita"]
                if hora_cita_str and hora_cita_str.strip():
                    try:
                        hora_cita = datetime.strptime(hora_cita_str, "%H:%M").replace(
                            year=datetime.now().year, month=datetime.now().month, day=datetime.now().day
                        )
                        if hora_cita == HORA_CITA_ESPECIFICA and paciente["nombre"] == PACIENTE_ESPECIFICO and paciente["llegada"]:
                            registrado = True
                            break
                    except ValueError:
                        print(f"⚠️ Formato de hora inválido al verificar paciente específico: {hora_cita_str}.")
            if not registrado:
                mensaje = f"El paciente {PACIENTE_ESPECIFICO} de la hora citada no se ha registrado"
                print(f"🎙️ Anunciando: {mensaje}")
                speak_message(mensaje)
                if not enviar_mensaje(TELEGRAM_CHAT_ID, mensaje):
                    print(f"❌ Falló el envío del mensaje a Telegram para paciente específico.")

def notificar_pacientes_citados_inicialmente(driver):
    global PACIENTE_ESPECIFICO, EVENTO_ACTIVO
    pacientes = detectar_llegadas(driver)
    if not pacientes:
        print("❌ No hay pacientes citados en este momento. Omitiendo notificación.")
        return

    ahora = datetime.now()
    print(f"⏰ Hora actual: {ahora.strftime('%H:%M:%S')}")

    pacientes_futuros = []
    for paciente in pacientes:
        hora_cita_str = paciente["hora_cita"]
        if hora_cita_str and hora_cita_str.strip():
            try:
                if len(hora_cita_str.split(":")[0]) == 1:
                    hora_cita_str = f"0{hora_cita_str}"
                hora_cita = datetime.strptime(hora_cita_str, "%H:%M").replace(
                    year=ahora.year, month=ahora.month, day=ahora.day
                )
                if hora_cita >= ahora:
                    pacientes_futuros.append((hora_cita, paciente))
            except ValueError as e:
                print(f"⚠️ Formato de hora inválido para {paciente['nombre']}: {hora_cita_str}. Error: {e}")

    pacientes_futuros.sort(key=lambda x: x[0])
    pacientes_proximos = [paciente for _, paciente in pacientes_futuros[:2]]

    if not pacientes_proximos:
        print("❌ No hay citas futuras hoy después de la hora actual. Omitiendo notificación.")
        return

    mensaje = "📋 Próximas citas:\n"
    for paciente in pacientes_proximos:
        mensaje += f"- {paciente['hora_cita']} - {paciente['nombre']}\n"

    if len(mensaje) > 4096:  # Límite de Telegram
        mensaje = mensaje[:4092] + "..."

    print(f"📢 Enviando mensaje: {mensaje}")
    if not enviar_mensaje(TELEGRAM_CHAT_ID, mensaje):
        print("❌ Falló el envío de la lista de próximas citas.")
    else:
        print("✅ Notificación enviada con las próximas citas.")

    for paciente in pacientes:
        hora_cita_str = paciente["hora_cita"]
        if hora_cita_str and hora_cita_str.strip():
            try:
                if len(hora_cita_str.split(":")[0]) == 1:
                    hora_cita_str = f"0{hora_cita_str}"
                hora_cita = datetime.strptime(hora_cita_str, "%H:%M").replace(
                    year=ahora.year, month=ahora.month, day=ahora.day
                )
                if hora_cita == HORA_CITA_ESPECIFICA and paciente["llegada"]:
                    EVENTO_ACTIVO = False
                    print(f"✅ El paciente {paciente['nombre']} ya se registró, evento anulado.")
            except ValueError:
                print(f"⚠️ Formato de hora inválido para {paciente['nombre']}: {hora_cita_str}.")

def notificar_pacientes_pendientes(pacientes):
    ahora = datetime.now()
    ventana_inferior = ahora - timedelta(minutes=60)
    ventana_superior = ahora + timedelta(minutes=60)
    pendientes_en_rango = []

    for paciente in pacientes:
        if paciente["estado"].lower() == "pendiente":
            hora_cita_str = paciente["hora_cita"].strip()
            if hora_cita_str:
                partes = hora_cita_str.split(":")
                if len(partes[0]) == 1:
                    hora_cita_str = f"0{hora_cita_str}"
                try:
                    hora_cita_dt = datetime.strptime(hora_cita_str, "%H:%M").replace(
                        year=ahora.year, month=ahora.month, day=ahora.day
                    )
                    if ventana_inferior <= hora_cita_dt <= ventana_superior:
                        pendientes_en_rango.append(paciente)
                except ValueError:
                    print(f"⚠️ Formato de hora inválido para {paciente['nombre']}: {hora_cita_str}")

    if pendientes_en_rango:
        mensaje = "📋 Pacientes PENDIENTES ±60min:\n"
        for p in pendientes_en_rango:
            mensaje += f"- {p['hora_cita']} - {p['nombre']} (Estado: {p['estado']})\n"
        if len(mensaje) > 4096:
            mensaje = mensaje[:4092] + "..."
        print(f"🎙️ Anunciando (voz):\n{mensaje}")
        speak_message(mensaje)
        print(f"📢 Enviando mensaje a Telegram:\n{mensaje}")
        if not enviar_mensaje(TELEGRAM_CHAT_ID, mensaje):
            print("❌ Falló el envío del mensaje de pendientes a Telegram.")

def mostrar_aviso_en_pantalla(driver, pacientes):
    if not pacientes:
        mensaje = "No se encontraron pacientes en la tabla."
    else:
        mensaje = "📋 Pacientes citados:\n"
        for paciente in pacientes:
            estado_llegada = f"Llegó (a las {paciente['llegada']})" if paciente["llegada"] else "No ha llegado"
            mensaje += f"- {paciente['hora_cita']} - {paciente['nombre']} (Estado: {paciente['estado']}, Llegada: {estado_llegada})\n"

    mensaje_sanitizado = json.dumps(mensaje, ensure_ascii=False)
    driver.execute_script(f"alert({mensaje_sanitizado});")
    time.sleep(3)
    try:
        WebDriverWait(driver, 5).until(EC.alert_is_present())
        driver.switch_to.alert.accept()
    except:
        pass

def auto_actualizar(driver, duracion_horas=9):
    global EVENTO_ACTIVO, PACIENTE_ESPECIFICO
    tiempo_final = time.time() + duracion_horas * 3600

    while time.time() < tiempo_final:
        print("🔄 Refrescando la página...")
        driver.refresh()

        navegar_a_pacientes_citados(driver)
        pacientes = detectar_llegadas(driver)

        # Verifica paciente específico
        verificar_paciente_especifico(driver)

        # Notifica próximas citas
        notificar_pacientes_citados_inicialmente(driver)

        # Notifica pendientes ±60min
        notificar_pacientes_pendientes(pacientes)

        ahora = datetime.now()
        hace_15_minutos = ahora - timedelta(minutes=15)
        print(f"⏰ Hora actual: {ahora.strftime('%H:%M:%S')}, Hace 15 minutos: {hace_15_minutos.strftime('%H:%M:%S')}")

        # Revisar quién llegó en los últimos 15 minutos
        llegaron_ultimos_15 = []
        for paciente in pacientes:
            if paciente["llegada"]:
                try:
                    hora_llegada_str = paciente["llegada"]
                    if len(hora_llegada_str.split(":")[0]) == 1:
                        hora_llegada_str = f"0{hora_llegada_str}"
                    hora_llegada = datetime.strptime(hora_llegada_str, "%H:%M").replace(
                        year=ahora.year, month=ahora.month, day=ahora.day
                    )
                    if hora_llegada >= hace_15_minutos:
                        llegaron_ultimos_15.append(paciente)
                except ValueError as e:
                    print(f"⚠️ Formato de hora inválido para llegada de {paciente['nombre']}: {paciente['llegada']}. Error: {e}")
            else:
                print(f"⚠️ Paciente {paciente['nombre']} no tiene hora de llegada registrada.")

        if llegaron_ultimos_15:
            mensaje = "📋 Nuevos pacientes en los últimos 15 minutos:\n"
            for paciente in llegaron_ultimos_15:
                mensaje += f"- {paciente['hora_cita']} - {paciente['nombre']} (Llegada: {paciente['llegada']}, Estado: {paciente['estado']})\n"
            if len(mensaje) > 4096:
                mensaje = mensaje[:4092] + "..."
            print(f"🎙️ Anunciando: {mensaje}")
            speak_message(mensaje)
        else:
            mensaje = "No hay pacientes que hayan llegado en los últimos 15 minutos."
            print(f"📢 Anunciando: {mensaje}")
            speak_message(mensaje)

        if len(mensaje) > 4096:
            mensaje = mensaje[:4092] + "..."

        print(f"📢 Enviando mensaje a Telegram: {mensaje}")
        if not enviar_mensaje(TELEGRAM_CHAT_ID, mensaje):
            print(f"❌ Falló el envío del mensaje a Telegram: {mensaje}")

        mostrar_aviso_en_pantalla(driver, pacientes)

        espera = 300
        print(f"⏳ Esperando {espera} segundos (5 minutos) antes de la próxima actualización...")
        time.sleep(espera)

def monitorar_cita(driver, cita):
    inicio_monitoreo = cita - timedelta(minutes=10)
    fin_monitoreo = cita + timedelta(minutes=5)
    sms_no_registrado_enviado = False
    llegada_enviada = False
    print(f"⏰ Iniciando monitoreo para la cita de las {cita.strftime('%H:%M')}.")

    while datetime.now() < fin_monitoreo:
        ahora = datetime.now()
        if ahora < inicio_monitoreo:
            tiempo_espera = (inicio_monitoreo - ahora).total_seconds()
            print(f"Esperando {int(tiempo_espera)} segundos para iniciar el monitoreo...")
            time.sleep(min(tiempo_espera, 30))
            continue

        driver.refresh()
        pacientes = detectar_llegadas(driver)

        for paciente in pacientes:
            hora_str = paciente["hora_cita"]
            if len(hora_str.split(":")[0]) == 1:
                hora_str = f"0{hora_str}"
            try:
                cita_paciente = datetime.strptime(hora_str, "%H:%M").replace(
                    year=ahora.year, month=ahora.month, day=ahora.day
                )
            except Exception as e:
                print(f"⚠️ Error al interpretar la hora de cita de {paciente['nombre']}: {hora_str}.")
                continue

            if cita_paciente == cita:
                if paciente["llegada"].strip() != "":
                    if not llegada_enviada:
                        mensaje = f"El paciente {paciente['nombre']} ha llegado a la cita de las {paciente['hora_cita']}."
                        print(f"🎙️ {mensaje}")
                        speak_message(mensaje)
                        enviar_mensaje(TELEGRAM_CHAT_ID, mensaje)
                        llegada_enviada = True
                        break
                else:
                    if ahora >= cita + timedelta(minutes=3) and not sms_no_registrado_enviado:
                        mensaje = f"El paciente {paciente['nombre']} de la cita de las {paciente['hora_cita']} no se ha registrado."
                        print(f"🎙️ {mensaje}")
                        speak_message(mensaje)
                        enviar_mensaje(TELEGRAM_CHAT_ID, mensaje)
                        sms_no_registrado_enviado = True

        if llegada_enviada:
            print("Monitoreo detenido por detección de llegada.")
            break

        print("⏳ Esperando 2 minutos para la siguiente verificación...")
        time.sleep(120)

    print("Fin del período de monitoreo de la cita.")

if __name__ == "__main__":
    max_reintentos = 5
    intento = 0
    driver = None
    set_webhook()  # Configura el webhook al iniciar

    while intento < max_reintentos:
        try:
            print(f"🚀 Intento {intento + 1}/{max_reintentos}: Iniciando el proceso...")
            driver = iniciar_navegador()
            iniciar_sesion(driver)
            navegar_a_pacientes_citados(driver)

            # (Opcional) Ejemplo si quisieras monitorar una cita específica:
            monitorar_cita(driver, HORA_CITA_ESPECIFICA)

            # Bucle general (avisos cada 5 minutos, etc.)
            auto_actualizar(driver, duracion_horas=9)
            break

        except Exception as e:
            print(f"⚠️ Error en el proceso: {e}")
            intento += 1
            if intento == max_reintentos:
                print(f"❌ Se alcanzó el máximo de reintentos ({max_reintentos}). Deteniendo el programa.")
                input("Presiona Enter para cerrar...")
                break
            print(f"🔄 Reintentando en 10 segundos (intento {intento + 1}/{max_reintentos})...")
            if driver:
                try:
                    print("⛔ Cerrando navegador antes de reintentar...")
                    driver.quit()
                except Exception as e:
                    print(f"⚠️ Error al cerrar el navegador: {e}")
            time.sleep(10)
        finally:
            if driver and intento == max_reintentos:
                try:
                    print("⛔ Cerrando navegador...")
                    driver.quit()
                except Exception as e:
                    print(f"⚠️ Error al cerrar el navegador en finally: {e}")

    # Para mantener el servidor Flask corriendo (necesario en Render)
    if os.environ.get("PORT"):
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))