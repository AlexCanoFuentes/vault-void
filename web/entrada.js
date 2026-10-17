/* Crear un espacio sin instalar asistentes. Las palabras permanecen locales hasta el consentimiento. */
async function apiEntrada(ruta, datos) {
  const r = await fetch('/v1/web/' + ruta, {method:datos === undefined ? 'GET':'POST', headers:{'content-type':'application/json'}, body:datos === undefined ? undefined:JSON.stringify(datos)});
  const d = await r.json(); if (!r.ok) throw new Error(d.error || 'No se pudo completar. Vuelve a intentarlo.'); return d;
}
function crearAlojado() {
  if(!guardada || !token || !semillaCuento){formada();return;}
  paso = 'alta';
  decir('', 'Ponle un nombre a <em>tu espacio</em>.', 'Aquí vivirá tu cuaderno. Podrás guardar ideas y pedir ayuda.');
  let pendiente;
  try { pendiente = JSON.parse(localStorage.getItem('void-alta-pendiente') || 'null'); } catch {}
  if (!pendiente) { const a=crypto.getRandomValues(new Uint8Array(32)); pendiente={recuperacion:'vr_'+Array.from(a,x=>x.toString(16).padStart(2,'0')).join(''),alias:''}; }
  const conservar = () => { try { localStorage.setItem('void-alta-pendiente',JSON.stringify(pendiente)); } catch {} };
  conservar();
  abajo.innerHTML = `<form id="alta-web" class="tres" style="width:min(520px,100%)"><label for="nombre-espacio">Nombre de tu espacio</label><input id="nombre-espacio" value="${esc(pendiente.alias)}" required pattern="[a-z0-9\\-]{3,24}" minlength="3" maxlength="24" autocomplete="username" autocapitalize="none" autocorrect="off" spellcheck="false" placeholder="por ejemplo: mi-cuaderno" aria-describedby="nombre-ayuda"><p id="nombre-ayuda">Entre 3 y 24 letras minúsculas, números o guiones. El nombre y la huella de colores son públicos; tus palabras son privadas.</p><label class="consentimiento"><input type="checkbox" id="acepto" required> Quiero guardar mis respuestas en mi espacio de Void.</label><p>Se guardan cerradas con tu candado: cuando tu espacio duerme, solo tus llaves lo abren. Mientras trabajas, el asistente y Void pueden leerlas. El piloto no cobra.</p><button class="principal" id="crear-espacio">Crear mi espacio</button><p id="alta-estado" role="status"></p></form><div class="fila"><button class="texto" id="volver-respuestas">Revisar mis respuestas</button><a class="texto" href="/mi-vault">Ya creé mi espacio</a></div>`;
  document.getElementById('volver-respuestas').onclick = porDentro;
  const form=document.getElementById('alta-web'),nombre=document.getElementById('nombre-espacio'),estado=document.getElementById('alta-estado'),boton=document.getElementById('crear-espacio');
  // El iPhone pone la primera letra en mayúscula y el nombre solo admite minúsculas: Gigi, 17-oct, no podía crear su
  // espacio y el navegador no decía por qué. Se pasa solo a minúsculas, sin tildes, y los espacios a guiones.
  const normaliza=v=>v.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,'-').replace(/[^a-z0-9-]/g,'');
  nombre.oninput=()=>{const v=normaliza(nombre.value);if(v!==nombre.value)nombre.value=v;pendiente.alias=v;conservar();estado.textContent='';};nombre.oninput();
  nombre.oninvalid=()=>{estado.textContent=nombre.value.length<3?'El nombre necesita al menos 3 letras o números.':'Usa solo letras minúsculas, números o guiones.';};
  document.getElementById('acepto').oninvalid=()=>{estado.textContent='Marca la casilla para guardar tus respuestas en tu espacio.';};
  form.onsubmit=async e=>{
    e.preventDefault();boton.disabled=true;estado.textContent='Preparando tu espacio…';
    pendiente.alias=nombre.value.trim();conservar();
    try {
      const creado=await apiEntrada('crear',{...pendiente,consentimiento:document.getElementById('acepto').checked,cuento:token,huella:cifrasDelCuento(),respuestas:respuestas.map(r=>r === undefined ? null:r),propuesta});
      const limpiar=()=>{try{localStorage.removeItem('void-alta-pendiente');localStorage.removeItem('void-cuento-borrador');}catch{}};
      // Con candado (14-oct): el candado se cierra y tus dos llaves vuelan a ti. Se enseñan una sola vez.
      if(creado.kit&&window.VoidCandado){
        paso = 'llaves';
        document.body.classList.add('con-llaves');
        decir('', '', '');
        VoidCandado.pantallaLlaves(abajo,{alias:pendiente.alias,codigo:pendiente.recuperacion,kit:creado.kit,alListo:async()=>{await apiEntrada('candado',{accion:'confirmar'});limpiar();location.assign('/mi-vault');}});
        return;
      }
      decir('', 'Tu espacio está <em>listo</em>.', 'Guarda este código: te permite volver desde otro móvil u ordenador. No lo compartas.');
      abajo.innerHTML=`<div class="tres" style="width:min(520px,100%)"><label for="codigo-vuelta">Código para volver a @${esc(pendiente.alias)}</label><textarea id="codigo-vuelta" readonly style="width:100%;height:104px;max-height:none;overflow-wrap:anywhere">${pendiente.recuperacion}</textarea><div class="fila"><button id="descargar-codigo">Guardar mi código en un archivo</button></div><p>Si ya te enseñamos tu kit de recuperación, guárdalo junto a este código en sitios distintos. Si no lo viste, pide uno nuevo en Mi espacio, en «Mi acceso y mis datos».</p><label class="consentimiento"><input type="checkbox" id="codigo-guardado"> He guardado mi código en un lugar privado.</label><div class="fila"><button class="principal" id="abrir-espacio" disabled>Abrir mi espacio</button></div></div>`;
      document.getElementById('descargar-codigo').onclick=()=>{const u=URL.createObjectURL(new Blob(['Void · @'+pendiente.alias+'\nhttps://vaultvoid.app/mi-vault\nCódigo privado: '+pendiente.recuperacion+'\n'],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=u;a.download='mi-acceso-void.txt';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);};
      const abrir=document.getElementById('abrir-espacio');document.getElementById('codigo-guardado').onchange=e=>abrir.disabled=!e.target.checked;
      abrir.onclick=()=>{try{localStorage.removeItem('void-alta-pendiente');localStorage.removeItem('void-cuento-borrador');}catch{}location.assign('/mi-vault');};
    } catch(e) {estado.textContent=e.message;boton.disabled=false;}
  };
  nombre.focus({preventScroll:true});
  apiEntrada('capacidad').then(d=>{if(!form.isConnected)return;if(!d.disponible){boton.disabled=true;estado.textContent='El piloto está completo por ahora. Tus respuestas siguen en este navegador. Si ya tienes un vault, usa Conectar mi vault para comprobar su acceso; si ya creaste tu espacio, puedes volver a él.';const a=document.createElement('a');a.href='/conectar-vault';a.textContent='Conectar mi vault existente';form.append(a);}}).catch(()=>{if(form.isConnected)estado.textContent='No pudimos consultar la disponibilidad. Puedes reintentar: tus respuestas se conservan aquí.';});
}
