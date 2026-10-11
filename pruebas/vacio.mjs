import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const creadas=[],dibujadas=[],contexto={window:{},document:{createElement(){const canvas={};canvas.getContext=()=>({getImageData:()=>({data:new Uint8ClampedArray(220*220*4)}),putImageData(){},canvas});return canvas;}},VoidHuella:{color:()=>[100,180,120],crear([entrada]){creadas.push(entrada);return {paso(){},pintar(ctx){ctx.canvas.entrada=entrada;}};}}};
vm.runInNewContext(readFileSync(new URL('../web/vacio.js',import.meta.url),'utf8'),contexto);
const entrada=(posicion,tono=posicion)=>({alias:'huella-'+posicion,posicion,semilla:'cuento:1',huella:{dias:365,tono,pulso:30,proyectos:3,decisiones:20,calladas:0}});
const lista=[entrada(2),entrada(3),entrada(4)],campo=contexto.window.VoidVacio.crear(lista),vista={x:0,y:0,s:1};
for(let i=0;i<3;i++)campo.avanzar(vista,2000,2000,true,false);
campo.pintar({drawImage(canvas){dibujadas.push(canvas.entrada);}},vista,2000,2000,100,true);
assert.equal(creadas.length,3);assert.equal(new Set(dibujadas).size,3);assert.deepEqual(new Set(dibujadas),new Set(lista));
for(const t of campo.territorios){assert.equal(t.semilla,'cuento:1');assert.equal(campo.quien(t.x,t.y),t);}
const muchos=contexto.window.VoidVacio.crear(Array.from({length:1000},(_,i)=>entrada(i))).territorios;
const diagonal=220*1.024*Math.SQRT2;
for(let i=0;i<muchos.length;i++)for(let j=i+1;j<muchos.length;j++)assert.ok(Math.hypot(muchos[i].x-muchos[j].x,muchos[i].y-muchos[j].y)>diagonal,'Dos texturas pueden superponerse durante el latido.');
const otra=contexto.window.VoidVacio.crear([entrada(4000),...lista.slice().reverse()]).territorios;
for(const t of campo.territorios){const igual=otra.find(o=>o.posicion===t.posicion);assert.equal(t.x,igual.x);assert.equal(t.y,igual.y);}
console.log('✓ Semillas compartidas producen tres texturas propias seleccionables; mil sitios no se pisan durante el latido y mantienen su ubicación al cambiar la lista.');
