# Guía para encender el bot de exenciones (paso a paso)

Esta guía es para Windows. Toma unos 20 minutos la primera vez.

---

## Paso 1 · Instalar Python

1. Entra a **python.org** → **Downloads** → descarga la versión más reciente para Windows.
2. Abre el instalador.
3. **MUY IMPORTANTE:** abajo, marca la casilla **«Add python.exe to PATH»**.
4. Da clic en **Install Now** y espera a que termine.
5. Para comprobarlo, abre el menú Inicio, escribe **cmd** y abre **Símbolo del sistema**. Escribe:
   ```
   python --version
   ```
   Debe aparecer algo como `Python 3.13.x`. Si dice que no lo reconoce, reinstala y marca la casilla del punto 3.

## Paso 2 · Poner los archivos en una carpeta

1. Descomprime el ZIP en una carpeta fácil de encontrar, por ejemplo `Documentos\bot_exenciones`.
2. Dentro deben estar: `bot.py`, `config.json`, `requirements.txt`, `.env.ejemplo` y esta guía.

## Paso 3 · Crear tu bot en Telegram y obtener el token

1. En Telegram, busca **@BotFather** (tiene una palomita azul de verificado).
2. Escríbele **/newbot**.
3. Te pide un **nombre**: escribe, por ejemplo, `Exenciones AutoTec`.
4. Te pide un **usuario** que debe terminar en `bot`: por ejemplo, `exenciones_autotec_bot`. Si ya existe, prueba otro.
5. BotFather te responde con un mensaje que dice **«Use this token to access the HTTP API»** y abajo un texto largo como `7123456789:AAH...`. **Ese es tu token.**
6. **No lo compartas con nadie ni lo pegues en tu documento.** Quien lo tenga puede controlar tu bot.

## Paso 4 · Crear el archivo .env

1. En la carpeta del bot, copia el archivo `.env.ejemplo` y pégalo en la misma carpeta.
2. Cambia el nombre de la copia a exactamente **`.env`** (punto + env, sin nada más). Si Windows te pregunta si quieres cambiar la extensión, di **Sí**.
   - Si no ves las extensiones: en el Explorador, menú **Ver** → activa **Extensiones de nombre de archivo**.
3. Abre `.env` con el **Bloc de notas** y en la línea `TELEGRAM_TOKEN=` pega tu token después del `=`, **sin espacios ni comillas**:
   ```
   TELEGRAM_TOKEN=7123456789:AAH...
   ```
4. En `SAL_ANONIMO=` escribe cualquier palabra (sirve para que los IDs del registro sean anónimos).
5. Guarda con **Ctrl + G** (o Ctrl + S).

## Paso 5 · Instalar las bibliotecas

1. Abre la carpeta del bot en el Explorador.
2. Da clic en la **barra de dirección** (arriba, donde dice la ruta), escribe **cmd** y presiona **Enter**. Se abre la terminal ya dentro de la carpeta.
3. Escribe y presiona Enter:
   ```
   pip install -r requirements.txt
   ```
4. Espera a que termine. Al final debe decir **«Successfully installed…»**.

## Paso 6 · Encender el bot

1. En la misma terminal escribe:
   ```
   python bot.py
   ```
2. Debe aparecer: **«Bot de exenciones encendido. Presiona Ctrl + C para apagarlo.»**
3. **No cierres esa ventana:** si la cierras o apagas la computadora, el bot se apaga.

## Paso 7 · Probarlo

1. En Telegram busca el usuario de tu bot (el del paso 3.4) y toca **Iniciar**.
2. Prueba: `/start`, `exención`, el botón **Sí, cumplo**, `documentos`, `fechas`, `asdf`.
3. Para usar **/conteo**: escríbele **/miid** al bot, copia el número que te da, ponlo en `.env` en la línea `ADMIN_IDS=` y reinicia el bot (Ctrl + C y otra vez `python bot.py`).

## Cómo cambiar el link, las fechas o cerrar el periodo (personal del área)

Abre `config.json` con el Bloc de notas y cambia solo lo que está entre comillas o los valores:

| Campo | Qué es | Ejemplo |
|---|---|---|
| `periodo` | Nombre del periodo | `"A-D 2026"` |
| `solicitud_abierta` | `true` = abierta, `false` = cerrada | `true` |
| `link_formulario` | Link del formulario de Google | `"https://forms.gle/..."` |
| `proxima_apertura` | Fecha de la siguiente apertura (año-mes-día) | `"2027-01-04"` |
| `fecha_inicio_pago` / `fecha_limite_pago` | Fechas de pago (año-mes-día) | `"2026-12-04"` |
| `dias_recordatorio` | Días antes de la fecha límite para avisar | `3` |
| `cuota_extemporanea` | Monto de la cuota tardía | `300` |
| `tiempo_respuesta` | Lo que tarda normalmente la respuesta | `"de 3 a 4 días"` |

Guarda el archivo. **No hay que reiniciar el bot:** los cambios se usan en el siguiente mensaje.
Cuidado con las comas y comillas: si el bot falla después de editar, revisa que el archivo siga igual de ordenado que el original.

## Problemas comunes

| Mensaje | Qué hacer |
|---|---|
| `Falta el token` | El archivo `.env` no existe, no se llama exactamente `.env` o la línea del token está vacía. |
| `'python' no se reconoce` | Reinstala Python marcando «Add python.exe to PATH». |
| `No module named telegram` | Repite el paso 5 en la carpeta del bot. |
| `InvalidToken` o `Unauthorized` | El token está mal copiado. Cópialo otra vez desde BotFather. |
| El bot no contesta | Revisa que la ventana negra siga abierta y sin errores. |

## Archivos que crea el bot solo

- `solicitudes.csv`: cada entrega del link con fecha, hora e ID anónimo. Sirve para medir en E4.
- `recordatorios.json`: los avisos pendientes. Si reinicias el bot, los vuelve a agendar.
