/* Plano sin bordes: coordenadas estables, textura propia de cada huella y caché solo de las visibles. */
(()=>{'use strict';
  function crear(lista,opciones={}){
    const perspectiva=!!opciones.plano;let omitir=null;
    const cache=new Map(),N=220;let turno=0;
    const territorios=lista.map((e,i)=>{
      const posicion=Number.isSafeInteger(e.posicion)&&e.posicion>=0?e.posicion:i;
      // 330 supera la diagonal de la textura de 220, incluido el latido máximo (1,024).
      const ang=posicion*2.399963229728653,rad=330*Math.sqrt(posicion),semilla=e.semilla||e.alias||'cuento:'+e.cuento;
      const tam=100*(.35+.65*Math.sqrt(Math.min(e.huella.dias,365)/365));
      return {alias:e.alias,cuento:!e.alias,h:e.huella,col:VoidHuella.color(semilla,e.huella.tono),semilla,posicion,x:rad*Math.cos(ang),y:rad*Math.sin(ang),tam:tam*1.2,entrada:e};
    });
    function visibles(vista,W,H){if(perspectiva){const plano=VoidPlano.crear(vista,W,H);return territorios.filter(t=>{const r=plano.cartel(t);return r&&r.x+r.w>0&&r.x<W&&r.y+r.h>0&&r.y<H;});}const margen=130;return territorios.filter(t=>Math.abs((t.x-vista.x)*vista.s)<W/2+margen*vista.s&&Math.abs((t.y-vista.y)*vista.s)<H/2+margen*vista.s);}
    function textura(t){let c=cache.get(t.posicion);if(c){cache.delete(t.posicion);cache.set(t.posicion,c);return c;}
      const campo=VoidHuella.crear([t.entrada],N,0),canvas=document.createElement('canvas');canvas.width=canvas.height=N;
      c={campo,canvas,ctx:canvas.getContext('2d'),pasos:0,gravedad:null};cache.set(t.posicion,c);
      while(cache.size>12)cache.delete(cache.keys().next().value);
      return c;
    }
    function pintarTextura(c,gravedad){c.campo.pintar(c.ctx,gravedad);const img=c.ctx.getImageData(0,0,N,N);for(let i=0;i<img.data.length;i+=4)if(img.data[i]===18&&img.data[i+1]===17&&img.data[i+2]===14)img.data[i+3]=0;c.ctx.putImageData(img,0,0);if(perspectiva)c.mascara=VoidPlano.mascara(c.canvas);}
    function avanzar(vista,W,H,quieto,gravedad){const cerca=visibles(vista,W,H).sort((a,b)=>Math.hypot(a.x-vista.x,a.y-vista.y)-Math.hypot(b.x-vista.x,b.y-vista.y)).slice(0,12);if(!cerca.length)return false;
      const t=cerca[turno++%cerca.length],c=textura(t);
      if(c.pasos<900){const pasos=Math.min(perspectiva?8:quieto?32:16,900-c.pasos);c.campo.paso(pasos);c.pasos+=pasos;pintarTextura(c,gravedad);c.gravedad=gravedad;}
      else if(c.gravedad!==gravedad){pintarTextura(c,gravedad);c.gravedad=gravedad;}
      return cerca.some(t=>!cache.has(t.posicion)||cache.get(t.posicion).pasos<900||cache.get(t.posicion).gravedad!==gravedad);
    }
    function pintar(ctx,vista,W,H,now,quieto){
      const cerca=visibles(vista,W,H);
      if(perspectiva){const plano=VoidPlano.crear(vista,W,H);plano.reticula(ctx);
        for(const t of [...cerca].sort((a,b)=>b.y-a.y)){
          if(t===omitir)continue;const r=plano.cartel(t),c=cache.get(t.posicion);
          ctx.save();ctx.globalAlpha=Math.max(.35,Math.min(1,1-r.z*vista.s/2800));
          if(c)ctx.drawImage(c.canvas,r.x,r.y,r.w,r.h);
          else {ctx.fillStyle='rgb('+t.col.join(',')+')';ctx.beginPath();ctx.arc(r.x+r.w/2,r.y+r.h*.6,3,0,Math.PI*2);ctx.fill();}
          ctx.restore();
        }return cerca.length;
      }
      for(const t of cerca){const c=cache.get(t.posicion),x=W/2+(t.x-vista.x)*vista.s,y=H/2+(t.y-vista.y)*vista.s;
        if(!c||220*vista.s<8){ctx.fillStyle='rgb('+t.col.join(',')+')';ctx.beginPath();ctx.arc(x,y,Math.max(1.5,Math.min(7,t.tam*vista.s*.16)),0,Math.PI*2);ctx.fill();continue;}const latido=quieto?1:1+.024*Math.sin(now/1900+t.x*.01);
        const ancho=220*vista.s*latido;ctx.drawImage(c.canvas,W/2+(t.x-vista.x)*vista.s-ancho/2,H/2+(t.y-vista.y)*vista.s-ancho/2,ancho,ancho);}
      return cerca.length;
    }
    function quien(x,y){return territorios.find(t=>Math.hypot(x-t.x,y-t.y)<t.tam)||null;}
    function tocar(x,y,vista,W,H){const plano=VoidPlano.crear(vista,W,H),rs=visibles(vista,W,H).map(t=>{const r=plano.cartel(t);r.mascara=cache.get(t.posicion)?.mascara;return r;});return VoidPlano.tocar(rs,x,y)?.t||null;}
    function fuente(t){return textura(t);}
    function destruir(){for(const c of cache.values()){c.canvas.width=c.canvas.height=0;c.campo=null;c.mascara=null;}cache.clear();}
    return {territorios,libres:[],avanzar,pintar,quien,visibles,tocar,fuente,destruir,omitir:t=>{omitir=t;}};
  }
  window.VoidVacio={crear};
})();
