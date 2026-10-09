/*
  vaultvoid.app/huella.js · el lienzo de huellas (ticket VV-007, etapa 1). Lo usan lienzo.html y la portada.

  Un solo campo de Gray-Scott para todos los vaults, no una huella suelta por vault:
    dU = Du·∇²U − U·V² + f·(1−U)      dV = Dv·∇²V + U·V² − (f+k)·V      Du = 1, Dv = 0.5, dt = 1, laplaciano 3×3.
  Cada vault es dueño de un territorio (el punto del lienzo más cercano a su centro, ponderado por su tamaño) y
  allí manda con sus parámetros: f y k se mueven entre dos regímenes reales, manchas que se dividen (0.0367, 0.0649)
  si hay más proyectos y laberinto (0.055, 0.062) si hay más decisiones. Fuera de todo territorio, f y k caen en un
  régimen donde V se apaga: el vacío. Donde dos territorios se tocan, la química de uno entra en la del otro por
  difusión, que es lo que da los bordes vivos (reacción-difusión con parámetros que varían en el espacio).

  De dónde sale cada cosa, y solo de cifras: el alias siembra dónde nace; los días, lo grande que es su territorio;
  decisiones contra proyectos, la forma; el último mes (pulso), cuánto brilla; cada pregunta sin contestar, un hueco;
  el color, el «tono» que elige la persona o, si no, uno sacado del alias.

  La gravedad es un modo de vista, apagado por defecto (Alex, 9-oct). Cada vault es una lente de masa puntual y el
  lienzo se ve a través de todas a la vez: β = θ − Σ θE²·(θ − θi)/|θ − θi|² (lentes delgadas sumadas, la misma
  ecuación que ya usa la web para una). θE crece con la raíz de lo hecho (decisiones + proyectos). La sombra del centro
  es una aproximación: dentro de ~½ θE no sale luz.
*/
(function () {
  "use strict";

  function semilla(str) { // cyrb53: el mismo alias da siempre el mismo número
    var h1 = 0xdeadbeef, h2 = 0x41c6ce57;
    for (var i = 0; i < str.length; i++) { var c = str.charCodeAt(i); h1 = Math.imul(h1 ^ c, 0x9e3779b1); h2 = Math.imul(h2 ^ c, 0x5f356495); }
    h1 = Math.imul(h1 ^ (h1 >>> 16), 0x85ebca6b) ^ Math.imul(h2 ^ (h2 >>> 13), 0xc2b2ae35);
    h2 = Math.imul(h2 ^ (h2 >>> 16), 0x85ebca6b) ^ Math.imul(h1 ^ (h1 >>> 13), 0xc2b2ae35);
    return 4294967296 * (2097151 & h2) + (h1 >>> 0);
  }
  function azar(s) { // mulberry32
    var a = s % 4294967296 >>> 0;
    return function () { a |= 0; a = a + 0x6D2B79F5 | 0; var t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  }
  function hsl(h, s, l) {
    var a = s * Math.min(l, 1 - l), k = function (n) { return (n + h / 30) % 12; };
    return [0, 8, 4].map(function (n) { return Math.round(255 * (l - a * Math.max(-1, Math.min(k(n) - 3, 9 - k(n), 1)))); });
  }
  function color(alias, tono) { return hsl(typeof tono === "number" ? tono : semilla(alias || "x") % 360, 0.72, 0.6); }

  var FONDO = [18, 17, 14];
  var VACIO_F = 0.012, VACIO_K = 0.07; // aquí V se apaga sola: no crece nada fuera de un territorio

  /* Prepara los territorios. h: [{alias, huella:{dias,pulso,decisiones,proyectos,calladas,tono?}}] */
  function territorios(lista, N) {
    var orden = lista.slice().sort(function (a, b) { return (b.huella.dias - a.huella.dias) || (a.alias < b.alias ? -1 : 1); });
    var n = orden.length, paso = N * 0.42 / Math.sqrt(Math.max(n, 1));
    return orden.map(function (e, i) {
      var h = e.huella, r = azar(semilla(e.alias));
      // espiral de girasol: el más antiguo en el centro, los nuevos alrededor; un pequeño giro propio por alias
      var rad = n === 1 ? 0 : paso * Math.sqrt(i + 0.5), ang = i * 2.399963 + r() * 0.6;
      var tam = paso * 1.3 * (0.35 + 0.65 * Math.sqrt(Math.min(h.dias, 365) / 365)); // los días: de un tercio a todo su sitio
      var lab = h.decisiones / (h.decisiones + h.proyectos + 1);
      return {
        alias: e.alias, h: h, r: r,
        x: N / 2 + rad * Math.cos(ang), y: N / 2 + rad * Math.sin(ang), tam: tam,
        f: 0.0367 + (0.055 - 0.0367) * lab, k: 0.0649 + (0.062 - 0.0649) * lab,
        brillo: 0.3 + 0.7 * Math.min(1, h.pulso / 60),
        col: color(e.alias, h.tono),
        masa: Math.min(N * 0.12, (3 + 1.1 * Math.sqrt(h.decisiones + h.proyectos)) * N / 180)
      };
    });
  }

  function crear(lista, N) {
    var T = territorios(lista, N), M = N * N;
    var U = new Float32Array(M).fill(1), V = new Float32Array(M), U2 = new Float32Array(M), V2 = new Float32Array(M);
    var F = new Float32Array(M).fill(VACIO_F), K = new Float32Array(M).fill(VACIO_K);
    var dueno = new Int16Array(M).fill(-1), luz = new Float32Array(M), muro = new Uint8Array(M);

    for (var y = 0; y < N; y++) for (var x = 0; x < N; x++) {
      var mejor = -1, md = 1e9;
      for (var t = 0; t < T.length; t++) { var dx = x - T[t].x, dy = y - T[t].y, d = Math.sqrt(dx * dx + dy * dy) / T[t].tam; if (d < md) { md = d; mejor = t; } }
      var i = y * N + x;
      if (mejor >= 0 && md < 1) {
        dueno[i] = mejor;
        var borde = Math.min(1, (1 - md) * 4); // el territorio se funde con el vacío en su último cuarto
        F[i] = VACIO_F + (T[mejor].f - VACIO_F) * borde; K[i] = VACIO_K + (T[mejor].k - VACIO_K) * borde;
        luz[i] = T[mejor].brillo;
      }
    }
    T.forEach(function (t, ti) {
      var r = t.r, nSem = Math.round(Math.min(48, 3 + Math.sqrt(t.h.decisiones + t.h.proyectos)) * Math.max(1, t.tam / 40));
      for (var s = 0; s < nSem; s++) {
        var a = r() * 6.2832, dd = t.tam * 0.55 * Math.sqrt(r()), cx = Math.round(t.x + dd * Math.cos(a)), cy = Math.round(t.y + dd * Math.sin(a)), rr = 1 + Math.floor(2 * r());
        for (var yy = -rr; yy <= rr; yy++) for (var xx = -rr; xx <= rr; xx++) {
          var X = cx + xx, Y = cy + yy; if (X < 0 || Y < 0 || X >= N || Y >= N) continue;
          var j = Y * N + X; if (dueno[j] === ti) { U[j] = 0.5; V[j] = 0.25 + 0.1 * r(); }
        }
      }
      for (var h = 0; h < t.h.calladas; h++) { // cada pregunta sin contestar, un hueco donde no crece nada
        var ha = r() * 6.2832, hd = t.tam * 0.5 * Math.sqrt(r()), hx = t.x + hd * Math.cos(ha), hy = t.y + hd * Math.sin(ha), hr = Math.max(2, t.tam * 0.16);
        for (var y2 = Math.floor(hy - hr); y2 <= hy + hr; y2++) for (var x2 = Math.floor(hx - hr); x2 <= hx + hr; x2++) {
          if (x2 < 0 || y2 < 0 || x2 >= N || y2 >= N) continue;
          if ((x2 - hx) * (x2 - hx) + (y2 - hy) * (y2 - hy) <= hr * hr) muro[y2 * N + x2] = 1;
        }
      }
    });

    function paso(n) {
      for (var it = 0; it < n; it++) {
        for (var y = 1; y < N - 1; y++) {
          var ym = (y - 1) * N, y0 = y * N, yp = (y + 1) * N;
          for (var x = 1; x < N - 1; x++) {
            var i = y0 + x;
            var lu = -U[i] + .2 * (U[ym + x] + U[yp + x] + U[i - 1] + U[i + 1]) + .05 * (U[ym + x - 1] + U[ym + x + 1] + U[yp + x - 1] + U[yp + x + 1]);
            var lv = -V[i] + .2 * (V[ym + x] + V[yp + x] + V[i - 1] + V[i + 1]) + .05 * (V[ym + x - 1] + V[ym + x + 1] + V[yp + x - 1] + V[yp + x + 1]);
            var uvv = U[i] * V[i] * V[i];
            U2[i] = U[i] + (lu - uvv + F[i] * (1 - U[i]));
            V2[i] = muro[i] ? 0 : V[i] + (.5 * lv + uvv - (F[i] + K[i]) * V[i]);
          }
        }
        var tu = U; U = U2; U2 = tu; var tv = V; V = V2; V2 = tv;
      }
    }

    function muestra(sx, sy) {
      if (sx < 0 || sy < 0 || sx > N - 1.001 || sy > N - 1.001) return [0, -1];
      var x0 = sx | 0, y0 = sy | 0, fx = sx - x0, fy = sy - y0, i = y0 * N + x0;
      var v = (V[i] * (1 - fx) + V[i + 1] * fx) * (1 - fy) + (V[i + N] * (1 - fx) + V[i + N + 1] * fx) * fy;
      return [v, dueno[Math.round(sy) * N + Math.round(sx)]];
    }

    function pintar(ctx, gravedad) {
      var img = ctx.createImageData(N, N), d = img.data;
      for (var i = 0; i < M; i++) {
        var v = V[i], q = dueno[i], mu = 1;
        if (gravedad && T.length) {
          var tx = (i % N) + .5, ty = ((i / N) | 0) + .5, bx = tx, by = ty, sombra = false, cerca = 1e9, tE = 0;
          for (var t = 0; t < T.length; t++) {
            var dx = tx - T[t].x, dy = ty - T[t].y, r2 = dx * dx + dy * dy || 1e-6, e2 = T[t].masa * T[t].masa;
            bx -= e2 * dx / r2; by -= e2 * dy / r2;
            var r = Math.sqrt(r2); if (r < T[t].masa * 0.5) sombra = true;
            if (r < cerca) { cerca = r; tE = T[t].masa; }
          }
          if (sombra) { v = 0; q = -1; }
          else { var s = muestra(bx, by); v = s[0]; q = s[1]; mu = Math.min(4, 1 / Math.abs(1 - Math.pow(tE / cerca, 4))); }
        }
        var o = i * 4, col = q >= 0 ? T[q].col : FONDO, b = q >= 0 ? T[q].brillo : 0;
        var a = Math.max(0, Math.min(1, (v - 0.08) / 0.27 * Math.sqrt(mu))) * b;
        d[o] = FONDO[0] + (col[0] - FONDO[0]) * a; d[o + 1] = FONDO[1] + (col[1] - FONDO[1]) * a; d[o + 2] = FONDO[2] + (col[2] - FONDO[2]) * a; d[o + 3] = 255;
      }
      ctx.putImageData(img, 0, 0);
    }

    function quien(x, y) { // x, y en celdas del campo
      var X = Math.max(0, Math.min(N - 1, Math.round(x))), Y = Math.max(0, Math.min(N - 1, Math.round(y))), q = dueno[Y * N + X];
      return q >= 0 ? T[q] : null;
    }

    return { paso: paso, pintar: pintar, quien: quien, territorios: T, N: N };
  }

  window.VoidHuella = { crear: crear, color: color };
})();
