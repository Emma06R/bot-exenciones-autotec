# Bot de exenciones de pago · IT Matehuala

**Prototipo escolar de AutoTec** · Josué Emmanuel Ramírez Cruz 

Bot de Telegram que entrega **al instante** el link del formulario de exención de pago de reinscripción
(solo para hijos de trabajadores de la educación). Antes, el alumno mandaba un correo y esperaba de **1 a 4 días**
a que alguien le contestara con el link. El bot confirma los requisitos, entrega el link, muestra los documentos
y las fechas de pago y recuerda la fecha límite. La revisión de documentos sigue siendo manual, como pidió el área.

> Usa **datos de ejemplo**: el formulario y las fechas no son los oficiales.

## Probarlo sin descargar nada

| | Enlace |
|---|---|
| ▶️ **Prototipo navegable** (simula el bot en el navegador, siempre disponible) | https://emma06r.github.io/bot-exenciones-autotec/ |
| 💬 **Bot real en Telegram** (responde mientras la computadora del autor está encendida) | https://t.me/exenciones_autotec_bot |
| 🎬 **Video de demostración** | https://drive.google.com/file/d/10DF43CK5yEv_NUlRE9To1zvNQKIOxk1Q/view?usp=drivesdk |

Prueba sugerida (la misma que hicieron los 5 usuarios de la prueba de usabilidad):
1. **Pedir formulario → Sí, cumplo** → aparece el botón «Abrir formulario».
2. **Documentos** → lista de documentos.
3. **Fechas de pago → Sí, recuérdame** → «¡Listo! Te avisaré el…».
4. Escribe `exención`, `requisitos`, `asdf` o `gracias`.

En el prototipo navegable, el panel de la derecha permite actuar como el personal del área: cerrar la solicitud,
cambiar el link (si no es de Google Forms, el bot no lo envía) y simular el recordatorio.

## Resultados

- **16 de 16** casos de prueba pasan ([`pruebas/resultado_pruebas.txt`](pruebas/resultado_pruebas.txt)).
- **5 defectos** encontrados con pruebas exploratorias y uso real, todos corregidos ([`evidencias/defectos.csv`](evidencias/defectos.csv)).
- **SUS promedio de 85.5** con 5 usuarios; la meta era 68 ([`evidencias/SUS_respuestas.csv`](evidencias/SUS_respuestas.csv)).
- Tiempo para recibir el link: de **1 a 6 días** a **al instante** ([`evidencias/mediciones_antes_despues.csv`](evidencias/mediciones_antes_despues.csv)).

## Contenido del repositorio

| Archivo o carpeta | Qué es |
|---|---|
| [`bot.py`](bot.py) | Programa del bot (Python 3 y python-telegram-bot 22), comentado. |
| [`config.json`](config.json) | Link del formulario, fechas, periodo y cuota. El área lo edita sin programar; el bot lo lee en cada mensaje. |
| `bienvenida.jpg` | Imagen de bienvenida. |
| `requirements.txt` | Librerías: python-telegram-bot (con JobQueue), python-dotenv y tzdata. |
| `.env.ejemplo` | Plantilla para el token (el token real no se publica). |
| `iniciar_bot.bat` | Enciende el bot en Windows y lo reinicia si se detiene. |
| `probar.bat` y [`pruebas/`](pruebas) | Pruebas automatizadas P-01 a P-16 y pruebas exploratorias; no necesitan token ni internet. |
| [`evidencias/`](evidencias) | SUS, prueba de usabilidad, métricas antes y después, defectos y horas (CSV). |
| [`docs/`](docs) | Prototipo navegable publicado con GitHub Pages. |
| [`GUIA.md`](GUIA.md) | Cómo instalar y encender el bot paso a paso. |

## Correrlo en tu computadora (opcional)

1. Instala Python 3.11 o superior y ejecuta `python -m pip install -r requirements.txt`.
2. Crea un bot con **@BotFather** (`/newbot`), copia `.env.ejemplo` como `.env` y pega tu token.
3. Ejecuta `python bot.py` (o doble clic en `iniciar_bot.bat`) y escríbele `/start`.

Para correr las pruebas: `python pruebas/pruebas_bot.py`.

## Qué automatiza y qué no

- **Automatiza:** entrega del link, confirmación de requisitos, apertura y cierre por periodo, recordatorios y conteo anónimo de entregas.
- **No automatiza:** la revisión de documentos ni la autorización, que el área pidió mantener manuales.
- El área **no publica el link** para que no lo llenen personas que no aplican; el bot lo entrega solo a quien confirma los requisitos y dentro del periodo.
