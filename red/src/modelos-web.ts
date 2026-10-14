import type {EntradaEnv} from './entrada-web.js';
export interface DuenoModelos {alias:string;recuperacion_hash:string;alojamiento_prueba?:string;aparato?:string}
export function pedirCaja(env:EntradaEnv,p:DuenoModelos,ruta:string,method='GET',body?:unknown){
  return env.NUBE!.fetch(new Request('https://privado'+ruta,{method,headers:{'x-void-alias':p.alias,'x-void-prueba':p.alojamiento_prueba||p.recuperacion_hash,'content-type':'application/json',...(p.aparato?{'x-void-aparato':p.aparato}:{})},body:body===undefined?undefined:JSON.stringify(body)}));
}
export async function catalogoModelos(env:EntradaEnv,p:DuenoModelos){
  const [r,c]=await Promise.all([pedirCaja(env,p,'/agente/config/providers'),pedirCaja(env,p,'/conexiones')]);
  if(!r.ok||!c.ok)throw new Error('modelos');
  const d=await r.json() as {providers?:Array<{id:string;name:string;models:Record<string,{name:string;tool_call?:boolean;cost?:{input:number;output:number}}>}>;default?:Record<string,string>};
  const propias=await c.json() as Record<string,string>;
  const modelos=(d.providers||[]).flatMap(provider=>Object.entries(provider.models||{}).filter(([,m])=>m.tool_call!==false&&
    (provider.id!=='opencode'||propias.opencode||m.cost?.input===0&&m.cost?.output===0)).map(([modelID,m])=>({providerID:provider.id,modelID,nombre:m.name||modelID,proveedor:provider.name||provider.id,cuentaPropia:provider.id!=='opencode'||!!propias.opencode})));
  const defecto=modelos.find(m=>m.providerID==='opencode'&&m.modelID==='space-bunny-free')||modelos.find(m=>!m.cuentaPropia)||modelos[0];
  return {modelos,defecto:defecto?{providerID:defecto.providerID,modelID:defecto.modelID}:null};
}
export async function proveedoresWeb(env:EntradaEnv,p:DuenoModelos){
  const [r,a,c]=await Promise.all([pedirCaja(env,p,'/agente/provider'),pedirCaja(env,p,'/agente/provider/auth'),pedirCaja(env,p,'/conexiones')]);
  if(!r.ok||!a.ok||!c.ok)throw new Error('proveedores');
  const d=await r.json() as {all:Array<{id:string;name:string}>;connected:string[]};
  const auth=await a.json() as Record<string,Array<{type:string;label:string;prompts?:Array<Record<string,unknown>>}>>;
  const conexiones=await c.json() as Record<string,string>;
  return {proveedores:d.all.filter(x=>/^[a-z0-9-]{1,80}$/.test(x.id)&&auth[x.id]?.length).map(x=>({id:x.id,nombre:x.name||x.id,conectado:!!conexiones[x.id]||x.id!=='opencode'&&d.connected.includes(x.id),
    metodos:auth[x.id].map((m,indice)=>({indice,tipo:m.type,nombre:m.label,campos:(m.prompts||[]).map(q=>({key:q.key,type:q.type,message:q.message,options:q.options,condition:q.condition}))}))
      .filter(m=>['api','oauth'].includes(m.tipo)&&!(x.id==='anthropic'&&m.tipo==='oauth')&&!(x.id==='openai'&&m.tipo==='oauth'&&/browser/i.test(m.nombre)&&!/headless/i.test(m.nombre)))}))};
}
