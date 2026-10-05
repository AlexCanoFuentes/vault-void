/**
 * La cara remota: HTTP streamable, sin sesión y sin estado. Copiada en forma del MCP de subvenciones
 * (`lexlabs-mcp/src/remoto.ts`), sin su contador:
 *   - el protocolo lo pone `createMcpHandler` del SDK oficial v2: 2026-07-28 y, con `legacy: "stateless"`,
 *     2025-11-25 y anteriores; GET y DELETE (sesión en 2025) dan 405;
 *   - cuerpos de más de 64 KiB: 413 antes de leer nada;
 *   - `subscriptions/listen` se rechaza: abriría un flujo que se queda vivo y aquí no hay nada que notificar;
 *   - sin CORS a propósito, y `cache-control: no-store` en todo lo que sale.
 */
import { createMcpHandler } from "@modelcontextprotocol/server";
import { crearServidor } from "./servidor-mcp.js";
import { huellaDeIp } from "./seguridad.js";

const MAX_CUERPO = 64 * 1024;

export interface Entorno {
  /** Solo para la prueba de sabotaje: apuntar el catálogo a un sitio que no existe. En producción no se define. */
  CATALOGO_URL?: string;
}

let entorno: Entorno = {};

const mcp = createMcpHandler(
  ({ requestInfo }) => {
    const ip = requestInfo?.headers.get("cf-connecting-ip") ?? "desconocida";
    return crearServidor({ catalogo: entorno.CATALOGO_URL || undefined, quien: "ip:" + huellaDeIp(ip) });
  },
  {
    legacy: "stateless",
    maxRequestBodySize: MAX_CUERPO,
    maxSubscriptions: 1,
    keepAliveMs: 0,
    onerror: (e) => console.error(JSON.stringify({ rechazo: e.name, motivo: String(e.message).slice(0, 200) })),
  },
);

function errorRpc(status: number, id: unknown, code: number, message: string): Response {
  return new Response(JSON.stringify({ jsonrpc: "2.0", id: id ?? null, error: { code, message } }), {
    status, headers: { "content-type": "application/json", "cache-control": "no-store" },
  });
}

export async function atender(request: Request, env: Entorno): Promise<Response> {
  entorno = env;
  if (request.method === "POST") {
    let listen: { id: unknown } | null = request.headers.get("mcp-method") === "subscriptions/listen" ? { id: null } : null;
    const largo = Number(request.headers.get("content-length") ?? "0");
    if (largo <= MAX_CUERPO) try {
      const txt = await request.clone().text();
      if (txt.length <= MAX_CUERPO && txt.includes("subscriptions/listen")) {
        const cuerpo = JSON.parse(txt);
        const m = (Array.isArray(cuerpo) ? cuerpo : [cuerpo]).find((x) => x && x.method === "subscriptions/listen");
        if (m) listen = { id: m.id };
      }
    } catch { /* cuerpo no JSON: lo contesta el SDK */ }
    if (listen) return errorRpc(400, listen.id, -32601, "subscriptions/listen no está disponible: este servidor no emite notificaciones.");
  }
  const res = await mcp.fetch(request);
  const h = new Headers(res.headers);
  h.set("cache-control", "no-store");
  h.set("x-content-type-options", "nosniff");
  return new Response(res.body, { status: res.status, statusText: res.statusText, headers: h });
}
