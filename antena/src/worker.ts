/**
 * Entrada del Worker de la antena (antena.vaultvoid.app).
 *
 *   /mcp              el servidor MCP (sin clave, sin sesión, solo lectura)
 *   /                 una línea que explica qué es y dónde conectarlo
 *   cualquier otra    404
 */
import { atender, type Entorno } from "./remoto.js";

const CABECERAS = { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store", "x-content-type-options": "nosniff" };

export default {
  async fetch(request: Request, env: Entorno): Promise<Response> {
    const ruta = new URL(request.url).pathname.replace(/\/+$/, "");
    if (ruta === "/mcp") return atender(request, env);
    if (ruta === "") {
      return new Response("La antena de Vault Void: un servidor MCP de solo lectura sobre el catálogo de estrellas.\n"
        + "Conéctalo a tu asistente con esta dirección: https://antena.vaultvoid.app/mcp\n"
        + "Y el vacío entero, en https://vaultvoid.app\n", { headers: CABECERAS });
    }
    return new Response("No encontrado. El servidor MCP está en /mcp.\n", { status: 404, headers: CABECERAS });
  },
};
