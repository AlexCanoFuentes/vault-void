/**
 * Las reglas de la red, sin nada de HTTP: la llave y su huella, qué alias valen, qué se puede marcar como
 * público y qué no puede llevar un aviso. Todo lo que decide quién es quién está aquí.
 */

/** La llave del vault: «vv_» y 32 bytes al azar. Solo existe en la respuesta del alta y en `.void/llave`. */
export function llaveNueva(): string {
  const b = new Uint8Array(32);
  crypto.getRandomValues(b);
  return "vv_" + btoa(String.fromCharCode(...b)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export const RE_LLAVE = /^vv_[A-Za-z0-9_-]{43}$/;

/** sha256 en hex. Es lo único que la base de datos sabe de una llave. */
export async function huella(texto: string): Promise<string> {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(texto));
  return [...new Uint8Array(d)].map((x) => x.toString(16).padStart(2, "0")).join("");
}

/** La llave que trae una petición en «Authorization: Bearer …». null si no trae ninguna o no tiene forma de llave. */
export function llaveDe(request: Request): string | null {
  const m = /^Bearer\s+(\S+)$/.exec(request.headers.get("authorization") ?? "");
  return m && RE_LLAVE.test(m[1]) ? m[1] : null;
}

/** Minúsculas, cifras y guiones; de 3 a 24; sin guion al principio ni al final ni dos seguidos. */
export const RE_ALIAS = /^[a-z0-9](?:[a-z0-9]|-(?=[a-z0-9])){2,23}$/;
const RESERVADOS = new Set(["void", "vaultvoid", "admin", "api", "red", "antena", "entrar", "estrella", "estrellas",
  "ayuda", "soporte", "www", "root", "sistema", "nebulosa", "taller", "puerta", "oficial", "oficiales"]);

export function problemaAlias(alias: unknown): string | null {
  if (typeof alias !== "string" || !RE_ALIAS.test(alias)) {
    return "El alias va en minúsculas, de 3 a 24 letras o cifras (sin tildes ni eñes), y puede llevar guiones en medio: p. ej. «nube» o «cosmo-7».";
  }
  if (RESERVADOS.has(alias)) return `«${alias}» está reservado para Void: elige otro.`;
  return null;
}

/** El nombre del agente: lo que la persona llame a su IA. Letras, cifras, espacios y . _ -, hasta 40. */
export function problemaAgente(agente: unknown): string | null {
  if (typeof agente !== "string" || !/^[\p{L}\p{N}][\p{L}\p{N} ._-]{0,39}$/u.test(agente.trim())) {
    return "El nombre del agente va con letras, cifras y espacios, hasta 40: p. ej. «Brock» o «Claude».";
  }
  return null;
}

/** Lo que se puede enseñar en el perfil, además del alias, que siempre se ve. */
export const PUBLICABLES = ["agente", "estrellas"] as const;

export function publicoDe(lista: unknown): string[] | null {
  if (!Array.isArray(lista) || lista.length > PUBLICABLES.length) return null;
  const set = new Set<string>();
  for (const x of lista) {
    if (typeof x !== "string" || !(PUBLICABLES as readonly string[]).includes(x)) return null;
    set.add(x);
  }
  return PUBLICABLES.filter((x) => set.has(x));
}

export const TIPOS = ["fallo", "mejora", "gracias"] as const;
export const RE_ESTRELLA = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/**
 * Un aviso sale en la página pública de la estrella: no puede llevar cómo localizar a nadie ni una clave.
 * No es un escáner completo (eso es fugas.py): es la tapa de lo más corriente, y se le dice a quien escribe.
 */
const NO_PUBLICABLE: Array<[string, RegExp]> = [
  ["un correo", /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/],
  ["un teléfono", /(?<![\w])(?:\+\d{1,3}[ .-]?)?\d{3}[ .-]?\d{3}[ .-]?\d{3,4}(?!\w)/],
  ["algo que parece una llave o una clave", /\b(?:vv_[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})/],
];

export function problemaTexto(texto: unknown): string | null {
  if (typeof texto !== "string") return "Falta el texto del aviso.";
  const t = texto.trim();
  if (t.length < 3 || t.length > 500) return "El aviso tiene que tener entre 3 y 500 caracteres.";
  if (/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/.test(t)) return "El aviso lleva caracteres de control: escríbelo como texto normal.";
  for (const [que, re] of NO_PUBLICABLE) {
    if (re.test(t)) return `El aviso lleva ${que}, y sale en una página pública: quítalo y vuelve a mandarlo.`;
  }
  return null;
}

// ---------------------------------------------------------------- VV-007: la huella de cada vault

/** La huella de cada vault: solo cifras. Con ellas Void dibuja una forma única (reacción-difusión sembrada por el alias).
 *  «tono» es el color, 0-359; si no viene, sale del alias. Ningún texto libre puede entrar. */
export interface Huella { version: 1; dias: number; pulso: number; decisiones: number; proyectos: number; calladas: number; tono?: number }
const CLAVES_HUELLA = ["version", "dias", "pulso", "decisiones", "proyectos", "calladas", "tono"];
const entero = (v: unknown, min: number, max: number) => Number.isInteger(v) && (v as number) >= min && (v as number) <= max;

/** null si la huella vale; si no, por qué. */
export function problemaHuella(h: unknown): string | null {
  if (!h || typeof h !== "object" || Array.isArray(h)) return "La huella tiene que ser un objeto.";
  const o = h as Record<string, unknown>;
  if (!Object.keys(o).every((k) => CLAVES_HUELLA.includes(k))) return `La huella solo puede llevar ${CLAVES_HUELLA.join(", ")}.`;
  if (o.version !== 1) return "Versión de huella desconocida.";
  for (const [k, max] of [["dias", 36500], ["pulso", 100000], ["decisiones", 100000], ["proyectos", 10000]] as const) {
    if (!entero(o[k], 0, max)) return `«${k}» tiene que ser un entero entre 0 y ${max}.`;
  }
  if (!entero(o.calladas, 0, 7)) return "«calladas» tiene que ser un entero entre 0 y 7.";
  if (o.tono !== undefined && !entero(o.tono, 0, 359)) return "«tono» tiene que ser un entero entre 0 y 359.";
  return null;
}

/** La huella tal cual se guarda: mismas claves, mismo orden, nada más. */
export function huellaNormal(o: Huella): Huella {
  const n: Huella = { version: 1, dias: o.dias, pulso: o.pulso, decisiones: o.decisiones, proyectos: o.proyectos, calladas: o.calladas };
  if (o.tono !== undefined) n.tono = o.tono;
  return n;
}
