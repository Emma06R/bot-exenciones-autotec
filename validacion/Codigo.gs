/**
 * VALIDACIÓN AUTOMÁTICA DE SOLICITUDES DE EXENCIÓN · AutoTec (prototipo escolar)
 * ---------------------------------------------------------------------------
 * Funciona con el formulario "Solicitud de exención de pago". Cuando un alumno lo envía,
 * este script, sin que nadie intervenga:
 *   1. Revisa los datos: periodo abierto, número de control, nombre, correo institucional,
 *      padre/madre/tutor y escuela.
 *   2. Revisa los 4 archivos: que estén, que sean PDF o imagen y que no pesen de más.
 *   3. LEE los documentos con reconocimiento de texto (OCR de Google Drive) y comprueba:
 *        - Acta de nacimiento: aparecen los apellidos del alumno y el nombre del padre/madre/tutor.
 *        - Constancia de servicio: aparece el nombre del trabajador y una fecha de no más de un mes.
 *        - Comprobante de percepciones: aparece el nombre del trabajador.
 *        - Solicitud: va dirigida al Director y menciona al trabajador.
 *   4. Asigna un folio, marca la solicitud como "Autorizada" o "Requiere corrección"
 *      y le manda al alumno un correo con el resultado y, si falta algo, qué corregir.
 *
 * Dónde va: hoja de respuestas del formulario → Extensiones → Apps Script.
 * Necesita el servicio avanzado "Drive API" (Servicios → + → Drive API → Agregar).
 * Primera vez: menú "Exenciones" → "Configurar (primera vez)".
 * Lo que NO puede saber: si un documento es auténtico o si la firma es real.
 */

// ===== 1. Cómo reconoce cada pregunta del formulario =====
// Busca estas palabras en el título de la columna (sin importar mayúsculas ni acentos),
// así funciona aunque el título tenga pequeñas diferencias.
const P = {
  control:     'numero de control',
  nombre:      'nombre completo',
  correo:      'correo institucional',
  trabajador:  'nombre del padre',
  escuela:     'escuela donde trabaja',
  acta:        'acta de nacimiento',
  constancia:  'constancia de servicio',
  comprobante: 'comprobante de percepciones',
  solicitud:   'solicitud firmada'
};
const DOCS = {                         // los 4 archivos obligatorios
  acta:        'Acta de nacimiento',
  constancia:  'Constancia de servicio activo',
  comprobante: 'Último comprobante de percepciones',
  solicitud:   'Solicitud firmada dirigida al Director'
};
const TIPOS_OK = ['application/pdf', 'image/jpeg', 'image/png', 'image/heic', 'image/heif', 'image/webp'];
const COLS = ['Folio', 'Estado', 'Motivos', 'Validado el', 'Correo enviado'];   // columnas que agrega el script
const ESTADOS = ['Autorizada', 'Requiere corrección', 'Rechazada', 'Completa · en revisión'];
const HOJA_CONFIG = 'Configuración';
const TIPOS_ESCUELA = ['ESC', 'ESCUELA', 'JARDIN', 'PREESCOLAR', 'PRIMARIA', 'SECUNDARIA', 'TELESECUNDARIA', 'PREPARATORIA', 'BACHILLERATO',
  'COLEGIO', 'INSTITUTO', 'UNIVERSIDAD', 'TECNOLOGICO', 'NORMAL', 'CBTIS', 'CBTA', 'CETIS', 'CONALEP', 'COBACH', 'CECYTE', 'EMSAD',
  'CAM', 'USAER', 'CENTRO', 'SUPERVISION', 'TELEBACHILLERATO', 'J. N.', 'J.N.'];


// ===== 2. Menú y configuración inicial =====
function onOpen() {
  SpreadsheetApp.getUi().createMenu('Exenciones')
    .addItem('Configurar (primera vez)', 'configurar')
    .addItem('Validar otra vez la fila seleccionada', 'validarSeleccionada')
    .addToUi();
}

function configurar() {
  const ss = SpreadsheetApp.getActive();
  if (!ss.getFormUrl()) throw new Error('Esta hoja no está vinculada al formulario. Créala desde Formulario → Respuestas → Vincular con Hojas de cálculo.');

  // Hoja de configuración: el área cambia aquí fechas y opciones sin tocar el código
  let cfg = ss.getSheetByName(HOJA_CONFIG);
  if (!cfg) {
    cfg = ss.insertSheet(HOJA_CONFIG);
    const hoy = new Date(), en30 = new Date(hoy.getTime() + 30 * 864e5);
    const filas = [
      ['Opción', 'Valor', 'Para qué sirve'],
      ['periodo', 'A-D 2026', 'Periodo que aparece en los correos'],
      ['inicio_solicitudes', hoy, 'Primer día en que se aceptan solicitudes'],
      ['fin_solicitudes', en30, 'Último día en que se aceptan solicitudes'],
      ['fecha_limite_pago', en30, 'Fecha límite de pago que se le dice al alumno autorizado'],
      ['confirmacion_automatica', true, 'Marcada = autoriza sola. Sin marcar = queda "en revisión" y el personal elige el estado'],
      ['revisar_contenido', true, 'Marcada = lee los documentos (OCR) y busca nombres y fechas'],
      ['dominio_institucional', 'matehuala.tecnm.mx', 'El correo del alumno debe terminar así (vacío = no se revisa)'],
      ['dias_max_constancia', 31, 'Antigüedad máxima de la constancia de servicio (días)'],
      ['tamano_max_mb', 10, 'Tamaño máximo de cada archivo'],
      ['correo_area', Session.getEffectiveUser().getEmail(), 'Recibe copia oculta de cada resultado (puede quedar vacío)'],
      ['remitente', 'Exenciones de pago · IT Matehuala (prototipo)', 'Nombre que ve el alumno en el correo']
    ];
    cfg.getRange(1, 1, filas.length, 3).setValues(filas);
    cfg.getRange('B6:B7').insertCheckboxes().setValue(true);
    cfg.getRange('B3:B5').setNumberFormat('dd/mm/yyyy');
    cfg.getRange('A1:C1').setFontWeight('bold').setBackground('#16496E').setFontColor('#FFFFFF');
    cfg.autoResizeColumns(1, 3);
  }

  // Columnas del sistema en la hoja de respuestas + lista desplegable de estados
  const hoja = hojaRespuestas_();
  const enc = asegurarColumnas_(hoja);
  hoja.getRange(2, enc['Estado'], hoja.getMaxRows() - 1, 1)
      .setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(ESTADOS, true).build());

  // Activadores: al enviar el formulario y al editar la hoja
  ScriptApp.getProjectTriggers().forEach(t => {
    if (['alEnviar', 'alEditar'].includes(t.getHandlerFunction())) ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('alEnviar').forSpreadsheet(ss).onFormSubmit().create();
  ScriptApp.newTrigger('alEditar').forSpreadsheet(ss).onEdit().create();

  const ocr = probarOcr_();
  avisar_('Listo ✅\n\nCada solicitud se validará y contestará sola.\nRevisa las fechas en la hoja "Configuración".' +
    (ocr ? '' : '\n\n⚠️ Falta activar el servicio "Drive API" (Apps Script → Servicios → + → Drive API). Sin él no se puede leer el contenido de los documentos.'));
}


// ===== 3. Activadores =====
function alEnviar(e) {                        // se ejecuta solo cuando llega una respuesta
  validarFila_(e.range.getSheet(), e.range.getRow());
}

function validarSeleccionada() {              // volver a revisar una fila a mano (para pruebas)
  const hoja = SpreadsheetApp.getActiveSheet();
  const fila = hoja.getActiveRange().getRow();
  if (fila < 2 || hoja.getName() === HOJA_CONFIG) return avisar_('Selecciona una fila con una respuesta.');
  validarFila_(hoja, fila);
}

function alEditar(e) {                         // el personal cambia el estado a mano → sale el correo solo
  const hoja = e.range.getSheet();
  if (hoja.getName() === HOJA_CONFIG || e.range.getRow() < 2) return;
  const enc = encabezados_(hoja);
  if (e.range.getColumn() !== enc['Estado']) return;
  const estado = String(e.value || '');
  if (!['Autorizada', 'Requiere corrección', 'Rechazada'].includes(estado)) return;
  const fila = e.range.getRow();
  const v = hoja.getRange(fila, 1, 1, hoja.getLastColumn()).getValues()[0];
  const motivos = String(v[enc['Motivos'] - 1] || '').split('\n').filter(String);
  const r = enviarCorreo_(datosDeFila_(enc, v), estado, motivos, v[enc['Folio'] - 1], leerConfig_());
  hoja.getRange(fila, enc['Correo enviado']).setValue(r);
}


// ===== 4. La validación =====
function validarFila_(hoja, fila) {
  const cfg = leerConfig_();
  const enc = asegurarColumnas_(hoja);
  const v = hoja.getRange(fila, 1, 1, hoja.getLastColumn()).getValues()[0];
  const d = datosDeFila_(enc, v);
  const folio = v[enc['Folio'] - 1] || 'EX-' + new Date().getFullYear() + '-' + String(fila - 1).padStart(4, '0');

  hoja.getRange(fila, enc['Estado']).setValue('Validando…');
  const archivos = leerArchivos_(d, cfg);                         // revisa los archivos en Drive y los lee (OCR)
  const motivos = revisar(d, cfg, archivos, otrasAutorizadas_(hoja, enc, fila));

  // Renombra los archivos con el folio para encontrarlos fácil en Drive
  archivos.forEach(a => a.archivos.forEach(f => {
    try { const x = DriveApp.getFileById(f.id); x.setName(folio + '_' + a.clave + extension_(x.getName())); } catch (err) {}
  }));

  const estado = motivos.length ? 'Requiere corrección' : (cfg.confirmacion_automatica ? 'Autorizada' : 'Completa · en revisión');
  hoja.getRange(fila, enc['Folio'], 1, 4).setValues([[folio, estado, motivos.join('\n'), new Date()]]);
  hoja.getRange(fila, enc['Validado el']).setNumberFormat('dd/mm/yyyy hh:mm');
  hoja.getRange(fila, enc['Estado']).setBackground(estado === 'Autorizada' ? '#D9F2E3' : estado === 'Requiere corrección' ? '#FBE3E3' : '#FFF3D6');
  hoja.getRange(fila, enc['Correo enviado']).setValue(enviarCorreo_(d, estado, motivos, folio, cfg));
}

/**
 * REGLAS DEL TRÁMITE. Recibe los datos ya leídos y devuelve la lista de motivos.
 * Lista vacía = la solicitud cumple todo. No usa servicios de Google, así que se puede probar aparte.
 */
function revisar(d, cfg, archivos, autorizadas) {
  const m = [];
  const enviado = d.marca instanceof Date ? d.marca : new Date();

  // a) Periodo abierto
  const ini = fecha_(cfg.inicio_solicitudes), fin = fecha_(cfg.fin_solicitudes);
  if (!ini || !fin) m.push('Revisar la hoja "Configuración": las fechas de inicio y fin de solicitudes no son válidas (usa el formato dd/mm/aaaa).');
  else if (enviado < inicioDia_(ini) || enviado >= new Date(inicioDia_(fin).getTime() + 864e5))
    m.push('La solicitud se envió fuera del periodo de solicitudes (del ' + fechaTexto_(ini) + ' al ' + fechaTexto_(fin) + ').');

  // b) Datos del alumno
  const control = String(d.control).trim().toUpperCase().replace(/\s/g, '');
  if (!/^[A-Z]?\d{8}$/.test(control)) m.push('El número de control debe tener 8 dígitos (por ejemplo, 24660080).');
  else if (autorizadas.includes(control)) m.push('Ya tienes una solicitud autorizada en este periodo.');

  const alumno = palabras_(d.nombre);
  if (alumno.length < 3) m.push('Escribe tu nombre completo empezando por los apellidos (por ejemplo, RAMÍREZ CRUZ JOSUÉ).');

  const correo = String(d.correo).trim().toLowerCase();
  if (!/^[^@\s]+@[^@\s]+\.[a-z]{2,}$/.test(correo)) m.push('El correo institucional no es válido.');
  else if (cfg.dominio_institucional && !correo.endsWith('@' + String(cfg.dominio_institucional).toLowerCase()))
    m.push('Usa tu correo institucional (termina en @' + cfg.dominio_institucional + ').');

  // c) Padre, madre o tutor y su escuela
  const tutor = palabras_(d.trabajador);
  if (tutor.length < 3) m.push('Escribe el nombre completo (nombre y dos apellidos) de tu padre, madre o tutor.');
  const escuela = sinAcentos_(d.escuela);
  if (escuela.replace(/[^A-Z0-9]/g, '').length < 8 || !TIPOS_ESCUELA.some(t => escuela.includes(t)))
    m.push('Escribe el nombre de la escuela tal cual (por ejemplo, Esc. Primaria "Benito Juárez").');

  // d) Archivos: que estén, que sean PDF o imagen y que no estén vacíos ni pesen de más
  archivos.forEach(a => {
    if (!a.archivos.length) return m.push('Falta el documento: ' + a.nombre + '.');
    a.archivos.forEach(f => {
      if (f.error) return m.push('No se pudo abrir el archivo de ' + a.nombre + '. Súbelo otra vez.');
      if (!TIPOS_OK.includes(f.tipo)) m.push(a.nombre + ' debe ser PDF o imagen (JPG o PNG).');
      if (f.bytes === 0) m.push(a.nombre + ' está vacío.');
      if (f.bytes > cfg.tamano_max_mb * 1048576) m.push(a.nombre + ' pesa más de ' + cfg.tamano_max_mb + ' MB.');
    });
  });

  // e) Contenido de los documentos (texto leído con OCR)
  if (cfg.revisar_contenido) {
    const texto = {};
    archivos.forEach(a => texto[a.clave] = a.archivos.map(f => f.texto || '').join(' '));
    const legible = clave => {
      const a = archivos.find(x => x.clave === clave);
      if (!a.archivos.length || a.archivos.some(f => f.error)) return false;              // ya se avisó del problema
      if (texto[clave].replace(/\s/g, '').length < 30) { m.push('No se pudo leer el texto de: ' + DOCS[clave] + '. Sube un archivo más claro (sin sombras ni partes cortadas).'); return false; }
      return true;
    };
    const apellidosAlumno = alumno.slice(0, 2);                                           // "por apellidos": las dos primeras palabras

    if (legible('acta')) {
      if (!contiene_(texto.acta, ['NACIMIENTO'], 1)) m.push('El archivo del acta no parece un acta de nacimiento.');
      if (alumno.length >= 3 && !contiene_(texto.acta, apellidosAlumno, 2)) m.push('Tus apellidos no aparecen en el acta de nacimiento.');
      if (tutor.length >= 3 && !contiene_(texto.acta, tutor, 2)) m.push('El nombre de tu padre, madre o tutor no aparece en el acta, así que no se comprueba el parentesco.');
    }
    if (legible('constancia')) {
      if (!contiene_(texto.constancia, ['SERVICIO', 'LABORA', 'ACTIVO', 'PLAZA'], 1)) m.push('El archivo no parece una constancia de servicio.');
      if (tutor.length >= 3 && !contiene_(texto.constancia, tutor, 2)) m.push('El nombre de tu padre, madre o tutor no aparece en la constancia de servicio.');
      const fechas = buscarFechas(texto.constancia).filter(f => f <= new Date(enviado.getTime() + 864e5));
      if (!fechas.length) m.push('No se encontró la fecha de emisión en la constancia de servicio.');
      else {
        const dias = Math.floor((inicioDia_(enviado) - inicioDia_(new Date(Math.max.apply(null, fechas)))) / 864e5);
        if (dias > cfg.dias_max_constancia) m.push('La constancia de servicio tiene ' + dias + ' días; debe tener máximo ' + cfg.dias_max_constancia + '. Pide una nueva.');
      }
    }
    if (legible('comprobante')) {
      if (tutor.length >= 3 && !contiene_(texto.comprobante, tutor, 2)) m.push('El nombre de tu padre, madre o tutor no aparece en el comprobante de percepciones.');
    }
    if (legible('solicitud')) {
      if (!contiene_(texto.solicitud, ['DIRECTOR', 'DIRECTORA'], 1)) m.push('La solicitud debe ir dirigida al Director.');
      if (tutor.length >= 3 && !contiene_(texto.solicitud, tutor, 2)) m.push('La solicitud debe mencionar el nombre de tu padre, madre o tutor.');
    }
  }
  return m;
}

/** Busca fechas escritas como 23/11/2026, 23-11-26 o "23 de noviembre de 2026". Devuelve objetos Date. */
function buscarFechas(texto) {
  const t = sinAcentos_(texto);
  const MESES = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE'];
  const res = [];
  const valida = (a, mes, dia) => { const f = new Date(a, mes, dia); if (f.getMonth() === mes && a > 2000 && a < 2100) res.push(f); };
  let x;
  const r1 = /\b(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2,4})\b/g;
  while ((x = r1.exec(t))) { let a = +x[3]; if (a < 100) a += 2000; valida(a, +x[2] - 1, +x[1]); }
  const r2 = new RegExp('\\b(\\d{1,2})\\s*(?:DE\\s+)?(' + MESES.join('|') + '|SETIEMBRE)\\s*(?:DE[L]?\\s+)?(\\d{4})\\b', 'g');
  while ((x = r2.exec(t))) valida(+x[3], x[2] === 'SETIEMBRE' ? 8 : MESES.indexOf(x[2]), +x[1]);
  return res;
}


// ===== 5. Correos =====
function enviarCorreo_(d, estado, motivos, folio, cfg) {
  const para = String(d.correo || d.correoGoogle || '').trim();
  if (!para) return 'Sin correo';
  let asunto, color, cuerpo;
  const nombre = nombreParaSaludo_(d.nombre);
  if (estado === 'Autorizada') {
    asunto = '✅ Exención autorizada · folio ' + folio; color = '#2E9E5B';
    cuerpo = '<p>¡Hola, ' + nombre + '! Tu solicitud de <b>exención de pago</b> del periodo <b>' + cfg.periodo + '</b> fue <b>autorizada</b>.</p>' +
             '<p>Ya puedes pagar tu reinscripción con la exención <b>a más tardar el ' + fechaTexto_(cfg.fecha_limite_pago) + '</b>.</p>';
  } else if (estado === 'Requiere corrección' || estado === 'Rechazada') {
    asunto = '⚠️ Tu solicitud de exención necesita correcciones · folio ' + folio; color = '#D64545';
    cuerpo = '<p>Hola, ' + nombre + '. Revisamos tu solicitud y <b>todavía no se puede autorizar</b> por lo siguiente:</p><ul>' +
             motivos.map(x => '<li>' + x + '</li>').join('') + '</ul>' +
             '<p>Corrige lo indicado y <a href="' + urlFormulario_() + '"><b>envía el formulario de nuevo</b></a>.</p>';
  } else {
    asunto = '📥 Recibimos tu solicitud de exención · folio ' + folio; color = '#2F7BD8';
    cuerpo = '<p>Hola, ' + nombre + '. Tu solicitud está <b>completa</b> y la tiene el personal del área. Te avisaremos por este medio cuando quede autorizada.</p>';
  }
  const html = '<div style="font-family:Calibri,Arial,sans-serif;max-width:560px;border:1px solid #D5DCE3;border-radius:10px;overflow:hidden">' +
    '<div style="background:#16496E;color:#fff;padding:14px 18px"><b>IT Matehuala · Exenciones de pago</b><br><span style="font-size:12px;color:#BFE6E6">Prototipo escolar de AutoTec</span></div>' +
    '<div style="border-left:6px solid ' + color + ';padding:14px 18px;color:#1F2A37;font-size:15px">' + cuerpo +
    '<p style="color:#6B7280;font-size:13px">Folio: <b>' + folio + '</b> · Número de control: ' + d.control + '</p></div>' +
    '<div style="background:#F2F5F7;color:#6B7280;font-size:12px;padding:10px 18px">Mensaje automático. Prototipo escolar: no es una resolución oficial del Instituto.</div></div>';
  try {
    const op = { htmlBody: html, name: cfg.remitente };
    if (cfg.correo_area) op.bcc = cfg.correo_area;
    MailApp.sendEmail(para, asunto, 'Folio ' + folio + ': ' + estado + (motivos.length ? '\n- ' + motivos.join('\n- ') : ''), op);
    return 'Enviado a ' + para + ' · ' + Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'dd/MM/yyyy HH:mm');
  } catch (err) {
    return 'Error: ' + err.message;
  }
}


// ===== 6. Lectura de archivos y OCR =====
function leerArchivos_(d, cfg) {
  return Object.keys(DOCS).map(clave => {
    const ids = (String(d[clave]).match(/id=([\w-]+)/g) || []).map(x => x.slice(3));
    return {
      clave: clave, nombre: DOCS[clave],
      archivos: ids.map(id => {
        try {
          const f = DriveApp.getFileById(id);
          const info = { id: id, tipo: f.getMimeType(), bytes: f.getSize() };
          if (cfg.revisar_contenido && TIPOS_OK.includes(info.tipo) && info.bytes > 0) info.texto = leerTexto_(id);
          return info;
        } catch (err) { console.error('No se pudo abrir ' + id + ': ' + err.message); return { id: id, error: true }; }
      })
    };
  });
}

/** Convierte una copia del archivo a Documento de Google con OCR, saca el texto y borra la copia. */
function leerTexto_(id) {
  let copia;
  try {
    try { copia = Drive.Files.copy({ name: 'ocr_temp', mimeType: MimeType.GOOGLE_DOCS }, id, { ocrLanguage: 'es' }); }   // Drive API v3
    catch (e3) { copia = Drive.Files.copy({ title: 'ocr_temp' }, id, { ocr: true, ocrLanguage: 'es' }); }                  // Drive API v2
    return DocumentApp.openById(copia.id).getBody().getText();
  } catch (err) {
    return '';
  } finally {
    if (copia) try { DriveApp.getFileById(copia.id).setTrashed(true); } catch (e) {}
  }
}

function probarOcr_() { try { return typeof Drive !== 'undefined' && !!Drive.Files; } catch (e) { return false; } }


// ===== 7. Funciones de apoyo =====
function sinAcentos_(t) { return String(t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase(); }

function palabras_(t) {                                      // palabras de un nombre, sin acentos y sin "DE", "LA"...
  return sinAcentos_(t).replace(/[^A-Z\s]/g, ' ').split(/\s+/).filter(p => p.length > 2 && !['DEL', 'LAS', 'LOS'].includes(p));
}

function contiene_(texto, palabras, minimo) {                // ¿aparecen al menos "minimo" de esas palabras en el texto?
  const t = ' ' + sinAcentos_(texto).replace(/[^A-Z0-9]+/g, ' ') + ' ';
  const unicas = Array.from(new Set(palabras.map(sinAcentos_)));
  return unicas.filter(p => t.includes(' ' + p + ' ') || (p.length > 7 && t.includes(p))).length >= Math.min(minimo, unicas.length);
}

function hojaRespuestas_() {
  const ss = SpreadsheetApp.getActive();
  return ss.getSheets().find(h => h.getFormUrl && h.getFormUrl()) || ss.getSheets()[0];
}

function encabezados_(hoja) {
  const fila = hoja.getRange(1, 1, 1, hoja.getLastColumn()).getValues()[0];
  const enc = {};
  fila.forEach((t, i) => { if (t) enc[String(t).trim()] = i + 1; });
  return enc;
}

function asegurarColumnas_(hoja) {                           // agrega al final las columnas del sistema si faltan
  const enc = encabezados_(hoja);
  COLS.forEach(c => {
    if (!enc[c]) {
      const col = hoja.getLastColumn() + 1;
      hoja.getRange(1, col).setValue(c).setFontWeight('bold').setBackground('#10A5A8').setFontColor('#FFFFFF');
      enc[c] = col;
    }
  });
  return enc;
}

function datosDeFila_(enc, v) {
  const titulos = Object.keys(enc);
  const buscar = clave => {
    const t = titulos.find(k => sinAcentos_(k).includes(sinAcentos_(clave)));
    return t ? v[enc[t] - 1] : '';
  };
  const colGoogle = titulos.find(k => /^(direcci[oó]n de )?correo electr[oó]nico$|^email/i.test(k.trim()));
  const d = { marca: v[0], correoGoogle: colGoogle ? v[enc[colGoogle] - 1] : '' };
  Object.keys(P).forEach(k => d[k] = buscar(P[k]));
  d.control = String(d.control).trim().toUpperCase().replace(/\s/g, '');
  return d;
}

function otrasAutorizadas_(hoja, enc, fila) {                // números de control ya autorizados en otras filas
  if (hoja.getLastRow() < 2) return [];
  const datos = hoja.getRange(2, 1, hoja.getLastRow() - 1, hoja.getLastColumn()).getValues();
  return datos.filter((r, i) => i + 2 !== fila && r[enc['Estado'] - 1] === 'Autorizada')
              .map(r => datosDeFila_(enc, r).control);
}

function leerConfig_() {
  const h = SpreadsheetApp.getActive().getSheetByName(HOJA_CONFIG);
  if (!h) throw new Error('Falta la hoja "Configuración". Usa el menú Exenciones → Configurar (primera vez).');
  const c = {};
  h.getRange(2, 1, h.getLastRow() - 1, 2).getValues().forEach(r => c[r[0]] = r[1]);
  c.confirmacion_automatica = c.confirmacion_automatica === true;
  c.revisar_contenido = c.revisar_contenido === true && probarOcr_();
  c.dominio_institucional = String(c.dominio_institucional || '').trim().replace(/^@/, '');
  c.fecha_limite_pago = fecha_(c.fecha_limite_pago) || c.fecha_limite_pago;
  c.dias_max_constancia = Number(c.dias_max_constancia) || 31;
  c.tamano_max_mb = Number(c.tamano_max_mb) || 10;
  return c;
}

function urlFormulario_() {
  try { return FormApp.openByUrl(SpreadsheetApp.getActive().getFormUrl()).getPublishedUrl(); } catch (err) { return ''; }
}

function extension_(n) { const m = String(n).match(/\.[A-Za-z0-9]{2,5}$/); return m ? m[0].toLowerCase() : ''; }
function avisar_(texto) {                                     // muestra un aviso en la hoja; si se ejecuta desde el editor, lo escribe en el registro
  try { SpreadsheetApp.getUi().alert(texto); } catch (e) { console.log(texto); }
}
function fecha_(v) {                                         // acepta una fecha de la hoja o un texto dd/mm/aaaa
  if (v instanceof Date && !isNaN(v)) return v;
  const m = String(v || '').trim().match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})$/);
  return m ? new Date(+m[3], +m[2] - 1, +m[1]) : null;
}
function inicioDia_(f) { const x = new Date(f); x.setHours(0, 0, 0, 0); return x; }
function nombreParaSaludo_(n) { const p = String(n).trim().split(/\s+/); return p.length >= 3 ? p.slice(2).join(' ') : (p[0] || ''); }
function fechaTexto_(f) {
  const M = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
  const x = new Date(f); return x.getDate() + ' de ' + M[x.getMonth()] + ' de ' + x.getFullYear();
}
