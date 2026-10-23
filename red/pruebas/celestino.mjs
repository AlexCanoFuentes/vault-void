// Worker real y SQL de las migraciones con SQLite en memoria; sin credenciales ni servicios externos.
// Ejecutar con Node 24: node red/pruebas/celestino.mjs
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, readdirSync } from 'node:fs';
import { registerHooks, stripTypeScriptTypes } from 'node:module';
const src = new URL('../src/', import.meta.url).href;
const hook = registerHooks({ resolve(specifier, context, next) {
  if (context.parentURL?.startsWith(src) && specifier.startsWith('./') && specifier.endsWith('.js'))
    return next(specifier.slice(0, -3) + '.ts', context);
  return next(specifier, context);
}, load(url, context, next) {
  if (url.startsWith(src) && url.endsWith('.ts')) return { format: 'module', shortCircuit: true,
    source: stripTypeScriptTypes(readFileSync(new URL(url), 'utf8'), { mode: 'transform' }) };
  return next(url, context);
} });
const { default: worker } = await import('../src/worker.ts');
hook.deregister();
const sql = new DatabaseSync(':memory:');
const migraciones = new URL('../migrations/', import.meta.url);
for (const n of readdirSync(migraciones).filter(n => n.endsWith('.sql')).sort()) sql.exec(readFileSync(new URL(n, migraciones), 'utf8'));
function consulta(orden, args = []) {
  const s = sql.prepare(orden);
  return { bind: (...a) => consulta(orden, a), first: async () => s.get(...args) || null,
    all: async () => ({ results: s.all(...args) }), run: async () => s.run(...args) };
}
const DB = { prepare: consulta, batch: async consultas => { for (const c of consultas) await c.run(); } };
const llave = 'vv_' + 'a'.repeat(43);
const huella = Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(llave))).toString('hex');
const publica = Buffer.alloc(32, 7).toString('base64');
for (const [id, alias] of [[1, 'emisor-prueba'], [2, 'void'], [3, 'otro-alias']])
  sql.prepare('INSERT INTO perfiles(id,alias,agente,huella_llave,creado,clave_publica) VALUES(?,?,?,?,?,?)')
    .run(id, alias, 'Agente', id === 1 ? huella : 'huella-' + id, Date.now(), publica);
const llamadas = [], tareas = [];
const env = { DB, CELESTINO_ALIAS: 'void', CELESTINO_PASE: 'pase-inventado', TOPE_MENSAJES_HORA: '1000',
  NUBE: { fetch: async req => { llamadas.push(req); return Response.json({ pendiente: true }, { status: 202 }); } } };
const ctx = { waitUntil: p => tareas.push(p) };
async function mandar(para = 'void', extra = {}, entorno = env) {
  const r = await worker.fetch(new Request('https://red.invalid/v1/mensajes', { method: 'POST',
    headers: { authorization: 'Bearer ' + llave, 'content-type': 'application/json' },
    body: JSON.stringify({ para, tipo: 'PETICION', enc: publica, sobre: Buffer.from('contenido cifrado inventado').toString('base64'), ...extra }),
  }), entorno, ctx);
  assert.equal(r.status, 201, await r.text());
  await Promise.all(tareas.splice(0));
}
try {
  await mandar('@void');
  assert.equal(llamadas.length, 1);
  assert.equal(llamadas[0].method, 'POST');
  assert.equal(new URL(llamadas[0].url).pathname, '/celestino/ronda');
  assert.equal(llamadas[0].headers.get('x-void-celestino'), env.CELESTINO_PASE);
  assert.equal(llamadas[0].headers.get('x-void-alias'), 'void');
  assert.equal(await llamadas[0].text(), '');
  await mandar('otro-alias'); assert.equal(llamadas.length, 1);
  await mandar('void', {}, { ...env, CELESTINO_ALIAS: undefined });
  await mandar('void', {}, { ...env, CELESTINO_PASE: undefined });
  await mandar('void', {}, { ...env, NUBE: undefined });
  assert.equal(llamadas.length, 1);
  await mandar('void', { nonce: 'a'.repeat(64) }); assert.equal(llamadas.length, 2, 'también con nonce');
  sql.prepare('INSERT INTO bloqueos VALUES(2,1,?)').run(Date.now());
  await mandar(); await mandar('void', { nonce: 'b'.repeat(64) });
  assert.equal(llamadas.length, 2, 'un bloqueo no despierta la caja');
  sql.exec('DELETE FROM bloqueos');
  await mandar('void', {}, { ...env, NUBE: { fetch() { throw Error('Fallo inventado'); } } });
  let terminar;
  const pendiente = new Promise(r => { terminar = r; });
  const lento = { ...env, NUBE: { fetch: () => pendiente } };
  const respuesta = await worker.fetch(new Request('https://red.invalid/v1/mensajes', { method: 'POST',
    headers: { authorization: 'Bearer ' + llave, 'content-type': 'application/json' },
    body: JSON.stringify({ para: 'void', tipo: 'PETICION', enc: publica, sobre: Buffer.from('otro sobre cifrado inventado').toString('base64') }),
  }), lento, ctx);
  assert.equal(respuesta.status, 201, 'el envío termina mientras la nube sigue pendiente');
  terminar(Response.json({ pendiente: true })); await Promise.all(tareas);
  console.log('✓ Destinatario, configuración, pase, bloqueo, nonce, fallo y nube lenta: el envío queda independiente.');
} finally { sql.close(); }
