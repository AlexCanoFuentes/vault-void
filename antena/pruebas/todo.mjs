// Las pruebas de la antena: el cliente MCP OFICIAL contra el Worker en local (wrangler dev), y los
// sabotajes vistos en rojo. Una orden, un veredicto:   npm test
import { spawn } from "node:child_process";
import { conectar, llamar } from "./cliente.mjs";

const PUERTO = 8799, PUERTO_ROTO = 8798;
let bien = 0, mal = 0;
function ver(nombre, ok, detalle = "") { ok ? bien++ : mal++; console.log(`  ${ok ? "ok   " : "FALLA"} ${nombre}${ok || !detalle ? "" : "  · " + detalle}`); }

function arranca(puerto, extra = []) {
  const p = spawn("npx", ["wrangler", "dev", "--port", String(puerto), "--ip", "127.0.0.1", ...extra], { stdio: ["ignore", "pipe", "pipe"] });
  return new Promise((ok, no) => {
    const t = setTimeout(() => no(new Error("wrangler dev no arrancó en 90 s")), 90_000);
    const mira = (d) => { if (/Ready on|localhost:\d+|127\.0\.0\.1:\d+/.test(String(d))) { clearTimeout(t); ok(p); } };
    p.stdout.on("data", mira); p.stderr.on("data", mira);
  });
}

const vivo = await arranca(PUERTO);
const roto = await arranca(PUERTO_ROTO, ["--var", "CATALOGO_URL:https://no-existe.invalid/catalogo.json"]);
try {
  const url = `http://127.0.0.1:${PUERTO}/mcp`;
  console.log("la antena:");
  for (const modo of ["auto", "legacy"]) {
    const c = await conectar(url, modo);
    const { tools } = await c.listTools();
    ver(`(${modo}) tres herramientas, todas de solo lectura`, tools.length === 3 && tools.every((t) => t.annotations?.readOnlyHint === true), tools.map((t) => t.name).join(","));
    await c.close();
  }
  const c = await conectar(url);
  let r = await llamar(c, "buscar_estrellas", { problema: "trabajo con dos IA en el mismo proyecto y se pisan" });
  ver("«dos IA se pisan» encuentra los candados", !r.isError && r.datos?.estrellas?.[0]?.nombre === "candados", r.texto.slice(0, 200));
  ver("y trae la orden para traerla", r.datos?.estrellas?.[0]?.traerla === "python herramientas/void.py traer candados");
  ver("con la huella del texto entregado", r.huellaOk === true);
  r = await llamar(c, "buscar_estrellas", { problema: "desarrollar una app de recetas" });
  ver("«desarrollar una app de recetas» no encuentra nada y lo dice", !r.isError && r.datos?.encontradas === 0 && /taller/.test(r.datos?.si_no_hay ?? ""), r.texto.slice(0, 200));
  r = await llamar(c, "ver_estrella", { nombre: "candados" });
  ver("la ficha de candados, con lo que no protege y cómo deshacerla", !r.isError && r.datos?.no_protege?.length > 0 && !!r.datos?.riesgo?.deshacer, r.texto.slice(0, 200));
  r = await llamar(c, "ver_estrella", { nombre: "no-existe" });
  ver("una estrella que no existe es un error de entrada, no de la fuente", r.isError && /Entrada no válida/.test(r.texto) && /candados/.test(r.texto), r.texto.slice(0, 200));
  r = await llamar(c, "listar_estrellas", {});
  ver("listar trae todas", !r.isError && r.datos?.total >= 1);
  await c.close();

  console.log("sabotajes (cada uno tiene que salir en rojo por su razón):");
  const cr = await conectar(`http://127.0.0.1:${PUERTO_ROTO}/mcp`);
  r = await llamar(cr, "buscar_estrellas", { problema: "dos IA se pisan" });
  ver("catálogo inalcanzable: devuelve el fallo y ningún dato", r.isError && /No se pudo leer el catálogo/.test(r.texto) && r.datos === null, r.texto.slice(0, 200));
  await cr.close();
  const grande = await fetch(url, { method: "POST", headers: { "content-type": "application/json", accept: "application/json, text/event-stream" }, body: "x".repeat(70 * 1024) });
  ver("un cuerpo de 70 KiB: 413", grande.status === 413, String(grande.status));
  const listen = await fetch(url, { method: "POST", headers: { "content-type": "application/json", accept: "application/json, text/event-stream", "mcp-method": "subscriptions/listen" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 7, method: "subscriptions/listen", params: {} }) });
  ver("subscriptions/listen: rechazado", listen.status === 400, String(listen.status));
  const raiz = await fetch(`http://127.0.0.1:${PUERTO}/`);
  ver("la raíz explica qué es y dónde conectarlo", raiz.status === 200 && /antena\.vaultvoid\.app\/mcp/.test(await raiz.text()));
} finally {
  vivo.kill(); roto.kill();
}
console.log(`\n${bien} en verde, ${mal} en rojo.`);
process.exit(mal ? 1 : 0);
