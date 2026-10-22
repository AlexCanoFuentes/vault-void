// Navegador real y API simulada con datos inventados. No certifica la caja real.
// Ejecutar: node red/pruebas/islas-navegador.mjs
import {createRequire} from 'node:module';
import {readFile,writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import http from 'node:http';
import path from 'node:path';
import assert from 'node:assert/strict';
const root=path.resolve(import.meta.dirname,'../..'),nube=process.env.VOID_NUBE_REPO||path.resolve(root,'../void-nube');
const {chromium}=createRequire(nube+'/pruebas/package.json')('playwright');
const server=http.createServer(async(req,res)=>{try{const u=new URL(req.url,'http://local'),p=path.resolve(root,'web','.'+(u.pathname==='/'?'/mi-vault.html':u.pathname));if(!p.startsWith(root+'/web/'))throw Error();const raw=await readFile(p);res.writeHead(200,{'content-type':p.endsWith('.js')?'text/javascript':p.endsWith('.css')?'text/css':p.endsWith('.svg')?'image/svg+xml':'text/html'});res.end(raw);}catch{res.writeHead(404);res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const url='http://127.0.0.1:'+server.address().port,browser=await chromium.launch({headless:true});
let vaultIslas=[],ajustesDoc={},ajustesN=0,ajustadas=[];
let registros=[],guardados=[],borrados=[],danadas=[],listados=0,modo=null,falloGuardar=null,conflicto=false,retraso=0,alias='prueba-islas',despierta=true,abierto=true;
const errores=[],externas=[];
let page,publicacion='no-publicada',peticionesPublicas=[];
const cifrasPublicas={dias:240,pulso:50,decisiones:12,proyectos:4,calladas:0,tono:42};
const mundoPublico=()=>[{alias:'vecina',posicion:0,huella:cifrasPublicas},{alias,semilla:alias,posicion:7,huella:cifrasPublicas}];
const revision=isla=>createHash('sha256').update(JSON.stringify(isla)).digest('hex');
const validar=isla=>execFileSync('python3',['-c',`import importlib.util,json,sys
s=importlib.util.spec_from_file_location('islas',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.validar(json.load(sys.stdin))`,path.join(nube,'imagen/islas.py')],{input:JSON.stringify(isla)});
try{
 page=await browser.newPage({viewport:{width:1440,height:1000}});await page.addInitScript(()=>{window.trabajoMundo=0;const frame=requestAnimationFrame.bind(window);window.requestAnimationFrame=f=>frame(t=>{if(['mundo','quimica'].includes(f.name))window.trabajoMundo++;f(t);});});page.on('pageerror',e=>errores.push(e.message));page.on('request',r=>{if(!r.url().startsWith(url))externas.push(r.url());});
 await page.route('https://**',r=>r.abort());
 await page.route('https://red.vaultvoid.app/v1/huellas**',async route=>{
  const u=new URL(route.request().url());peticionesPublicas.push(u.searchParams.get('cursor'));
  if(publicacion==='error'){await route.fulfill({status:503,json:{error:'Red inventada sin conexión'}});return;}
  const lista=mundoPublico();await route.fulfill({json:publicacion==='publicada'?(u.searchParams.has('cursor')?{huellas:[lista[1]],siguiente:null}:{huellas:[lista[0]],siguiente:'segunda'}):{huellas:[lista[0]],siguiente:null}});
 });
 await page.route('**/v1/web/**',async route=>{
  const req=route.request(),u=new URL(req.url()),p=u.pathname.replace('/v1/web/',''),b=req.postDataJSON();let d;
  if(p==='yo')d={alias,listo:true,huella:null};
  else if(p==='candado'){if(b?.accion==='despertar')despierta=true;d={candado:true,abierto,despierta};}
  else if(p==='agente/session')d=[];
  else if(p==='modelos')d={modelos:[],defecto:null};
  else if(p==='proveedores')d={proveedores:[]};
  else if(p==='comunidad/resumen')d={mensajes:0,plaza:0,oficial:0};
  else if(p==='islas/listar'){
   assert.equal(req.method(),'GET');listados++;const vistas=vaultIslas.filter(v=>!ajustesDoc[v.isla.id]?.oculta).map(v=>({...v,isla:{...v.isla,...Object.fromEntries(Object.entries(ajustesDoc[v.isla.id]||{}).filter(([k])=>k!=='oculta'))}}));
   const snapshot=structuredClone({islas:[...registros,...vistas],danadas,ocultas:vaultIslas.filter(v=>ajustesDoc[v.isla.id]?.oculta).map(v=>({id:v.isla.id,nombre:v.isla.nombre,archivo:v.archivo})),ajustes:ajustesN?'a'.repeat(63)+ajustesN%10:null});
   if(retraso)await new Promise(r=>setTimeout(r,retraso));
   if(modo){await route.fulfill({status:modo.status,json:modo.d});return;}d=snapshot;
  }else if(p==='islas/guardar'){
   assert.equal(req.method(),'POST');validar(b.isla);
   if(falloGuardar){await route.fulfill({status:falloGuardar.status,json:falloGuardar.d});return;}
   const i=registros.findIndex(r=>r.isla.id===b.isla.id);
   if(conflicto){conflicto=false;if(i>=0){registros[i].isla.nombre='Cambio desde otra pestaña';registros[i].revision=revision(registros[i].isla);}await route.fulfill({status:409,json:{error:'La isla cambió. Recarga antes de guardar o borrar.'}});return;}
   assert.equal(b.revision,i<0?null:registros[i].revision,'revisión obsoleta');
   guardados.push(structuredClone(b));const r={isla:b.isla,revision:revision(b.isla)};if(i<0)registros.push(r);else registros[i]=r;
   d={guardado:true,revision:r.revision};
  }else if(p==='islas/ajustar'){
   assert.equal(req.method(),'POST');assert.deepEqual(Object.keys(b).sort(),['ajuste','id','revision']);assert.equal(b.revision,ajustesN?'a'.repeat(63)+ajustesN%10:null,'revisión de ajustes obsoleta');
   assert.ok(vaultIslas.some(v=>v.isla.id===b.id));ajustadas.push(structuredClone(b));ajustesDoc[b.id]={...(ajustesDoc[b.id]||{}),...b.ajuste};ajustesN++;d={ajustado:true,ajustes:'a'.repeat(63)+ajustesN%10};
  }else if(p==='islas/borrar'){
   const i=registros.findIndex(r=>r.isla.id===b.id);assert.ok(i>=0);assert.equal(b.revision,registros[i].revision);borrados.push(b);registros.splice(i,1);d={borrado:true};
  }else if(p==='salir')d={saliste:true};
  else if(p==='entrar')d={candado:'abierto'};
  else {await route.fulfill({status:404,json:{error:'Ruta simulada sin respuesta: '+p}});return;}
  await route.fulfill({json:d});
 });
 const cargada=async()=>{await page.waitForFunction(()=>!document.querySelector('#islas-vistas').hidden);await page.waitForFunction(()=>document.querySelector('#islas').getAttribute('aria-busy')==='false');};
 const guardada=async()=>{await page.waitForFunction(()=>document.querySelector('#islas-estado').textContent==='Isla guardada.');await page.waitForFunction(()=>document.querySelector('#islas').getAttribute('aria-busy')==='false');};
 const crear=async(tipo,nombre)=>{await page.locator('#islas-nueva').click();await page.locator('#islas-crear [name=nombre]').fill(nombre);await page.locator('#islas-crear [name=plantilla]').selectOption(tipo);await page.locator('#islas-crear-form button.principal').click();await page.locator('#islas-panel').waitFor({state:'visible'});await guardada();};
 const salirIsla=()=>page.locator('#islas-volver').click();
 const viajeTerminado=()=>page.waitForFunction(()=>!document.querySelector('#islas-mapa').classList.contains('islas-viajando'));
 const mundo=async()=>{await page.evaluate(()=>scrollTo(0,0));await page.waitForFunction(()=>document.body.classList.contains('plano-visible'));};
 const tinta=async loc=>{await loc.locator('canvas').waitFor();await loc.locator('canvas').evaluate(c=>new Promise(resolve=>{const mirar=()=>c.dataset.quimica==='lista'?resolve():setTimeout(mirar,50);mirar();}));return loc.evaluate(b=>{const c=b.querySelector('canvas'),r=b.getBoundingClientRect(),p=c.getContext('2d').getImageData(0,0,c.width,c.height).data;for(let d=0;d<c.width;d++)for(let x=0;x<c.width;x++){const y=Math.floor(c.height/2)+(d%2?-1:1)*Math.floor(d/2);if(y>=0&&y<c.height&&p[(y*c.width+x)*4+3]>32)return {x:r.x+(x+.5)/c.width*r.width,y:r.y+(y+.5)/c.height*r.height};}return {x:r.x+r.width/2,y:r.y+r.height/2};});};
 const tocar=async loc=>{await mundo();const p=await tinta(loc);await page.mouse.click(p.x,p.y);};
 const comprobarHUD=async nivel=>{
  assert.equal(await page.locator('#islas-mapa').getAttribute('data-nivel'),String(nivel));
  assert.equal(await page.locator('.islas-alejar').isVisible(),nivel===2,'Volver solo aparece al entrar; la selección usa su propia vuelta');
  assert.equal(await page.locator('.islas-juego-cerrar').isVisible(),nivel===3);
  const candado=page.locator('#estado-espacio-boton');
  assert.equal(await page.locator('#estado-espacio-detalle').isVisible(),false,'el aviso despierto está recogido');
  assert.match(await candado.getAttribute('aria-label'),/Candado abierto.*despierto/);
  const r=await page.locator('#estado-espacio').boundingBox();assert.ok(r.width<=48&&r.height<=48,'el candado solo ocupa un icono en el HUD');
  await candado.click();assert.equal(await candado.getAttribute('aria-expanded'),'true');
  assert.equal(await page.locator('#dormir-despertar').isVisible(),true);
  assert.match(await page.locator('#estado-espacio-detalle').innerText(),/Se guarda cada pocos minutos/);
  await page.keyboard.press('Escape');assert.equal(await candado.getAttribute('aria-expanded'),'false');
  assert.equal(await page.locator('#estado-espacio-detalle').isVisible(),false);
 };
 const abrirMapa=async selector=>{
  await tocar(page.locator(selector));
  const abrir=page.getByRole('group',{name:/^Opciones de /}).getByRole('button',{name:'Abrir',exact:true});
  const r=await abrir.boundingBox();
  // Ponemos la cabecera detrás del botón: el mundo debe seguir delante y recibir el clic.
  await page.evaluate(y=>scrollTo(0,innerHeight-y+8),r.y);await page.waitForTimeout(50);
  assert.equal(await abrir.evaluate(b=>{const r=b.getBoundingClientRect();return b.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));}),true,'la cabecera no intercepta Abrir');
  await abrir.click({timeout:3000});
 };
 await page.goto(url);await cargada();assert.equal(await page.locator('#islas-mapa canvas').count(),6,'plano, huella grande y un campo independiente por isla');
 assert.equal(await page.locator('#islas-mapa').getAttribute('data-nivel'),'1');
 await comprobarHUD(1);
 const grande=page.locator('.islas-huella-grande');
 assert.equal(await grande.locator('canvas').evaluate(c=>c.width>=512),true,'el campo grande tiene resolución propia');
 const gr=await grande.boundingBox();assert.ok(gr.width>300&&Math.abs(gr.y+gr.height/2-1000*.52)<2,'huella grande centrada');
 assert.equal(await page.getByRole('navigation',{name:'Menú de mi huella'}).isVisible(),true);
 assert.equal(await page.locator('.islas-juego-instalar').isHidden(),true,'no ofrece instalar sin oferta del navegador');
 for(const [nombre,zona] of [['Comunidad','comunidad'],['Mis cuentas','modelos']]){
  await page.getByRole('navigation',{name:'Menú de mi huella'}).getByRole('button',{name:nombre,exact:true}).click();assert.equal(await page.locator('#'+zona).isVisible(),true);await mundo();
 }
 await page.evaluate(()=>{const e=new Event('beforeinstallprompt');e.prompt=async()=>{window.instalacionProbada=true;};e.userChoice=Promise.resolve({outcome:'dismissed'});dispatchEvent(e);});
 await page.locator('.islas-juego-instalar button').click();
 assert.equal(await page.evaluate(()=>window.instalacionProbada),true);await page.locator('.islas-juego-instalar').waitFor({state:'hidden'});await mundo();
 assert.equal(await page.locator('#islas-etiquetas').evaluate(e=>getComputedStyle(e).visibility),'hidden','de lejos, las islas no se tocan');
 await page.locator('.islas-acercar').focus();await page.keyboard.press('Enter');
 assert.equal(await page.locator('#islas-mapa').getAttribute('data-nivel'),'2');
 assert.equal(await page.locator('.islas-alejar').evaluate(e=>e===document.activeElement),true,'el foco viaja a la vuelta');
 assert.equal(await page.locator('#islas-mapa').evaluate(e=>e.classList.contains('islas-viajando')),true);
 assert.ok(await page.locator('.islas-huella-grande').evaluate(e=>Math.max(...getComputedStyle(e).transitionDuration.split(',').map(parseFloat))<1),'el viaje visual dura menos de un segundo');
 await viajeTerminado();assert.equal(await page.locator('#islas-etiquetas').evaluate(e=>getComputedStyle(e).visibility),'visible');
 await comprobarHUD(2);
 await page.locator('.islas-alejar').click();await page.waitForTimeout(700);await tocar(page.locator('.islas-lejos'));await viajeTerminado();assert.equal(await page.locator('#islas-mapa').evaluate(e=>e.classList.contains('de-cerca')),true,'tocar la huella acerca');
 await page.locator('#islas-mapa').dispatchEvent('wheel',{ctrlKey:true,deltaY:120});assert.equal(await page.locator('#islas-mapa').getAttribute('data-nivel'),'1');
 await page.locator('#islas-mapa').dispatchEvent('wheel',{ctrlKey:true,deltaY:-120});await viajeTerminado();assert.equal(await page.locator('#islas-mapa').getAttribute('data-nivel'),'2','conserva el zoom con Ctrl y rueda');
 for(const [id,zona] of [['fija_hablar','hablar'],['fija_comunidad','comunidad'],['fija_modelos','modelos'],['fija_cuidar','cuidar']]){
  await abrirMapa(`#islas-etiquetas [data-id=${id}]`);assert.equal(await page.locator('#'+zona).isVisible(),true);assert.equal(await page.locator('.zona').count(),5);await mundo();await page.locator('.islas-juego-cerrar').click();
 }
 console.log('✓ Los dos niveles, viaje menor de un segundo, vuelta con foco, oferta de instalación y menús hacia las secciones existentes.');
 await crear('semana@1','Mi semana');
 await page.locator('[name=nueva-0]').fill('Pasear un rato');await page.getByRole('button',{name:'Añadir tarea',exact:true}).click();await guardada();
 await page.locator('[name=hecho-0-0]').check();await guardada();assert.equal(registros[0].isla.bloques[0].items[0].hecho,true);
 await page.locator('[name=tarea-0-0]').fill('Pasear y descansar');await page.locator('[name=tarea-0-0]').press('Tab');await guardada();
 await page.locator('[name=nota-1]').fill('Texto privado con tildes: árbol, montaña.');await page.locator('[name=nota-1]').press('Tab');await guardada();
 for(const forma of ['montaña','atolón','archipiélago','alargada','redonda']){await page.locator('[name=forma]').selectOption(forma);await guardada();assert.equal(registros[0].isla.forma,forma);}
 for(const estilo of ['sobria','serena','viva']){await page.locator('[name=estilo]').selectOption(estilo);await guardada();}
 await page.locator('[name=color]').fill('#c9784e');await page.locator('[name=color]').dispatchEvent('change');await guardada();
 assert.equal(await page.getByRole('button',{name:'Publicar como estrella · pronto',exact:true}).isDisabled(),true);
 await salirIsla();
 await crear('proyecto@1','Mi proyecto');await page.getByRole('button',{name:'Sumar uno',exact:true}).click();await guardada();assert.equal(registros[1].isla.bloques[1].valor,1);await salirIsla();
 await crear('notas@1','Mis notas');await salirIsla();
 assert.deepEqual(new Set(guardados.filter(b=>b.revision===null).map(b=>b.isla.plantilla)),new Set(['semana@1','proyecto@1','notas@1']));
 console.log('✓ Tres plantillas válidas contra validar() de Python; tareas, notas, contador, formas, estilos y color guardados con revisión.');
 // [21-oct] Por defecto, huellas: un campo del motor del lienzo y una etiqueta por isla que la abre. Las islas en 3D se piden.
 assert.equal(await page.locator('#islas-mapa canvas.islas-huellas').count(),1,'una huella fusionada');
 assert.equal(await page.locator('#islas-mapa canvas.islas-huella-pequena').count(),7,'un campo con detalle por isla');
 assert.equal(await page.locator('.islas-huella-pequena').evaluateAll(cs=>cs.every(c=>c.width>=192&&c.height>=192)),true);
 assert.equal(await page.locator('#islas-etiquetas .islas-huella-etiqueta').count(),7,'una etiqueta por isla, fijas incluidas');
 assert.equal(externas.filter(u=>u.includes('three')).length,0);assert.equal(await page.evaluate(()=>!!window.THREE),false,'three.js no se carga si no se pide');
 assert.equal(await page.locator('#islas-vista-boton').isVisible(),false,'sin vista 3D por ahora');
 console.log('✓ Huellas por defecto, sin three.js y sin botón de vista 3D.');
 // [21-oct] Arrastrar huellas, suponiendo que alguien lo hace mal a propósito.
 const id=registros[0].isla.id,nodo=page.locator(`#islas-etiquetas [data-id="${id}"]`),pos=structuredClone(registros[0].isla.posicion);
 let previos=guardados.length;await nodo.focus();for(let k=0;k<5;k++)await nodo.press('ArrowRight');await guardada();await page.waitForTimeout(600);
 assert.equal(guardados.length,previos+1,'cinco flechas seguidas guardan una sola vez');assert.notEqual(registros[0].isla.posicion.x,pos.x);
 const caja=await page.locator('#islas-mapa').boundingBox(),mover=async(dx,dy)=>{const b=await tinta(nodo);await page.mouse.move(b.x,b.y);await page.mouse.down();await page.mouse.move(b.x+dx,b.y+dy,{steps:8});await page.mouse.up();};
 previos=guardados.length;await mover(-25,10);await guardada();assert.equal(guardados.length,previos+1);assert.equal(await page.locator('#islas-panel').isVisible(),false,'arrastrar no abre la isla');
 previos=guardados.length;const b0=await tinta(nodo);await page.mouse.move(b0.x,b0.y);await page.mouse.down();await page.mouse.move(caja.x+caja.width+400,caja.y-300,{steps:8});await page.mouse.up();await page.waitForTimeout(500);
 assert.equal(guardados.length,previos,'soltar fuera del recuadro no guarda');
 const fija=await page.locator('#islas-etiquetas [data-id="fija_hablar"]').boundingBox(),b1=await nodo.boundingBox();
 await mover(fija.x+fija.width/2-(b1.x+b1.width/2),fija.y+fija.height/2-(b1.y+b1.height/2));await guardada();
 const p2=registros[0].isla.posicion;assert.ok(Math.hypot(p2.x-.18,p2.y-.2)>=.11,'no se queda encima de otra huella');assert.ok(p2.x>=.08&&p2.x<=.92&&p2.y>=.08&&p2.y<=.92);
 previos=guardados.length;const f0=await page.locator('#islas-etiquetas [data-id="fija_hablar"]').boundingBox();await page.mouse.move(f0.x+f0.width/2,f0.y+f0.height/2);await page.mouse.down();await page.mouse.move(f0.x+120,f0.y+120,{steps:8});await page.mouse.up();await page.waitForTimeout(500);
 assert.equal(guardados.length,previos,'una isla fija no se mueve ni guarda');if(await page.locator('#islas-panel').isVisible())await salirIsla();
 previos=guardados.length;await nodo.focus();await page.keyboard.press('Enter');await page.locator('.islas-menu-isla').waitFor({state:'visible'});
 assert.equal(await page.getByRole('button',{name:'Esconder',exact:true}).count(),0,'las propias no se esconden');
 assert.equal(await page.locator('.islas-menu-isla button').first().evaluate(e=>e===document.activeElement),true);
 await page.getByRole('button',{name:'Mover',exact:true}).click();assert.equal(await nodo.evaluate(e=>e===document.activeElement),true,'Mover enfoca la isla');
 await page.keyboard.press('Escape');await abrirMapa(`#islas-etiquetas [data-id="${id}"]`);await page.locator('#islas-panel').waitFor({state:'visible'});assert.equal(guardados.length,previos,'un toque abre las opciones sin mover; Abrir lleva al panel');await salirIsla();
 // Cancelar un gesto no guarda ni abre, y el fondo tiene parallax sin recalcular la química.
 previos=guardados.length;
 await nodo.dispatchEvent('pointerdown',{button:0,pointerId:99,clientX:100,clientY:100});
 await nodo.dispatchEvent('pointercancel',{pointerId:99,clientX:160,clientY:140});assert.equal(guardados.length,previos);
 await page.keyboard.press('Escape');await page.locator('#islas-mapa').scrollIntoViewIfNeeded();
 // [22-oct, Claude] Abajo vive el menú anclado: el fondo se arrastra desde un punto libre del mundo, buscado, no supuesto.
 const vacio=await page.evaluate(()=>{for(let y=innerHeight*.3;y<innerHeight*.8;y+=20)for(let x=innerWidth*.2;x<innerWidth*.8;x+=20){const e=document.elementFromPoint(x,y);if(e&&e.id==='islas-mapa')return {x,y};}return null;});assert.ok(vacio,'hay fondo libre para arrastrar');
 await page.mouse.move(vacio.x,vacio.y);await page.mouse.down();await page.mouse.move(vacio.x+140,vacio.y+20,{steps:5});await page.mouse.up();await page.waitForTimeout(30);
 assert.notEqual(await nodo.evaluate(e=>e.style.getPropertyValue('--par-x')),'0px','arrastrar el fondo cambia la profundidad');
 console.log('✓ Arrastrar huellas: un toque no mueve, soltar fuera no guarda, encima de otra se aparta, las flechas guardan una vez, las fijas no se mueven.');
 await page.locator('#islas-lista-boton').click();assert.equal(await page.locator('#islas-lista li').count(),7);
 const semana=page.locator(`#islas-lista [data-id="${id}"]`);await semana.focus();await page.keyboard.press('Enter');await page.locator('#islas-panel').waitFor({state:'visible'});
 await page.getByRole('button',{name:'Borrar isla',exact:true}).click();await page.keyboard.press('Escape');assert.equal(borrados.length,0);
 await page.getByRole('button',{name:'Borrar isla',exact:true}).click();await page.locator('#islas-borrar-si').click();await page.locator('#islas-confirmar').waitFor({state:'hidden'});assert.equal(borrados.length,1);
 console.log('✓ Arrastre, flechas, lista con teclado y borrado solo tras confirmación.');
 // Conflicto de revisión: releer, mostrar versión vigente y avisar, sin reintento ciego.
 await page.locator(`#islas-lista [data-id="${registros[0].isla.id}"]`).click();conflicto=true;const antes=listados;
 await page.locator('#islas-panel [name=nombre]').fill('No debe pisar');await page.locator('#islas-panel [name=nombre]').press('Tab');await page.waitForFunction(()=>document.querySelector('#islas-estado').textContent.includes('Hemos recargado'));
 assert.ok(listados>antes);assert.equal(await page.locator('#islas-panel [name=nombre]').inputValue(),'Cambio desde otra pestaña');await salirIsla();
 // Isla dañada: las buenas permanecen. El contenido recibido nunca se interpreta como HTML.
 danadas=[{archivo:'rota-<img src=x>.json',error:'Texto no válido.'}];await page.locator('#islas-recargar').click();await cargada();assert.match(await page.locator('#islas-danadas').textContent(),/Hay una isla que no se puede leer: rota-<img src=x>.json/);assert.equal(await page.locator('#islas-danadas img').count(),0);
 console.log('✓ Conflicto recarga y avisa; una isla dañada no esconde las demás ni inyecta HTML.');
 // Mapas y lista a todos los tamaños, también con 40 islas propias.
 const modelo=structuredClone(registros[0].isla);registros=Array.from({length:40},(_,i)=>{const isla={...structuredClone(modelo),id:'prueba-'+i,nombre:'Isla '+i+' · '+ 'á'.repeat(60)};return {isla,revision:revision(isla)};});danadas=[];
 await page.locator('#islas-recargar').click();await cargada();assert.equal(await page.locator('#islas-lista li').count(),44);assert.equal(await page.locator('#islas-nueva').isDisabled(),true);
 for(const width of [320,360,412,699,700,1024,1440]){
  await page.setViewportSize({width,height:1000});
  for(const vista of ['lista','mapa']){
   const esLista=await page.locator('#islas-lista-boton').getAttribute('aria-pressed')==='true';if(esLista!==(vista==='lista'))await page.locator('#islas-lista-boton').click();
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`desbordamiento ${width} ${vista}`);
   if(vista==='mapa'){
    await page.locator('.islas-alejar').click();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`desbordamiento ${width} nivel 1`);
    await comprobarHUD(1);
    await page.locator('.islas-acercar').click();await viajeTerminado();
    await comprobarHUD(2);
    const paginador=await page.locator('#islas-paginas').boundingBox();assert.ok(paginador.y<130&&paginador.height<=48&&paginador.width<=140,'flechas pequeñas en el HUD, fuera del mundo');
    assert.deepEqual(await page.locator('#islas-paginas button').allTextContents(),['‹','›']);
    const carteles=await page.locator('.islas-juego-isla').evaluateAll(bs=>bs.map(b=>{const r=b.getBoundingClientRect(),n=b.querySelector('span'),t=n.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:t.bottom-r.y,visible:getComputedStyle(b).visibility,nombre:getComputedStyle(n).whiteSpace};}));
    for(let i=0;i<carteles.length;i++){
     const a=carteles[i];assert.equal(a.visible,'visible');assert.equal(a.nombre,'nowrap');assert.ok(a.w>=44&&a.y>130&&a.y+a.h<900,'huella completa entre los mandos');
     for(const b of carteles.slice(i+1))assert.ok(a.x+a.w<=b.x||b.x+b.w<=a.x||a.y+a.h<=b.y||b.y+b.h<=a.y,'huellas y nombres separados');
    }
   }
  }
 }
 await page.getByRole('button',{name:'Página siguiente',exact:true}).click();assert.equal(await page.locator('#islas-etiquetas button').count(),8);
 // Pixel 7, ocho islas con nombres largos, selección y clic nativo sobre Abrir.
 await page.setViewportSize({width:412,height:915});await mundo();await page.waitForFunction(()=>[...document.querySelectorAll('.islas-huella-pequena')].every(c=>c.dataset.quimica==='lista'));
 assert.equal(await page.locator('.islas-huella-pequena').evaluateAll(cs=>cs.every(c=>{const p=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let tinta=0;for(let i=0;i<p.length;i+=4)if(p[i+3]>32)tinta++;return tinta>500;})),true,'cada isla tiene huella visible');
 const seleccion=page.locator('.islas-juego-isla').first();await tocar(seleccion);await comprobarHUD(3);
 await page.waitForTimeout(450);
 assert.equal(await page.locator('.islas-juego-isla').evaluateAll(bs=>bs.every(b=>b.getAttribute('aria-pressed')==='true'?getComputedStyle(b.querySelector('canvas')).filter==='brightness(1.8)':Number(getComputedStyle(b).opacity)<.5)),true,'la elegida se ilumina y las demás se atenúan');
 await page.screenshot({path:'/tmp/m15-seleccion-pixel.png'});
 await page.locator('.islas-juego-cerrar').click();
 await abrirMapa('.islas-juego-isla:first-child');await page.locator('#islas-panel').waitFor({state:'visible'});await salirIsla();
 await page.locator('.islas-juego-cerrar').click();
 await page.setViewportSize({width:1440,height:1000});
 await page.emulateMedia({reducedMotion:'reduce'});await page.locator('#islas-lista-boton').click();await page.locator('#islas-lista-boton').click();await page.waitForTimeout(300);
 await page.locator('.islas-alejar').click();await page.locator('.islas-acercar').click();assert.equal(await page.locator('#islas-mapa').evaluate(e=>e.classList.contains('islas-viajando')),false,'reducir movimiento cambia directamente');
 await mundo();await page.waitForFunction(()=>[...document.querySelectorAll('#islas-mapa canvas:not(.islas-plano)')].every(c=>c.dataset.quimica==='lista'));
 const agua=await page.locator('#islas-mapa').screenshot();await page.waitForTimeout(120);assert.deepEqual(await page.locator('#islas-mapa').screenshot(),agua);
 await page.screenshot({path:'/tmp/m09-islas-1440.png',fullPage:true});
 // Si falla el juego se recupera la vista anterior, y si falla también el motor queda la lista.
 await page.evaluate(()=>{window.VoidJuegoIslas=()=>{throw Error('Fallo inventado del juego');};});await page.locator('#islas-lista-boton').click();await page.locator('#islas-lista-boton').click();
 assert.equal(await page.locator('#islas-mapa.vista-huellas').count(),1);assert.equal(await page.locator('#islas-mapa canvas').count(),2,'vuelve a la vista anterior');
 await page.evaluate(()=>{window.VoidHuella=undefined;});await page.locator('#islas-lista-boton').click();await page.locator('#islas-lista-boton').click();
 assert.equal(await page.locator('#islas-lista').isVisible(),true);assert.match(await page.locator('#islas-estado').textContent(),/lista/);
 console.log('✓ 320 a 1440 px, 40 islas, paginación, movimiento reducido y sin motor de huellas.');
 for(const error of [{status:503,d:{error:'Puente no disponible.'}},{status:409,d:{dormida:true}},{status:423,d:{error:'Candado cerrado.'}}]){
  modo=error;await page.reload();await page.waitForFunction(()=>!document.querySelector('#islas-recargar').hidden||document.querySelector('#islas-estado').textContent.includes('candado está cerrado')||document.querySelector('#islas-estado').textContent.includes('espacio está dormido'));
  assert.equal(await page.locator('#hablar').isVisible(),true);assert.equal(await page.locator('.zonas').isVisible(),true);assert.equal(await page.locator('#islas-vistas').isVisible(),false);
 }
 modo=null;abierto=false;despierta=false;await page.reload();await page.waitForFunction(()=>document.querySelector('#estado-espacio').dataset.estado==='cerrado');
 assert.equal(await page.locator('#estado-espacio-detalle').isVisible(),true,'el candado cerrado conserva su aviso');assert.match(await page.locator('#estado-espacio-texto').innerText(),/Ábrelo/);
 abierto=true;despierta=false;const sinListar=listados;await page.reload();await page.waitForFunction(()=>document.querySelector('#islas-estado').textContent.includes('espacio está dormido'));assert.equal(listados,sinListar);
 assert.equal(await page.locator('#estado-espacio-detalle').isVisible(),true,'la caja dormida conserva la acción visible');assert.match(await page.locator('#estado-espacio-texto').innerText(),/Despiértalo/);
 await page.locator('#dormir-despertar').click();await cargada();
 console.log('✓ Puente ausente, 409 dormida, 423 y despertar conservan el espacio anterior.');
 // Error de escritura conserva el borrador para reintentar. Un cierre durante escritura retira los datos.
 await page.locator('#islas-lista-boton').click();await page.locator('#islas-lista button').first().click();falloGuardar={status:503,d:{error:'Sin puente.'}};
 await page.locator('#islas-panel [name=nombre]').fill('Borrador conservado');await page.locator('#islas-panel [name=nombre]').press('Tab');await page.waitForFunction(()=>document.querySelector('#islas-estado').textContent.includes('no se ha confirmado'));assert.equal(await page.locator('#islas-panel [name=nombre]').inputValue(),'Borrador conservado');falloGuardar=null;
 await page.getByRole('button',{name:'Guardar cambios',exact:true}).click();await guardada();await salirIsla();
 // Una lectura tardía de la cuenta anterior nunca aparece después de salir y entrar con otra.
 retraso=400;await page.locator('#islas-recargar').click();await page.locator('#salir').click();alias='otra-persona';registros=[];
 await page.locator('#alias').fill(alias);await page.locator('#codigo').fill('vr_'+'a'.repeat(64));await page.locator('#entrar-boton').click();await cargada();await page.waitForTimeout(450);assert.equal(await page.locator('#islas-lista li').count(),4);
 assert.equal(await page.evaluate(()=>Object.keys(localStorage).some(k=>/^(void-islas|void-archipielago)/i.test(k))),false);
 // Vendor: ningún recurso de three se pide fuera del mismo origen.
 assert.ok(!externas.some(u=>/three|cdnjs|unpkg|jsdelivr/i.test(u)));assert.deepEqual(errores,[]);
 await writeFile('/tmp/m09-islas-guardados.json',JSON.stringify(guardados,null,2));
 console.log('✓ Reintento conserva el borrador; salida descarta lecturas tardías; sin contenido en localStorage ni three.js externo.');
 // [21-oct, fase 1b] Islas que salen del vault: se ven, no se editan sus tareas, se renombran y se esconden por ajustes.
 vaultIslas=[{isla:{formato:1,id:'v-0123456789ab',nombre:'Huerto inventado',icono:'',color:'#5BE06A',forma:'redonda',estilo:'viva',publica:false,plantilla:'proyecto@1',posicion:{x:.5,y:.45},bloques:[{id:'nota',tipo:'nota',titulo:'De tu vault',texto:'Objetivo: Tomates en verano'},{id:'tareas',tipo:'tareas',titulo:'Tareas',items:[{texto:'Comprar macetas',hecho:false}]}]},revision:null,origen:'vault',archivo:'proyectos/huerto.md'}];
 await page.reload();await cargada();await mundo();await page.locator('.islas-acercar').click();await viajeTerminado();
 const huerto=page.locator('#islas-etiquetas [data-id="v-0123456789ab"]');await tocar(huerto);
 assert.equal(await page.getByRole('button',{name:'Esconder',exact:true}).isVisible(),true);
 await page.getByRole('button',{name:'Mover',exact:true}).click();await huerto.press('ArrowRight');
 await page.waitForFunction(()=>document.querySelector('#islas-estado').textContent==='Cambio guardado.');
 assert.ok(ajustadas.at(-1).ajuste.posicion,'Mover una isla del vault usa ajustar');
 await tocar(huerto);await page.getByRole('button',{name:'Esconder',exact:true}).click();await page.locator('#islas-ocultas').waitFor({state:'visible'});
 await page.getByRole('button',{name:'Mostrar «Huerto inventado»',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#islas-ocultas').hidden);
 await page.locator('#islas-recargar').click();await page.waitForFunction(()=>document.querySelector('#islas-estado').textContent.includes('privadas'));
 if(await page.locator('#islas-lista').isHidden())await page.locator('#islas-lista-boton').click();
 assert.match(await page.locator('#islas-lista [data-id="v-0123456789ab"]').innerText(),/De tu vault/);
 await page.locator('#islas-lista [data-id="v-0123456789ab"]').click();await page.locator('#islas-panel').waitFor({state:'visible'});
 assert.match(await page.locator('#islas-panel').innerText(),/Sale de tu vault: proyectos\/huerto\.md/);assert.equal(await page.locator('#islas-panel input[type=checkbox]').first().isDisabled(),true,'las tareas del vault no se tocan aquí');
 assert.equal(await page.getByRole('button',{name:'Borrar isla',exact:true}).count(),0,'una isla del vault no se borra: se esconde');
 await page.locator('#islas-panel [name=nombre]').fill('Mi huerto');await page.locator('#islas-panel [name=nombre]').press('Tab');await page.waitForFunction(()=>document.querySelector('#islas-estado').textContent.includes('Cambio guardado'));
 assert.equal(ajustadas.at(-1).ajuste.nombre,'Mi huerto');assert.equal(guardados.filter(g=>g.isla?.id==='v-0123456789ab').length,0,'nunca se guarda como isla propia');
 await page.getByRole('button',{name:'Esconder del mapa',exact:true}).click();await page.locator('#islas-ocultas').waitFor({state:'visible'});
 assert.match(await page.locator('#islas-ocultas').innerText(),/Mi huerto/);
 await page.getByRole('button',{name:'Mostrar «Mi huerto»',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#islas-ocultas').hidden);
 assert.equal(ajustadas.at(-1).ajuste.oculta,false);
 assert.deepEqual(errores,[],'sin errores de navegador también tras los menús del vault');
 console.log('✓ Islas del vault: tareas de solo lectura con su fichero, renombrar y esconder por ajustes, nunca se guardan como propias.');
 // M-15: publicación paginada, no publicada y red caída son estados distintos.
 registros=[];vaultIslas=[];danadas=[];ajustesDoc={};await page.setViewportSize({width:412,height:915});
 for(const estado of ['publicada','no-publicada','error']){
  publicacion=estado;peticionesPublicas=[];await page.reload();await cargada();await mundo();
  await page.waitForFunction(e=>document.querySelector('#islas-mapa').dataset.publicacion===e,estado);
  if(estado==='publicada')assert.deepEqual(peticionesPublicas,[null,'segunda']);
  if(estado!=='error'){
   const o=JSON.parse(await page.locator('#islas-mapa').getAttribute('data-origen')),r=330*Math.sqrt(7),a=7*2.399963229728653;
   assert.ok(estado==='publicada'?Math.hypot(o.x-r*Math.cos(a),o.y-r*Math.sin(a))<1e-7:o.x===0&&o.y===0,'misma espiral que la portada');
  }
  await page.screenshot({path:'/tmp/m15-mi-espacio-'+estado+'-pixel.png'});
  const geometria=await page.evaluate(()=>{
   const cv=document.querySelector('.islas-plano'),r=document.querySelector('#islas-mapa').getBoundingClientRect(),css=getComputedStyle(document.querySelector('#islas-mapa'));
   const v={x:61,y:-33,s:1.4},p=VoidPlano.crear(v,innerWidth,innerHeight),pt={x:150,y:80},u=p.proyectar(pt.x,pt.y),q=p.inversa(u.x,u.y);
   const ancla=p.inversa(innerWidth*.6,innerHeight*.6);p.zoom(1.7,innerWidth*.6,innerHeight*.6);const despues=p.inversa(innerWidth*.6,innerHeight*.6);
   return {r:{x:r.x,y:r.y,w:r.width,h:r.height},W:innerWidth,H:innerHeight,borde:css.borderTopWidth,radio:css.borderRadius,position:css.position,dpr:cv.width/innerWidth,error:Math.hypot(q.x-pt.x,q.y-pt.y),zoom:Math.hypot(ancla.x-despues.x,ancla.y-despues.y),horizonte:p.inversa(0,-10000)};
  });
  assert.deepEqual(geometria.r,{x:0,y:0,w:geometria.W,h:geometria.H});assert.equal(geometria.borde,'0px');assert.equal(geometria.radio,'0px');assert.equal(geometria.position,'fixed');assert.ok(geometria.dpr<=2&&geometria.dpr>=1);assert.ok(geometria.error<1e-7&&geometria.zoom<1e-7);assert.equal(geometria.horizonte,null);
  const menu=await page.locator('.islas-menu-entrada').boundingBox();assert.ok(menu.y>geometria.H*.7);
  await page.locator('.islas-mas').click();assert.equal(await page.locator('#islas-titulo').evaluate(e=>e===document.activeElement),true);await page.waitForFunction(()=>!document.body.classList.contains('plano-visible'));
  assert.equal(await page.locator('.zonas').isVisible(),true);await page.waitForTimeout(100);let trabajo=await page.evaluate(()=>trabajoMundo);await page.waitForTimeout(180);assert.equal(await page.evaluate(()=>trabajoMundo),trabajo,'ningún fotograma del mundo fuera de la zona inicial');await mundo();
  await page.waitForFunction(()=>document.querySelector('#islas-mapa').dataset.trabajando==='false');const camara=await page.locator('#islas-mapa').getAttribute('data-camara');
  await page.locator('.islas-acercar').click();await viajeTerminado();assert.equal(await page.locator('#islas-mapa').evaluate(e=>[...e.querySelectorAll('canvas,button')].every(n=>!getComputedStyle(n).filter.includes('blur'))),true);
  await page.waitForFunction(()=>document.querySelector('#islas-mapa').dataset.trabajando==='false');
  await page.screenshot({path:'/tmp/m15-mis-islas-'+estado+'-pixel.png'});
  await page.evaluate(()=>document.querySelector('#islas-crear').showModal());await page.waitForTimeout(80);trabajo=await page.evaluate(()=>trabajoMundo);await page.waitForTimeout(180);assert.equal(await page.evaluate(()=>trabajoMundo),trabajo,'sin bucle con un diálogo');await page.locator('#islas-cancelar-crear').click();
  await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'));});await page.waitForTimeout(80);trabajo=await page.evaluate(()=>trabajoMundo);await page.waitForTimeout(180);assert.equal(await page.evaluate(()=>trabajoMundo),trabajo,'sin bucle con la pestaña oculta');await page.evaluate(()=>{delete document.hidden;document.dispatchEvent(new Event('visibilitychange'));});
  await page.locator('.islas-alejar').click();await page.waitForFunction(c=>document.querySelector('#islas-mapa').dataset.camara===c,camara);
 }
 // Bordes, máscara transparente y solapes se resuelven por el cartel más cercano.
 assert.equal(await page.evaluate(()=>{
  const m={w:2,h:2,datos:new Uint8ClampedArray(16)};m.datos[3]=255;
  const lejos={x:10,y:10,w:100,h:100,z:20,id:'lejos'},cerca={...lejos,z:-2,id:'cerca',mascara:m};
  return VoidPlano.tocar([lejos,cerca],10,10).id==='cerca'&&VoidPlano.tocar([lejos,cerca],90,90).id==='lejos'&&!VoidPlano.tocar([lejos],110,50)&&!VoidPlano.tocar([lejos],9.9,50);
 }),true);
 // Al cerrar el candado se retiran también los buffers, no solo los nodos.
 const modeloPrivado=structuredClone(modelo);modeloPrivado.id='prueba-privada';registros=[{isla:modeloPrivado,revision:revision(modeloPrivado)}];publicacion='no-publicada';await page.reload();await cargada();
 await page.evaluate(()=>{window.buffersRetirados=[...document.querySelectorAll('.islas-huella-pequena,.islas-huellas')];});abierto=false;await page.evaluate(()=>dispatchEvent(new CustomEvent('void-estado-espacio',{detail:{candado:true,abierto:false,despierta:true}})));
 assert.equal(await page.evaluate(()=>buffersRetirados.every(c=>c.width===0&&c.height===0&&!c._mascara)),true);assert.equal(await page.locator('.islas-zona-inicial').count(),0);abierto=true;
 // Portada: la llave no cambia la ruta pública normal. Con ella la ficha usa el cartel.
 const portada=await browser.newPage({viewport:{width:412,height:915},deviceScaleFactor:2,isMobile:true,hasTouch:true});portada.on('pageerror',e=>errores.push(e.message));await portada.route('https://**',r=>r.abort());await portada.route('https://red.vaultvoid.app/v1/huellas**',r=>r.fulfill({json:{huellas:mundoPublico(),siguiente:null}}));
 await portada.addInitScript(()=>localStorage.setItem('void-historia-v1','1'));
 await portada.goto(url+'/index.html');await portada.locator('#lista-huellas button').first().waitFor({state:'attached'});assert.equal(await portada.locator('#lienzo').getAttribute('data-plano'),null,'la portada normal conserva la rama plana');
 await portada.goto(url+'/index.html?plano');await portada.locator('#lista-huellas button').first().waitFor({state:'attached'});await portada.locator('.mandos summary').click();await portada.locator('#encuadrar').click();await portada.locator('.mandos summary').click();await portada.waitForFunction(()=>document.querySelector('#lienzo').dataset.quimica==='lista');
 const toque=await portada.evaluate(lista=>{
  const cv=document.querySelector('#lienzo'),v=JSON.parse(cv.dataset.camara),plano=VoidPlano.crear(v,innerWidth,innerHeight),ts=VoidVacio.crear(lista,{plano:true}).territorios,ctx=cv.getContext('2d'),dpr=cv.width/innerWidth;
  for(const t of ts){const r=plano.cartel(t);if(!r)continue;for(let y=Math.max(80,Math.ceil(r.y));y<Math.min(innerHeight,r.y+r.h);y++)for(let x=Math.max(0,Math.ceil(r.x));x<Math.min(innerWidth,r.x+r.w);x++){
   if(document.elementFromPoint(x,y)!==cv)continue;const p=ctx.getImageData(Math.floor(x*dpr),Math.floor(y*dpr),1,1).data;
   if(Math.max(p[0],p[1],p[2])>95)return {x,y,alias:t.alias};
  }}return null;
 },mundoPublico());assert.ok(toque,'hay tinta visible y tocable en un cartel');await portada.mouse.click(toque.x,toque.y);await portada.locator('#ficha').waitFor({state:'visible'});assert.match(await portada.locator('#f-alias').textContent(),new RegExp('@'+toque.alias));await portada.locator('#f-cerrar').click();
 const cv=portada.locator('#lienzo'),centro={x:206,y:520};
 const ancla=await portada.evaluate(p=>{const c=document.querySelector('#lienzo');return VoidPlano.crear(JSON.parse(c.dataset.camara),innerWidth,innerHeight).inversa(p.x,p.y);},centro);
 await cv.dispatchEvent('wheel',{clientX:centro.x,clientY:centro.y,deltaY:-120});await portada.waitForTimeout(50);
 const ancla2=await portada.evaluate(p=>VoidPlano.crear(JSON.parse(document.querySelector('#lienzo').dataset.camara),innerWidth,innerHeight).inversa(p.x,p.y),centro);assert.ok(Math.hypot(ancla.x-ancla2.x,ancla.y-ancla2.y)<1e-6,'la rueda conserva el centro en el plano');
 const tactil=await portada.context().newCDPSession(portada);
 await tactil.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:180,y:520,id:31},{x:232,y:520,id:32}]});await tactil.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:164,y:520,id:31},{x:248,y:520,id:32}]});await tactil.send('Input.dispatchTouchEvent',{type:'touchCancel',touchPoints:[]});await tactil.detach();
 assert.equal(await portada.locator('#ficha').isHidden(),true,'cancelar el pellizco no abre una ficha');
 assert.ok(await portada.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await portada.screenshot({path:'/tmp/m15-portada-pixel.png'});
 await portada.goto(url+'/index.html?plano&historia');await portada.locator('dialog.vh').waitFor({state:'visible'});await portada.locator('dialog.vh[open]').waitFor({state:'hidden',timeout:20000});assert.equal(await portada.locator('#lienzo').getAttribute('data-plano'),'true');
 await portada.close();
 assert.deepEqual(errores,[]);console.log('✓ M-15: lienzo paginado, identidad, fallo de red, proyección inversa, zoom, bordes y máscara, mundo completo, Más, nitidez y destrucción privada.');
 console.log(`${guardados.length} guardados validados. API simulada; navegador y WebGL reales. Captura: /tmp/m09-islas-1440.png`);
}catch(e){await page?.screenshot({path:'/tmp/m09-islas-fallo.png',fullPage:true}).catch(()=>{});throw e;
}finally{await browser.close();await new Promise(r=>server.close(r));}
