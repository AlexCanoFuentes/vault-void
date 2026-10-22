/* M-15 · Codex. Un suelo, carteles verticales y la misma cámara para dibujar y tocar. */
(()=>{'use strict';
 const limitar=(n,a,b)=>Math.max(a,Math.min(b,n));
 function crear(vista,W,H){
  const f=H<700||W<400?Math.max(500,H*.9):Math.max(380,H*.6),theta=Math.PI*.32,c=Math.cos(theta),s=Math.sin(theta),ox=W/2,oy=H*.62;
  function proyectar(X,Z){
   const x=X-vista.x,z=Z-vista.y,D=f+vista.s*z*s;
   if(!Number.isFinite(D)||D<f*.08)return null;
   const k=vista.s*f/D;return {x:ox+k*x,y:oy-k*z*c,k,z};
  }
  function inversa(u,v){
   const V=oy-v,den=vista.s*(f*c-V*s);
   if(!Number.isFinite(den)||den<=vista.s*f*.035)return null;
   const z=f*V/den,D=f+vista.s*z*s;
   if(D<f*.08)return null;
   return {x:vista.x+(u-ox)*D/(vista.s*f),y:vista.y+z};
  }
  function cartel(t,lado=220){
   const p=proyectar(t.x,t.y);if(!p)return null;
   const w=lado*p.k;return {x:p.x-w/2,y:p.y-w,w,h:w,k:p.k,z:p.z,t};
  }
  function zoom(factor,u=ox,v=oy){
   const ancla=inversa(u,v);if(!ancla)return false;
   const anterior=vista.s;vista.s=limitar(anterior*factor,.015,12);
   const despues=inversa(u,v);if(!despues){vista.s=anterior;return false;}
   vista.x+=ancla.x-despues.x;vista.y+=ancla.y-despues.y;return true;
  }
  function anclar(p,u,v){const q=inversa(u,v);if(q&&p){vista.x+=p.x-q.x;vista.y+=p.y-q.y;}}
  function reticula(ctx){
   const paso=160,baseX=Math.floor(vista.x/paso)*paso,baseZ=Math.floor(vista.y/paso)*paso;
   ctx.save();ctx.strokeStyle='#a59b8026';ctx.lineWidth=1;
   // Cada segmento se proyecta con la misma perspectiva; se descartan las singularidades.
   for(let i=-12;i<=18;i++)for(let j=-12;j<18;j++){
    for(const [dx,dz] of [[1,0],[0,1]]){
     const a=proyectar(baseX+i*paso,baseZ+j*paso),b=proyectar(baseX+(i+dx)*paso,baseZ+(j+dz)*paso);
     if(!a||!b||Math.max(Math.abs(a.x),Math.abs(b.x))>W*8||Math.max(Math.abs(a.y),Math.abs(b.y))>H*8)continue;
     ctx.globalAlpha=limitar(1-Math.max(a.z,b.z)*vista.s/4500,.05,.7);
     ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();
    }
   }ctx.restore();
  }
  return {proyectar,inversa,cartel,zoom,anclar,reticula};
 }
 // Una máscara se lee una sola vez al madurar la textura. Nunca getImageData por gesto.
 function mascara(canvas){const {width:w,height:h}=canvas;return {w,h,datos:canvas.getContext('2d').getImageData(0,0,w,h).data};}
 function contiene(r,x,y,m){
  if(!r||x<r.x||y<r.y||x>=r.x+r.w||y>=r.y+r.h)return false;
  if(!m)return true;
  const u=Math.floor((x-r.x)/r.w*m.w),v=Math.floor((y-r.y)/r.h*m.h);
  return m.datos[(v*m.w+u)*4+3]>16;
 }
 function tocar(carteles,x,y){
  return [...carteles].sort((a,b)=>a.z-b.z).find(r=>contiene(r,x,y,r.mascara))||null;
 }
 function paralaje(x,y){return {x:limitar(x,-18,18),y:limitar(y,-14,14)};}
 window.VoidPlano={crear,mascara,contiene,tocar,paralaje};
})();
