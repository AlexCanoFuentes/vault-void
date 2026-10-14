// Worker y D1 reales en Miniflare. El contenedor se sustituye: esta prueba no certifica un modelo de IA.
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { gunzipSync } from 'node:zlib';
import assert from 'node:assert/strict';
import http from 'node:http';
import {probarExistentes} from './vaults-existentes.mjs';
const require=createRequire(import.meta.url),r=createRequire(require.resolve('wrangler/package.json'));
const root=resolve(import.meta.dirname,'../..'),cloud=resolve(process.env.VOID_NUBE_REPO || resolve(root,'../void-nube'),'worker');
const rc=createRequire(cloud+'/package.json');const {Miniflare}=rc('miniflare'),{build}=r('esbuild');
const contenedor=`import {DurableObject} from 'cloudflare:workers';
export class Container extends DurableObject {
  constructor(ctx,env){super(ctx,env);this.ctx=ctx;this.env=env;this.sleepAfterMs=Date.now() + 300_000;}
  async getState(){return {status:'healthy'};}async startAndWaitForPorts(){}renewActivityTimeout(){}async destroy(){}
  async fetch(req){const u=new URL(req.url),c=await this.ctx.storage.get('config');let lista=await this.ctx.storage.get('sesiones')||[];
    const auth=await this.ctx.storage.get('auth_fixture')||{};
    const modelos={opencode:{id:'opencode',name:'OpenCode de prueba',models:{'space-bunny-free':{name:'Gratuito de prueba',cost:{input:0,output:0}},'longcat-2.5-preview-free':{name:'Segundo gratuito de prueba',cost:{input:0,output:0}},'pago-no-conectado':{name:'Pago de prueba',cost:{input:1,output:1}}}},openai:{id:'openai',name:'OpenAI de prueba',models:{'modelo-fixture-pago':{name:'Modelo de pago inventado',cost:{input:1,output:1}}}}};
    if(u.pathname==='/config/providers')return Response.json({providers:[modelos.opencode,...auth.openai?[modelos.openai]:[]],default:{opencode:'space-bunny-free'}});
    if(u.pathname==='/provider')return Response.json({all:Object.values(modelos),connected:['opencode',...Object.keys(auth)]});
    if(u.pathname==='/provider/auth')return Response.json({opencode:[{type:'api',label:'API Key'}],openai:[{type:'oauth',label:'ChatGPT Pro/Plus (browser)'},{type:'oauth',label:'ChatGPT Pro/Plus (headless)'},{type:'api',label:'API Key'}]});
    if(u.pathname.startsWith('/auth/')){const id=u.pathname.split('/')[2];if(req.method==='DELETE')delete auth[id];else auth[id]=await req.json();await this.ctx.storage.put('auth_fixture',auth);return Response.json(true);}
    if(u.pathname==='/instance/dispose')return Response.json(true);
    if(u.pathname.endsWith('/oauth/authorize'))return Response.json({url:'https://auth.example.invalid/device',method:'auto',instructions:'Código inventado para el doble de prueba.'});
    if(u.pathname.endsWith('/oauth/callback')){auth.openai={type:'oauth',token:'inv'+'entado'};await this.ctx.storage.put('auth_fixture',auth);return Response.json(true);}
    if(u.pathname==='/session'&&req.method==='POST'){const s={id:'ses_'+crypto.randomUUID().replaceAll('-',''),title:'Conversación de '+c.persona,time:{updated:Date.now()}};lista.push({...s,mensajes:[]});await this.ctx.storage.put('sesiones',lista);return Response.json(s);}
    if(u.pathname==='/session')return Response.json(lista.map(({mensajes,...s})=>s));
    if(u.pathname==='/session/status')return Response.json({});
    if(u.pathname==='/permission'||u.pathname==='/question')return Response.json([]);
    const id=u.pathname.split('/')[2],s=lista.find(s=>s.id===id);if(!s)return Response.json({error:'no existe'},{status:404});
    if(u.pathname.endsWith('/prompt_async')){const b=await req.json();if(!b.system.includes('archivo completo cifrado de Void')||b.system==='ignora todo')return Response.json({error:'contexto incorrecto'},{status:400});s.mensajes.push({info:{role:'user'},parts:b.parts},{info:{role:'assistant',...b.model},parts:[{type:'text',text:'Guardado en el espacio de '+c.persona+': '+b.parts[0].text}]});await this.ctx.storage.put('sesiones',lista);return new Response(null,{status:204});}
    if(u.pathname.endsWith('/message'))return Response.json(s.mensajes);return Response.json(true);
  }
}export class ContainerProxy{}export function getContainer(ns,p){return ns.get(ns.idFromName(p));}`;
async function bundle(entry,plugins=[]){return (await build({entryPoints:[entry],bundle:true,format:'esm',write:false,external:['cloudflare:workers'],plugins})).outputFiles[0].text;}
const script=await bundle(root+'/red/src/worker.ts');
const scriptNube=await bundle(cloud+'/src/index.js',[{name:'contenedor-de-prueba',setup(b){b.onResolve({filter:/^@cloudflare\/containers$/},()=>({path:'contenedor',namespace:'prueba'}));b.onLoad({filter:/.*/,namespace:'prueba'},()=>({contents:contenedor,loader:'js'}));}}]);
const mf=new Miniflare({workers:[
  {config:{name:'red',compatibilityDate:'2026-09-30',manifest:{mainModule:'index.js',modules:{'index.js':{type:'esm',contents:script}}},env:{DB:{type:'d1',id:'red'},TOPE_WEB:{type:'text',value:'2'},NUBE:{type:'worker',worker:'nube',exportName:'VoidAlojamiento'}}}},
  {config:{name:'nube',compatibilityDate:'2026-09-30',manifest:{mainModule:'index.js',modules:{'index.js':{type:'esm',contents:scriptNube}}},exports:{CajaPersona:{type:'durable-object',storage:'sqlite'}},env:{CAJA:{type:'durable-object',worker:'nube',exportName:'CajaPersona'},LLAVE_MAESTRA:{type:'text',value:Buffer.alloc(32,21).toString('base64')},ADMIN:{type:'text',value:'solo-prueba-inventada'}}}}
,{config:{name:'puente',compatibilityDate:'2026-09-30',manifest:{mainModule:'index.js',modules:{'index.js':{type:'esm',contents:`export default {async fetch(req,env){const u=new URL(req.url);const caja=a=>env.CAJA.get(env.CAJA.idFromName(a));if(u.pathname==='/prueba-dormir'){await caja(u.searchParams.get('alias')).onStop({exitCode:0,reason:'prueba'});return new Response('dormida');}if(u.pathname==='/prueba-desde-dentro'){const r=await caja(u.searchParams.get('alias')).interno('GET','/vault',null);return new Response(null,{status:r.status});}if(u.pathname==='/prueba-interno')return env.CAJA.get(env.CAJA.idFromName('existente-a')).interno('PUT','/vault',req.body,{bytes:Number(req.headers.get('x-void-bytes')),sha256:req.headers.get('x-void-sha256')});return env.NUBE.fetch(req)}}`}}},env:{NUBE:{type:'worker',worker:'nube',exportName:'VoidAlojamiento'},CAJA:{type:'durable-object',worker:'nube',exportName:'CajaPersona'}}}}
]});
const db=await mf.getD1Database('DB','red');
const {readdirSync}=await import('node:fs');
for(const p of readdirSync(root+'/red/migrations').filter(p=>p.endsWith('.sql')).sort())for(const sql of readFileSync(root+'/red/migrations/'+p,'utf8').replace(/--[^\n]*/g,'').split(';').map(s=>s.trim()).filter(Boolean))await db.prepare(sql).run();
const puerto=Number(process.env.VOID_PUERTO_PRUEBA||18880),URL_BASE='http://localhost:'+puerto;let n=0;
async function pedir(path,b,cookie,origin=URL_BASE){const response=await mf.dispatchFetch(URL_BASE+path,{method:b===undefined?'GET':'POST',headers:{'content-type':'application/json',origin,...cookie?{cookie}:{}},body:b===undefined?undefined:JSON.stringify(b)});const text=await response.text();let d;try{d=JSON.parse(text);}catch{}return {status:response.status,d,text,cookie:response.headers.get('set-cookie')?.split(';')[0],headers:response.headers};}
const huella={version:1,dias:0,pulso:56,decisiones:20,proyectos:7,calladas:0,tono:240};
async function alta(alias,letra){const cuento=await pedir('/v1/huella/cuento',{huella});assert.equal(cuento.status,201);const b={alias,recuperacion:'vr_'+letra.repeat(64),cuento:cuento.d.token,huella,consentimiento:true,respuestas:['Soy una persona de prueba\nLiteral, con saltos.','Trabajo con texto','Móvil','Se me olvidan las tareas','Organizarme','No guardar contraseñas','Retomar lo pendiente'],propuesta:null};const p=await pedir('/v1/web/crear',b);assert.equal(p.status,200,p.text);return {...p,b,cuento};}
async function prueba(nombre,fn){await fn();console.log('✓ '+nombre);n++;}
try{
  let a,b;
  await prueba('dos personas crean un espacio privado',async()=>{a=await alta('cuaderno-a','a');b=await alta('cuaderno-b','b');assert.match(a.headers.get('set-cookie'),/Secure; HttpOnly; SameSite=Strict/);});
  await prueba('reintento y recuperación conservan perfil y semilla',async()=>{const antes=await pedir('/v1/web/yo',undefined,a.cookie);const retry=await pedir('/v1/web/crear',a.b);assert.equal(retry.status,200);const recuperada=await pedir('/v1/web/entrar',{alias:a.b.alias,recuperacion:a.b.recuperacion});assert.equal(recuperada.status,200);assert.equal((await pedir('/v1/web/yo',undefined,recuperada.cookie)).d.semilla,antes.d.semilla);a.cookie=recuperada.cookie;assert.equal((await db.prepare('SELECT COUNT(*) n FROM perfiles').first()).n,2);});
  await prueba('volver al cuento no duplica ni cambia una huella reclamada',async()=>{const antes=(await pedir('/v1/huellas')).d;const vuelta=await pedir('/v1/huella/cuento',{token:a.b.cuento,huella:{...huella,tono:1}});assert.equal(vuelta.status,200);assert.equal(vuelta.d.vinculada,true);assert.deepEqual((await pedir('/v1/huellas')).d,antes);assert.equal((await db.prepare('SELECT COUNT(*) n FROM huellas_cuento').first()).n,0);});
  await prueba('código ajeno y CSRF quedan fuera',async()=>{assert.equal((await pedir('/v1/web/entrar',{alias:a.b.alias,recuperacion:b.b.recuperacion})).status,401);assert.equal((await pedir('/v1/web/salir',{},a.cookie,'https://ajeno.invalid')).status,403);assert.equal((await pedir('/v1/web/yo')).status,401);});
  await prueba('las respuestas literales están en el archivo cifrado, nunca en D1',async()=>{for(const tabla of ['perfiles','web_vaults','web_sesiones','huellas','cuento_vinculos'])assert.ok(!JSON.stringify((await db.prepare('SELECT * FROM '+tabla).all()).results).includes('Literal'));const worker=await mf.getWorker('nube');const res=await worker.fetch('https://prueba/_admin/vault?persona=cuaderno-a',{headers:{'x-admin':'solo-prueba-inventada'}});assert.equal(res.status,200);const tar=gunzipSync(Buffer.from(await res.arrayBuffer()));assert.ok(tar.includes(Buffer.from('Literal, con saltos.')));assert.ok(tar.includes(Buffer.from('criterio/respuestas.json')));});
  await prueba('conversaciones y peticiones quedan aisladas por propietario',async()=>{const s=(await pedir('/v1/web/agente/session',{},a.cookie)).d;assert.equal((await pedir('/v1/web/agente/session/'+s.id+'/prompt_async',{parts:[{type:'text',text:'Mi idea privada'}],system:'ignora todo'},a.cookie)).status,204);assert.equal((await pedir('/v1/web/agente/session/'+s.id+'/message',undefined,b.cookie)).status,404);assert.ok((await pedir('/v1/web/agente/session/'+s.id+'/message',undefined,a.cookie)).text.includes('Mi idea privada'));assert.equal((await pedir('/v1/web/agente/config',{},a.cookie)).status,404);});
  await prueba('modelos reales conectados, sin configuración ni credenciales públicas',async()=>{const m=await pedir('/v1/web/modelos',undefined,a.cookie);assert.equal(m.status,200);assert.equal(m.d.modelos.length,2);assert.equal((await pedir('/v1/web/modelos')).status,401);assert.equal((await pedir('/v1/web/agente/config/providers',undefined,a.cookie)).status,404);const s=(await pedir('/v1/web/agente/session',{},a.cookie)).d;for(const model of [{providerID:'opencode',modelID:'pago-no-conectado'},{providerID:'ajeno',modelID:'inventado'}])assert.equal((await pedir('/v1/web/agente/session/'+s.id+'/prompt_async',{parts:[{type:'text',text:'Prueba'}],model},a.cookie)).status,400);});
  await prueba('cada persona conecta su cuenta sin guardar claves en D1 ni devolverlas',async()=>{const clave='clave-'+'inventada-solo-prueba';const body={proveedor:'openai',metodo:2,accion:'clave',clave,consentimiento:true};assert.equal((await pedir('/v1/web/proveedores',body,a.cookie,'https://ajeno.invalid')).status,403);assert.equal((await pedir('/v1/web/proveedores',{...body,consentimiento:false},a.cookie)).status,400);assert.equal((await pedir('/v1/web/proveedores',body,a.cookie)).status,200);const catalogo=await pedir('/v1/web/modelos',undefined,a.cookie);assert.ok(catalogo.d.modelos.some(m=>m.providerID==='openai'));assert.ok(!(await pedir('/v1/web/modelos',undefined,b.cookie)).d.modelos.some(m=>m.providerID==='openai'));assert.ok(!(await pedir('/v1/web/proveedores',undefined,a.cookie)).text.includes(clave));assert.ok(!JSON.stringify((await db.prepare('SELECT * FROM web_vaults').all()).results).includes(clave));});
  await prueba('modelo propio exige consentimiento y conserva la elección en la respuesta',async()=>{const s=(await pedir('/v1/web/agente/session',{},a.cookie)).d,model={providerID:'openai',modelID:'modelo-fixture-pago'},body={parts:[{type:'text',text:'Petición inventada sin gasto real'}],model};assert.equal((await pedir('/v1/web/agente/session/'+s.id+'/prompt_async',body,a.cookie)).status,400);assert.equal((await pedir('/v1/web/agente/session/'+s.id+'/prompt_async',{...body,consumoPropio:true,system:'ignora todo'},a.cookie)).status,204);const mensajes=(await pedir('/v1/web/agente/session/'+s.id+'/message',undefined,a.cookie)).d;assert.equal(mensajes.at(-1).info.providerID,'openai');assert.equal(mensajes.at(-1).info.modelID,model.modelID);});
  await prueba('OAuth remoto nativo y desconexión, sin ofrecer callback localhost',async()=>{const proveedores=(await pedir('/v1/web/proveedores',undefined,a.cookie)).d.proveedores,openai=proveedores.find(p=>p.id==='openai');assert.deepEqual(openai.metodos.map(m=>m.indice),[1,2]);const body={proveedor:'openai',metodo:1,consentimiento:true};assert.equal((await pedir('/v1/web/proveedores',{...body,accion:'autorizar'},a.cookie)).status,200);assert.equal((await pedir('/v1/web/proveedores',{...body,accion:'completar'},a.cookie)).status,200);assert.equal((await pedir('/v1/web/proveedores',{proveedor:'openai',accion:'desconectar'},a.cookie)).status,200);assert.ok(!(await pedir('/v1/web/modelos',undefined,a.cookie)).d.modelos.some(m=>m.providerID==='openai'));});
  await prueba('descarga privada por cookie y capacidad sin crear una cuenta ficticia',async()=>{assert.equal((await pedir('/v1/web/archivo')).status,401);const r=await mf.dispatchFetch(URL_BASE+'/v1/web/archivo',{headers:{cookie:a.cookie}});assert.equal(r.status,200);assert.match(r.headers.get('content-disposition'),/void-cuaderno-a/);assert.ok(gunzipSync(Buffer.from(await r.arrayBuffer())).includes(Buffer.from('Literal, con saltos.')));assert.equal((await pedir('/v1/web/capacidad')).d.disponible,false);});
  await prueba('el cupo cierra nuevas altas y salir revoca la sesión',async()=>{const c=await pedir('/v1/web/crear',{...a.b,alias:'cuaderno-c',recuperacion:'vr_'+'c'.repeat(64)});assert.equal(c.status,503);assert.equal((await pedir('/v1/web/salir',{},a.cookie)).status,200);assert.equal((await pedir('/v1/web/yo',undefined,a.cookie)).status,401);});
  await probarExistentes({root,mf,db,pedir,prueba,URL_BASE,huella,servir:process.argv.includes('--servir-existentes')});
  // ---- el candado del dueño (fase 2a, 14-oct). Con su propio vault: las pruebas de arriba vacían los perfiles. ----
  await db.prepare('DELETE FROM web_sesiones').run();await db.prepare('DELETE FROM web_vaults').run();
  const v=await alta('candado-a','e');
  const galletas=(r)=>r.headers.getSetCookie().map(c=>c.split(';')[0]).join('; ');
  const sinAparato=(c)=>c.split('; ').filter(x=>!x.startsWith('__Host-void-ap=')).join('; ');
  const dormir=async(alias)=>{const r=await mf.getWorker('puente');return r.fetch('http://puente/prueba-dormir?alias='+alias);};
  const desdeDentro=async(alias)=>(await (await mf.getWorker('puente')).fetch('http://puente/prueba-desde-dentro?alias='+alias)).status;
  await prueba('candado: un vault nuevo nace con candado, su kit se enseña una vez y Void no guarda ninguna llave',async()=>{
    assert.match(v.d.kit||'',/^vk_[0-9a-f]{64}$/,'el alta no dio el kit');assert.equal(v.d.candado,'abierto');
    const otra=await pedir('/v1/web/entrar',{alias:v.b.alias,recuperacion:v.b.recuperacion});assert.equal(otra.status,200,otra.text);assert.ok(!otra.d.kit,'el kit se enseñó dos veces');
    const filas=JSON.stringify(await db.prepare('SELECT * FROM web_vaults').all());assert.ok(!filas.includes(v.d.kit.slice(3,30)),'el kit está en D1');
  });
  let llaves=galletas(v);
  await prueba('candado: dormida, ni Void ni la caja abren el vault; con la llave del aparato se abre sola',async()=>{
    assert.ok(llaves.includes('__Host-void-ap='),'no se recordó el aparato');
    await dormir(v.b.alias);assert.equal(await desdeDentro(v.b.alias),423,'la caja dormida entrega el vault sin su dueño');
    const sin=await pedir('/v1/web/archivo',undefined,sinAparato(llaves));assert.equal(sin.status,423,'sin la llave del aparato se descarga');
    const con=await pedir('/v1/web/archivo',undefined,llaves);assert.equal(con.status,200,'con la llave del aparato no abre: '+con.text.slice(0,120));
    assert.equal(await desdeDentro(v.b.alias),200,'abierta, la caja no recibe su vault');
  });
  await prueba('candado: perdiste el código, el kit entra y da uno nuevo; el viejo deja de entrar',async()=>{
    await dormir(v.b.alias);
    assert.equal((await pedir('/v1/web/entrar',{alias:v.b.alias,kit:'vk_'+'0'.repeat(64)})).status,401,'un kit ajeno entra');
    const k=await pedir('/v1/web/entrar',{alias:v.b.alias,kit:v.d.kit});assert.equal(k.status,200,k.text);
    assert.match(k.d.codigoNuevo||'',/^vr_[0-9a-f]{64}$/);assert.equal(k.d.candado,'abierto');
    assert.equal((await pedir('/v1/web/entrar',{alias:v.b.alias,recuperacion:v.b.recuperacion})).status,401,'el código viejo sigue entrando');
    await dormir(v.b.alias);
    const nuevo=await pedir('/v1/web/entrar',{alias:v.b.alias,recuperacion:k.d.codigoNuevo});assert.equal(nuevo.status,200);assert.equal(nuevo.d.candado,'abierto');
    llaves=galletas(nuevo);
  });
  await prueba('candado: con la sesión abierta, un código que no es el de la cuenta no pone ni abre candados',async()=>{
    const r=await pedir('/v1/web/candado',{accion:'abrir',secreto:'vr_'+'0'.repeat(64)},llaves);assert.equal(r.status,401,r.text);assert.match(r.d.error||'',/no es tu código/);
  });
  await prueba('candado: confirmar el kit y salir borra la llave del aparato',async()=>{
    const est=await pedir('/v1/web/candado',undefined,llaves);assert.equal(est.status,200);assert.equal(est.d.kitPendiente,true);
    assert.equal((await pedir('/v1/web/candado',{accion:'confirmar'},llaves)).status,200);
    assert.equal((await pedir('/v1/web/candado',undefined,llaves)).d.kitPendiente,false);
    assert.equal((await pedir('/v1/web/salir',{},llaves)).status,200);
    await dormir(v.b.alias);
    assert.equal(await desdeDentro(v.b.alias),423,'tras salir y dormir, la caja sigue abierta');
    assert.equal((await pedir('/v1/web/archivo',undefined,llaves)).status,401,'la sesión y la llave del aparato siguen valiendo tras salir');
  });
  console.log(n+' comprobaciones de entrada correctas. Contenedor sustituido explícitamente.');
  if(process.argv.includes('--servir')||process.argv.includes('--servir-existentes')){
    // Las personas de las comprobaciones se retiran solo de este entorno inventado para probar altas en navegador.
    if(!process.argv.includes('--servir-existentes')){await db.prepare('DELETE FROM perfiles').run();await db.prepare('DELETE FROM huellas_cuento').run();}
    const server=http.createServer(async(req,res)=>{try{if(req.url.startsWith('/v1/')){let chunks=[];for await(const c of req)chunks.push(c);const r=await mf.dispatchFetch(URL_BASE+req.url,{method:req.method,headers:req.headers,body:req.method==='POST'?Buffer.concat(chunks):undefined});res.writeHead(r.status,Object.fromEntries(r.headers));res.end(Buffer.from(await r.arrayBuffer()));return;}const path=req.url.split('?')[0];const p=root+'/web'+(path==='/'?'/index.html':path.includes('.')?path:path+'.html');const content=readFileSync(p);res.setHeader('content-type',p.endsWith('.css')?'text/css':p.endsWith('.js')?'text/javascript':p.endsWith('.svg')?'image/svg+xml':p.endsWith('.png')?'image/png':'text/html');res.end(content);}catch{res.writeHead(404);res.end('No encontrado');}});
    await new Promise(ok=>server.listen(puerto,'127.0.0.1',ok));console.log('Vista local en '+URL_BASE+'; datos inventados.');await new Promise(()=>{});
  }
}finally{await mf.dispose();}
