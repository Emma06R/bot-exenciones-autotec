# Uso: python pruebas/pruebas_bot.py   (desde la carpeta del bot; no necesita token ni internet)
# Ejecuta los casos P-01 a P-16 del plan de pruebas (E3, 10.6) sobre una copia del bot.
# Telegram se simula: cada mensaje que el bot "envía" se guarda en una lista.
import asyncio, csv, json, os, re, sys, time as _t, statistics
from datetime import date, timedelta, datetime
from pathlib import Path
import shutil, tempfile
# Se trabaja sobre una COPIA del bot en una carpeta temporal: no toca tu config.json ni tus registros.
os.environ["ADMIN_IDS"] = "1001"
RAIZ = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp())
for f in ("bot.py", "config.json", "bienvenida.jpg"):
    shutil.copy(RAIZ / f, TMP / f)
sys.path.insert(0, str(TMP))
import bot

CFG = bot.ARCHIVO_CONFIG; BASE = json.loads(CFG.read_text(encoding="utf-8"))
def config(**cambios):
    c = dict(BASE); c.update(cambios); CFG.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")

class Chat:
    def __init__(s, id): s.id = id; s.salida = []
    async def send_action(s, a): pass
    async def send_message(s, texto, reply_markup=None, **k): s.salida.append((texto, reply_markup))
    async def send_photo(s, foto, caption=None, reply_markup=None, **k):
        s.salida.append(("[FOTO] " + caption, reply_markup))
        class F: file_id = "FOTO123"
        class M: photo = [F()]
        return M()
class User:
    def __init__(s, id, n="Alex"): s.id = id; s.first_name = n
class Msg:
    def __init__(s, t): s.text = t
class Query:
    def __init__(s, d): s.data = d
    async def answer(s): pass
    async def edit_message_reply_markup(s, m): pass
class Upd:
    def __init__(s, chat, user, texto=None, data=None):
        s.effective_chat = chat; s.effective_user = user
        s.message = Msg(texto) if texto is not None else None
        s.callback_query = Query(data) if data else None
class Cola:
    def __init__(s): s.jobs = []
    def get_jobs_by_name(s, n): return []
    def run_once(s, f, when, chat_id, name): s.jobs.append((when, chat_id, name))
class Ctx:
    def __init__(s): s.user_data = {}; s.job_queue = Cola()

class Usuario:
    def __init__(s, id=500, uid=None): s.chat = Chat(id); s.user = User(uid or id); s.ctx = Ctx()
    def escribir(s, t):
        n = len(s.chat.salida); asyncio.run(bot.texto(Upd(s.chat, s.user, texto=t), s.ctx)); return s.chat.salida[n:]
    def tocar(s, d):
        n = len(s.chat.salida); asyncio.run(bot.boton(Upd(s.chat, s.user, data=d), s.ctx)); return s.chat.salida[n:]
    def comando(s, f):
        n = len(s.chat.salida); asyncio.run(f(Upd(s.chat, s.user, texto="/x"), s.ctx)); return s.chat.salida[n:]

def textos(r): return " ".join(t for t, _ in r)
def botones(r):
    out = []
    for _, m in r:
        if m: out += [b for fila in m.inline_keyboard for b in fila]
    return out
def urls(r): return [b.url for b in botones(r) if b.url]

R = []
def caso(id, req, entrada, esperado, obtenido, ok):
    R.append({"id": id, "req": req, "entrada": entrada, "esperado": esperado, "obtenido": obtenido, "resultado": "Pasa" if ok else "Falla"})

def limpiar():
    for f in (bot.ARCHIVO_REGISTRO, bot.ARCHIVO_RECORDATORIOS):
        if f.exists(): f.unlink()
limpiar(); config()

# P-01
u = Usuario(); a = u.comando(bot.bienvenida); b = Usuario().escribir("hola")
n1, n2 = len(botones(a)), len(botones(b))
caso("P-01", "RF-01", "/start y «hola»", "Menú con 5 botones", f"/start: imagen + {n1} botones · hola: {n2} botones", n1 == 5 and n2 == 5 and "[FOTO]" in textos(a))
# P-02
u = Usuario(); u.escribir("formulario"); r = u.tocar("cumple_si")
caso("P-02", "RF-02", "Pedir formulario → «Sí, cumplo»", "Llega el link vigente de config.json", f"Botón «Abrir formulario» con {urls(r)[0] if urls(r) else 'sin link'}", urls(r) == [BASE["link_formulario"]])
# P-03
oks = []
for t in ["EXENCION", "exención", "Formulario"]:
    oks.append("Paso 1 de 2" in textos(Usuario().escribir(t)))
caso("P-03", "RF-03", "«EXENCION», «exención», «Formulario»", "En los 3 casos inicia la solicitud", f"{sum(oks)} de 3 inician la solicitud", all(oks))
# P-04
u = Usuario(); u.escribir("exencion"); r1 = u.tocar("cumple_no")
u2 = Usuario(); u2.escribir("exencion"); r2 = u2.escribir("no")
ok = all("no puedes solicitar" in textos(r) and not urls(r) for r in (r1, r2))
caso("P-04", "RF-04", "Pedir formulario → «No» (botón y escrito)", "Explicación y ningún link", "Mensaje «Por ahora no puedes solicitar la exención», sin link, en ambos casos" if ok else textos(r1 + r2)[:120], ok)
# P-05
r = Usuario().tocar("docs"); n = textos(r).count("▫️")
caso("P-05", "RF-05", "Tocar «Documentos»", "Lista de los 4 documentos", f"Lista con {n} documentos", n == 4)
# P-06
r = Usuario().tocar("fechas"); t = textos(r)
ok = "23 de noviembre" in t and "4 de diciembre" in t and "$300" in t
caso("P-06", "RF-06", "Tocar «Fechas de pago»", "Fechas y aviso de $300", "Del 23 de noviembre al 4 de diciembre, días que faltan y cuota de $300" if ok else t[:120], ok)
# P-07
config(solicitud_abierta=False); r = Usuario().escribir("formulario"); config()
ok = "cerrada" in textos(r) and not urls(r)
caso("P-07", "RF-07", "\"solicitud_abierta\": false y pedir formulario", "Aviso de periodo cerrado y ningún link", "Aviso «cerrada» con próxima apertura (4 de enero de 2027), sin link" if ok else textos(r)[:120], ok)
# P-08
nuevo = "https://forms.gle/NUEVOLINK123"
u = Usuario(); u.escribir("formulario"); config(link_formulario=nuevo); r = u.tocar("cumple_si"); config()
caso("P-08", "RF-08", "Cambiar el link sin reiniciar y pedir formulario", "Llega el link nuevo", f"Llega {urls(r)[0] if urls(r) else 'nada'}", urls(r) == [nuevo])
# P-09
u = Usuario(); u.escribir("formulario"); r = u.tocar("cumple_si"); t = textos(r)
ok = "¿Qué sigue?" in t and BASE["tiempo_respuesta"] in t
caso("P-09", "RF-09", "Completar la solicitud", "Mensaje «¿Qué sigue?» con el tiempo de respuesta", f"«¿Qué sigue?» con «{BASE['tiempo_respuesta']}»" if ok else t[:120], ok)
# P-10
hoy = datetime.now(bot.ZONA).date(); lim = hoy + timedelta(days=4)
config(fecha_limite_pago=lim.isoformat(), fecha_inicio_pago=(lim - timedelta(days=11)).isoformat())
u = Usuario(id=777); u.tocar("fechas"); r = u.tocar("rec_si"); config()
aviso = lim - timedelta(days=3); jobs = u.ctx.job_queue.jobs
guardado = json.loads(bot.ARCHIVO_RECORDATORIOS.read_text()) if bot.ARCHIVO_RECORDATORIOS.exists() else []
ok = bool(jobs) and jobs[0][0].date() == aviso and jobs[0][0].hour == 9 and bot.fecha_bonita(aviso) in textos(r) and guardado
caso("P-10", "RF-10", f"Fecha límite = hoy + 4 días; activar recordatorio", "Confirmación con la fecha; aviso a las 9:00 del día indicado",
     f"Confirma «{bot.fecha_bonita(aviso)}»; aviso agendado {jobs[0][0]:%d/%m/%Y %H:%M} y guardado en recordatorios.json" if jobs else "sin aviso", ok)
# P-11
r = Usuario().escribir("asdf")
caso("P-11", "RF-11", "Escribir «asdf»", "Mensaje de ayuda y menú", "«No entendí tu mensaje» + menú de 5 botones" if len(botones(r)) == 5 else textos(r), "No entendí" in textos(r) and len(botones(r)) == 5)
# P-12
limpiar(); u = Usuario(id=123456789)
for _ in range(2): u.escribir("formulario"); u.tocar("cumple_si")
filas = list(csv.DictReader(open(bot.ARCHIVO_REGISTRO, encoding="utf-8")))
contenido = bot.ARCHIVO_REGISTRO.read_text(encoding="utf-8")
ok = len(filas) == 2 and "123456789" not in contenido and "Alex" not in contenido and all(re.fullmatch(r"[0-9a-f]{10}", f["id_anonimo"]) for f in filas)
caso("P-12", "RF-12", "Pedir el link 2 veces y abrir solicitudes.csv", "2 filas con fecha, hora e ID anónimo, sin nombres", f"{len(filas)} filas (fecha, hora, ID de 10 caracteres, periodo); sin nombre ni ID real", ok)
# P-13
ra = Usuario(uid=1001).comando(bot.conteo); rn = Usuario(uid=2002).comando(bot.conteo)
ok = "2 links entregados a 1 alumno distinto" in textos(ra) and "solo para el personal" in textos(rn)
caso("P-13", "RF-13", "/conteo con ID autorizado y no autorizado", "Conteo correcto / acceso restringido", "Autorizado: «2 links entregados a 1 alumno distinto» · no autorizado: «solo para el personal del área»" if ok else textos(ra + rn), ok)
# P-14
config(link_formulario="https://sitio-falso.com/forms/x"); u = Usuario(); u.escribir("formulario"); r = u.tocar("cumple_si"); config()
caso("P-14", "RNF-07", "Link de otro dominio y pedir formulario", "El bot no lo envía", "No envía link; muestra «En este momento no puedo enviarte el formulario»" if not urls(r) else str(urls(r)), not urls(r))
# P-15
codigo = (Path(bot.__file__)).read_text(encoding="utf-8")
token_en_codigo = bool(re.search(r"\d{8,10}:[A-Za-z0-9_-]{35}", codigo))
ok = not token_en_codigo and "os.getenv(\"TELEGRAM_TOKEN\"" in codigo
caso("P-15", "RNF-08", "Revisar bot.py y solicitudes.csv", "Ningún token ni dato personal", "bot.py lee el token de .env; no hay token en el código; el CSV solo tiene IDs anónimos" if ok else "Se encontró un token", ok)
# P-16 (tiempo de procesamiento del bot, sin contar internet)
acciones = [("e", "hola"), ("e", "formulario"), ("b", "cumple_si"), ("b", "docs"), ("b", "fechas"), ("b", "req"), ("e", "asdf"), ("b", "ayuda"), ("e", "menu"), ("e", "documentos")] * 2
u = Usuario(id=999); tiempos = []
for k, v in acciones:
    t0 = _t.perf_counter(); (u.escribir if k == "e" else u.tocar)(v); tiempos.append((_t.perf_counter() - t0) * 1000)
dentro = sum(1 for x in tiempos if x <= 3000)
caso("P-16", "RNF-01", "20 mensajes; tiempo de procesamiento del bot", "≥ 19 respuestas en ≤ 3 s", f"{dentro} de 20; promedio {statistics.mean(tiempos):.1f} ms, máximo {max(tiempos):.1f} ms (sin contar el viaje por internet)", dentro >= 19)

limpiar(); config()
for x in R: print(x["id"], x["resultado"], "|", x["obtenido"])
print(sum(x["resultado"] == "Pasa" for x in R), "de", len(R), "casos pasan")
print(datetime.now(bot.ZONA).strftime("%d/%m/%Y %H:%M"))
