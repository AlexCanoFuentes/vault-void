/**
 * Decisiones de seguridad, tomadas a propósito. Copiadas de `lexlabs-mcp` (subvenciones, en vivo desde el 3-oct-2026),
 * sin el contador ni su clave: la antena no cuenta a nadie.
 *
 * Postura:
 *   - SOLO LECTURA. Ninguna herramienta escribe en ningún sitio.
 *   - CERO CREDENCIALES hacia fuera. El catálogo es un fichero público de GitHub.
 *   - DOS HOSTS de salida, literales en el código: el catálogo en GitHub y los avisos públicos de
 *     red.vaultvoid.app. Lo único que sale de lo que escribe el usuario es el nombre de una estrella,
 *     validado con /^[a-z0-9]+(-[a-z0-9]+)*$/ antes de ponerlo en la ruta. No hay superficie de SSRF.
 *   - NO MANDA AVISOS: mandarlos pide la llave del vault, y una llave pegada en un chat queda escrita
 *     en la conversación. La antena los lee; se mandan desde el vault con void.py avisar.
 */
import { createHash } from "node:crypto";

/**
 * Lo que devuelve el catálogo entra en el contexto del modelo, y los textos de cada estrella los
 * escribe su autor: es texto de terceros y por tanto una
 * superficie de inyección de prompt aunque la fuente sea oficial. No se intenta «detectar
 * ataques»: se neutraliza la forma que los hace funcionar, que es parecer una instrucción.
 * Mismas reglas que el remoto normativo, más las comillas invertidas sueltas y un tope por campo.
 */
export function sanear(texto: unknown, tope = 2_000): string | null {
  if (texto === null || texto === undefined) return null;
  return String(texto)
    .replace(/```/g, "'''")
    .replace(/<\/?(system|assistant|user|tool|instructions?)[^>]*>/gi, "[etiqueta eliminada]")
    .replace(/^\s*(ignora|olvida|ignore|disregard|forget)\b.*/gim, "[línea eliminada]")
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "")
    .trim()
    .slice(0, tope);
}

/**
 * LÍMITE DE RITMO POR TRAMOS, igual que el remoto normativo: uno corto que corta un bucle en
 * segundos y uno largo que pone techo a la hora. Se comprueban todos antes de anotar.
 *
 * ⚠️ LÍMITE DICHO: vive en la memoria del isolate. En Workers cada isolate cuenta lo suyo
 * (medido el 25-sep en el remoto normativo: salta en la 11.ª y en el mismo minuto pasaron 6 más
 * por otros isolates). Frena un bucle; no para un ataque.
 * ⚠️ Y otro: los conectores de claude.ai llaman desde servidores de Anthropic, así que sin clave
 * en la URL todos los usuarios de Claude comparten huella. Por eso el tope es más alto que en el
 * normativo y la huella prefiere la clave cuando la hay.
 */
export interface Tramo { ventanaMs: number; tope: number }

export function crearLimite(tramos: Tramo[]) {
  const mayor = Math.max(...tramos.map((t) => t.ventanaMs));
  const marcas = new Map<string, number[]>();
  return function comprobar(huellaQuien: string):
    { ok: true } | { ok: false; hechas: number; tope: number; ventana_s: number; espera_s: number } {
    const ahora = Date.now();
    const previas = (marcas.get(huellaQuien) ?? []).filter((t) => ahora - t < mayor);
    if (marcas.size > 5_000) {
      for (const k of [...marcas.keys()].slice(0, 1_000)) marcas.delete(k);
    }
    for (const t of tramos) {
      const dentro = previas.filter((m) => ahora - m < t.ventanaMs);
      if (dentro.length >= t.tope) {
        marcas.set(huellaQuien, previas);
        return { ok: false, hechas: dentro.length, tope: t.tope, ventana_s: t.ventanaMs / 1000,
                 espera_s: Math.max(1, Math.ceil((t.ventanaMs - (ahora - dentro[0])) / 1000)) };
      }
    }
    previas.push(ahora);
    marcas.set(huellaQuien, previas);
    return { ok: true };
  };
}

/** SHA-256 recortado a 16 hex: el mismo corte que el remoto normativo. */
export function huella(texto: string): string {
  return createHash("sha256").update(texto).digest("hex").slice(0, 16);
}

/**
 * Sal de la huella de IP, nueva en cada isolate. La IP nunca se guarda: se guarda un hash que
 * sirve para contar dentro del isolate y no sirve para identificar a nadie ni cruzarlo con nada.
 */
const SAL = createHash("sha256").update(String(Math.random()) + String(Date.now())).digest("hex");

export function huellaDeIp(ip: string): string {
  return createHash("sha256").update(SAL + ip).digest("hex").slice(0, 20);
}
