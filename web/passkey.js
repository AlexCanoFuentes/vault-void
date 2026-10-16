(() => {
  'use strict';
  const $=id=>document.getElementById(id);
  const SIN_PRF='Este navegador o esta passkey no permite abrir el candado con ella. Sigue con tu código o tu kit de recuperación.';
  const disponible=()=>window.isSecureContext && !!window.PublicKeyCredential && !!navigator.credentials;
  const b64=b=>btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
  const bytes=s=>Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/')),c=>c.charCodeAt(0));
  let ocupada=false,turno=0,control=null;
  async function api(accion,b={}) {
    const r=await fetch('/v1/web/passkey/'+accion,{method:'POST',headers:{'content-type':'application/json'},
      body:JSON.stringify(b),signal:AbortSignal.timeout(30000)});
    const d=await r.json();if(!r.ok)throw new Error(d.error||'No se pudo completar. Vuelve a intentarlo.');return d;
  }
  function opciones(o) {
    const p=structuredClone(o);p.challenge=bytes(p.challenge);
    if(p.user)p.user.id=bytes(p.user.id);
    for(const clave of ['allowCredentials','excludeCredentials'])if(p[clave])for(const c of p[clave])c.id=bytes(c.id);
    const prf=p.extensions?.prf;
    if(prf?.eval)prf.eval.first=bytes(prf.eval.first);
    if(prf?.evalByCredential)for(const v of Object.values(prf.evalByCredential))v.first=bytes(v.first);
    return p;
  }
  function serializar(c) {
    const r=c.response;
    // Lista cerrada: PRF nunca viaja dentro de clientExtensionResults ni queda en el historial.
    return {id:c.id,rawId:b64(c.rawId),type:c.type,clientExtensionResults:{},response:r.attestationObject
      ?{clientDataJSON:b64(r.clientDataJSON),attestationObject:b64(r.attestationObject),transports:r.getTransports?.()||[]}
      :{clientDataJSON:b64(r.clientDataJSON),authenticatorData:b64(r.authenticatorData),signature:b64(r.signature),userHandle:r.userHandle?b64(r.userHandle):null}};
  }
  function secretoPRF(c) {
    const resultado=c?.getClientExtensionResults()?.prf?.results?.first;
    if(!resultado || resultado.byteLength!==32)throw new Error(SIN_PRF);
    return 'vp_'+Array.from(new Uint8Array(resultado),v=>v.toString(16).padStart(2,'0')).join('');
  }
  async function lista() {
    const t=turno,d=await api('lista');if(t!==turno)return;
    $('passkeys-lista').replaceChildren();
    for(const p of d.passkeys) {
      const li=document.createElement('li'),nombre=document.createElement('span'),boton=document.createElement('button');
      nombre.textContent=p.nombre+' ';boton.type='button';boton.textContent='Quitar '+p.nombre;
      boton.onclick=()=>accion($('passkey-estado'),async()=>{
        const secreto=$('passkey-secreto').value.trim();$('passkey-secreto').value='';
        if(!secreto)throw new Error('Escribe tu código o tu kit debajo para quitar esta passkey.');
        await api('quitar',{id:p.id,secreto});await lista();return 'Passkey quitada. Tu código y tu kit siguen abriendo.';
      });
      li.append(nombre,boton);$('passkeys-lista').append(li);
    }
  }
  async function accion(estado,fn) {
    if(ocupada)return;ocupada=true;const t=turno;control=new AbortController();
    for(const id of ['entrar-passkey','abrir-passkey','crear-passkey'])$(id).disabled=true;
    estado.textContent='Sigue las indicaciones de tu aparato…';
    try { const mensaje=await fn(control.signal);if(t===turno&&mensaje)estado.textContent=mensaje; }
    catch(e) { if(t===turno)estado.textContent=e.name==='NotAllowedError'||e.name==='AbortError'
      ?'Se canceló o no se encontró la passkey. Puedes reintentar o usar tu código o tu kit.'
      :e.message||'No se pudo completar. Usa tu código o tu kit.'; }
    finally { ocupada=false;control=null;for(const id of ['entrar-passkey','abrir-passkey','crear-passkey'])$(id).disabled=false; }
  }
  function entrar(desdeDentro) {
    const estado=desdeDentro?$('cerrado-estado'):$('login-estado');
    accion(estado,async signal=>{
      if(!disponible())throw new Error(SIN_PRF);
      const alias=desdeDentro?window.VoidEspacio.dueno?.alias:$('alias').value.trim();
      if(!alias)throw new Error('Escribe primero el nombre de tu espacio.');
      const d=await api('opciones',{alias});
      const c=await navigator.credentials.get({publicKey:opciones(d.opciones),signal});
      if(signal.aborted)return;
      await api('entrar',{alias,ceremonia:d.ceremonia,credencial:serializar(c),prf:secretoPRF(c)});
      if(!signal.aborted)await window.VoidEspacio.abrirPasskey();
      return '';
    });
  }
  $('entrar-passkey').onclick=()=>entrar(false);
  $('abrir-passkey').onclick=()=>entrar(true);
  $('passkey-form').onsubmit=e=>{
    e.preventDefault();
    accion($('passkey-estado'),async signal=>{
      const secreto=$('passkey-secreto').value.trim(),nombre=$('passkey-nombre').value.trim();$('passkey-secreto').value='';
      if(!disponible())throw new Error(SIN_PRF);
      const d=await api('crear',{secreto});
      const c=await navigator.credentials.create({publicKey:opciones(d.opciones),signal});
      if(signal.aborted)return;
      if(c.getClientExtensionResults()?.prf?.enabled===false)throw new Error(SIN_PRF);
      const v=await api('atestiguar',{ceremonia:d.ceremonia,credencial:serializar(c)});
      $('passkey-estado').textContent='Comprueba tu passkey una vez más para activar la llave.';
      const comprobacion=await navigator.credentials.get({publicKey:opciones(v.opciones),signal});
      if(signal.aborted)return;
      await api('confirmar',{ceremonia:v.ceremonia,credencial:serializar(comprobacion),prf:secretoPRF(comprobacion),secreto,nombre});
      await lista();return 'Passkey añadida. Tu código y tu kit siguen abriendo.';
    });
  };
  addEventListener('void-abrir',()=>{lista().catch(e=>{$('passkey-estado').textContent=e.message;});});
  addEventListener('void-salir',()=>{turno++;control?.abort();$('passkey-secreto').value='';$('passkey-nombre').value='';$('passkey-estado').textContent='';$('passkeys-lista').replaceChildren();});
  if(window.VoidEspacio?.dueno)lista().catch(()=>{});
})();
