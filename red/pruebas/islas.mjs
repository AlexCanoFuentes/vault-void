// Sesión y binding con dobles locales, sin abrir puertos ni consultar servicios.
import { createRequire } from 'node:module';
import assert from 'node:assert/strict';
const require = createRequire(import.meta.url);
const { build } = createRequire(require.resolve('wrangler/package.json'))('esbuild');
const { outputFiles } = await build({ entryPoints: [new URL('../src/entrada-web.ts', import.meta.url).pathname], bundle: true, format: 'esm', write: false });
const { entradaWeb } = await import('data:text/javascript;base64,' + Buffer.from(outputFiles[0].text).toString('base64'));
const token = 'vv_' + 'a'.repeat(43), prueba = 'b'.repeat(64), llamadas = [];
const hash = Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(token))).toString('hex');
const env = {
  DB: { prepare(sql) {
    assert.ok(sql.includes('FROM web_sesiones'));
    return { bind(h) { return { first: async () => h === hash ? { id: 1, alias: 'dueno-inventado', listo: 1, recuperacion_hash: 'c'.repeat(64), alojamiento_prueba: prueba } : null }; } };
  } },
  NUBE: { fetch: async req => { llamadas.push(req); return Response.json({ dormida: true, error: 'Caja inventada dormida.' }, { status: 409 }); } },
};
const origen = 'https://vaultvoid.app';
const pedir = (ruta, { metodo = 'GET', body, cookie = true, origin = origen, headers = {} } = {}) => entradaWeb(new Request(origen + '/v1/web/islas/' + ruta, {
  method: metodo, headers: { origin, 'content-type': 'application/json', ...(cookie ? { cookie: '__Host-void=' + token } : {}), ...headers }, body,
}), env, () => { throw Error('Las islas no publican.'); });
assert.equal((await pedir('listar', { cookie: false })).status, 401);
assert.equal((await pedir('guardar', { metodo: 'POST', body: '{}', origin: 'https://ajeno.invalid' })).status, 403);
for (const [ruta, metodo] of [['ejecutar', 'POST'], ['listar', 'POST'], ['guardar', 'GET'], ['borrar', 'GET'], ['listar?alias=ajeno', 'GET']]) assert.equal((await pedir(ruta, { metodo, body: metodo === 'POST' ? '{}' : undefined })).status, 404);
assert.equal(llamadas.length, 0);
assert.equal((await pedir('guardar', { metodo: 'POST', body: 'x'.repeat(69633) })).status, 413);
assert.equal((await pedir('guardar', { metodo: 'POST', body: '{}', headers: { 'content-type': 'text/plain' } })).status, 415);
const r = await pedir('listar', { headers: { 'x-void-alias': 'ajeno', 'x-void-prueba': 'ajena' } });
assert.equal(r.status, 409); assert.equal(r.headers.get('cache-control'), 'no-store'); assert.equal((await r.json()).dormida, true);
assert.equal(llamadas[0].url, 'https://privado/islas/listar');
assert.equal(llamadas[0].headers.get('x-void-alias'), 'dueno-inventado'); assert.equal(llamadas[0].headers.get('x-void-prueba'), prueba);
const raw = '{"isla":{"nombre":"Una","nombre":"Dos"},"revision":null}';
assert.equal((await pedir('guardar', { metodo: 'POST', body: raw })).status, 409);
assert.equal(await llamadas.at(-1).text(), raw, 'El JSON llega sin normalizar para rechazar campos duplicados en la caja.');
assert.equal((await pedir('borrar', { metodo: 'POST', body: '{"id":"inventada","revision":null}' })).status, 409);
console.log('✓ Cookie obligatoria, CSRF, acciones y métodos cerrados, límite por bytes y JSON.');
console.log('✓ El alias y la prueba salen de la sesión; se conserva el rechazo de caja dormida.');
console.log('✓ El binding conserva el JSON completo para la validación estricta de la caja.');
