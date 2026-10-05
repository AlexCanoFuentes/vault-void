// Cliente de prueba con el cliente OFICIAL v2 (@modelcontextprotocol/client 2.1.0), forma copiada de
// remoto/pruebas/eras-y-llamada.mjs del remoto normativo.
// Uso: node pruebas/cliente.mjs <url> <auto|legacy> [herramienta] [json-args]
//   auto -> 2026-07-28 (server/discover) · legacy -> 2025-11-25 (initialize).
import { Client, StreamableHTTPClientTransport } from "@modelcontextprotocol/client";
import { createHash } from "node:crypto";

export async function conectar(url, modo = "auto") {
  const cliente = new Client({ name: "prueba-void-antena", version: "0.0.1" }, { versionNegotiation: { mode: modo } });
  await cliente.connect(new StreamableHTTPClientTransport(new URL(url)));
  return cliente;
}

export async function llamar(cliente, herramienta, args) {
  const r = await cliente.callTool({ name: herramienta, arguments: args });
  const texto = r.content?.[0]?.text ?? "";
  const meta = r._meta?.["void/huella"];
  const huellaOk = meta ? meta.sha256 === createHash("sha256").update(texto).digest("hex").slice(0, 16) : null;
  let datos = null;
  try { datos = JSON.parse(texto); } catch { /* texto de error */ }
  return { isError: !!r.isError, texto, datos, huellaOk };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const [url, modo = "auto", herramienta, argsJson] = process.argv.slice(2);
  const t0 = Date.now();
  const cliente = await conectar(url, modo);
  console.log(`modo=${modo} versión negociada=${cliente.getNegotiatedProtocolVersion()} (${Date.now() - t0} ms)`);
  if (!herramienta) {
    const { tools } = await cliente.listTools();
    for (const t of tools) console.log(`  - ${t.name} · "${t.title}" · readOnlyHint=${t.annotations?.readOnlyHint}`);
  } else {
    const t1 = Date.now();
    const r = await llamar(cliente, herramienta, JSON.parse(argsJson ?? "{}"));
    console.log(`${herramienta}: isError=${r.isError} (${Date.now() - t1} ms de pared) huella=${r.huellaOk}`);
    console.log(r.texto.length > 2500 ? r.texto.slice(0, 2500) + " …[recortado]" : r.texto);
  }
  await cliente.close();
}
