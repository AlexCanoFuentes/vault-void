import {readFileSync,mkdtempSync,mkdirSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {resolve} from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync,gzipSync,createGzip} from 'node:zlib';
import {Readable} from 'node:stream';
import assert from 'node:assert/strict';
const hash=t=>createHash('sha256').update(t).digest('hex');
export async function probarExistentes({root,mf,db,pedir,prueba,URL_BASE,huella,servir}){
  await db.prepare('DELETE FROM perfiles').run();await db.prepare('DELETE FROM huellas_cuento').run();
  const carpeta=mkdtempSync(resolve(tmpdir(),'void-conexion-fixtures-'));
  execFileSync('python3',[root+'/pruebas/pruebas_conectar_vault.py',carpeta]);
  const fixtures=JSON.parse(readFileSync(carpeta+'/fixtures.json','utf8'));
  async function propietario(f,ruta,cuerpo,extra={}){
    const r=await mf.dispatchFetch(URL_BASE+ruta,{method:'POST',headers:{authorization:'Bearer '+f.llave,'x-void-origen':'archivo','x-void-consentimiento':'alojar-mi-vault','content-type':'application/gzip',...extra},body:cuerpo});
    return {status:r.status,d:await r.json()};
  }
  const worker=await mf.getWorker('nube');let conexiones=[];
  async function privado(path,alias,prueba,body,origen='archivo'){
    const servicio=await mf.getWorker('puente');
    return servicio.fetch('https://privado'+path,{method:'POST',headers:{'x-void-alias':alias,'x-void-prueba':prueba,'x-void-origen':origen,'content-type':origen==='archivo'?'application/gzip':'application/json'},body});
  }
  await prueba('vaults existentes y a medida mantienen perfil, huella, plantilla y git',async()=>{
    for(const [i,f] of fixtures.entries()){
      await db.prepare("INSERT INTO perfiles(alias,agente,huella_llave,publico,creado) VALUES(?,'Agente propio',?,'',?)").bind(f.alias,hash(f.llave),Date.now()).run();
      assert.equal((await propietario(f,'/v1/huella',JSON.stringify({huella:{...huella,dias:90+i,tono:42+i}}),{'content-type':'application/json'})).status,200);
      const antes=await pedir('/v1/huellas');
      const r=await propietario(f,'/v1/alojar',readFileSync(f.archivo));assert.equal(r.status,200,JSON.stringify(r.d));conexiones.push(r.d);
      assert.deepEqual((await pedir('/v1/huellas')).d,antes.d);
      const archivo=await worker.fetch('https://prueba/_admin/vault?persona='+f.alias,{headers:{'x-admin':'solo-prueba-inventada'}});
      const tar=gunzipSync(Buffer.from(await archivo.arrayBuffer()));assert.ok(tar.includes(Buffer.from('Plantilla a medida '+i)));assert.ok(tar.includes(Buffer.from('.git/HEAD')));assert.ok(tar.includes(Buffer.from('Nota que todavía no tiene commit.')));
    }
    assert.equal((await db.prepare('SELECT COUNT(*) n FROM perfiles').first()).n,2);
  });
  await prueba('reintentar no pisa el archivo y los códigos privados no quedan en D1',async()=>{
    for(const f of fixtures){const r=await propietario(f,'/v1/alojar',new Uint8Array([1,2,3]));assert.equal(r.status,200);conexiones[fixtures.indexOf(f)]=r.d;}
    const datos=JSON.stringify((await db.prepare('SELECT * FROM web_enlaces').all()).results);for(const c of conexiones)assert.ok(!datos.includes(c.enlace));
  });
  await prueba('propiedad vigente, consentimiento y origen propio son obligatorios',async()=>{
    assert.equal((await propietario({...fixtures[0],llave:'vv_'+'z'.repeat(43)},'/v1/alojar',readFileSync(fixtures[0].archivo))).status,401);
    assert.equal((await propietario(fixtures[0],'/v1/alojar',readFileSync(fixtures[0].archivo),{'x-void-consentimiento':''})).status,400);
    assert.equal((await pedir('/v1/web/conectar',{enlace:conexiones[0].enlace,recuperacion:'vr_'+'f'.repeat(64)},null,'https://ajeno.invalid')).status,403);
  });
  await prueba('dos consumos simultáneos abren una sesión y recuperan la misma identidad',async()=>{
    const cuerpo={enlace:conexiones[0].enlace,recuperacion:'vr_'+'f'.repeat(64)},res=await Promise.all([pedir('/v1/web/conectar',cuerpo),pedir('/v1/web/conectar',cuerpo)]);
    assert.deepEqual(res.map(r=>r.status).sort(),[200,410]);const cookie=res.find(r=>r.status===200).cookie;
    const yo=(await pedir('/v1/web/yo',undefined,cookie)).d;assert.equal(yo.alias,fixtures[0].alias);assert.equal(yo.huella.tono,42);assert.equal(yo.semilla,fixtures[0].alias);
    const entrar=await pedir('/v1/web/entrar',{alias:'',recuperacion:cuerpo.recuperacion});assert.equal(entrar.status,200);assert.deepEqual((await pedir('/v1/web/yo',undefined,entrar.cookie)).d,yo);
    assert.ok((await pedir('/v1/web/agente/session',{},entrar.cookie)).d.id);
    assert.equal((await pedir('/v1/web/conectar',cuerpo)).status,410);
  });
  await prueba('caducidad y rotación de llave invalidan los enlaces pendientes',async()=>{
    await db.prepare('UPDATE web_enlaces SET caduca=0 WHERE token_hash=?').bind(hash(conexiones[1].enlace)).run();assert.equal((await pedir('/v1/web/conectar',{enlace:conexiones[1].enlace,recuperacion:'vr_'+'9'.repeat(64)})).status,410);
    const nuevo=await propietario(fixtures[1],'/v1/alojar',readFileSync(fixtures[1].archivo));
    const rotacion=await propietario(fixtures[1],'/v1/llave/cambiar',JSON.stringify({}),{'content-type':'application/json'});assert.equal(rotacion.status,200);fixtures[1].llave=rotacion.d.llave;
    assert.equal((await pedir('/v1/web/conectar',{enlace:nuevo.d.enlace,recuperacion:'vr_'+'9'.repeat(64)})).status,410);
  });
  await prueba('archivo peligroso y caja ajena se rechazan; caja previa exige contraseña',async()=>{
    const caja=await worker.fetch('https://prueba/_admin/alta?persona=previo-seguro',{method:'POST',headers:{'x-admin':'solo-prueba-inventada','content-type':'application/json'},body:JSON.stringify({origen:'nube'})});assert.equal(caja.status,200);const cred=await caja.json();
    const sembrar=await worker.fetch('https://prueba/_admin/siembra?persona=previo-seguro',{method:'POST',headers:{'x-admin':'solo-prueba-inventada'},body:readFileSync(fixtures[0].archivo)});assert.equal(sembrar.status,200);
    let r=await privado('/conectar','previo-seguro','1'.repeat(64),readFileSync(fixtures[0].archivo));assert.equal(r.status,403);
    r=await privado('/conectar','previo-seguro','1'.repeat(64),JSON.stringify({pass:'incorrecta'}),'alojado');assert.equal(r.status,403);
    r=await privado('/conectar','previo-seguro','1'.repeat(64),JSON.stringify({pass:cred.contraseña}),'alojado');assert.equal(r.status,200);
    r=await privado('/conectar','archivo-invalido','1'.repeat(64),new Uint8Array([1,2,3]));assert.equal(r.status,400);
    // Un USTAR bien formado pero con traversal, para comprobar la validación de rutas, no solo gzip.
    const mal=gunzipSync(readFileSync(fixtures[0].archivo));mal.fill(0,0,100);Buffer.from('../escape').copy(mal);mal.fill(32,148,156);let suma=0;for(let i=0;i<512;i++)suma+=mal[i];mal.write(suma.toString(8).padStart(6,'0')+'\0 ',148,'ascii');
    r=await privado('/conectar','ruta-invalida','1'.repeat(64),gzipSync(mal));assert.equal(r.status,400);
    r=await privado('/conectar','archivo-grande','1'.repeat(64),new Uint8Array(50*1024*1024+1));assert.equal(r.status,413);
    // Un cuerpo pequeño comprimido no puede expandirse más allá del límite del piloto.
    const cabecera=Buffer.from(gunzipSync(readFileSync(fixtures[0].archivo)).subarray(0,512));cabecera.fill(0,0,100);Buffer.from('contenido.md').copy(cabecera);
    cabecera.write((200*1024*1024).toString(8).padStart(11,'0')+'\0',124,'ascii');cabecera.fill(32,148,156);let control=0;for(const v of cabecera)control+=v;cabecera.write(control.toString(8).padStart(6,'0')+'\0 ',148,'ascii');
    const comprimidor=Readable.from((function*(){yield cabecera;const bloque=Buffer.alloc(1024*1024);for(let i=0;i<200;i++)yield bloque;yield Buffer.alloc(1024);})()).pipe(createGzip());const trozos=[];for await(const t of comprimidor)trozos.push(t);
    r=await privado('/conectar','archivo-expandido','1'.repeat(64),Buffer.concat(trozos));assert.equal(r.status,400);assert.match((await r.json()).error,/200 MiB/);
  });
  await prueba('la paginación muestra todas las huellas sin un aforo fijo del lienzo',async()=>{
    const lote=[];for(let i=0;i<300;i++){const alias='pagina-'+String(i).padStart(3,'0');lote.push(db.prepare("INSERT INTO perfiles(alias,agente,huella_llave,publico,creado) VALUES(?,'Prueba',?,'',?)").bind(alias,hash(alias),Date.now()),db.prepare('INSERT INTO huellas(perfil_id,datos,actualizado) SELECT id,?,? FROM perfiles WHERE alias=?').bind(JSON.stringify(huella),Date.now(),alias));}
    await db.batch(lote);const vistos=[];let cursor='0,0';do{const r=await pedir('/v1/huellas?cursor='+encodeURIComponent(cursor));assert.equal(r.status,200);vistos.push(...r.d.huellas.map(h=>h.alias));cursor=r.d.siguiente;}while(cursor);
    assert.equal(vistos.length,302);assert.equal(new Set(vistos).size,302);assert.equal((await pedir('/v1/huellas?cursor=mal')).status,400);
    await db.prepare("DELETE FROM perfiles WHERE alias LIKE 'pagina-%'").run();
  });
  if(servir){
    const enlaces=[];for(const f of fixtures){const r=await propietario(f,'/v1/alojar',readFileSync(f.archivo));assert.equal(r.status,200);enlaces.push(r.d);}
    mkdirSync(root+'/.impeccable/review',{recursive:true});writeFileSync(root+'/.impeccable/review/enlaces.json',JSON.stringify(enlaces));
  }
}
