/** VV-010 · Credenciales aleatorias, sesiones privadas y alojamiento por binding. */
import { huella, llaveNueva, problemaAlias, problemaHuella } from './reglas.js';
import {catalogoModelos,proveedoresWeb,pedirCaja} from './modelos-web.js';

export interface EntradaEnv {
  DB: D1Database;
  NUBE?: Fetcher;
  TOPE_WEB?: string;
}
interface Propietario { id: number; alias: string; listo: number; recuperacion_hash: string; alojamiento_prueba?: string }
const COOKIE = '__Host-void';
const VIDA = 30 * 24 * 60 * 60 * 1000;
const RE_CODIGO = /^vr_[0-9a-f]{64}$/;
const cab = { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' };
const json = (status: number, datos: unknown, extra = {}) => new Response(JSON.stringify(datos), { status, headers: { ...cab, ...extra } });
const fallo = (status: number, error: string) => json(status, { error });
async function leer(req: Request) {
  if (!req.headers.get('content-type')?.startsWith('application/json')) throw new Error('formato');
  const texto = await req.text();
  if (texto.length > 32_768) throw new Error('tamaño');
  const b = JSON.parse(texto);
  if (!b || typeof b !== 'object' || Array.isArray(b)) throw new Error('formato');
  return b;
}
async function sesion(req: Request, env: EntradaEnv): Promise<Propietario | null> {
  const token = req.headers.get('cookie')?.split(';').map(s => s.trim()).find(s => s.startsWith(COOKIE + '='))?.slice(COOKIE.length + 1);
  if (!token || !/^vv_[A-Za-z0-9_-]{43}$/.test(token)) return null;
  return env.DB.prepare('SELECT p.id,p.alias,w.listo,w.recuperacion_hash,w.alojamiento_prueba FROM web_sesiones s JOIN perfiles p ON p.id=s.perfil_id JOIN web_vaults w ON w.perfil_id=p.id WHERE s.token_hash=? AND s.caduca>?')
    .bind(await huella(token), Date.now()).first<Propietario>();
}
async function entrar(p: Propietario, req: Request, env: EntradaEnv) {
  const token = llaveNueva();
  const anterior = req.headers.get('cookie')?.split(';').map(s => s.trim()).find(s => s.startsWith(COOKIE + '='))?.slice(COOKIE.length + 1);
  await env.DB.batch([
    env.DB.prepare('DELETE FROM web_sesiones WHERE caduca<? OR token_hash=?').bind(Date.now(), await huella(anterior || '')),
    env.DB.prepare('INSERT INTO web_sesiones(token_hash,perfil_id,caduca) VALUES(?,?,?)').bind(await huella(token), p.id, Date.now() + VIDA),
  ]);
  return json(200, { alias: p.alias, listo: !!p.listo }, { 'set-cookie': `${COOKIE}=${token}; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=${VIDA / 1000}` });
}
export async function llaveWeb(codigo: string) {
  const hex = await huella('void-web-v1:' + codigo);
  return 'vv_' + btoa(String.fromCharCode(...hex.match(/../g)!.map(n => parseInt(n, 16)))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
export async function entradaWeb(req: Request, env: EntradaEnv, publicar: (req: Request) => Promise<Response>): Promise<Response> {
  const url = new URL(req.url), ruta = url.pathname.slice('/v1/web'.length);
  // El binding no está expuesto por URL. Cookie solo en el dominio de la interfaz.
  if (url.hostname !== 'vaultvoid.app' && !['localhost', '127.0.0.1'].includes(url.hostname)) return fallo(404, 'Esta entrada está en vaultvoid.app.');
  if (!['GET', 'POST'].includes(req.method)) return fallo(405, 'Método no permitido.');
  if (req.method === 'POST' && req.headers.get('origin') !== url.origin) return fallo(403, 'Abre esta pantalla desde Void para continuar.');
  try {
    if (ruta === '/capacidad' && req.method === 'GET') {
      const usados = await env.DB.prepare('SELECT COUNT(*) n FROM web_vaults').first<{n:number}>();
      const limite = Number(env.TOPE_WEB || 0);
      return json(200, { disponible: !!env.NUBE && Number.isInteger(limite) && limite > (usados?.n || 0) });
    }
    if (ruta === '/conectar' && req.method === 'POST') {
      const b=await leer(req);
      if(!/^ve_[A-Za-z0-9_-]{43}$/.test(b.enlace||'') || !RE_CODIGO.test(b.recuperacion||'')) return fallo(400,'Pega el código temporal que preparó tu vault.');
      // RETURNING consume una sola vez, incluso con dos peticiones simultáneas. La llave debe seguir vigente.
      const enlace=await env.DB.prepare('UPDATE web_enlaces SET usado=1 WHERE token_hash=? AND usado=0 AND caduca>? AND llave_hash=(SELECT huella_llave FROM perfiles WHERE id=web_enlaces.perfil_id) AND EXISTS(SELECT 1 FROM web_vaults WHERE perfil_id=web_enlaces.perfil_id AND listo=1) RETURNING perfil_id').bind(await huella(b.enlace),Date.now()).first<{perfil_id:number}>();
      if(!enlace)return fallo(410,'Ese código caducó o ya se usó. Pide a tu vault un nuevo código para conectar.');
      await env.DB.batch([
        env.DB.prepare('UPDATE web_vaults SET alojamiento_prueba=COALESCE(alojamiento_prueba,recuperacion_hash),recuperacion_hash=? WHERE perfil_id=?').bind(await huella(b.recuperacion),enlace.perfil_id),
        env.DB.prepare('DELETE FROM web_sesiones WHERE perfil_id=?').bind(enlace.perfil_id)
      ]);
      const p=await env.DB.prepare('SELECT p.id,p.alias,w.listo,w.recuperacion_hash,w.alojamiento_prueba FROM perfiles p JOIN web_vaults w ON w.perfil_id=p.id WHERE p.id=?').bind(enlace.perfil_id).first<Propietario>();
      return entrar(p!,req,env);
    }
    if (ruta === '/crear' && req.method === 'POST') {
      const b = await leer(req), alias = typeof b.alias === 'string' ? b.alias.trim() : '';
      const mal = problemaAlias(alias) || problemaHuella(b.huella);
      if (mal) return fallo(400, mal);
      if (!RE_CODIGO.test(b.recuperacion || '') || b.consentimiento !== true || !Array.isArray(b.respuestas) || b.respuestas.length !== 7 || b.respuestas.some((r: unknown) => r !== null && (typeof r !== 'string' || r.length > 3000))) return fallo(400, 'Faltan tus respuestas, tu código o la autorización para guardarlas.');
      if (!/^vc_[0-9a-f]{64}$/.test(b.cuento || '')) return fallo(400, 'Guarda primero tu huella: así será la misma al volver.');
      if (b.propuesta !== null && (typeof b.propuesta !== 'string' || b.propuesta.length > 100)) return fallo(400, 'La propuesta no es válida.');
      if (!env.NUBE) return fallo(503, 'El alojamiento todavía no está abierto. Tus respuestas siguen en este navegador.');
      const prueba = await huella(b.recuperacion), llave = await llaveWeb(b.recuperacion);
      let p = await env.DB.prepare('SELECT p.id,p.alias,w.listo,w.recuperacion_hash FROM perfiles p LEFT JOIN web_vaults w ON w.perfil_id=p.id WHERE p.alias=?').bind(alias).first<Propietario>();
      if (p && p.recuperacion_hash !== prueba) return fallo(409, 'Ese nombre ya tiene un vault. Elige otro o entra con su código.');
      if (!p) {
        const limite = Number(env.TOPE_WEB || 0);
        if (!Number.isInteger(limite) || limite < 1) return fallo(503, 'El piloto de alojamiento aún está cerrado. Conservamos tus respuestas aquí.');
        // D1 serializa este lote: el límite también vale con dos altas simultáneas.
        await env.DB.batch([
          env.DB.prepare("INSERT OR IGNORE INTO perfiles(alias,agente,huella_llave,publico,creado) SELECT ?,'Void',?,'',? WHERE (SELECT COUNT(*) FROM web_vaults)<?").bind(alias, await huella(llave), Date.now(), limite),
          env.DB.prepare('INSERT OR IGNORE INTO web_vaults(perfil_id,recuperacion_hash,creado) SELECT id,?,? FROM perfiles WHERE alias=? AND huella_llave=?').bind(prueba, Date.now(), alias, await huella(llave)),
        ]);
        p = await env.DB.prepare('SELECT p.id,p.alias,w.listo,w.recuperacion_hash FROM perfiles p JOIN web_vaults w ON w.perfil_id=p.id WHERE p.alias=?').bind(alias).first<Propietario>();
        if (!p) return fallo(503, 'Ahora mismo no queda sitio en el piloto. Tus respuestas siguen aquí.');
        if (p.recuperacion_hash !== prueba) return fallo(409, 'Ese nombre acaba de reservarse. Elige otro.');
      }
      if (!p.listo) {
        // Reclamar antes de sembrar: una huella ajena nunca crea una caja con palabras.
        const r = await publicar(new Request(req.url, { method: 'POST', headers: { authorization: 'Bearer ' + llave, 'content-type': 'application/json' }, body: JSON.stringify({ huella: b.huella, cuento: b.cuento }) }));
        if (!r.ok) return r;
        const nube = await env.NUBE.fetch(new Request('https://privado/crear', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ alias, prueba, llave, respuestas: b.respuestas, propuesta: b.propuesta }) }));
        if (!nube.ok) return fallo(503, 'No hemos podido preparar tu espacio. Vuelve a intentarlo: no se crea otro vault ni se pierden tus respuestas.');
        await env.DB.prepare('UPDATE web_vaults SET listo=1 WHERE perfil_id=?').bind(p.id).run();
        p.listo = 1;
      }
      return entrar(p, req, env);
    }
    if (ruta === '/entrar' && req.method === 'POST') {
      const b = await leer(req);
      if (typeof b.alias !== 'string' || !RE_CODIGO.test(b.recuperacion || '')) return fallo(401, 'El nombre o el código no coinciden.');
      const p = await env.DB.prepare('SELECT p.id,p.alias,w.listo,w.recuperacion_hash FROM perfiles p JOIN web_vaults w ON w.perfil_id=p.id WHERE (?=\'\' OR p.alias=?) AND w.recuperacion_hash=?').bind(b.alias.trim(),b.alias.trim(), await huella(b.recuperacion)).first<Propietario>();
      if (!p) return fallo(401, 'El nombre o el código no coinciden.');
      if (!p.listo) return fallo(409, 'Tu espacio está a medio preparar. Vuelve al cuento en el navegador donde empezaste y pulsa Crear mi espacio.');
      return entrar(p, req, env);
    }
    const p = await sesion(req, env);
    if (!p) return fallo(401, 'Entra con el nombre y el código de tu espacio.');
    if (ruta === '/yo' && req.method === 'GET') {
      const h = await env.DB.prepare('SELECT datos,semilla FROM huellas WHERE perfil_id=?').bind(p.id).first<{datos:string;semilla:string|null}>();
      return json(200, { alias: p.alias, listo: !!p.listo, huella: h ? JSON.parse(h.datos) : null, semilla: h?.semilla || p.alias });
    }
    if (ruta === '/archivo' && req.method === 'GET' && env.NUBE && p.listo) {
      const r = await recuperarArchivo(env, p);
      const h = new Headers(r.headers);
      if (r.ok) h.set('content-disposition', `attachment; filename="void-${p.alias}.tgz"`);
      return new Response(r.body, {status:r.status, headers:h});
    }
    if (ruta === '/modelos' && req.method === 'GET' && env.NUBE && p.listo) {
      return json(200,await catalogoModelos(env,p));
    }
    if (ruta === '/proveedores' && req.method === 'GET' && env.NUBE && p.listo) return json(200,await proveedoresWeb(env,p));
    if (ruta === '/proveedores' && req.method === 'POST' && env.NUBE && p.listo) {
      const b=await leer(req),catalogo=await proveedoresWeb(env,p),proveedor=catalogo.proveedores.find(x=>x.id===b.proveedor);
      if(!proveedor)return fallo(400,'Elige un proveedor de la lista.');
      const metodo=proveedor.metodos.find(m=>m.indice===b.metodo);
      if(b.accion==='desconectar'){
        const r=await pedirCaja(env,p,'/agente/auth/'+proveedor.id,'DELETE');
        return r.ok&&await r.json()===true?json(200,{desconectado:true}):fallo(503,'No se pudo desconectar. Vuelve a intentarlo.');
      }
      if(!metodo||b.consentimiento!==true)return fallo(400,'Confirma la conexión y el consumo en tu propia cuenta.');
      if(b.accion==='clave'&&metodo.tipo==='api'){
        if(typeof b.clave!=='string'||b.clave.length<8||b.clave.length>8192||/[\x00-\x20\x7f]/.test(b.clave))return fallo(400,'Escribe una clave de API válida, sin espacios.');
        const r=await pedirCaja(env,p,'/agente/auth/'+proveedor.id,'PUT',{type:'api',key:b.clave});
        return r.ok&&await r.json()===true?json(200,{conectado:true,validacion:'primer-uso'}):fallo(r.status===409?409:503,r.status===409?'Espera a que termine el asistente antes de cambiar sus conexiones.':'No se pudo guardar la conexión. Vuelve a intentarlo.');
      }
      if(b.accion==='autorizar'&&metodo.tipo==='oauth'){
        const inputs:Record<string,string>={};
        for(const q of metodo.campos){if(typeof q.key==='string'&&typeof b.inputs?.[q.key]==='string'&&b.inputs[q.key].length<=1000)inputs[q.key]=b.inputs[q.key];}
        const r=await pedirCaja(env,p,'/agente/provider/'+proveedor.id+'/oauth/authorize','POST',{method:metodo.indice,inputs});
        if(!r.ok)return fallo(503,'El proveedor no pudo iniciar la conexión. Vuelve a intentarlo.');
        const d=await r.json() as {url:string;method:string;instructions:string};
        const u=new URL(d.url);if(u.protocol!=='https:')return fallo(503,'Ese método necesita una conexión desde un dispositivo local. Elige el método para navegador remoto o código.');
        return json(200,{url:u.href,method:d.method,instructions:d.instructions});
      }
      if(b.accion==='completar'&&metodo.tipo==='oauth'){
        if(b.codigo!==undefined&&(typeof b.codigo!=='string'||b.codigo.length>4096))return fallo(400,'El código de autorización no es válido.');
        const r=await pedirCaja(env,p,'/agente/provider/'+proveedor.id+'/oauth/callback','POST',{method:metodo.indice,...b.codigo?{code:b.codigo}:{}});
        return r.ok&&await r.json()===true?json(200,{conectado:true}):fallo(503,'La autorización no terminó. Revisa el acceso en el proveedor y vuelve a intentarlo.');
      }
      return fallo(400,'Elige un método de conexión disponible.');
    }
    if (ruta === '/salir' && req.method === 'POST') {
      const token = req.headers.get('cookie')!.split(';').map(s => s.trim()).find(s => s.startsWith(COOKIE + '='))!.slice(COOKIE.length + 1);
      await env.DB.prepare('DELETE FROM web_sesiones WHERE token_hash=?').bind(await huella(token)).run();
      return json(200, { saliste: true }, { 'set-cookie': `${COOKIE}=; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=0` });
    }
    if (ruta.startsWith('/agente/') && env.NUBE && p.listo) {
      const api = ruta.slice('/agente'.length);
      const permitido = req.method === 'GET' ? /^\/(session(?:\/status|\/ses_[A-Za-z0-9]+(?:\/message)?)?|permission|question)$/.test(api)
        : /^\/(session|session\/ses_[A-Za-z0-9]+\/(prompt_async|abort)|permission\/[A-Za-z0-9_-]+\/reply|question\/[A-Za-z0-9_-]+\/(reply|reject))$/.test(api);
      if (!permitido) return fallo(404, 'Esa acción no está disponible.');
      const b = req.method === 'POST' ? await leer(req) : null;
      if (api.endsWith('/prompt_async')) {
        if (!Array.isArray(b.parts) || b.parts.length !== 1 || b.parts[0].type !== 'text' || typeof b.parts[0].text !== 'string' || !b.parts[0].text.trim() || b.parts[0].text.length > 6000) return fallo(400, 'Escribe una petición de hasta 6000 caracteres.');
        const catalogo=await catalogoModelos(env,p),elegido=b.model||catalogo.defecto;
        const modelo=catalogo.modelos.find(m=>m.providerID===elegido?.providerID&&m.modelID===elegido?.modelID);
        if(!modelo)return fallo(400,'Elige un modelo disponible en tus conexiones.');
        if(modelo.cuentaPropia&&b.consumoPropio!==true)return fallo(400,'Confirma que esta petición consume tu cuenta del proveedor.');
        b.model={providerID:modelo.providerID,modelID:modelo.modelID};
        Object.keys(b).forEach(k => { if (!['parts','model'].includes(k)) delete b[k]; });
      } else if (req.method === 'POST' && api === '/session') Object.keys(b).forEach(k => delete b[k]);
      else if (api.startsWith('/permission/') && api.endsWith('/reply')) {
        if (!['once','reject'].includes(b.reply)) return fallo(400, 'Elige permitir esta vez o rechazar.');
        Object.keys(b).forEach(k=>{if(k!=='reply')delete b[k];});
      } else if(api.startsWith('/question/') && api.endsWith('/reply')) {
        if(!Array.isArray(b.answers)||b.answers.length>10||b.answers.some((a:unknown)=>!Array.isArray(a)||a.length>20||a.some(s=>typeof s!=='string'||s.length>3000)))return fallo(400,'Las respuestas no son válidas.');
        Object.keys(b).forEach(k=>{if(k!=='answers')delete b[k];});
      }
      const r = await env.NUBE.fetch(new Request('https://privado/agente' + api, { method: req.method, headers: { 'x-void-alias': p.alias, 'x-void-prueba': p.alojamiento_prueba || p.recuperacion_hash, 'content-type': 'application/json' }, body: b ? JSON.stringify(b) : undefined }));
      return new Response(r.body, { status: r.status, headers: cab });
    }
    return fallo(404, 'Esa pantalla no existe.');
  } catch { return fallo(503, 'No hemos podido completar la petición. Tus datos no se han borrado; vuelve a intentarlo.'); }
}

/** Solo el vault con su llave vigente prepara el vínculo. Nunca cambia el perfil ni la huella. */
export async function alojarExistente(req:Request,env:EntradaEnv,p:{id:number;alias:string},llaveHash:string):Promise<Response>{
  if(req.headers.get('x-void-consentimiento')!=='alojar-mi-vault')return fallo(400,'Confirma primero que quieres abrir tu vault existente en Void.');
  if(!env.NUBE)return fallo(503,'El alojamiento no está disponible.');
  try{
    const previa=await env.DB.prepare('SELECT recuperacion_hash,alojamiento_prueba,listo FROM web_vaults WHERE perfil_id=?').bind(p.id).first<Propietario>();
    const prueba=previa?.alojamiento_prueba || previa?.recuperacion_hash || await huella(llaveNueva());
    const limite=Number(env.TOPE_WEB || 0);
    if(!previa && (!Number.isInteger(limite)||limite<1))return fallo(503,'El piloto está cerrado para nuevos alojamientos.');
    await env.DB.prepare('INSERT OR IGNORE INTO web_vaults(perfil_id,recuperacion_hash,alojamiento_prueba,creado) SELECT ?,?,?,? WHERE (SELECT COUNT(*) FROM web_vaults)<?').bind(p.id,prueba,prueba,Date.now(),limite).run();
    const propia=await env.DB.prepare('SELECT recuperacion_hash,alojamiento_prueba,listo FROM web_vaults WHERE perfil_id=?').bind(p.id).first<Propietario>();
    if(!propia)return fallo(503,'No queda sitio en el piloto; tu vault original sigue intacto.');
    const origen=req.headers.get('x-void-origen');
    if(origen!=='archivo'&&origen!=='alojado')return fallo(400,'Indica si tu vault está en una carpeta o ya alojado.');
    const accion=req.headers.get('x-void-subida');
    if(accion&&(!['iniciar','trozo','terminar'].includes(accion)||origen!=='archivo'))return fallo(400,'Paso de subida no válido.');
    const h=new Headers({'x-void-alias':p.alias,'x-void-prueba':propia.alojamiento_prueba || propia.recuperacion_hash,'x-void-origen':origen,'content-type':origen==='archivo'?'application/gzip':'application/json'});
    for(const nombre of ['x-void-subida-id','x-void-indice']){const valor=req.headers.get(nombre);if(valor)h.set(nombre,valor);}
    const r=await env.NUBE.fetch(new Request(accion?'https://privado/subida/'+accion:'https://privado/conectar',{method:'POST',headers:h,body:req.body}));
    if(!r.ok){const d=await r.json() as {error?:string};return fallo(r.status,d.error||'No se pudo abrir el alojamiento; el original sigue intacto.');}
    const recibo=await r.json() as {importado?:boolean;conservado?:boolean;archivo_sha256?:string};
    if(accion&&accion!=='terminar'&&!recibo.conservado)return json(200,recibo);
    const enlace=llaveNueva().replace(/^vv_/,'ve_'),caduca=Date.now()+10*60*1000;
    await env.DB.batch([
      env.DB.prepare('UPDATE web_vaults SET listo=1 WHERE perfil_id=?').bind(p.id),
      env.DB.prepare('DELETE FROM web_enlaces WHERE caduca<? OR perfil_id=?').bind(Date.now(),p.id),
      env.DB.prepare('INSERT INTO web_enlaces(token_hash,perfil_id,llave_hash,caduca) VALUES(?,?,?,?)').bind(await huella(enlace),p.id,llaveHash,caduca)
    ]);
    return json(200,{alias:p.alias,enlace,caduca,pagina:'https://vaultvoid.app/conectar-vault',ya_alojado:!!previa?.listo,importado:recibo.importado===true,conservado:recibo.conservado===true,archivo_sha256:recibo.archivo_sha256});
  }catch{return fallo(503,'No se pudo preparar la conexión. Reintenta: nunca sustituimos tu vault por uno vacío.');}
}

/** Exportación privada para verificar y recuperar únicamente el vault de la llave vigente. */
export async function recuperarArchivo(env:EntradaEnv,p:{id:number;alias:string}):Promise<Response>{
  if(!env.NUBE)return fallo(503,'El alojamiento no está disponible.');
  const propia=await env.DB.prepare('SELECT recuperacion_hash,alojamiento_prueba,listo FROM web_vaults WHERE perfil_id=?').bind(p.id).first<Propietario>();
  if(!propia?.listo)return fallo(404,'Tu vault todavía no está alojado.');
  const r=await env.NUBE.fetch(new Request('https://privado/archivo',{headers:{'x-void-alias':p.alias,'x-void-prueba':propia.alojamiento_prueba || propia.recuperacion_hash}}));
  return new Response(r.body,{status:r.status,headers:{'content-type':r.ok?'application/gzip':'application/json','cache-control':'no-store','x-content-type-options':'nosniff'}});
}
