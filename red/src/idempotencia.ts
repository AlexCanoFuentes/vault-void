import { huella } from './reglas.js';
type Sobre = { tipo: string; enc: string; sobre: string; nonce: unknown };
const json = (d: unknown, status = 200) => Response.json(d, { status, headers: { 'cache-control': 'no-store' } });
export async function mandarReintento(db: D1Database, de: number, paraId: number, para: string, b: Sobre, max: number, nuevos: number) {
  if (typeof b.nonce !== 'string' || !/^[0-9a-f]{64}$/.test(b.nonce)) return json({ error: 'El identificador del envío no es válido.' }, 400);
  const ahora = Date.now(), hora = ahora - 3600000, dia = ahora - 86400000, caduca = ahora + 180 * 86400000;
  const sha = await huella(JSON.stringify({ para, tipo: b.tipo, enc: b.enc, sobre: b.sobre }));
  await db.prepare('DELETE FROM mensajes_recibos WHERE caduca<?').bind(ahora).run();
  await db.batch([
    db.prepare(`INSERT OR IGNORE INTO mensajes_recibos(de_perfil,nonce,sha,para_perfil,creado,caduca)
      SELECT ?,?,?,?,?,? WHERE
      (SELECT COUNT(*) FROM mensajes_recibos WHERE de_perfil=? AND creado>?)+(SELECT COUNT(*) FROM ritmo WHERE clave=? AND creado>?)<?
      AND (EXISTS(SELECT 1 FROM contactos WHERE (de_perfil=? AND para_perfil=?) OR (de_perfil=? AND para_perfil=?))
      OR (SELECT COUNT(*) FROM contactos WHERE de_perfil=? AND primero>?)<?)`)
      .bind(de, b.nonce, sha, paraId, ahora, caduca, de, hora, 'msg:' + de, hora, max, de, paraId, paraId, de, de, dia, nuevos),
    db.prepare(`INSERT OR IGNORE INTO mensajes(de_perfil,para_perfil,tipo,enc,sobre,creado,caduca)
      SELECT ?,?,?,?,?,?,? FROM mensajes_recibos r WHERE r.de_perfil=? AND r.nonce=? AND r.sha=? AND r.procesado=0
      AND NOT EXISTS(SELECT 1 FROM bloqueos WHERE perfil_id=? AND bloquea_a=?)`)
      .bind(de, paraId, b.tipo, b.enc, b.sobre, ahora, caduca, de, b.nonce, sha, paraId, de),
    db.prepare(`INSERT OR IGNORE INTO contactos(de_perfil,para_perfil,primero) SELECT ?,?,? WHERE EXISTS(SELECT 1 FROM mensajes_recibos WHERE de_perfil=? AND nonce=? AND sha=?)`).bind(de, paraId, ahora, de, b.nonce, sha),
    db.prepare('UPDATE mensajes_recibos SET procesado=1 WHERE de_perfil=? AND nonce=? AND sha=?').bind(de, b.nonce, sha)
  ]);
  const r = await db.prepare('SELECT sha FROM mensajes_recibos WHERE de_perfil=? AND nonce=?').bind(de, b.nonce).first<{sha:string}>();
  if (!r) return json({ error: 'Has llegado al límite de mensajes o de destinatarios nuevos. Prueba más tarde.' }, 429);
  if (r.sha !== sha) return json({ error: 'Ese envío ya tiene otro contenido. No se vuelve a utilizar su identificador.' }, 409);
  return json({ para, tipo: b.tipo, enviado: true }, 201);
}
