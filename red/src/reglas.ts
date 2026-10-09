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

// ---------------------------------------------------------------- VV-007: el planeta de cada vault

/** Las luces que puede tener un planeta: la paleta de Void (paleta.md, 9-oct). Una lista cerrada, sin colores libres. */
export const LUCES = ["ambar", "laton", "teja", "salvia", "arena", "verde"] as const;
export interface Planeta { version: 1; dias: number; pulso: number; luz: string; capas: { t: "contada" | "callada"; peso: 1 | 2 | 3 }[] }

const entero = (v: unknown, min: number, max: number) => Number.isInteger(v) && (v as number) >= min && (v as number) <= max;
const soloClaves = (o: Record<string, unknown>, permitidas: string[]) => Object.keys(o).every((k) => permitidas.includes(k));

/** null si el planeta vale; si no, por qué. Solo números y palabras de listas cerradas: ningún texto libre puede entrar. */
export function problemaPlaneta(p: unknown): string | null {
  if (!p || typeof p !== "object" || Array.isArray(p)) return "El planeta tiene que ser un objeto.";
  const o = p as Record<string, unknown>;
  if (!soloClaves(o, ["version", "dias", "pulso", "luz", "capas"])) return "El planeta solo puede llevar version, dias, pulso, luz y capas.";
  if (o.version !== 1) return "Versión de planeta desconocida.";
  if (!entero(o.dias, 0, 36500)) return "«dias» tiene que ser un entero entre 0 y 36500.";
  if (!entero(o.pulso, 0, 100000)) return "«pulso» tiene que ser un entero entre 0 y 100000.";
  if (!(LUCES as readonly string[]).includes(o.luz as string)) return `«luz» tiene que ser una de: ${LUCES.join(", ")}.`;
  if (!Array.isArray(o.capas) || o.capas.length > 12) return "«capas» tiene que ser una lista de 12 como mucho.";
  for (const c of o.capas) {
    if (!c || typeof c !== "object" || Array.isArray(c) || !soloClaves(c as Record<string, unknown>, ["t", "peso"])) return "Cada capa solo lleva t y peso.";
    const k = c as Record<string, unknown>;
    if (k.t !== "contada" && k.t !== "callada") return "Cada capa es «contada» o «callada».";
    if (k.peso !== 1 && k.peso !== 2 && k.peso !== 3) return "El peso de una capa es 1, 2 o 3.";
  }
  return null;
}

/** El planeta tal cual se guarda: mismas claves, mismo orden, nada más. */
export function planetaNormal(o: Planeta): Planeta {
  return { version: 1, dias: o.dias, pulso: o.pulso, luz: o.luz, capas: o.capas.map((c) => ({ t: c.t, peso: c.peso })) };
}
