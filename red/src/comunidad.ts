import { huella } from './reglas.js';
type Persona = { id: number; alias: string; listo?: number };
type Entorno = { DB: D1Database };
const json = (d: unknown, status = 200) => Response.json(d, { status, headers: { 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' } });
const fallo = (error: string, s = 400) => json({ error }, s);
const TOKEN = /^[0-9a-f]{64}$/;
const CREDENCIAL = /\b(?:vv_[A-Za-z0-9_-]{43}|v[rkd]_[0-9a-f]{64}|sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|sbp_[A-Za-z0-9]{20,})\b|-----BEGIN [A-Z ]*PRIVATE KEY-----/;
export function publicacion(b: Record<string, unknown>, p: Persona) {
  if (Object.keys(b).some(k => !['texto', 'tipo', 'token'].includes(k))) throw Error('La publicación solo admite texto y su tipo.');
  if (b.tipo !== 'plaza' && b.tipo !== 'oficial') throw Error('Elige una publicación para la plaza o un aviso de Void.');
  if (b.tipo === 'oficial' && p.alias !== 'void') throw Error('Solo la cuenta verificada de Void puede publicar avisos oficiales.');
  if (typeof b.texto !== 'string' || !b.texto.trim() || b.texto.trim().length > 1500 || /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(b.texto)) throw Error('Escribe un texto de hasta 1500 caracteres.');
  if (CREDENCIAL.test(b.texto)) throw Error('El texto parece incluir una credencial. Retírala antes de publicar.');
  return { tipo: b.tipo, texto: b.texto.trim() };
}
export async function comunidad(req: Request, env: Entorno, p: Persona, ruta: string, b: Record<string, unknown> = {}): Promise<Response> {
  const db = env.DB, ahora = Date.now(), u = new URL(req.url);
  if (!p.listo) return fallo('Termina de crear tu espacio antes de entrar en la comunidad.', 403);
  if (ruta === '/comunidad/resumen' && req.method === 'GET') {
    const r = await db.prepare(`SELECT
      (SELECT COUNT(*) FROM mensajes WHERE para_perfil=? AND caduca>?) mensajes,
      (SELECT COUNT(*) FROM comunidad_publicaciones c JOIN perfiles a ON a.id=c.perfil_id WHERE c.id>COALESCE(l.plaza,0) AND ((c.tipo='oficial' AND a.alias='void') OR NOT EXISTS(SELECT 1 FROM bloqueos b WHERE b.perfil_id=? AND b.bloquea_a=c.perfil_id))) plaza,
      (SELECT COUNT(*) FROM comunidad_publicaciones c JOIN perfiles a ON a.id=c.perfil_id WHERE c.tipo='oficial' AND a.alias='void' AND c.id>COALESCE(l.oficial,0)) oficial
      FROM (SELECT 1) LEFT JOIN comunidad_lecturas l ON l.perfil_id=?`).bind(p.id, ahora, p.id, p.id).first();
    return json({ ...r, puedeAvisar: p.alias === 'void' });
  }
  if (ruta === '/comunidad/publicaciones' && req.method === 'GET') {
    const cursor = u.searchParams.get('antes') || '9007199254740991', solo = u.searchParams.get('solo') || '';
    if (!/^[1-9][0-9]{0,15}$/.test(cursor) || (solo && solo !== 'oficial')) return fallo('La página no es válida.');
    const rows = (await db.prepare(`SELECT c.id,a.alias autor,c.tipo,c.texto,c.creado FROM comunidad_publicaciones c JOIN perfiles a ON a.id=c.perfil_id
      WHERE c.id<? AND (?='' OR (c.tipo='oficial' AND a.alias='void'))
      AND ((c.tipo='oficial' AND a.alias='void') OR NOT EXISTS(SELECT 1 FROM bloqueos b WHERE b.perfil_id=? AND b.bloquea_a=c.perfil_id))
      ORDER BY c.id DESC LIMIT 31`).bind(Number(cursor), solo, p.id).all<{id:number;autor:string;tipo:string;texto:string;creado:number}>()).results;
    const publicaciones = rows.slice(0, 30).map(c => ({ ...c, oficial: c.tipo === 'oficial' && c.autor === 'void', propia: c.autor === p.alias }));
    return json({ publicaciones, siguiente: rows.length > 30 ? publicaciones.at(-1)!.id : null });
  }
  if (ruta === '/comunidad/preparar' && req.method === 'POST') {
    let d; try { d = publicacion(b, p); } catch (e) { return fallo((e as Error).message, b.tipo === 'oficial' ? 403 : 400); }
    const token = [...crypto.getRandomValues(new Uint8Array(32))].map(x => x.toString(16).padStart(2, '0')).join('');
    await db.prepare('DELETE FROM comunidad_aprobaciones WHERE caduca<?').bind(ahora).run();
    await db.prepare('DELETE FROM comunidad_ritmo WHERE creado<?').bind(ahora-7200000).run();
    const pendientes = await db.prepare('SELECT COUNT(*) n FROM comunidad_aprobaciones WHERE perfil_id=?').bind(p.id).first<{n:number}>();
    if ((pendientes?.n || 0) >= 10) return fallo('Ya tienes varias vistas previas. Espera unos minutos.', 429);
    await db.prepare('INSERT INTO comunidad_aprobaciones(token,perfil_id,sha,caduca) VALUES(?,?,?,?)').bind(token, p.id, await huella(JSON.stringify(d)), ahora + 600000).run();
    return json({ token, ...d, destino: 'Todos los miembros de Void', autor: p.alias, oficial: d.tipo === 'oficial' });
  }
  if (ruta === '/comunidad/publicar' && req.method === 'POST') {
    if (!TOKEN.test(String(b.token || ''))) return fallo('Prepara y revisa la publicación antes de enviarla.');
    let d; try { d = publicacion(b, p); } catch (e) { return fallo((e as Error).message, b.tipo === 'oficial' ? 403 : 400); }
    const sha = await huella(JSON.stringify(d));
    const a = await db.prepare('SELECT sha,caduca FROM comunidad_aprobaciones WHERE token=? AND perfil_id=?').bind(b.token, p.id).first<{sha:string;caduca:number}>();
    if (!a || a.sha !== sha) return fallo('El texto cambió: prepara otra vista previa.', 409);
    const previa = await db.prepare('SELECT id FROM comunidad_publicaciones WHERE aprobacion=? AND perfil_id=?').bind(b.token, p.id).first();
    if (previa) return json({ publicado: true, ...previa });
    if (await db.prepare('SELECT 1 FROM comunidad_ritmo WHERE token=?').bind(b.token).first()) return fallo('Esa publicación ya fue retirada.', 410);
    if (a.caduca < ahora) return fallo('La vista previa caducó. Revisa otra vez la publicación.', 409);
    await db.batch([
      db.prepare(`INSERT OR IGNORE INTO comunidad_publicaciones(perfil_id,tipo,texto,creado,aprobacion)
        SELECT ?,?,?,?,? WHERE NOT EXISTS(SELECT 1 FROM comunidad_ritmo WHERE token=?) AND (SELECT COUNT(*) FROM comunidad_ritmo WHERE perfil_id=? AND creado>?)<10`).bind(p.id, d.tipo, d.texto, ahora, b.token, b.token, p.id, ahora - 3600000),
      db.prepare(`INSERT OR IGNORE INTO comunidad_ritmo(token,perfil_id,creado) SELECT ?,?,? WHERE EXISTS(SELECT 1 FROM comunidad_publicaciones WHERE aprobacion=?)`).bind(b.token, p.id, ahora, b.token)
    ]);
    const creada = await db.prepare('SELECT id FROM comunidad_publicaciones WHERE aprobacion=? AND perfil_id=?').bind(b.token, p.id).first();
    return creada ? json({ publicado: true, ...creada }, 201) : fallo('Has llegado al límite de diez publicaciones por hora. Vuelve más tarde.', 429);
  }
  if (ruta === '/comunidad/leido' && req.method === 'POST') {
    if (!['plaza', 'oficial'].includes(String(b.tipo)) || !Number.isSafeInteger(b.hasta) || Number(b.hasta) < 0) return fallo('Marca de lectura no válida.');
    const columna = b.tipo === 'oficial' ? 'oficial' : 'plaza';
    await db.prepare(`INSERT INTO comunidad_lecturas(perfil_id,${columna}) VALUES(?,?) ON CONFLICT(perfil_id) DO UPDATE SET ${columna}=MAX(${columna},excluded.${columna})`).bind(p.id, b.hasta).run();
    return json({ leido: true });
  }
  if (ruta === '/comunidad/borrar' && req.method === 'POST') {
    if (!Number.isSafeInteger(b.id) || Number(b.id) <= 0) return fallo('Publicación no válida.');
    const r = await db.prepare('DELETE FROM comunidad_publicaciones WHERE id=? AND (perfil_id=? OR ?=\'void\')').bind(b.id, p.id, p.alias).run();
    return r.meta.changes ? json({ borrado: true }) : fallo('La publicación no está o no puedes borrarla.', 404);
  }
  if (ruta === '/comunidad/bloqueos' && req.method === 'GET') return json({ bloqueados: (await db.prepare('SELECT a.alias FROM bloqueos b JOIN perfiles a ON a.id=b.bloquea_a WHERE b.perfil_id=? ORDER BY a.alias').bind(p.id).all()).results });
  if (['/comunidad/bloquear', '/comunidad/desbloquear'].includes(ruta) && req.method === 'POST') {
    const alias = typeof b.alias === 'string' ? b.alias.replace(/^@/, '').trim().toLowerCase() : '';
    if (!/^[a-z0-9](?:[a-z0-9]|-(?=[a-z0-9])){2,23}$/.test(alias) || alias === p.alias) return fallo('Elige otro vault por su alias.');
    const o = await db.prepare('SELECT id FROM perfiles WHERE alias=?').bind(alias).first<{id:number}>();
    if (!o) return fallo('Ese vault no existe.', 404);
    const si = ruta.endsWith('/bloquear');
    if (si) await db.batch([db.prepare('INSERT OR IGNORE INTO bloqueos(perfil_id,bloquea_a,creado) VALUES(?,?,?)').bind(p.id, o.id, ahora), db.prepare('DELETE FROM mensajes WHERE para_perfil=? AND de_perfil=?').bind(p.id, o.id)]);
    else await db.prepare('DELETE FROM bloqueos WHERE perfil_id=? AND bloquea_a=?').bind(p.id, o.id).run();
    return json({ alias, bloqueado: si });
  }
  return fallo('Esa acción no existe.', 404);
}
