# =============================================================================
#  BOT DE EXENCIONES · AutoTec · "Trámites sin esperas"
#  Entrega el formulario de exención de pago y orienta al alumno por Telegram.
#
#  Qué hace (con el requerimiento de la E2 entre paréntesis):
#   - Menú con botones al escribir /start, "hola" o "menú"            (RF-01)
#   - Envía el link vigente del formulario                             (RF-02)
#   - Reconoce palabras clave sin importar mayúsculas ni acentos       (RF-03)
#   - Pide confirmar los requisitos antes de dar el link               (RF-04)
#   - Muestra la lista de documentos                                   (RF-05)
#   - Muestra las fechas de pago y la cuota extemporánea               (RF-06)
#   - Si el periodo está cerrado, no envía link                        (RF-07)
#   - Todo se cambia en config.json, sin tocar este código             (RF-08)
#   - Explica qué sigue después de enviar el link                      (RF-09)
#   - Recordatorio 3 días antes de la fecha límite                     (RF-10)
#   - Si no entiende el mensaje, muestra ayuda y el menú               (RF-11)
#   - Guarda cada entrega del link con un ID anónimo en un CSV         (RF-12)
#   - Comando /conteo para el personal del área                        (RF-13)
#   - Solo envía links de Google Forms                                 (RNF-07)
#   - El token se lee del archivo .env, no está en el código           (RNF-08)
# =============================================================================

import csv            # para escribir el registro solicitudes.csv
import hashlib        # para crear el ID anónimo
import html           # para escribir nombres de forma segura en los mensajes
import json           # para leer config.json y recordatorios.json
import logging        # para ver en la terminal lo que hace el bot
import os             # para leer las variables del archivo .env
import re             # para revisar que el link sea de Google Forms
import unicodedata    # para quitar acentos
from datetime import datetime, date, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, LinkPreviewOptions
from telegram.constants import ChatAction, ParseMode
from telegram.error import TimedOut, NetworkError
from telegram.ext import (Application, CommandHandler, MessageHandler, CallbackQueryHandler,
                          ContextTypes, filters)

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN GENERAL
# -----------------------------------------------------------------------------
CARPETA = Path(__file__).parent                      # carpeta donde está este archivo
ARCHIVO_CONFIG = CARPETA / "config.json"             # lo edita el personal del área
ARCHIVO_REGISTRO = CARPETA / "solicitudes.csv"       # registro anónimo de entregas
ARCHIVO_RECORDATORIOS = CARPETA / "recordatorios.json"
ZONA = ZoneInfo("America/Mexico_City")               # hora de Matehuala
HORA_RECORDATORIO = time(9, 0, tzinfo=ZONA)          # los avisos salen a las 9:00 a.m.

load_dotenv(CARPETA / ".env")                        # lee el archivo .env
TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()      # token que te dio BotFather
SAL = os.getenv("SAL_ANONIMO", "autotec")            # texto secreto para el ID anónimo
# IDs de Telegram del personal que puede usar /conteo, separados por comas
ADMINS = {x.strip() for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}

logging.basicConfig(format="%(asctime)s · %(levelname)s · %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)  # oculta mensajes técnicos de conexión
log = logging.getLogger("bot")


def cargar_config() -> dict:
    """Lee config.json cada vez que se necesita.
    Así, si el personal cambia el link o las fechas, el bot usa lo nuevo
    sin reiniciarse (RF-08, criterio CA-08)."""
    with open(ARCHIVO_CONFIG, encoding="utf-8") as f:
        return json.load(f)


def leer_fecha(texto: str) -> date:
    """Convierte '2026-08-14' en una fecha."""
    return datetime.strptime(texto, "%Y-%m-%d").date()


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_bonita(d: date) -> str:
    """2026-08-14 -> '14 de agosto de 2026'."""
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def link_valido(link: str) -> bool:
    """Solo acepta formularios de Google (RNF-07)."""
    return bool(re.match(r"^https://(docs\.google\.com/forms/|forms\.gle/)", link.strip(), re.IGNORECASE))


def normalizar(texto: str) -> str:
    """Pasa a minúsculas y quita acentos: 'EXENCIÓN' -> 'exencion' (RF-03)."""
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn").strip()


def primera_palabra(texto: str) -> str:
    """Primera palabra sin signos: 'No.' -> 'no', 'Sí, cumplo' -> 'si' (D-09 y D-10)."""
    palabras = re.findall(r"[a-zñ]+", texto)
    return palabras[0] if palabras else ""


SI = {"si", "sip", "claro", "ok", "va", "cumplo"}      # respuestas que cuentan como "sí"
NO = {"no", "nop", "nel"}                             # respuestas que cuentan como "no"


def id_anonimo(chat_id: int) -> str:
    """Crea un código que no permite saber quién es el alumno (RNF-08)."""
    return hashlib.sha256(f"{SAL}{chat_id}".encode()).hexdigest()[:10]


# -----------------------------------------------------------------------------
# 2. TEXTOS Y BOTONES  (versión 2: más visual)
#    Los emojis siempre van junto a un texto, para que nada dependa solo de
#    ellos (RNF-05). Los textos usan formato HTML de Telegram: <b>negritas</b>.
# -----------------------------------------------------------------------------
ARCHIVO_BIENVENIDA = CARPETA / "bienvenida.jpg"      # imagen que se envía con /start (JPG: pesa poco)
FOTO_ID = None   # D-13: después del primer envío, Telegram guarda la foto y se reutiliza su código

REQUISITOS = ("1️⃣ No reprobaste más de <b>1 materia</b> el semestre anterior\n"
              "      <i>(no aplica a nuevo ingreso)</i>\n"
              "2️⃣ Tu papá o tu mamá está en <b>servicio activo</b>\n"
              "      <i>(no aplica a jubilados)</i>")

DOCUMENTOS = ("📎 <b>Ten listos estos documentos en PDF:</b>\n\n"
              "▫️ Acta de nacimiento donde conste el parentesco\n"
              "▫️ Constancia de servicio activo <i>(con no más de un mes)</i>\n"
              "▫️ Último comprobante de percepciones <i>(quincena anterior)</i>\n"
              "▫️ Solicitud firmada por tu papá o mamá, dirigida al Director")


# Colores de los botones (Telegram solo ofrece estos 3, más el normal):
#   "success" = verde · "primary" = azul · "danger" = rojo · None = color normal de la app
# Cada código de botón tiene su color; si no aparece aquí, queda con el color normal.
COLORES = {
    "pedir": "success", "cumple_si": "success", "rec_si": "success",   # acciones principales: verde
    "req": "primary", "docs": "primary", "fechas": "primary",         # consultas: azul
    "cumple_no": "danger",                                            # respuesta negativa: rojo
}


def boton_(texto: str, codigo: str) -> InlineKeyboardButton:
    """Crea un botón. Si el código empieza con 'http', el botón abre ese link (en verde)."""
    if codigo.startswith("http"):
        return InlineKeyboardButton(texto, url=codigo, style="success")
    return InlineKeyboardButton(texto, callback_data=codigo, style=COLORES.get(codigo))


def teclado(*filas):
    """Arma botones. Cada fila es una lista de (texto, código)."""
    return InlineKeyboardMarkup([[boton_(t, c) for t, c in fila] for fila in filas])


MENU = teclado([("📝 Pedir formulario", "pedir")],
               [("✅ Requisitos", "req"), ("📎 Documentos", "docs")],
               [("📅 Fechas de pago", "fechas"), ("❓ Ayuda", "ayuda")])
SOLO_MENU = teclado([("🏠 Volver al menú", "menu")])

# Palabras clave (ya sin acentos) y la opción a la que llevan (RF-03)
PALABRAS = [
    # "exen" y "excen" también atrapan errores comunes como "exension" o "excencion" (D-12)
    (("exencion", "exen", "excen", "formulario", "link", "solicitud", "solicitar", "snte", "descuento"), "pedir"),
    (("requisito",), "req"),
    (("documento",), "docs"),
    (("fecha", "pago", "pagar"), "fechas"),
    (("ayuda", "informacion", "info"), "ayuda"),
    (("gracias",), "gracias"),
    (("hola", "buenas", "inicio", "empezar"), "inicio"),
    (("menu",), "menu"),
]


# -----------------------------------------------------------------------------
# 3. ACCIONES DEL BOT (cada una responde una opción del menú)
# -----------------------------------------------------------------------------
async def enviar(update: Update, texto: str, botones=None):
    """Responde en el chat. Antes muestra 'escribiendo…' para que se sienta natural."""
    chat = update.effective_chat
    await chat.send_action(ChatAction.TYPING)
    await chat.send_message(texto, reply_markup=botones, parse_mode=ParseMode.HTML,
                            link_preview_options=LinkPreviewOptions(is_disabled=True))


def nombre(update: Update) -> str:
    """Primer nombre que el alumno tiene en Telegram (solo para saludar; no se guarda)."""
    u = update.effective_user
    return html.escape(u.first_name) if u and u.first_name else ""


async def bienvenida(update, context):                                     # /start con imagen
    context.user_data["esperando"] = None
    saludo = f"¡Hola, {nombre(update)}! 👋" if nombre(update) else "¡Hola! 👋"
    texto = (f"<b>{saludo}</b>\nSoy el asistente de <b>exenciones de pago</b> del Tec.\n"
             "👨‍👩‍👧 Este bot es solo para <b>hijos de trabajadores de la educación</b>.\n\n"
             "Te ayudo a obtener el formulario, revisar los requisitos y no pasarte de la fecha de pago.\n\n"
             "👇 <b>Elige una opción:</b>")
    chat = update.effective_chat
    global FOTO_ID
    if FOTO_ID:                                          # ya está en Telegram: no se vuelve a subir
        await chat.send_photo(FOTO_ID, caption=texto, reply_markup=MENU, parse_mode=ParseMode.HTML)
    elif ARCHIVO_BIENVENIDA.exists():
        await chat.send_action(ChatAction.UPLOAD_PHOTO)
        with open(ARCHIVO_BIENVENIDA, "rb") as foto:
            msg = await chat.send_photo(foto, caption=texto, reply_markup=MENU, parse_mode=ParseMode.HTML)
        FOTO_ID = msg.photo[-1].file_id                  # se guarda para los siguientes /start
    else:
        await enviar(update, texto, MENU)


async def mostrar_menu(update, context):                                   # RF-01
    context.user_data["esperando"] = None
    await enviar(update, "🏠 <b>Menú principal</b>\n¿Qué necesitas?", MENU)


async def pedir_formulario(update, context):                               # RF-04 y RF-07
    cfg = cargar_config()
    if not cfg.get("solicitud_abierta", False):
        texto = "🔒 <b>La solicitud de exención está cerrada por ahora.</b>"
        if cfg.get("proxima_apertura"):
            texto += f"\n\n📆 Próxima apertura: <b>{fecha_bonita(leer_fecha(cfg['proxima_apertura']))}</b>"
        await enviar(update, texto, teclado([("✅ Requisitos", "req"), ("🏠 Menú", "menu")]))
        return
    context.user_data["esperando"] = "requisitos"
    await enviar(update, "📋 <b>Paso 1 de 2 · Requisitos</b>\n\n"
                         f"Antes de enviarte el formulario, confirma que cumples:\n\n{REQUISITOS}\n\n"
                         "<b>¿Cumples los dos?</b>",
                 teclado([("👍 Sí, cumplo", "cumple_si"), ("👎 No", "cumple_no")]))


async def entregar_link(update, context):                                  # RF-02, RF-09, RF-12
    context.user_data["esperando"] = None
    cfg = cargar_config()
    if not cfg.get("solicitud_abierta", False):          # por si lo cerraron mientras tanto
        return await pedir_formulario(update, context)
    link = cfg.get("link_formulario", "")
    if not link_valido(link):                            # RNF-07: no se envían links raros
        log.warning("El link de config.json no es de Google Forms; no se envió.")
        await enviar(update, "⚠️ En este momento no puedo enviarte el formulario.\n"
                             "Por favor, comunícate con la <b>Subdirección de Servicios Administrativos</b>.", SOLO_MENU)
        return
    await enviar(update, f"🎉 <b>Paso 2 de 2 · Tu formulario</b>\n\nPeriodo <b>{html.escape(cfg.get('periodo', ''))}</b>\n"
                         "Toca el botón para abrirlo 👇",
                 teclado([("📄 Abrir formulario", link)]))
    await enviar(update, DOCUMENTOS)
    await enviar(update, "⏳ <b>¿Qué sigue?</b>\n\nEl personal del área revisa tus documentos y te responde <b>por correo</b>.\n"
                         f"Normalmente tarda <b>{html.escape(cfg.get('tiempo_respuesta', 'unos días'))}</b>.",
                 teclado([("📅 Fechas de pago", "fechas"), ("🏠 Menú", "menu")]))
    registrar_entrega(update.effective_chat.id, cfg.get("periodo", ""))


async def no_cumple(update, context):                                      # RF-04 (respuesta "No")
    context.user_data["esperando"] = None
    await enviar(update, "😕 <b>Por ahora no puedes solicitar la exención.</b>\n\n"
                         "Es necesario cumplir los dos requisitos. Si tienes dudas, acude a la "
                         "<b>Subdirección de Servicios Administrativos</b>.", SOLO_MENU)


async def mostrar_requisitos(update, context):
    await enviar(update, f"✅ <b>Requisitos</b>\n<i>Hijos de trabajadores de la educación</i>\n\n{REQUISITOS}",
                 teclado([("📝 Pedir formulario", "pedir"), ("🏠 Menú", "menu")]))


async def mostrar_documentos(update, context):                             # RF-05
    await enviar(update, DOCUMENTOS, teclado([("📝 Pedir formulario", "pedir"), ("🏠 Menú", "menu")]))


async def mostrar_fechas(update, context):                                 # RF-06
    cfg = cargar_config()
    inicio, limite = leer_fecha(cfg["fecha_inicio_pago"]), leer_fecha(cfg["fecha_limite_pago"])
    faltan = (limite - datetime.now(ZONA).date()).days
    if faltan > 1:
        aviso = f"⏰ Faltan <b>{faltan} días</b> para la fecha límite."
    elif faltan == 1:
        aviso = "⏰ <b>¡Mañana</b> es la fecha límite!"
    elif faltan == 0:
        aviso = "⏰ <b>¡Hoy</b> es la fecha límite!"
    else:
        aviso = "⏰ La fecha límite de este periodo <b>ya pasó</b>."
    context.user_data["esperando"] = "recordatorio" if faltan > 0 else None
    texto = (f"📅 <b>Fechas de pago</b>\n\nDel <b>{fecha_bonita(inicio)}</b>\nal <b>{fecha_bonita(limite)}</b>\n\n{aviso}\n"
             f"Si pagas después, se cobra una cuota extemporánea de <b>${cfg.get('cuota_extemporanea', 300)}</b>.")
    if faltan > 0:
        texto += f"\n\n🔔 <b>¿Te recuerdo {cfg.get('dias_recordatorio', 3)} días antes?</b>"
        botones = teclado([("🔔 Sí, recuérdame", "rec_si"), ("No, gracias", "rec_no")])
    else:
        botones = SOLO_MENU
    await enviar(update, texto, botones)


async def mostrar_ayuda(update, context):
    await enviar(update, "❓ <b>Ayuda</b>\n\nPuedes tocar los botones o escribir palabras como:\n"
                         "<b>formulario</b> · <b>requisitos</b> · <b>documentos</b> · <b>fechas</b>\n\n"
                         "ℹ️ La revisión de documentos y la autorización las hace el <b>personal del área</b>; "
                         "este bot solo te orienta y te envía el formulario.\n\n"
                         "<i>Prototipo escolar de AutoTec con datos de ejemplo.</i>", MENU)


async def de_nada(update, context):                                        # D-12
    await enviar(update, "😊 ¡De nada! Si necesitas algo más, aquí estoy.", MENU)


async def no_entendi(update, context):                                     # RF-11
    await enviar(update, "🤔 <b>No entendí tu mensaje.</b>\nElige una opción o escribe, por ejemplo, «formulario».", MENU)


# -----------------------------------------------------------------------------
# 4. RECORDATORIOS (RF-10)
# -----------------------------------------------------------------------------
def leer_recordatorios() -> list:
    if ARCHIVO_RECORDATORIOS.exists():
        with open(ARCHIVO_RECORDATORIOS, encoding="utf-8") as f:
            return json.load(f)
    return []


def guardar_recordatorios(lista: list):
    with open(ARCHIVO_RECORDATORIOS, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)


async def enviar_recordatorio(context: ContextTypes.DEFAULT_TYPE):
    """La ejecuta el programador de tareas el día del aviso."""
    chat_id = context.job.chat_id
    cfg = cargar_config()
    limite = leer_fecha(cfg["fecha_limite_pago"])
    await context.bot.send_message(chat_id, f"🔔 <b>Recordatorio de pago</b>\n\nTu fecha límite es el <b>{fecha_bonita(limite)}</b>.\n"
                                            f"Después se cobra una cuota extemporánea de <b>${cfg.get('cuota_extemporanea', 300)}</b>.",
                                   parse_mode=ParseMode.HTML)
    # ya se envió: se quita de la lista
    guardar_recordatorios([r for r in leer_recordatorios() if r["chat_id"] != chat_id])


def programar(app_o_context, chat_id: int, dia_aviso: date):
    """Agenda el aviso para las 9:00 a.m. del día indicado."""
    cuando = datetime.combine(dia_aviso, HORA_RECORDATORIO)
    cola = app_o_context.job_queue
    for job in cola.get_jobs_by_name(f"rec_{chat_id}"):   # evita avisos repetidos
        job.schedule_removal()
    cola.run_once(enviar_recordatorio, when=cuando, chat_id=chat_id, name=f"rec_{chat_id}")


async def activar_recordatorio(update, context):
    context.user_data["esperando"] = None
    cfg = cargar_config()
    limite = leer_fecha(cfg["fecha_limite_pago"])
    dia_aviso = limite - timedelta(days=cfg.get("dias_recordatorio", 3))
    hoy = datetime.now(ZONA).date()
    if limite < hoy:
        await enviar(update, "⏰ La fecha límite de este periodo <b>ya pasó</b>.", SOLO_MENU)
        return
    if dia_aviso <= hoy:                                   # faltan menos días que los del aviso
        faltan = (limite - hoy).days
        await enviar(update, f"⏰ Tu fecha límite es el <b>{fecha_bonita(limite)}</b>: faltan <b>{faltan} día(s)</b>.\n"
                             "Te recomiendo pagar cuanto antes.", SOLO_MENU)
        return
    chat_id = update.effective_chat.id
    programar(context, chat_id, dia_aviso)
    lista = [r for r in leer_recordatorios() if r["chat_id"] != chat_id]
    lista.append({"chat_id": chat_id, "dia_aviso": dia_aviso.isoformat()})
    guardar_recordatorios(lista)
    await enviar(update, f"🔔 <b>¡Listo!</b> Te avisaré el <b>{fecha_bonita(dia_aviso)}</b> a las 9:00 a.m.", SOLO_MENU)


async def rechazar_recordatorio(update, context):
    context.user_data["esperando"] = None
    await enviar(update, "👌 De acuerdo, no activé el recordatorio.", MENU)


async def reprogramar_al_iniciar(app: Application):
    """Al encender: publica los comandos del menú de Telegram y vuelve a agendar los avisos pendientes."""
    await app.bot.set_my_commands([BotCommand("start", "Inicio y menú principal"),
                                   BotCommand("menu", "Volver al menú")])
    hoy = datetime.now(ZONA).date()
    vigentes = []
    for r in leer_recordatorios():
        dia = leer_fecha(r["dia_aviso"])
        if dia >= hoy:
            programar(app, r["chat_id"], dia)
            vigentes.append(r)
    guardar_recordatorios(vigentes)
    log.info("Recordatorios reprogramados: %d", len(vigentes))


# -----------------------------------------------------------------------------
# 5. REGISTRO ANÓNIMO Y CONTEO (RF-12 y RF-13)
# -----------------------------------------------------------------------------
def registrar_entrega(chat_id: int, periodo: str):
    nuevo = not ARCHIVO_REGISTRO.exists()
    ahora = datetime.now(ZONA)
    with open(ARCHIVO_REGISTRO, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["fecha", "hora", "id_anonimo", "periodo"])
        w.writerow([ahora.date().isoformat(), ahora.strftime("%H:%M:%S"), id_anonimo(chat_id), periodo])


async def conteo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMINS:       # solo el personal autorizado
        await enviar(update, "🔒 Este comando es solo para el personal del área.")
        return
    periodo = cargar_config().get("periodo", "")
    total, personas = 0, set()
    if ARCHIVO_REGISTRO.exists():
        with open(ARCHIVO_REGISTRO, encoding="utf-8") as f:
            for fila in csv.DictReader(f):
                if fila["periodo"] == periodo:
                    total += 1
                    personas.add(fila["id_anonimo"])
    n = len(personas)                                    # D-11: singular o plural según el número
    await enviar(update, f"📊 <b>Periodo {html.escape(periodo)}</b>\n{total} link{'s' if total != 1 else ''} "
                         f"entregado{'s' if total != 1 else ''} a {n} alumno{'s' if n != 1 else ''} distinto{'s' if n != 1 else ''}.")


async def mi_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra tu ID de Telegram, para ponerlo en ADMIN_IDS del archivo .env."""
    await enviar(update, f"🪪 Tu ID de Telegram es: <code>{update.effective_user.id}</code>")


# -----------------------------------------------------------------------------
# 6. RECEPCIÓN DE MENSAJES Y BOTONES
# -----------------------------------------------------------------------------
ACCIONES = {
    "menu": mostrar_menu, "inicio": bienvenida, "pedir": pedir_formulario, "req": mostrar_requisitos, "docs": mostrar_documentos,
    "fechas": mostrar_fechas, "ayuda": mostrar_ayuda, "cumple_si": entregar_link, "cumple_no": no_cumple,
    "rec_si": activar_recordatorio, "rec_no": rechazar_recordatorio, "gracias": de_nada,
}


async def boton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Se ejecuta cuando el alumno toca un botón."""
    await update.callback_query.answer()                  # quita el "relojito" del botón
    try:                                                  # quita los botones ya usados (chat más limpio)
        await update.callback_query.edit_message_reply_markup(None)
    except Exception:
        pass
    accion = ACCIONES.get(update.callback_query.data, no_entendi)
    await accion(update, context)


async def texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Se ejecuta cuando el alumno escribe un mensaje."""
    t = normalizar(update.message.text)
    esperando = context.user_data.get("esperando")
    # Si el bot hizo una pregunta de Sí/No, también se puede contestar escribiendo.
    # Se revisa la PRIMERA PALABRA completa: así "sin dinero" ya no cuenta como "sí" (D-09)
    # y "No." o "no gracias" sí cuentan como "no" (D-10).
    p = primera_palabra(t)
    if esperando and (p in SI or p in NO):
        if esperando == "requisitos":
            return await (entregar_link if p in SI else no_cumple)(update, context)
        if esperando == "recordatorio":
            return await (activar_recordatorio if p in SI else rechazar_recordatorio)(update, context)
    for palabras, opcion in PALABRAS:                     # busca palabras clave (RF-03)
        if any(p in t for p in palabras):
            return await ACCIONES[opcion](update, context)
    await no_entendi(update, context)                     # RF-11


async def error(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Si algo falla, lo anota en la terminal y avisa al alumno con un mensaje claro."""
    if isinstance(context.error, (TimedOut, NetworkError)):   # internet lento o cortado: el bot reintenta solo
        log.warning("Internet lento o sin conexión (%s). El bot sigue funcionando.", context.error)
        return
    log.error("Error: %s", context.error)
    if isinstance(update, Update) and update.effective_chat:
        await update.effective_chat.send_message("⚠️ Ocurrió un problema. Intenta de nuevo o escribe «menú».")


def crear_app(token: str) -> Application:
    # D-13: más tiempo de espera por si el internet está lento (antes salía "Timed out")
    app = (Application.builder().token(token).post_init(reprogramar_al_iniciar)
           .connect_timeout(15).read_timeout(20).write_timeout(20).media_write_timeout(60).build())
    app.add_handler(CommandHandler("start", bienvenida))
    app.add_handler(CommandHandler("menu", mostrar_menu))
    app.add_handler(CommandHandler("conteo", conteo))
    app.add_handler(CommandHandler("miid", mi_id))
    app.add_handler(CallbackQueryHandler(boton))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, texto))
    app.add_error_handler(error)
    return app


def main():
    if not TOKEN:
        raise SystemExit("Falta el token. Crea el archivo .env con la línea TELEGRAM_TOKEN=tu_token (ver GUIA.md).")
    cargar_config()                                       # revisa que config.json exista y esté bien escrito
    log.info("Bot de exenciones encendido. Presiona Ctrl + C para apagarlo.")
    crear_app(TOKEN).run_polling()


if __name__ == "__main__":
    main()
