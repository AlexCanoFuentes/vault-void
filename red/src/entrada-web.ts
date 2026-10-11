/** VV-010 · Credenciales aleatorias, sesiones privadas y alojamiento por binding. */
import { huella, llaveNueva, problemaAlias, problemaHuella } from './reglas.js';

export interface EntradaEnv {
  DB: D1Database;
  NUBE?: Fetcher;
  TOPE_WEB?: string;
}
interface Propietario { id: number; alias: string; listo: number; recuperacion_hash: string }
const COOKIE = '__Host-void';
const VIDA = 30 * 24 * 60 * 60 * 1000;
const RE_CODIGO = /^vr_[0-9a-f]{64}$/;
const cab = { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' };
const json = (status: number, datos: unknown, extra = {}) => new Response(JSON.stringify(datos), { status, headers: { ...cab, ...extra } });
const fallo = (status: number, error: string) => json(status, { error });
async function leer(req: Request) {
  if (!req.headers.get('content-type')?.startsWith('application/json')) throw new Error('formato');
  const texto = await req.text();
  if (texto.length > 32_768) throw new Error('tamaño');
  const b = JSON.parse(texto);
  if (!b || typeof b !== 'object' || Array.isArray(b)) throw new Error('formato');
  return b;
}
async function sesion(req: Request, env: EntradaEnv): Promise<Propietario | null> {
  const token = req.headers.get('cookie')?.split(';').map(s => s.trim()).find(s => s.startsWith(COOKIE + '='))?.slice(COOKIE.length + 1);
  if (!token || !/^vv_[A-Za-z0-9_-]{43}$/.test(token)) return null;
  return env.DB.prepare('SELECT p.id,p.alias,w.listo,w.recuperacion_hash FROM web_sesiones s JOIN perfiles p ON p.id=s.perfil_id JOIN web_vaults w ON w.perfil_id=p.id WHERE s.token_hash=? AND s.caduca>?')
    .bind(await huella(token), Date.now()).first<Propietario>();
}
async function entrar(p: Propietario, req: Request, env: EntradaEnv) {
  const token = llaveNueva();
  const anterior = req.headers.get('cookie')?.split(';').map(s => s.trim()).find(s => s.startsWith(COOKIE + '='))?.slice(COOKIE.length + 1);
  await env.DB.batch([
    env.DB.prepare('DELETE FROM web_sesiones WHERE caduca<? OR token_hash=?').bind(Date.now(), await huella(anterior || '')),
    env.DB.prepare('INSERT INTO web_sesiones(token_hash,perfil_id,caduca) VALUES(?,?,?)').bind(await huella(token), p.id, Date.now() + VIDA),
  ]);
  return json(200, { alias: p.alias, listo: !!p.listo }, { 'set-cookie': `${COOKIE}=${token}; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=${VIDA / 1000}` });
}
export async function llaveWeb(codigo: string) {
  const hex = await huella('void-web-v1:' + codigo);
  return 'vv_' + btoa(String.fromCharCode(...hex.match(/../g)!.map(n => parseInt(n, 16)))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
export async function entradaWeb(req: Request, env: EntradaEnv, publicar: (req: Request) => Promise<Response>): Promise<Response> {
  const url = new URL(req.url), ruta = url.pathname.slice('/v1/web'.length);
  // El binding no está expuesto por URL. Cookie solo en el dominio de la interfaz.
  if (url.hostname !== 'vaultvoid.app' && !['localhost', '127.0.0.1'].includes(url.hostname)) return fallo(404, 'Esta entrada está en vaultvoid.app.');
  if (!['GET', 'POST'].includes(req.method)) return fallo(405, 'Método no permitido.');
  if (req.method === 'POST' && req.headers.get('origin') !== url.origin) return fallo(403, 'Abre esta pantalla desde Void para continuar.');
  try {
    if (ruta === '/crear' && req.method === 'POST') {
      const b = await leer(req), alias = typeof b.alias === 'string' ? b.alias.trim() : '';
      const mal = problemaAlias(alias) || problemaHuella(b.huella);
      if (mal) return fallo(400, mal);
      if (!RE_CODIGO.test(b.recuperacion || '') || b.consentimiento !== true || !Array.isArray(b.respuestas) || b.respuestas.length !== 7 || b.respuestas.some((r: unknown) => r !== null && (typeof r !== 'string' || r.length > 3000))) return fallo(400, 'Faltan tus respuestas, tu código o la autorización para guardarlas.');
      if (!/^vc_[0-9a-f]{64}$/.test(b.cuento || '')) return fallo(400, 'Guarda primero tu huella: así será la misma al volver.');
      if (b.propuesta !== null && (typeof b.propuesta !== 'string' || b.propuesta.length > 100)) return fallo(400, 'La propuesta no es válida.');
      if (!env.NUBE) return fallo(503, 'El alojamiento todavía no está abierto. Tus respuestas siguen en este navegador.');
      const prueba = await huella(b.recuperacion), llave = await llaveWeb(b.recuperacion);
      let p = await env.DB.prepare('SELECT p.id,p.alias,w.listo,w.recuperacion_hash FROM perfiles p LEFT JOIN web_vaults w ON w.perfil_id=p.id WHERE p.alias=?').bind(alias).first<Propietario>();
      if (p && p.recuperacion_hash !== prueba) return fallo(409, 'Ese nombre ya tiene un vault. Elige otro o entra con su código.');
      if (!p) {
        const limite = Number(env.TOPE_WEB || 0);
        if (!Number.isInteger(limite) || limite < 1) return fallo(503, 'El piloto de alojamiento aún está cerrado. Conservamos tus respuestas aquí.');
        // D1 serializa este lote: el límite también vale con dos altas simultáneas.
        await env.DB.batch([
          env.DB.prepare("INSERT OR IGNORE INTO perfiles(alias,agente,huella_llave,publico,creado) SELECT ?,'Void',?,'',? WHERE (SELECT COUNT(*) FROM web_vaults)<?").bind(alias, await huella(llave), Date.now(), limite),
          env.DB.prepare('INSERT OR IGNORE INTO web_vaults(perfil_id,recuperacion_hash,creado) SELECT id,?,? FROM perfiles WHERE alias=? AND huella_llave=?').bind(prueba, Date.now(), alias, await huella(llave)),
        ]);
        p = await env.DB.prepare('SELECT p.id,p.alias,w.listo,w.recuperacion_hash FROM perfiles p JOIN web_vaults w ON w.perfil_id=p.id WHERE p.alias=?').bind(alias).first<Propietario>();
        if (!p) return fallo(503, 'Ahora mismo no queda sitio en el piloto. Tus respuestas siguen aquí.');
        if (p.recuperacion_hash !== prueba) return fallo(409, 'Ese nombre acaba de reservarse. Elige otro.');
      }
      if (!p.listo) {
        // Reclamar antes de sembrar: una huella ajena nunca crea una caja con palabras.
        const r = await publicar(new Request(req.url, { method: 'POST', headers: { authorization: 'Bearer ' + llave, 'content-type': 'application/json' }, body: JSON.stringify({ huella: b.huella, cuento: b.cuento }) }));
        if (!r.ok) return r;
        const nube = await env.NUBE.fetch(new Request('https://privado/crear', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ alias, prueba, llave, respuestas: b.respuestas, propuesta: b.propuesta }) }));
        if (!nube.ok) return fallo(503, 'No hemos podido preparar tu espacio. Vuelve a intentarlo: no se crea otro vault ni se pierden tus respuestas.');
        await env.DB.prepare('UPDATE web_vaults SET listo=1 WHERE perfil_id=?').bind(p.id).run();
        p.listo = 1;
      }
      return entrar(p, req, env);
    }
    if (ruta === '/entrar' && req.method === 'POST') {
      const b = await leer(req);
      if (typeof b.alias !== 'string' || !RE_CODIGO.test(b.recuperacion || '')) return fallo(401, 'El nombre o el código no coinciden.');
      const p = await env.DB.prepare('SELECT p.id,p.alias,w.listo,w.recuperacion_hash FROM perfiles p JOIN web_vaults w ON w.perfil_id=p.id WHERE p.alias=? AND w.recuperacion_hash=?').bind(b.alias.trim(), await huella(b.recuperacion)).first<Propietario>();
      if (!p) return fallo(401, 'El nombre o el código no coinciden.');
      if (!p.listo) return fallo(409, 'Tu espacio está a medio preparar. Vuelve al cuento en el navegador donde empezaste y pulsa Crear mi espacio.');
      return entrar(p, req, env);
    }
    const p = await sesion(req, env);
    if (!p) return fallo(401, 'Entra con el nombre y el código de tu espacio.');
    if (ruta === '/yo' && req.method === 'GET') {
      const h = await env.DB.prepare('SELECT datos,semilla FROM huellas WHERE perfil_id=?').bind(p.id).first<{datos:string;semilla:string|null}>();
      return json(200, { alias: p.alias, listo: !!p.listo, huella: h ? JSON.parse(h.datos) : null, semilla: h?.semilla || p.alias });
    }
    if (ruta === '/salir' && req.method === 'POST') {
      const token = req.headers.get('cookie')!.split(';').map(s => s.trim()).find(s => s.startsWith(COOKIE + '='))!.slice(COOKIE.length + 1);
      await env.DB.prepare('DELETE FROM web_sesiones WHERE token_hash=?').bind(await huella(token)).run();
      return json(200, { saliste: true }, { 'set-cookie': `${COOKIE}=; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=0` });
    }
    if (ruta.startsWith('/agente/') && env.NUBE && p.listo) {
      const api = ruta.slice('/agente'.length);
      const permitido = req.method === 'GET' ? /^\/(session(?:\/status|\/ses_[A-Za-z0-9]+(?:\/message)?)?|permission|question)$/.test(api)
        : /^\/(session|session\/ses_[A-Za-z0-9]+\/(prompt_async|abort)|permission\/[A-Za-z0-9_-]+\/reply|question\/[A-Za-z0-9_-]+\/(reply|reject))$/.test(api);
      if (!permitido) return fallo(404, 'Esa acción no está disponible.');
      const b = req.method === 'POST' ? await leer(req) : null;
      if (api.endsWith('/prompt_async')) {
        if (!Array.isArray(b.parts) || b.parts.length !== 1 || b.parts[0].type !== 'text' || typeof b.parts[0].text !== 'string' || !b.parts[0].text.trim() || b.parts[0].text.length > 6000) return fallo(400, 'Escribe una petición de hasta 6000 caracteres.');
        // No se aceptan overrides de sistema, modelo, agente o herramientas.
        Object.keys(b).forEach(k => { if (k !== 'parts') delete b[k]; });
      } else if (req.method === 'POST' && api === '/session') Object.keys(b).forEach(k => delete b[k]);
      else if (api.startsWith('/permission/') && api.endsWith('/reply')) {
        if (!['once','reject'].includes(b.reply)) return fallo(400, 'Elige permitir esta vez o rechazar.');
        Object.keys(b).forEach(k=>{if(k!=='reply')delete b[k];});
      } else if(api.startsWith('/question/') && api.endsWith('/reply')) {
        if(!Array.isArray(b.answers)||b.answers.length>10||b.answers.some((a:unknown)=>!Array.isArray(a)||a.length>20||a.some(s=>typeof s!=='string'||s.length>3000)))return fallo(400,'Las respuestas no son válidas.');
        Object.keys(b).forEach(k=>{if(k!=='answers')delete b[k];});
      }
      const r = await env.NUBE.fetch(new Request('https://privado/agente' + api, { method: req.method, headers: { 'x-void-alias': p.alias, 'x-void-prueba': p.recuperacion_hash, 'content-type': 'application/json' }, body: b ? JSON.stringify(b) : undefined }));
      return new Response(r.body, { status: r.status, headers: cab });
    }
    return fallo(404, 'Esa pantalla no existe.');
  } catch { return fallo(503, 'No hemos podido completar la petición. Tus datos no se han borrado; vuelve a intentarlo.'); }
}
