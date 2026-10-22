// Geometría sin navegador ni sockets: node red/pruebas/plano.mjs
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
const entorno={window:{},Uint8ClampedArray};
vm.createContext(entorno);
await vm.runInContext(await readFile(new URL('../../web/plano.js',import.meta.url),'utf8'),entorno);
const {crear,tocar,paralaje}=entorno.window.VoidPlano;
let casos=0;
for(const [W,H] of [[320,900],[412,915],[1440,1000]]){
 for(const s of [.015,.3,1,3,12])for(let i=0;i<80;i++){
  const vista={x:123,y:-49,s},plano=crear(vista,W,H);
  const u=W*(.1+(i%8)/10),v=H*(.48+Math.floor(i/8)*.035),p=plano.inversa(u,v);
  assert.ok(p);
  const q=plano.proyectar(p.x,p.y);
  assert.ok(Math.hypot(q.x-u,q.y-v)<1e-7,'ida y vuelta');
  assert.ok(plano.zoom(1.4,u,v));
  const despues=plano.inversa(u,v);
  assert.ok(Math.hypot(p.x-despues.x,p.y-despues.y)<1e-7,'el centro del pellizco no deriva');
  const destino={x:u+12,y:v+8};plano.anclar(p,destino.x,destino.y);
  const movido=plano.proyectar(p.x,p.y);
  assert.ok(Math.hypot(movido.x-destino.x,movido.y-destino.y)<1e-7,'arrastre sin salto');
  casos++;
 }
}
const mascara={w:2,h:2,datos:new Uint8ClampedArray(16)};
mascara.datos[3]=255;
const lejos={x:10,y:10,w:100,h:100,z:50,id:'lejos'};
const cerca={...lejos,z:-2,id:'cerca',mascara};
assert.equal(tocar([lejos,cerca],10,10).id,'cerca');
assert.equal(tocar([cerca,lejos],90,90).id,'lejos','un hueco deja tocar el cartel de detrás');
assert.equal(tocar([lejos],110,50),null,'el borde derecho queda fuera');
assert.equal(tocar([lejos],50,110),null,'el borde inferior queda fuera');
assert.equal(tocar([lejos],9.9,50),null);
const plano=crear({x:0,y:0,s:1},412,915);
assert.equal(plano.inversa(50,-10000),null,'no hay arrastre por encima del horizonte');
assert.equal(plano.proyectar(0,-10000),null,'se descarta detrás de la cámara');
assert.equal(paralaje(800,-800).x,18);
assert.equal(paralaje(800,-800).y,-14);
console.log(`✓ ${casos} casos de proyección, inversa, zoom y arrastre. Máscara, bordes, solapes, horizonte y paralaje.`);
