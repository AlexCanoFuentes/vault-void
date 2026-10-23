import type { Entorno } from './worker.js';

/** Aviso interno sin contenido. Un fallo de la nube nunca cambia el envío ya guardado. */
export async function despertarCelestino(env: Entorno, alias: string, de: number, para: number): Promise<void> {
  if (!env.CELESTINO_ALIAS || alias !== env.CELESTINO_ALIAS || !env.CELESTINO_PASE || !env.NUBE) return;
  try {
    if (await env.DB.prepare('SELECT 1 FROM bloqueos WHERE perfil_id = ? AND bloquea_a = ?').bind(para, de).first()) return;
    const r = await env.NUBE.fetch(new Request('https://nube.interna/celestino/ronda', {
      method: 'POST', headers: { 'x-void-alias': alias, 'x-void-celestino': env.CELESTINO_PASE },
    }));
    await r.body?.cancel();
  } catch { /* El mensaje ya está guardado; se recogerá en otra ronda. */ }
}
