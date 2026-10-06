/**
 * El catálogo de Void: el `catalogo.json` público del repo, el mismo que leen `void.py`, la web y la antena.
 * Aquí sirve para dos cosas: no aceptar avisos a estrellas que no existen y poner título y liga en las páginas.
 *
 * SI GITHUB NO CONTESTA, SE DEVUELVE EL FALLO (igual que en la antena): caché de 10 minutos solo de respuestas buenas.
 */
export const CATALOGO_URL = "https://raw.githubusercontent.com/AlexCanoFuentes/vault-void/main/catalogo.json";

export class ErrorDeFuente extends Error {}

export interface Estrella {
  titulo: string; nivel: string; liga?: string; regla?: string;
  resuelve?: { frase?: string }; kernel?: { total?: number };
}
export interface Catalogo { estrellas: Record<string, Estrella> }

const TTL_MS = 10 * 60 * 1000;
const LIMITE = 2 * 1024 * 1024;
let cache: { datos: Catalogo; expira: number; url: string } | null = null;

export async function leerCatalogo(url = CATALOGO_URL): Promise<Catalogo> {
  if (cache && cache.url === url && cache.expira > Date.now()) return cache.datos;
  let r: Response;
  try {
    r = await fetch(url, { headers: { accept: "application/json" }, signal: AbortSignal.timeout(10_000) });
  } catch (e) {
    throw new ErrorDeFuente(`GitHub no contesta (${e instanceof Error ? e.message : String(e)}).`);
  }
  if (!r.ok) throw new ErrorDeFuente(`GitHub contesta ${r.status} al pedir el catálogo.`);
  const txt = await r.text();
  if (txt.length > LIMITE) throw new ErrorDeFuente("El catálogo pesa más de 2 MB.");
  let datos: Catalogo;
  try { datos = JSON.parse(txt); } catch { throw new ErrorDeFuente("El catálogo no es un JSON válido."); }
  if (!datos || typeof datos.estrellas !== "object" || datos.estrellas === null) {
    throw new ErrorDeFuente("El catálogo no trae estrellas.");
  }
  cache = { datos, expira: Date.now() + TTL_MS, url };
  return datos;
}
