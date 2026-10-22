/* Los datos y las texturas solo viven en memoria, durante esta vista. */
'use strict';
self.window=self;
importScripts('huella.js','islas-campos.js');
const motor=VoidCamposIslas.crear({
 lienzo:N=>new OffscreenCanvas(N,N),presupuesto:12,
 entregar(id,canvas,lista){const bitmap=canvas.transferToImageBitmap();postMessage({id,bitmap,lista},[bitmap]);},
 error:()=>postMessage({error:true})
});
onmessage=({data:d})=>{
 if(d.tipo==='preparar')motor.preparar(d.id,d.lista,d.N);
 else if(d.tipo==='quitar')motor.quitar(d.id);
 else if(d.tipo==='pausa')motor.pausar(d.si);
};
