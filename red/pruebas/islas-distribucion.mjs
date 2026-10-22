// M-15: distribución y materia reales, sin navegador, red ni datos privados.
// Ejecutar: node red/pruebas/islas-distribucion.mjs
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
const entorno={window:{}};vm.createContext(entorno);
for(const nombre of ['plano','huella','islas-juego'])vm.runInContext(await readFile(new URL(`../../web/${nombre}.js`,import.meta.url),'utf8'),entorno);
const {VoidPlano,VoidJuegoIslas,VoidHuella}=entorno.window;
let casos=0;
for(const [W,H] of [[320,568],[320,1000],[360,800],[412,915],[699,1000],[700,1000],[915,412],[1440,1000]]){
 for(let n=1;n<=VoidJuegoIslas.capacidad(W,H);n++)for(let patron=0;patron<5;patron++){
  const datos=Array.from({length:n},(_,i)=>({id:String(i),posicion:patron===0?{x:.5,y:.5}:patron===1?{x:i%2?.82:.18,y:i<4?.82:.2}:{x:.08+((i*37+patron*17)%85)/100,y:.12+((i*23+patron*19)%74)/100}}));
  const origen={x:453,y:-712},lugares=(()=>{try{return VoidJuegoIslas.distribucion(W,H,datos,origen);}catch(e){throw Error(`${W}×${H}, n=${n}, patrón=${patron}`,{cause:e});}})(),s=Math.min(W/400,H/600,2);
  assert.equal(lugares.size,n);
  assert.equal(new Set([...lugares.values()].map(t=>t.lado)).size,1,'un tamaño común en el mundo, sin compensación por profundidad');
  for(const [dx,dy] of [[0,0],[-18,-14],[18,14]]){
   const p=VoidPlano.crear({x:origen.x+dx,y:origen.y+dy,s},W,H),cajas=[];
   for(const t of lugares.values()){
    const r=p.cartel(t,t.lado),caja={x:r.x-10,y:r.y,w:r.w+20,h:r.h+25};
    if(!dx){
     assert.ok(r.w>=44,'zona táctil de al menos 44 px');
     assert.ok(caja.x>=0&&caja.x+caja.w<=W,'nombre dentro de la pantalla');
     assert.ok(caja.y>=130&&caja.y+caja.h<=H-(W<=380?140:80),'mandos libres');
    }
    for(const b of cajas)assert.ok(caja.x+caja.w<=b.x||b.x+b.w<=caja.x||caja.y+caja.h<=b.y||b.y+b.h<=caja.y,`no se pisan nombres ni huellas (${W}×${H}, ${n}, ${patron}, paralaje ${dx}/${dy})`);
    cajas.push(caja);
   }
   if(!dx&&n>=4)assert.ok(Math.max(...cajas.map(r=>r.w))/Math.min(...cajas.map(r=>r.w))>1.08,'profundidades con tamaños diferentes');
  }
  const p=VoidPlano.crear({...origen,s},W,H),orden=[...lugares.values()].sort((a,b)=>a.y-b.y);
  for(let i=1;i<orden.length;i++){
   const a=p.cartel(orden[i-1],orden[i-1].lado),b=p.cartel(orden[i],orden[i].lado);
   assert.ok(a.w>=b.w-1e-8&&a.y+a.h>=b.y+b.h-1e-8,'delante: más grande y abajo; detrás: más pequeño y arriba');
  }
  casos++;
 }
}
// Con espacio libre se respeta literalmente la posición del plano, y su origen público.
const O={x:1200,y:-700},d={id:'sola',posicion:{x:.35,y:.7}};
const t=VoidJuegoIslas.distribucion(1440,1000,[d],O).get('sola');
assert.ok(Math.hypot(t.x-(O.x+360*(d.posicion.x-.5)),t.y-(O.y+360*(d.posicion.y-.5)))<1e-7);
console.log(`✓ ${casos} distribuciones: posición, perspectiva, tamaños, nombres, mandos y paralaje sin solapes.`);
// Campos individuales centrados, incluso islas vacías y las cuatro fijas.
const muestras=[...['fija_hablar','fija_comunidad','fija_modelos','fija_cuidar'].map(alias=>({alias,dias:150,pulso:40,decisiones:3,proyectos:3})),
 {alias:'isla-vacia',dias:160,pulso:18,decisiones:1,proyectos:1},
 {alias:'isla-tareas',dias:365,pulso:60,decisiones:1,proyectos:32},
 {alias:'isla-terminada',dias:365,pulso:60,decisiones:32,proyectos:1}];
for(const {alias,...huella} of muestras){
 const N=192,campo=VoidHuella.crear([{alias,semilla:alias,pos:{x:.5,y:.5},huella:{...huella,tono:80,calladas:0}}],N,0,{detalle:1.35});
 let imagen;const ctx={createImageData:(w,h)=>({data:new Uint8ClampedArray(w*h*4)}),putImageData:i=>{imagen=i;}};
 campo.paso(1600);campo.pintar(ctx,false);
 let tinta=0,minX=N,maxX=0;
 for(let i=0;i<N*N;i++)if(Math.max(...imagen.data.subarray(i*4,i*4+3))>40){tinta++;minX=Math.min(minX,i%N);maxX=Math.max(maxX,i%N);}
 assert.ok(tinta>500,`${alias}: una huella, no unos pocos puntos (${tinta})`);
 assert.ok(maxX-minX>N*.35,`${alias}: la materia ocupa el campo`);
}
console.log('✓ Siete campos independientes de 192 celdas: todas las fijas, isla vacía y extremos de tareas tienen materia visible.');
