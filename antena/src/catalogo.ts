/**
 * El catálogo de Void: el `catalogo.json` público del repo, el mismo que leen `void.py` y la web.
 *
 * Regla de siempre: SI GITHUB NO CONTESTA, SE DEVUELVE EL FALLO. No hay copia de reserva ni datos de
 * memoria. Caché de 10 minutos solo de respuestas buenas; un fallo no se guarda nunca.
 */
export const CATALOGO_URL = "https://raw.githubusercontent.com/AlexCanoFuentes/vault-void/main/catalogo.json";
export const REPO = "https://github.com/AlexCanoFuentes/vault-void";

/** Lo que escribe quien pregunta está mal (una estrella que no existe, un texto vacío). */
export class ErrorDeEntrada extends Error {}
/** El catálogo no ha llegado, o ha llegado roto. */
export class ErrorDeFuente extends Error {}

const TTL_MS = 10 * 60 * 1000;
const LIMITE = 2 * 1024 * 1024;
let cache: { datos: Catalogo; consultado: string; expira: number; url: string } | null = null;

export interface Estrella {
  titulo: string; version?: string; nivel: string; autor?: string; regla: string;
  resuelve: { frase: string; medido?: string };
  nacio_de: Array<{ fallo: string; que_paso: string; coste: string }>;
  criterio: string; cuando?: string[]; palabras_clave?: string[]; no_protege?: string[];
  requisitos?: string; instalar?: string[]; probado_en?: string[];
  riesgo?: { ejecuta?: string; red?: string; deshacer?: string };
  prueba?: { comprobaciones?: number; rojos?: number; sabotaje?: string };
  uso?: { vaults?: number; semanas?: number };
  liga?: string; kernel?: { total?: number; mas_debil?: string }; buscar?: string; ruta?: string;
}
export interface Catalogo { estrellas: Record<string, Estrella> }

export interface Procedencia { catalogo: string; consultado: string; de_cache: boolean }

export async function leerCatalogo(url = CATALOGO_URL): Promise<{ datos: Catalogo; procedencia: Procedencia }> {
  if (cache && cache.url === url && cache.expira > Date.now()) {
    return { datos: cache.datos, procedencia: { catalogo: url, consultado: cache.consultado, de_cache: true } };
  }
  let r: Response;
  try {
    r = await fetch(url, { headers: { accept: "application/json" }, signal: AbortSignal.timeout(10_000) });
  } catch (e) {
    throw new ErrorDeFuente(`GitHub no contesta (${e instanceof Error ? e.message : String(e)}).`);
  }
  if (!r.ok) throw new ErrorDeFuente(`GitHub contesta ${r.status} al pedir el catálogo.`);
  const txt = await r.text();
  if (txt.length > LIMITE) throw new ErrorDeFuente("El catálogo pesa más de 2 MB: no se lee.");
  let datos: Catalogo;
  try { datos = JSON.parse(txt); } catch { throw new ErrorDeFuente("El catálogo no es un JSON válido."); }
  if (!datos || typeof datos.estrellas !== "object" || datos.estrellas === null) {
    throw new ErrorDeFuente("El catálogo no trae estrellas.");
  }
  const consultado = new Date().toISOString();
  cache = { datos, consultado, expira: Date.now() + TTL_MS, url };
  return { datos, procedencia: { catalogo: url, consultado, de_cache: false } };
}
