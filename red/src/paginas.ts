/**
 * Las dos páginas que sirve la red dentro de vaultvoid.app: el perfil (/@alias) y la página de una estrella
 * con sus avisos (/estrella/<nombre>). El mismo vacío negro que web/, sin JavaScript.
 *
 * TODO lo que escribe una persona (alias, agente, avisos) pasa por `esc` y la página sale con una CSP que no
 * deja ejecutar nada: aunque alguien cuele una etiqueta en un aviso, se ve como texto.
 */
export function esc(s: unknown): string {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
}

const WEB = "https://vaultvoid.app";

export const CSP = "default-src 'none'; style-src 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
  + "img-src https://vaultvoid.app; base-uri 'none'; form-action 'none'; frame-ancestors 'none'";

const ESTILO = `
:root{--vacio:#12110E;--tinta:#ECE7DE;--tinta-2:#B3AC9F;--tenue:#8C8578;--linea:#2B2822;--panel:#1B1915;
--acento:#F2A93B;--acento-2:#F8CB86;--ambar:#F2A93B;--rojo:#FF6B6B;--verde:#5BE06A;
--serif:"Instrument Serif",Georgia,"Times New Roman",serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;color-scheme:dark}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--vacio);color:var(--tinta);font:15px/1.7 var(--mono);-webkit-font-smoothing:antialiased;min-height:100vh;
background-image:radial-gradient(1px 1px at 12% 18%,#fff8 50%,transparent),radial-gradient(1px 1px at 78% 12%,#fff6 50%,transparent),
radial-gradient(1px 1px at 63% 74%,#fff5 50%,transparent),radial-gradient(1px 1px at 28% 86%,#fff4 50%,transparent),
radial-gradient(1.5px 1.5px at 88% 52%,#F8CB8688 50%,transparent)}
main{max-width:42rem;margin:0 auto;padding:72px 16px 72px}
.n{margin:0 0 10px;font:500 11px var(--mono);letter-spacing:.2em;text-transform:uppercase;color:var(--acento-2)}
h1{margin:0 0 14px;font:400 clamp(48px,11vw,88px)/1 var(--serif);letter-spacing:-.02em;overflow-wrap:anywhere}
h1 em{font-style:italic;color:transparent;-webkit-text-stroke:1px var(--tinta)}
h2{margin:48px 0 14px;font:400 28px/1.15 var(--serif)}
p{color:var(--tinta-2);margin:0 0 12px}
strong{color:var(--tinta);font-weight:500}
a{color:var(--acento-2);text-underline-offset:3px}
code{font:inherit;color:var(--tinta);background:var(--panel);border:1px solid var(--linea);border-radius:4px;padding:0 .3em;overflow-wrap:anywhere}
pre{margin:14px 0;padding:12px 14px;background:var(--panel);border:1px solid var(--linea);border-left:2px solid var(--acento);border-radius:6px;overflow-x:auto}
pre code{background:none;border:0;padding:0;white-space:pre-wrap;overflow-wrap:anywhere}
ul.lista{list-style:none;margin:0;padding:0;border-top:1px solid var(--linea)}
ul.lista li{padding:14px 0;border-bottom:1px solid var(--linea)}
.liga{display:inline-block;margin-left:8px;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--ambar)}
.tipo{display:inline-block;min-width:8em;margin-right:10px;font-size:11px;letter-spacing:.14em;text-transform:uppercase}
.tipo.fallo{color:var(--rojo)}.tipo.mejora{color:var(--ambar)}.tipo.gracias{color:var(--verde)}
.de{font-size:12px;color:var(--tenue)}
.aviso p{margin:6px 0 4px;color:var(--tinta);white-space:pre-wrap;overflow-wrap:anywhere}
.vacio{color:var(--tenue)}
footer{margin-top:64px;padding-top:18px;border-top:1px solid var(--linea);font-size:13px;color:var(--tenue)}
footer p{color:var(--tenue)}`;

function pagina(o: { titulo: string; descripcion: string; url: string; cuerpo: string }): string {
  return `<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>${esc(o.titulo)}</title>
<meta name="description" content="${esc(o.descripcion)}">
<meta name="robots" content="noindex">
<meta property="og:title" content="${esc(o.titulo)}">
<meta property="og:description" content="${esc(o.descripcion)}">
<meta property="og:url" content="${esc(o.url)}">
<meta property="og:type" content="website">
<meta property="og:locale" content="es_ES">
<meta property="og:image" content="${WEB}/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Vault Void: un vacío negro con la primera estrella.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="${WEB}/og.jpg">
<link rel="icon" href="${WEB}/icono.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="${WEB}/apple-touch-icon.png">
<meta name="theme-color" content="#12110E">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>${ESTILO}</style>
</head>
<body>
<main>
${o.cuerpo}
<footer>
<p><a href="${WEB}">vaultvoid.app</a> · Para entrar en la red, pégale a tu agente: «conéctate a Void: vaultvoid.app/entrar».</p>
<p>Void no guarda nada de tu vault: solo tu alias, el nombre de tu agente y lo que tú decidas enseñar.</p>
</footer>
</main>
</body>
</html>
`;
}

export interface EstrellaDePerfil { nombre: string; titulo: string; liga: string | null }

export function paginaPerfil(p: { alias: string; agente: string | null; estrellas: EstrellaDePerfil[] | null; desde: string }): string {
  const partes: string[] = [];
  partes.push(`<p class="n">En la red de Void desde ${esc(p.desde)}</p>`);
  partes.push(`<h1>@${esc(p.alias)}</h1>`);
  if (p.agente !== null) partes.push(`<p>Trabaja con su agente <strong>${esc(p.agente)}</strong>.</p>`);
  if (p.estrellas !== null) {
    partes.push(`<h2>Sus estrellas</h2>`);
    partes.push(p.estrellas.length
      ? `<ul class="lista">${p.estrellas.map((e) => `<li><a href="${WEB}/estrella/${esc(e.nombre)}">${esc(e.titulo)}</a>`
          + (e.liga ? `<span class="liga">liga ${esc(e.liga)}</span>` : "") + `</li>`).join("")}</ul>`
      : `<p class="vacio">Todavía no ha publicado ninguna estrella.</p>`);
  }
  if (p.agente === null && p.estrellas === null) {
    partes.push(`<p class="vacio">Esta persona solo enseña su alias.</p>`);
  }
  return pagina({
    titulo: `@${p.alias} · Void`,
    descripcion: `@${p.alias} está en la red de Vault Void.`,
    url: `${WEB}/@${p.alias}`,
    cuerpo: partes.join("\n"),
  });
}

export interface AvisoPublico { tipo: string; texto: string; de: string | null; creado: number }

/** La fecha en la hora de España (la de Void): un aviso de las 01:00 del 7 no sale como del 6. */
const FECHA = new Intl.DateTimeFormat("es-ES", { day: "numeric", month: "short", year: "numeric", timeZone: "Europe/Madrid" });
function fecha(ms: number): string {
  return FECHA.format(new Date(ms)).replace(/\./g, "");
}

export function fechaCorta(ms: number): string { return fecha(ms); }

export function paginaEstrella(e: { nombre: string; titulo: string; resuelve: string; liga: string | null; creador: string | null;
  avisos: AvisoPublico[] }): string {
  const lista = e.avisos.length
    ? `<ul class="lista">${e.avisos.map((a) => `<li class="aviso"><span class="tipo ${esc(a.tipo)}">${esc(a.tipo)}</span>`
        + `<span class="de">${a.de ? `de <a href="${WEB}/@${esc(a.de)}">@${esc(a.de)}</a>` : "de alguien que ya no está en la red"} · ${fecha(a.creado)}</span>`
        + `<p>${esc(a.texto)}</p></li>`).join("")}</ul>`
    : `<p class="vacio">Nadie le ha escrito todavía.</p>`;
  return pagina({
    titulo: `${e.titulo} · Void`,
    descripcion: e.resuelve || `La estrella ${e.nombre} de Vault Void.`,
    url: `${WEB}/estrella/${e.nombre}`,
    cuerpo: [
      `<p class="n">Estrella${e.liga ? ` · liga ${esc(e.liga)}` : ""}</p>`,
      `<h1>${esc(e.titulo)}</h1>`,
      e.resuelve ? `<p>${esc(e.resuelve)}</p>` : "",
      e.creador ? `<p>La hizo <a href="${WEB}/@${esc(e.creador)}">@${esc(e.creador)}</a>.</p>` : "",
      `<p>Para traerla a tu vault:</p><pre><code>python herramientas/void.py traer ${esc(e.nombre)}</code></pre>`,
      `<h2>Lo que le han escrito</h2>`,
      lista,
      `<p style="margin-top:20px">Si te ha fallado, se te ocurre una mejora o quieres darle las gracias, desde tu vault:</p>`,
      `<pre><code>python herramientas/void.py avisar ${esc(e.nombre)} gracias "lo que le quieras decir"</code></pre>`,
      `<p class="de">Lo que escribas sale aquí, a la vista de todos, con tu alias.</p>`,
    ].join("\n"),
  });
}

export function paginaNoEncontrada(que: string): string {
  return pagina({
    titulo: "No está · Void",
    descripcion: "Aquí no hay nada.",
    url: WEB,
    cuerpo: `<p class="n">404</p><h1>Aquí no hay <em>nada</em></h1><p>${esc(que)}</p>`,
  });
}
