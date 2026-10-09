// Las pruebas de la red: el Worker de verdad en local (wrangler dev con su D1 local), un catálogo de prueba servido
// aquí al lado, y los sabotajes vistos en rojo. Una orden, un veredicto:
//   npm test              las pruebas
//   npm run sabotaje      rompe el Worker a propósito, un candado cada vez, y comprueba que las pruebas lo cazan
import { spawn, execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import http from "node:http";
import { cpSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const RAIZ = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const WRANGLER = join(RAIZ, "node_modules", ".bin", "wrangler");
const PUERTO_CATALOGO = 8789;
const sha256 = (t) => createHash("sha256").update(t).digest("hex");

// ---------------------------------------------------------------- el montaje

const CATALOGO = { estrellas: {
  candados: { titulo: "Candados para dos agentes", nivel: "oficiales", liga: "grande", resuelve: { frase: "Que dos IA no se pisen." } },
  prueba: { titulo: "Una estrella de prueba", nivel: "comunidad", liga: "pequeña", resuelve: { frase: "Nada." } },
} };

function servirCatalogo() {
  const s = http.createServer((req, res) => {
    res.writeHead(req.url === "/catalogo.json" ? 200 : 404, { "content-type": "application/json" });
    res.end(req.url === "/catalogo.json" ? JSON.stringify(CATALOGO) : "{}");
  });
  return new Promise((ok) => s.listen(PUERTO_CATALOGO, "127.0.0.1", () => ok(s)));
}

/** Un Worker de la red en local, con su propia D1 vacía y la migración puesta. */
async function levantar(dir, puerto, vars = []) {
  // Si el puerto ya contesta antes de arrancar, es un servidor viejo colgado: las pruebas hablarían con él, con otra base
  // de datos y otro límite, y fallarían por la razón equivocada (pasó el 8-oct: un wrangler de hacía 4 h en el 8791).
  try { await fetch(`http://127.0.0.1:${puerto}/`); throw new Error(`el puerto ${puerto} ya está ocupado por otro servidor: páralo antes de probar`); }
  catch (e) { if (String(e.message).startsWith("el puerto")) throw e; }
  const persist = mkdtempSync(join(tmpdir(), "void-red-d1-"));
  execFileSync(WRANGLER, ["d1", "migrations", "apply", "DB", "--local", "--persist-to", persist], { cwd: dir, stdio: "pipe" });
  const todas = [`CATALOGO_URL:http://127.0.0.1:${PUERTO_CATALOGO}/catalogo.json`, ...vars];
  const p = spawn(WRANGLER, ["dev", "--port", String(puerto), "--ip", "127.0.0.1", "--persist-to", persist,
    ...todas.flatMap((v) => ["--var", v])], { cwd: dir, stdio: ["ignore", "pipe", "pipe"], detached: true });
  // Se pregunta al puerto hasta que contesta, en vez de leer lo que escribe wrangler: desde la 4.14x, cuando lo lanza
  // un agente y sin pantalla, ya no escribe «Ready on» (8-oct) y la espera se quedaba colgada aunque arrancara.
  const limite = Date.now() + 90_000;
  for (;;) {
    try { await fetch(`http://127.0.0.1:${puerto}/`); break; } catch { /* aún no escucha */ }
    if (Date.now() > limite) throw new Error("wrangler dev no arrancó en 90 s");
    await new Promise((r) => setTimeout(r, 500));
  }
  return {
    url: `http://127.0.0.1:${puerto}`,
    /** SQL directo contra la D1 local de este Worker: lo que haría Alex con wrangler. */
    sql(orden) {
      const salida = execFileSync(WRANGLER, ["d1", "execute", "DB", "--local", "--persist-to", persist, "--json", "--command", orden],
        { cwd: dir, stdio: ["ignore", "pipe", "pipe"] }).toString();
      return JSON.parse(salida)[0].results;
    },
    // Su propio grupo de procesos: se mata entero (wrangler y workerd), o workerd se queda con el puerto.
    parar() { try { process.kill(-p.pid, "SIGKILL"); } catch { /* ya no estaba */ } rmSync(persist, { recursive: true, force: true }); },
  };
}

// ---------------------------------------------------------------- ayudas

let n = 0;
const alias = (pre = "p") => `${pre}${Date.now().toString(36)}${(n++).toString(36)}`.slice(0, 24);

async function pedir(w, metodo, ruta, { llave, cuerpo } = {}) {
  const h = { "content-type": "application/json" };
  if (llave) h.authorization = `Bearer ${llave}`;
  const r = await fetch(w.url + ruta, { method: metodo, headers: h, body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo) });
  const texto = await r.text();
  let datos = null;
  try { datos = JSON.parse(texto); } catch { /* html */ }
  return { estado: r.status, datos, texto, cabeceras: r.headers };
}

const alta = (w, a, agente = "Brock") => pedir(w, "POST", "/v1/registrar", { cuerpo: { alias: a, agente } });
const LLAVE_FALSA = "vv_" + "A".repeat(43);

class Falla extends Error {}
function exige(cond, motivo) { if (!cond) throw new Falla(motivo); }

// ---------------------------------------------------------------- las pruebas (cada una, un nombre)

const HUELLA = { version: 1, dias: 12, pulso: 40, decisiones: 9, proyectos: 2, calladas: 1, tono: 200 };

const PRUEBAS = {
  async "huella: solo cifras, nunca texto"(w) {
    const r = await alta(w, alias()); const llave = r.datos.llave;
    const ok = await pedir(w, "POST", "/v1/huella", { llave, cuerpo: { huella: HUELLA } });
    exige(ok.estado === 200, `una huella válida dio ${ok.estado}: ${ok.texto.slice(0, 160)}`);
    for (const [motivo, malo] of [["una clave de más con texto", { ...HUELLA, nota: "me llamo Lucía" }],
      ["un tono fuera de la rueda", { ...HUELLA, tono: 400 }], ["un número con decimales", { ...HUELLA, dias: 1.5 }],
      ["más de siete calladas", { ...HUELLA, calladas: 8 }], ["texto donde va un número", { ...HUELLA, decisiones: "muchas" }]]) {
      const x = await pedir(w, "POST", "/v1/huella", { llave, cuerpo: { huella: malo } });
      exige(x.estado === 400, `${motivo} dio ${x.estado}, no 400`);
    }
    const sin = await pedir(w, "POST", "/v1/huella", { cuerpo: { huella: HUELLA } });
    exige(sin.estado === 401, `sin llave dio ${sin.estado}, no 401`);
    const lienzo = await pedir(w, "GET", "/v1/huellas");
    exige(lienzo.cabeceras.get("access-control-allow-origin") === "*", "el lienzo no se puede leer desde vaultvoid.app");
    const mia = (lienzo.datos?.huellas ?? []).find((x) => x.alias === r.datos.alias);
    exige(mia && JSON.stringify(Object.keys(mia.huella)) === JSON.stringify(["version", "dias", "pulso", "decisiones", "proyectos", "calladas", "tono"]), "el lienzo no trae la huella, o trae algo más");
    exige(!JSON.stringify(w.sql("SELECT * FROM huellas")).includes("Lucía"), "la base guardó texto de una huella rechazada");
  },

  async "huella: retirarla o darse de baja la quita del lienzo"(w) {
    const a = await alta(w, alias()), b = await alta(w, alias());
    for (const x of [a, b]) await pedir(w, "POST", "/v1/huella", { llave: x.datos.llave, cuerpo: { huella: HUELLA } });
    await pedir(w, "POST", "/v1/huella/retirar", { llave: a.datos.llave });
    await pedir(w, "POST", "/v1/baja", { llave: b.datos.llave });
    const quedan = (await pedir(w, "GET", "/v1/huellas")).datos.huellas.map((x) => x.alias);
    exige(!quedan.includes(a.datos.alias), "retirada, sigue en el lienzo");
    exige(!quedan.includes(b.datos.alias), "dado de baja, su huella sigue en el lienzo");
    exige(w.sql("SELECT COUNT(*) AS n FROM huellas h LEFT JOIN perfiles p ON p.id = h.perfil_id WHERE p.id IS NULL")[0].n === 0,
      "dado de baja, su huella no sale en el lienzo pero sigue guardada en la base");
  },

  async "alta: da una llave y la base solo guarda su huella"(w) {
    const a = alias();
    const r = await alta(w, a);
    exige(r.estado === 201, `el alta dio ${r.estado}: ${r.texto.slice(0, 160)}`);
    exige(/^vv_[A-Za-z0-9_-]{43}$/.test(r.datos?.llave ?? ""), "la llave no tiene la forma vv_ + 43");
    const filas = w.sql(`SELECT * FROM perfiles WHERE alias = '${a}'`);
    exige(filas.length === 1 && filas[0].huella_llave === sha256(r.datos.llave), "en D1 no está la huella sha256 de la llave");
    const todo = JSON.stringify([w.sql("SELECT * FROM perfiles"), w.sql("SELECT * FROM avisos"), w.sql("SELECT * FROM ajustes")]);
    exige(!todo.includes(r.datos.llave), "la llave está guardada tal cual en D1");
  },

  async "llave falsa: 401 en todo lo que pide llave"(w) {
    const a = alias();
    await alta(w, a);   // que haya al menos un perfil al que una llave falsa pudiera colarse
    for (const [m, ruta, cuerpo] of [["GET", "/v1/yo"], ["POST", "/v1/perfil", { publico: ["agente"] }],
      ["POST", "/v1/avisos", { estrella: "candados", tipo: "gracias", texto: "hola" }], ["POST", "/v1/llave/cambiar"],
      ["POST", "/v1/registrar", { alias: a, agente: "Brock" }], ["POST", "/v1/baja"]]) {
      const r = await pedir(w, m, ruta, { llave: LLAVE_FALSA, cuerpo });
      exige(r.estado === 401, `${m} ${ruta} con una llave falsa dio ${r.estado}, no 401`);
      const s = await pedir(w, m, ruta, { cuerpo });
      exige(ruta === "/v1/registrar" ? s.estado === 409 : s.estado === 401, `${m} ${ruta} sin llave dio ${s.estado}`);
    }
    exige(w.sql(`SELECT COUNT(*) AS n FROM perfiles WHERE alias = '${a}'`)[0].n === 1, "la baja con llave falsa borró algo");
  },

  async "registrar dos veces: un solo perfil"(w) {
    const a = alias();
    const r1 = await alta(w, a, "Brock");
    const r2 = await pedir(w, "POST", "/v1/registrar", { llave: r1.datos.llave, cuerpo: { alias: a, agente: "Brock 2" } });
    exige(r2.estado === 200 && r2.datos?.nuevo === false, `con la misma llave dio ${r2.estado} (${r2.texto.slice(0, 120)}), no 200 «el mismo»`);
    exige(!("llave" in (r2.datos ?? {})), "con la llave de vuelta, dio otra llave");
    const r3 = await pedir(w, "POST", "/v1/registrar", { llave: r1.datos.llave, cuerpo: { alias: alias(), agente: "Brock" } });
    exige(r3.estado === 409, `la misma llave con otro alias dio ${r3.estado}, no 409`);
    const r4 = await alta(w, a, "Otro");   // sin llave (la borró) y el mismo alias
    exige(r4.estado === 409, `sin llave y con el mismo alias dio ${r4.estado}, no 409`);
    const total = w.sql(`SELECT COUNT(*) AS n FROM perfiles WHERE huella_llave = '${sha256(r1.datos.llave)}' OR alias = '${a}'`)[0].n;
    exige(total === 1, `hay ${total} perfiles para un solo vault`);
  },

  async "alias: solo minúsculas, de 3 a 24, únicos y sin los reservados"(w) {
    for (const malo of ["Nube", "ab", "a".repeat(25), "-abc", "abc-", "a--b", "lúa", "void", "a b"]) {
      const r = await alta(w, malo);
      exige(r.estado === 400, `el alias «${malo}» dio ${r.estado}, no 400`);
    }
    const r = await alta(w, "abc" + (n++), "<script>");
    exige(r.estado === 400, `un agente «<script>» dio ${r.estado}, no 400`);
  },

  async "perfil: lo no marcado como público no sale en /@alias"(w) {
    const a = alias("pf");
    const r = await alta(w, a, "Agenteoculto");
    const id = w.sql(`SELECT id FROM perfiles WHERE alias = '${a}'`)[0].id;
    w.sql(`INSERT INTO autoria (estrella, perfil_id) VALUES ('prueba', ${id})`);
    let p = await pedir(w, "GET", `/@${a}`);
    exige(p.estado === 200 && p.texto.includes(`@${a}`), `/@${a} dio ${p.estado}`);
    exige(!p.texto.includes("Agenteoculto"), "sin marcar nada, /@alias enseña el agente");
    exige(!p.texto.includes("Una estrella de prueba"), "sin marcar nada, /@alias enseña sus estrellas");
    let e = await pedir(w, "GET", "/estrella/prueba");
    exige(!e.texto.includes(`@${a}`), "sin marcar «estrellas», la página de la estrella dice quién la hizo");
    let s = await pedir(w, "POST", "/v1/perfil", { llave: r.datos.llave, cuerpo: { publico: ["estrellas"] } });
    exige(s.estado === 200, `marcar público dio ${s.estado}`);
    p = await pedir(w, "GET", `/@${a}`);
    exige(!p.texto.includes("Agenteoculto"), "con solo «estrellas» marcado, /@alias enseña el agente");
    exige(p.texto.includes("Una estrella de prueba") && p.texto.includes("liga pequeña"), "con «estrellas» marcado, no salen sus estrellas con su liga");
    e = await pedir(w, "GET", "/estrella/prueba");
    exige(e.texto.includes(`@${a}`), "con «estrellas» marcado, la página de la estrella no dice quién la hizo");
    s = await pedir(w, "POST", "/v1/perfil", { llave: r.datos.llave, cuerpo: { publico: ["agente"] } });
    p = await pedir(w, "GET", `/@${a}`);
    exige(p.texto.includes("Agenteoculto") && !p.texto.includes("Una estrella de prueba"), "con solo «agente», no sale justo el agente");
    s = await pedir(w, "POST", "/v1/perfil", { llave: r.datos.llave, cuerpo: { publico: ["correo"] } });
    exige(s.estado === 400, `marcar «correo» como público dio ${s.estado}, no 400`);
    exige((await pedir(w, "GET", "/@nadie-se-llama-asi")).estado === 404, "un alias que no existe no da 404");
  },

  async "avisos: llegan a la página de la estrella y al estado del creador"(w) {
    const creador = await alta(w, alias("cr"));
    const id = w.sql(`SELECT id FROM perfiles WHERE alias = '${creador.datos.alias}'`)[0].id;
    w.sql(`INSERT OR REPLACE INTO autoria (estrella, perfil_id) VALUES ('candados', ${id})`);
    const quien = await alta(w, alias("av"));
    const texto = "Me salvó el lunes, gracias " + n++;
    const r = await pedir(w, "POST", "/v1/avisos", { llave: quien.datos.llave, cuerpo: { estrella: "candados", tipo: "gracias", texto } });
    exige(r.estado === 201, `avisar dio ${r.estado}: ${r.texto.slice(0, 160)}`);
    const pub = await pedir(w, "GET", "/v1/estrella/candados/avisos");
    exige(pub.datos?.avisos?.some((a) => a.texto === texto && a.de === quien.datos.alias), "el aviso no sale en los avisos públicos de la estrella");
    const pag = await pedir(w, "GET", "/estrella/candados");
    exige(pag.texto.includes(texto), "el aviso no sale en la página de la estrella");
    const yo = await pedir(w, "GET", "/v1/yo", { llave: creador.datos.llave });
    exige(yo.datos?.avisos?.some((a) => a.texto === texto && a.tipo === "gracias"), "el creador no ve el aviso en /v1/yo");
    const otro = await pedir(w, "GET", "/v1/yo", { llave: quien.datos.llave });
    exige(!otro.datos?.avisos?.some((a) => a.texto === texto), "quien no es el creador ve el aviso como suyo");
  },

  async "avisos: lo que no puede llevar"(w) {
    const q = await alta(w, alias("mal"));
    for (const [cuerpo, esperado, que] of [
      [{ estrella: "no-existe", tipo: "gracias", texto: "hola hola" }, 404, "una estrella que no existe"],
      [{ estrella: "candados", tipo: "queja", texto: "hola hola" }, 400, "un tipo que no es fallo, mejora ni gracias"],
      [{ estrella: "candados", tipo: "fallo", texto: "escribidme a nadie@" + "ejemplo.es" }, 400, "un correo"],
      [{ estrella: "candados", tipo: "fallo", texto: "llamadme al " + ["612", "345", "678"].join(" ") }, 400, "un teléfono"],
      [{ estrella: "candados", tipo: "fallo", texto: "x".repeat(501) }, 400, "más de 500 caracteres"],
    ]) {
      const r = await pedir(w, "POST", "/v1/avisos", { llave: q.datos.llave, cuerpo });
      exige(r.estado === esperado, `un aviso con ${que} dio ${r.estado}, no ${esperado}`);
    }
  },

  async "avisos: una etiqueta en el texto sale como texto"(w) {
    const q = await alta(w, alias("xs"));
    const texto = "<script>alert(1)</script><img src=x onerror=alert(2)>";
    const r = await pedir(w, "POST", "/v1/avisos", { llave: q.datos.llave, cuerpo: { estrella: "prueba", tipo: "fallo", texto } });
    exige(r.estado === 201, `avisar dio ${r.estado}`);
    const pag = await pedir(w, "GET", "/estrella/prueba");
    exige(!pag.texto.includes("<script>alert(1)") && pag.texto.includes("&lt;script&gt;alert(1)"), "la página mete el aviso sin escapar");
    exige(/default-src 'none'/.test(pag.cabeceras.get("content-security-policy") ?? ""), "la página sale sin CSP");
  },

  async "límite de avisos: 429 al pasar de 10 por hora"(w) {
    const q = await alta(w, alias("lim"));
    for (let i = 0; i < 10; i++) {
      const r = await pedir(w, "POST", "/v1/avisos", { llave: q.datos.llave, cuerpo: { estrella: "prueba", tipo: "mejora", texto: `idea número ${i}` } });
      exige(r.estado === 201, `el aviso ${i + 1} de 10 dio ${r.estado}`);
    }
    const r = await pedir(w, "POST", "/v1/avisos", { llave: q.datos.llave, cuerpo: { estrella: "prueba", tipo: "mejora", texto: "uno más" } });
    exige(r.estado === 429, `el aviso 11 dio ${r.estado}, no 429`);
    exige(r.cabeceras.get("retry-after") === "3600", "el 429 no dice cuándo volver a probar");
  },

  async "llave revocable: al cambiarla, la vieja da 401"(w) {
    const r = await alta(w, alias("rv"));
    const c = await pedir(w, "POST", "/v1/llave/cambiar", { llave: r.datos.llave });
    exige(c.estado === 200 && c.datos?.llave && c.datos.llave !== r.datos.llave, `cambiar la llave dio ${c.estado}`);
    exige((await pedir(w, "GET", "/v1/yo", { llave: r.datos.llave })).estado === 401, "la llave vieja sigue valiendo");
    exige((await pedir(w, "GET", "/v1/yo", { llave: c.datos.llave })).estado === 200, "la llave nueva no vale");
  },

  async "baja: el perfil desaparece y sus avisos quedan sin nombre"(w) {
    const r = await alta(w, alias("bj"));
    await pedir(w, "POST", "/v1/avisos", { llave: r.datos.llave, cuerpo: { estrella: "prueba", tipo: "gracias", texto: "me voy, gracias" } });
    const b = await pedir(w, "POST", "/v1/baja", { llave: r.datos.llave });
    exige(b.estado === 200, `la baja dio ${b.estado}`);
    exige((await pedir(w, "GET", `/@${r.datos.alias}`)).estado === 404, "tras la baja, el perfil sigue");
    exige((await pedir(w, "GET", "/v1/yo", { llave: r.datos.llave })).estado === 401, "tras la baja, la llave sigue valiendo");
    const pub = await pedir(w, "GET", "/v1/estrella/prueba/avisos");
    exige(pub.datos.avisos.some((a) => a.texto === "me voy, gracias" && a.de === null), "tras la baja, su aviso sigue con su alias");
  },
};

// Con su propio Worker: el tope de altas es por conexión y el resto de pruebas da muchas de alta.
const PRUEBAS_ALTAS = {
  async "límite de altas: 429 al pasar del tope por conexión y hora"(w) {
    for (let i = 0; i < 2; i++) exige((await alta(w, alias("al"))).estado === 201, `el alta ${i + 1} de 2 no entró`);
    const r = await alta(w, alias("al"));
    exige(r.estado === 429, `el alta 3 con tope 2 dio ${r.estado}, no 429`);
    exige(w.sql("SELECT * FROM ritmo").every((f) => /^alta:[0-9a-f]{64}$/.test(f.clave)), "el ritmo guarda algo que no es una huella");
  },
};

async function correr(w, pruebas, nombres = Object.keys(pruebas)) {
  const rojas = [];
  for (const nombre of nombres) {
    try { await pruebas[nombre](w); console.log(`  ok    ${nombre}`); }
    catch (e) { rojas.push([nombre, e instanceof Falla ? e.message : String(e)]); console.log(`  FALLA ${nombre}  · ${rojas.at(-1)[1]}`); }
  }
  return rojas;
}

// ---------------------------------------------------------------- sabotajes

const SABOTAJES = [
  { nombre: "la huella deja pasar claves de más", fichero: "src/reglas.ts",
    buscar: "if (!Object.keys(o).every((k) => CLAVES_HUELLA.includes(k))) return", poner: "if (false) return",
    pruebas: ["huella: solo cifras, nunca texto"] },
  { nombre: "la baja deja la huella guardada (sin el borrado de la baja ni el de la base en cascada)", fichero: "src/worker.ts",
    buscar: "    env.DB.prepare(\"DELETE FROM huellas WHERE perfil_id = ?\").bind(p.id),\n", poner: "",
    mas: [{ fichero: "migrations/0002_huellas.sql", buscar: "REFERENCES perfiles(id) ON DELETE CASCADE", poner: "" }],
    pruebas: ["huella: retirarla o darse de baja la quita del lienzo"] },
  { nombre: "una llave falsa entra como el primer perfil", fichero: "src/worker.ts",
    buscar: ".bind(await huella(llave)).first<Perfil>();",
    poner: ".bind(await huella(llave)).first<Perfil>() ?? await env.DB.prepare(\"SELECT id, alias, agente, publico, creado FROM perfiles\").first<Perfil>();",
    pruebas: ["llave falsa: 401 en todo lo que pide llave"] },
  { nombre: "la base guarda la llave en vez de su huella", fichero: "src/worker.ts",
    buscar: ".bind(alias, agente, await huella(llave), Date.now())", poner: ".bind(alias, agente, llave, Date.now())",
    pruebas: ["alta: da una llave y la base solo guarda su huella"] },
  { nombre: "con la llave, registrar crea otro perfil", fichero: "src/worker.ts",
    buscar: "if (request.headers.get(\"authorization\")) {", poner: "if (request.headers.get(\"authorization\") && alias === \"nunca\") {",
    pruebas: ["registrar dos veces: un solo perfil"] },
  { nombre: "el perfil enseña el agente aunque no esté marcado", fichero: "src/worker.ts",
    buscar: "agente: publico.has(\"agente\") ? p.agente : null,", poner: "agente: p.agente,",
    pruebas: ["perfil: lo no marcado como público no sale en /@alias"] },
  { nombre: "sin tope de avisos", fichero: "src/worker.ts",
    buscar: "if (n >= max) {\n    return error(429", poner: "if (false) {\n    return error(429",
    pruebas: ["límite de avisos: 429 al pasar de 10 por hora"] },
  { nombre: "sin tope de altas", fichero: "src/worker.ts",
    buscar: "if (n >= max) {\n    throw new Rechazo(error(429", poner: "if (false) {\n    throw new Rechazo(error(429",
    pruebas: ["límite de altas: 429 al pasar del tope por conexión y hora"], altas: true },
  { nombre: "el aviso entra en la página sin escapar", fichero: "src/paginas.ts",
    buscar: "<p>${esc(a.texto)}</p>", poner: "<p>${a.texto}</p>",
    pruebas: ["avisos: una etiqueta en el texto sale como texto"] },
];

async function sabotaje() {
  let mal = 0, puerto = 8800;
  for (const s of SABOTAJES) {
    const dir = mkdtempSync(join(tmpdir(), "void-red-sabotaje-"));
    try {
      for (const x of ["src", "migrations", "wrangler.jsonc", "package.json", "tsconfig.json"]) cpSync(join(RAIZ, x), join(dir, x), { recursive: true });
      symlinkSync(join(RAIZ, "node_modules"), join(dir, "node_modules"));
      const f = join(dir, s.fichero), texto = readFileSync(f, "utf-8");
      if (!texto.includes(s.buscar)) { console.log(`EL SABOTAJE NO SE PUDO APLICAR (${s.nombre})`); mal++; continue; }
      writeFileSync(f, texto.replace(s.buscar, s.poner));
      for (const x of s.mas ?? []) {   // la misma defensa puesta dos veces: el sabotaje quita las dos
        const g = join(dir, x.fichero), tx = readFileSync(g, "utf-8");
        if (!tx.includes(x.buscar)) { console.log(`EL SABOTAJE NO SE PUDO APLICAR (${s.nombre})`); mal++; continue; }
        writeFileSync(g, tx.replace(x.buscar, x.poner));
      }
      const w = await levantar(dir, puerto++, s.altas ? ["TOPE_ALTAS_HORA:2"] : ["TOPE_ALTAS_HORA:1000"]);
      let rojas;
      try { rojas = await correr(w, s.altas ? PRUEBAS_ALTAS : PRUEBAS, s.pruebas); } finally { w.parar(); }
      if (rojas.length) console.log(`ROJO, como debe | ${s.nombre}`);
      else { console.log(`NO LO CAZA: ${s.nombre}`); mal++; }
    } finally { rmSync(dir, { recursive: true, force: true }); }
  }
  console.log(mal ? `\nMAL: ${mal} sabotajes no se cazan.` : `\nOK: las pruebas cazan los ${SABOTAJES.length} sabotajes.`);
  return mal ? 1 : 0;
}

// ---------------------------------------------------------------- entrada

const catalogo = await servirCatalogo();
let codigo = 1;
try {
  if (process.argv.includes("--sabotaje")) {
    codigo = await sabotaje();
  } else {
    const w = await levantar(RAIZ, 8791, ["TOPE_ALTAS_HORA:1000"]);
    const w2 = await levantar(RAIZ, 8792, ["TOPE_ALTAS_HORA:2"]);
    let rojas = [];
    try {
      console.log("la red:");
      rojas = [...await correr(w, PRUEBAS), ...await correr(w2, PRUEBAS_ALTAS)];
    } finally { w.parar(); w2.parar(); }
    const total = Object.keys(PRUEBAS).length + Object.keys(PRUEBAS_ALTAS).length;
    console.log(`\n${total - rojas.length} en verde, ${rojas.length} en rojo.`);
    codigo = rojas.length ? 1 : 0;
  }
} finally { catalogo.close(); }
process.exit(codigo);
