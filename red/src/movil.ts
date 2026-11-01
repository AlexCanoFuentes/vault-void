// Avisos en el móvil (23-oct-2026).
// Protocolo estándar de avisos web (RFC 8030) firmado con VAPID (RFC 8292). El aviso va VACÍO: los mensajes van cifrados
// y la red no sabe qué dicen, así que solo despierta al móvil para que enseñe «Mensaje nuevo en Void».
// Sin cuerpo no hay nada que cifrar y por eso solo se guarda la dirección de la suscripción, nunca sus claves.

export interface MovilEnv {
  DB: D1Database;
  /** Clave privada VAPID en JWK (secreto). Sin ella no se avisa a nadie y todo lo demás sigue igual. */
  VAPID_PRIVADA?: string;
  /** Clave pública VAPID, base64url sin relleno (65 bytes sin comprimir). La necesita el navegador para apuntarse. */
  VAPID_PUBLICA?: string;
  /** Solo las pruebas: acepta direcciones http://127.0.0.1 para un servicio de avisos de mentira. */
  MOVIL_PRUEBA?: string;
}

export const MAX_POR_ESPACIO = 5;

// Solo servicios de avisos conocidos: si no, cualquiera podría registrar una dirección para que la red le haga peticiones.
const HOSTS = [/^fcm\.googleapis\.com$/, /^updates\.push\.services\.mozilla\.com$/, /^web\.push\.apple\.com$/, /^[a-z0-9-]+\.notify\.windows\.com$/];

export function endpointValido(env: MovilEnv, endpoint: unknown): endpoint is string {
  if (typeof endpoint !== 'string' || endpoint.length > 1024) return false;
  let u: URL;
  try { u = new URL(endpoint); } catch { return false; }
  if (env.MOVIL_PRUEBA === '1' && u.protocol === 'http:' && u.hostname === '127.0.0.1') return true;
  return u.protocol === 'https:' && !u.username && !u.password && HOSTS.some(h => h.test(u.hostname));
}

const b64url = (b: ArrayBuffer | Uint8Array) => btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const texto = (o: unknown) => b64url(new TextEncoder().encode(JSON.stringify(o)));

let clave: CryptoKey | null = null;
async function firmar(env: MovilEnv, aud: string): Promise<string> {
  clave ??= await crypto.subtle.importKey('jwk', JSON.parse(env.VAPID_PRIVADA!), { name: 'ECDSA', namedCurve: 'P-256' }, false, ['sign']);
  const cuerpo = texto({ typ: 'JWT', alg: 'ES256' }) + '.' + texto({ aud, exp: Math.floor(Date.now() / 1000) + 12 * 3600, sub: 'https://vaultvoid.app' });
  // WebCrypto devuelve ECDSA como r‖s de 64 bytes, que es justo el formato que pide un JWT ES256.
  const firma = await crypto.subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, clave, new TextEncoder().encode(cuerpo));
  return cuerpo + '.' + b64url(firma);
}

/** Avisa a los móviles de quien recibe. Nunca lanza: un aviso que falla no puede tumbar un mensaje ya guardado. */
export async function avisarMovil(env: MovilEnv, paraId: number, deId: number): Promise<void> {
  try {
    if (!env.VAPID_PRIVADA || !env.VAPID_PUBLICA) return;
    // Un remitente bloqueado no puede hacer sonar el móvil de quien le bloqueó.
    if (await env.DB.prepare('SELECT 1 FROM bloqueos WHERE perfil_id = ? AND bloquea_a = ?').bind(paraId, deId).first()) return;
    const { results } = await env.DB.prepare('SELECT endpoint FROM avisos_movil WHERE perfil_id = ? LIMIT ?').bind(paraId, MAX_POR_ESPACIO).all<{ endpoint: string }>();
    await Promise.all(results.map(async ({ endpoint }) => {
      if (!endpointValido(env, endpoint)) return;
      try {
        const r = await fetch(endpoint, { method: 'POST', redirect: 'manual', headers: {
          authorization: `vapid t=${await firmar(env, new URL(endpoint).origin)}, k=${env.VAPID_PUBLICA}`,
          ttl: '86400', urgency: 'high', 'content-length': '0' } });
        if (r.status === 404 || r.status === 410) await env.DB.prepare('DELETE FROM avisos_movil WHERE endpoint = ?').bind(endpoint).run();
      } catch { /* el servicio de avisos no contesta: se intentará con el siguiente mensaje */ }
    }));
  } catch { /* nunca tumba el envío */ }
}

/** Alta y baja desde Mi espacio, con la sesión web ya comprobada por quien llama. */
export async function apuntar(env: MovilEnv, perfilId: number, accion: unknown, endpoint: unknown): Promise<{ status: number; datos: Record<string, unknown> }> {
  if (!env.VAPID_PUBLICA) return { status: 503, datos: { error: 'Los avisos en el móvil todavía no están disponibles.' } };
  if (!endpointValido(env, endpoint)) return { status: 400, datos: { error: 'Este navegador no ha dado una dirección de avisos válida.' } };
  if (accion === 'baja') {
    await env.DB.prepare('DELETE FROM avisos_movil WHERE perfil_id = ? AND endpoint = ?').bind(perfilId, endpoint).run();
    return { status: 200, datos: { apuntado: false } };
  }
  if (accion !== 'alta') return { status: 400, datos: { error: 'La acción es «alta» o «baja».' } };
  const n = (await env.DB.prepare('SELECT COUNT(*) AS n FROM avisos_movil WHERE perfil_id = ? AND endpoint != ?').bind(perfilId, endpoint).first<{ n: number }>())!.n;
  if (n >= MAX_POR_ESPACIO) return { status: 409, datos: { error: `Ya avisas a ${MAX_POR_ESPACIO} aparatos. Quita alguno antes de añadir este.` } };
  await env.DB.prepare('INSERT OR REPLACE INTO avisos_movil (perfil_id, endpoint, creado) VALUES (?, ?, ?)').bind(perfilId, endpoint, Date.now()).run();
  return { status: 200, datos: { apuntado: true } };
}

export async function estadoMovil(env: MovilEnv, perfilId: number, endpoint: string | null) {
  const apuntado = endpoint ? !!(await env.DB.prepare('SELECT 1 FROM avisos_movil WHERE perfil_id = ? AND endpoint = ?').bind(perfilId, endpoint).first()) : false;
  return { clave: env.VAPID_PUBLICA ?? null, apuntado };
}
