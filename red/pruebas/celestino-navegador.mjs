// Navegador real y API simulada: la entrada «Preguntar a Celestino» de Mi espacio y la apertura desde /mi-vault#celestino.
// No certifica la caja real. Ejecutar: node red/pruebas/celestino-navegador.mjs [carpeta-capturas]
import {createRequire} from 'node:module';
import {readFile} from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import assert from 'node:assert/strict';
const root=path.resolve(import.meta.dirname,'../..'),nube=process.env.VOID_NUBE_REPO||path.resolve(root,'../void-nube'),capturas=process.argv[2];
const {chromium}=createRequire(nube+'/pruebas/package.json')('playwright');
const server=http.createServer(async(req,res)=>{try{const u=new URL(req.url,'http://local'),p=path.resolve(root,'web','.'+(u.pathname==='/'?'/mi-vault.html':u.pathname));if(!p.startsWith(root+'/web/'))throw Error();const raw=await readFile(p);res.writeHead(200,{'content-type':p.endsWith('.js')?'text/javascript':p.endsWith('.css')?'text/css':p.endsWith('.svg')?'image/svg+xml':'text/html'});res.end(raw);}catch{res.writeHead(404);res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const url='http://127.0.0.1:'+server.address().port,browser=await chromium.launch({headless:true}),errores=[],preparados=[];
try{
 for(const [ancho,alto] of [[1440,1000],[390,844]]){
  const page=await browser.newPage({viewport:{width:ancho,height:alto}});page.on('pageerror',e=>errores.push(e.message));
  await page.route('https://**',r=>r.abort());
  await page.route('**/v1/web/**',async route=>{
   const req=route.request(),p=new URL(req.url()).pathname.replace('/v1/web/',''),b=req.postDataJSON();let d;
   if(p==='yo')d={alias:'prueba-celestino',listo:true,huella:null};
   else if(p==='candado')d={candado:true,abierto:true,despierta:true};
   else if(p==='agente/session')d=[];
   else if(p==='modelos')d={modelos:[],defecto:null};
   else if(p==='proveedores')d={proveedores:[]};
   else if(p==='comunidad/resumen')d={mensajes:0,plaza:0,oficial:0};
   else if(p==='islas/listar')d={islas:[],danadas:[],ocultas:[],ajustes:null};
   else if(p==='comunidad/bloqueos')d={bloqueos:[]};
   else if(p==='mensajeria/preparar'){preparados.push(b);d={para:b.para.replace('@',''),mensaje:{asunto:b.asunto,cuerpo:b.cuerpo,devuelve:b.devuelve},nonce:'n'};}
   else {await route.fulfill({status:404,json:{error:'Ruta simulada sin respuesta: '+p}});return;}
   await route.fulfill({json:d});
  });
  // Desde el perfil de @void: llega con #celestino y el mensaje ya está preparado.
  await page.goto(url+'/#celestino');
  await page.locator('#comunidad-mensaje').waitFor({state:'visible'});
  assert.equal(await page.locator('#comunidad').isVisible(),true);
  assert.equal(await page.inputValue('#comunidad-para'),'@void');
  assert.equal(await page.locator('#comunidad-para').getAttribute('readonly'),'');
  assert.equal(await page.inputValue('#comunidad-asunto'),'Pregunta para Celestino');
  assert.equal(await page.locator('#comunidad-mensaje-titulo').textContent(),'Pregúntale a Celestino');
  assert.equal(new URL(page.url()).hash,'','el #celestino no se queda para la próxima recarga');
  await page.waitForTimeout(1500);
  const caja=await page.locator('#comunidad-cuerpo').boundingBox();
  assert.ok(caja&&caja.y>=0&&caja.y+caja.height<=alto,'la pregunta queda a la vista a '+ancho+' px');
  assert.equal(await page.evaluate(()=>document.activeElement.id),'comunidad-cuerpo');
  if(capturas)await page.screenshot({path:path.join(capturas,`celestino-${ancho}.png`),fullPage:false});
  await page.fill('#comunidad-cuerpo','¿Esto es gratis?');
  await page.locator('#comunidad-mensaje button.principal').click();
  await page.locator('#comunidad-previa').waitFor({state:'visible'});
  assert.match(await page.locator('#comunidad-previa-destino').textContent(),/@void/);
  await page.locator('#comunidad-volver').click();
  // Un mensaje normal después no hereda nada de Celestino.
  await page.locator('#comunidad-cancelar-mensaje').click();
  await page.locator('#comunidad-escribir').click();
  assert.equal(await page.inputValue('#comunidad-para'),'');
  assert.equal(await page.locator('#comunidad-para').getAttribute('readonly'),null);
  assert.equal(await page.locator('#comunidad-cuerpo').getAttribute('placeholder'),'');
  // Y el botón de la propia Comunidad hace lo mismo.
  await page.locator('#comunidad-celestino').click();
  assert.equal(await page.inputValue('#comunidad-para'),'@void');
  const desborde=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
  assert.ok(desborde<=0,'sin scroll horizontal a '+ancho+' px');
  if(capturas)await page.locator('.comunidad-celestino').screenshot({path:path.join(capturas,`celestino-entrada-${ancho}.png`)});
  await page.close();
 }
 assert.equal(preparados.length,2);assert.equal(preparados[0].para,'@void');
 assert.deepEqual(errores,[]);
 console.log('✓ Preguntar a Celestino: desde #celestino y desde Comunidad, a 1440 y 390 px; el siguiente mensaje sale limpio.');
}finally{await browser.close();server.close();}
