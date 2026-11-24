# Bot de exenciones de pago · IT Matehuala

**Prototipo escolar de AutoTec** · Josué Emmanuel Ramírez Cruz 

Bot de Telegram que entrega **al instante** el link del formulario de exención de pago de reinscripción
(solo para hijos de trabajadores de la educación), y un sistema en Google Forms + Sheets + Apps Script que **valida
la solicitud automáticamente** y le contesta al alumno por correo.

Antes, el alumno mandaba un correo y esperaba de **1 a 4 días** a que alguien le contestara con el link, y después
otros días a que revisaran sus documentos. Ahora todo el proceso es automático:

1. **Bot de Telegram:** confirma los requisitos, entrega el link del formulario, muestra los documentos y fechas y recuerda la fecha límite.
2. **Formulario de Google:** el alumno captura sus datos y sube los 4 documentos.
3. **Validación automática (Apps Script):** al enviarse el formulario revisa los datos, los archivos y **lee los documentos (OCR)**
   para comprobar nombres, parentesco y la fecha de la constancia; asigna un folio y lo marca **Autorizada** o **Requiere corrección**.
4. **Correo automático** al alumno con el resultado y, si falta algo, qué corregir.

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
- Tiempo para recibir el link: de **1 a 4 días** a **al instante** ([`evidencias/mediciones_antes_despues.csv`](evidencias/mediciones_antes_despues.csv)).

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
| [`validacion/Codigo.gs`](validacion/Codigo.gs) | Script de Google Apps Script que valida cada solicitud del formulario y envía el correo. |
| [`validacion/prueba_reglas.js`](validacion/prueba_reglas.js) | Prueba las reglas de validación sin Google (`node validacion/prueba_reglas.js`). |
| [`validacion/documentos_prueba/`](validacion/documentos_prueba) | Documentos **inventados** para probar: un juego correcto y otro con la constancia vencida. |
| [`GUIA.md`](GUIA.md) | Cómo instalar y encender el bot paso a paso. |

## Correrlo en tu computadora (opcional)

1. Instala Python 3.11 o superior y ejecuta `python -m pip install -r requirements.txt`.
2. Crea un bot con **@BotFather** (`/newbot`), copia `.env.ejemplo` como `.env` y pega tu token.
3. Ejecuta `python bot.py` (o doble clic en `iniciar_bot.bat`) y escríbele `/start`.

Para correr las pruebas: `python pruebas/pruebas_bot.py`.

## Validación automática de la solicitud

| Qué revisa | Cómo |
|---|---|
| Periodo abierto | Fecha de envío contra las fechas de la hoja «Configuración». |
| Número de control | 8 dígitos y que no tenga ya una solicitud autorizada en el periodo. |
| Nombre, padre/madre/tutor y escuela | Nombre completo y una escuela con tipo reconocible (Esc. Primaria, Secundaria, CBTis…). |
| Correo | Válido; opcionalmente del dominio institucional (se apaga para alumnos de nuevo ingreso). |
| Archivos | Están los 4, son PDF o imagen y pesan menos de 10 MB. |
| Acta de nacimiento | Contiene los apellidos del alumno y el nombre del padre/madre/tutor (parentesco). |
| Constancia de servicio | Contiene el nombre del trabajador y una fecha de no más de 31 días. |
| Comprobante de percepciones | Contiene el nombre del trabajador. |
| Solicitud | Va dirigida al Director y menciona al trabajador. |

La hoja «Configuración» permite cambiar fechas y reglas sin tocar el código, y apagar la confirmación automática
si el área quiere dar el visto bueno final (en ese caso el correo sale solo al elegir el estado).

**Límite:** el sistema comprueba que los documentos estén completos y coincidan entre sí; no puede detectar si un documento es falso o si la firma es real.

## Qué automatiza

- **Bot:** entrega del link, confirmación de requisitos, apertura y cierre por periodo, recordatorios y conteo anónimo de entregas.
- **Validación:** revisión de datos, archivos y contenido de los documentos, folio, resultado y correo al alumno, sin intervención del personal.
- El área **no publica el link** para que no lo llenen personas que no aplican; el bot lo entrega solo a quien confirma los requisitos y dentro del periodo.
