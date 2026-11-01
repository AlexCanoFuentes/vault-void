// Avisos en el móvil (src/movil.ts) con una base de datos de mentira y un servicio de avisos de mentira en 127.0.0.1.
// Ejecutar: node red/pruebas/movil.mjs   (Node 24 entiende el TypeScript de movil.ts quitándole los tipos)
import assert from 'node:assert/strict';
import http from 'node:http';
import { webcrypto as crypto } from 'node:crypto';
const { avisarMovil, apuntar, endpointValido, MAX_POR_ESPACIO } = await import('../src/movil.ts');

// D1 de mentira: solo las consultas que usa movil.ts.
function base() {
  const filas = [], bloqueos = new Set();
  const db = { filas, bloqueos, prepare(sql) { return { bind(...a) { return {
    first: async () => {
      if (sql.includes('FROM bloqueos')) return bloqueos.has(a[0] + ':' + a[1]) ? { 1: 1 } : null;
      if (sql.includes('COUNT(*)')) return { n: filas.filter(f => f.perfil_id === a[0] && f.endpoint !== a[1]).length };
      if (sql.includes('SELECT 1 FROM avisos_movil')) return filas.some(f => f.perfil_id === a[0] && f.endpoint === a[1]) ? { 1: 1 } : null;
      throw Error('consulta no esperada: ' + sql);
    },
    all: async () => ({ results: filas.filter(f => f.perfil_id === a[0]).slice(0, a[1]).map(f => ({ endpoint: f.endpoint })) }),
    run: async () => {
      if (sql.startsWith('INSERT OR REPLACE')) { const i = filas.findIndex(f => f.perfil_id === a[0] && f.endpoint === a[1]); const f = { perfil_id: a[0], endpoint: a[1], creado: a[2] }; i < 0 ? filas.push(f) : filas[i] = f; }
      else if (sql.startsWith('DELETE FROM avisos_movil WHERE perfil_id')) { const i = filas.findIndex(f => f.perfil_id === a[0] && f.endpoint === a[1]); if (i >= 0) filas.splice(i, 1); }
      else if (sql.startsWith('DELETE FROM avisos_movil WHERE endpoint')) { for (let i = filas.length - 1; i >= 0; i--) if (filas[i].endpoint === a[0]) filas.splice(i, 1); }
      else throw Error('escritura no esperada: ' + sql);
    } }; } }; } };
  return db;
}

// Servicio de avisos de mentira: apunta cada petición y contesta lo que se le pida por ruta.
const recibidas = [];
const servicio = http.createServer((req, res) => { let cuerpo = ''; req.on('data', c => cuerpo += c); req.on('end', () => {
  recibidas.push({ url: req.url, metodo: req.method, cabeceras: req.headers, cuerpo });
  res.writeHead(req.url.startsWith('/caducada') ? 410 : 201); res.end(); }); });
await new Promise(r => servicio.listen(0, '127.0.0.1', r));
const raiz = `http://127.0.0.1:${servicio.address().port}`;

const par = await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']);
const publica = Buffer.from(await crypto.subtle.exportKey('raw', par.publicKey)).toString('base64url');
const env = { DB: base(), VAPID_PRIVADA: JSON.stringify(await crypto.subtle.exportKey('jwk', par.privateKey)), VAPID_PUBLICA: publica, MOVIL_PRUEBA: '1' };

try {
  // Lista cerrada de servicios
  assert.equal(endpointValido({}, 'https://fcm.googleapis.com/fcm/send/abc'), true);
  assert.equal(endpointValido({}, 'https://web.push.apple.com/QWxl'), true);
  assert.equal(endpointValido({}, 'https://evil.example/push'), false, 'otro host no vale');
  assert.equal(endpointValido({}, 'http://fcm.googleapis.com/x'), false, 'sin https no vale');
  assert.equal(endpointValido({}, raiz + '/x'), false, '127.0.0.1 solo en pruebas');
  console.log('✓ Solo direcciones https de servicios de avisos conocidos: la red no hace peticiones a donde le digan.');

  assert.equal((await apuntar(env, 1, 'alta', 'https://evil.example/x')).status, 400);
  assert.equal((await apuntar(env, 1, 'otra', raiz + '/a')).status, 400);
  assert.equal((await apuntar(env, 1, 'alta', raiz + '/a')).status, 200);
  assert.equal((await apuntar(env, 2, 'alta', raiz + '/a')).status, 200, 'el mismo móvil en dos espacios');
  for (let i = 0; i < MAX_POR_ESPACIO - 1; i++) await apuntar(env, 3, 'alta', raiz + '/t' + i);
  assert.equal((await apuntar(env, 3, 'alta', raiz + '/t-extra')).status, 200);
  assert.equal((await apuntar(env, 3, 'alta', raiz + '/t-otro')).status, 409, `tope de ${MAX_POR_ESPACIO} por espacio`);
  console.log('✓ Alta, el mismo móvil en dos espacios y tope de 5 por espacio.');

  // Aviso: vacío, firmado y con sus cabeceras
  await avisarMovil(env, 1, 99);
  assert.equal(recibidas.length, 1); const r = recibidas[0];
  assert.equal(r.metodo, 'POST'); assert.equal(r.cuerpo, '', 'el aviso va vacío'); assert.equal(r.cabeceras.ttl, '86400'); assert.equal(r.cabeceras.urgency, 'high');
  const m = /^vapid t=([^,]+), k=(.+)$/.exec(r.cabeceras.authorization); assert.ok(m, 'cabecera VAPID'); assert.equal(m[2], publica);
  const [h, c, f] = m[1].split('.');
  const reclamo = JSON.parse(Buffer.from(c, 'base64url'));
  assert.equal(reclamo.aud, raiz); assert.ok(reclamo.exp > Date.now() / 1000 && reclamo.exp <= Date.now() / 1000 + 24 * 3600); assert.match(reclamo.sub, /^(mailto:|https:\/\/)/);
  assert.equal(JSON.parse(Buffer.from(h, 'base64url')).alg, 'ES256');
  assert.ok(await crypto.subtle.verify({ name: 'ECDSA', hash: 'SHA-256' }, par.publicKey, Buffer.from(f, 'base64url'), new TextEncoder().encode(h + '.' + c)), 'la firma se verifica con la clave pública');
  console.log('✓ El aviso sale vacío, con TTL y urgencia, y su firma VAPID se verifica con la clave pública.');

  // Bloqueo, caducadas y sin claves
  recibidas.length = 0; env.DB.bloqueos.add('1:99'); await avisarMovil(env, 1, 99); assert.equal(recibidas.length, 0, 'un bloqueado no hace sonar el móvil');
  env.DB.bloqueos.clear();
  await apuntar(env, 4, 'alta', raiz + '/caducada'); await avisarMovil(env, 4, 99);
  assert.ok(!env.DB.filas.some(f => f.endpoint.endsWith('/caducada')), 'una suscripción caducada (410) se borra');
  recibidas.length = 0; await avisarMovil({ ...env, VAPID_PRIVADA: undefined }, 1, 99); assert.equal(recibidas.length, 0, 'sin claves no se avisa');
  recibidas.length = 0; await avisarMovil(env, 5, 99); assert.equal(recibidas.length, 0, 'sin suscripción no se avisa');
  await apuntar(env, 1, 'baja', raiz + '/a'); recibidas.length = 0; await avisarMovil(env, 1, 99); assert.equal(recibidas.length, 0, 'tras la baja no suena');
  console.log('✓ Un bloqueado no hace sonar el móvil; caducadas, sin claves, sin suscripción y tras la baja: nada.');
  await avisarMovil({ ...env, DB: { prepare() { throw Error('base caída'); } } }, 1, 99);
  console.log('✓ Si algo falla, el aviso no lanza: el mensaje ya guardado no se tumba.');
} finally { servicio.close(); }
