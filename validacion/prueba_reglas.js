// Prueba las reglas de validación sin Google: node validacion/prueba_reglas.js
const fs = require('fs'); eval(fs.readFileSync(require('path').join(__dirname,'Codigo.gs'), 'utf8') + '\nglobalThis.revisar=revisar;globalThis.buscarFechas=buscarFechas;');
const env = new Date(2026, 10, 23, 10, 0);
const cfg = { inicio_solicitudes: new Date(2026, 10, 16), fin_solicitudes: new Date(2026, 11, 4), dias_max_constancia: 31, tamano_max_mb: 10, revisar_contenido: true, dominio_institucional: 'matehuala.tecnm.mx' };
const T = {
  acta: 'ACTA DE NACIMIENTO. REGISTRADO: JOSUÉ EMMANUEL RAMÍREZ CRUZ. PADRES: MARÍA CRUZ LÓPEZ, JUAN RAMÍREZ PÉREZ',
  constancia: 'CONSTANCIA DE SERVICIO. Se hace constar que la C. MARIA CRUZ LOPEZ labora en esta escuela con plaza... Matehuala, S.L.P., a 10 de noviembre de 2026',
  comprobante: 'COMPROBANTE DE PERCEPCIONES NOMINA QNA 21 CRUZ LOPEZ MARIA importe',
  solicitud: 'C. DIRECTOR DEL INSTITUTO TECNOLÓGICO DE MATEHUALA. Yo, María Cruz López, solicito la exención para mi hijo...'
};
const docs = (cambios = {}) => Object.keys(T).map(k => ({ clave: k, nombre: k, archivos: cambios[k] === null ? [] : [{ id: 'x', tipo: 'application/pdf', bytes: 200000, texto: cambios[k] ?? T[k] }] }));
const base = { marca: env, nombre: 'Ramírez Cruz Josué Emmanuel', control: '24660080', correo: 'l24660080@matehuala.tecnm.mx', trabajador: 'María Cruz López', escuela: 'Esc. Primaria "Benito Juárez"' };
const casos = [
  ['Todo correcto', base, docs()],
  ['Correo gmail', { ...base, correo: 'ec7046032@gmail.com' }, docs()],
  ['Escuela vaga', { ...base, escuela: 'la de mi pueblo' }, docs()],
  ['Acta de otra familia', base, docs({ acta: 'ACTA DE NACIMIENTO DE PEDRO GOMEZ SOLIS, PADRES ANA SOLIS RUIZ' })],
  ['Constancia vieja (01/09/2026)', base, docs({ constancia: 'CONSTANCIA DE SERVICIO MARIA CRUZ LOPEZ labora. 01/09/2026' })],
  ['Constancia sin fecha', base, docs({ constancia: 'CONSTANCIA DE SERVICIO MARIA CRUZ LOPEZ labora en la escuela primaria' })],
  ['Solicitud sin Director', base, docs({ solicitud: 'Solicito la exencion de pago para mi hijo. Maria Cruz Lopez, firma' })],
  ['Imagen ilegible', base, docs({ comprobante: '  ' })],
  ['Falta acta', base, docs({ acta: null })],
];
for (const [n, d, a] of casos) console.log(n.padEnd(30), '→', JSON.stringify(revisar(d, cfg, a, [])));
console.log(buscarFechas('a 5 de Setiembre del 2026; 03-11-26; 31/02/2026').map(f => f.toISOString().slice(0, 10)));
