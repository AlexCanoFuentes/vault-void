(()=>{'use strict';const $=id=>document.getElementById(id),almacenBorrador='void-vinculo-pendiente';let pendiente;
  try{pendiente=JSON.parse(localStorage.getItem(almacenBorrador)||'null');}catch{}
  function mostrar(d){$('conexion').hidden=true;$('guardado').hidden=false;$('titulo').textContent='El vault de @'+d.alias+' está conectado.';$('recuperacion').value=d.recuperacion;pendiente=d;}
  if(pendiente?.alias&&/^vr_[0-9a-f]{64}$/.test(pendiente.recuperacion))mostrar(pendiente);
  $('copiar').onclick=async()=>{try{await navigator.clipboard.writeText($('orden').textContent);$('copiar').textContent='Copiado';}catch{$('estado').textContent='Selecciona y copia la frase para tu asistente.';}};
  $('vincular').onsubmit=async e=>{e.preventDefault();if($('conectar').disabled)return;const enlace=$('enlace').value.trim();if(!/^ve_[A-Za-z0-9_-]{43}$/.test(enlace)){$('estado').textContent='Necesitas el código temporal que empieza por ve_. La llave del vault se queda en tu vault.';return;}
    const a=crypto.getRandomValues(new Uint8Array(32)),recuperacion='vr_'+Array.from(a,x=>x.toString(16).padStart(2,'0')).join('');
    try{localStorage.setItem(almacenBorrador,JSON.stringify({recuperacion}));}catch{$('estado').textContent='Este navegador no puede conservar tu código si se interrumpe. Permite el almacenamiento local antes de conectar.';return;}
    $('conectar').disabled=true;$('estado').textContent='Conectando tu vault…';
    try{const r=await fetch('/v1/web/conectar',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({enlace,recuperacion})});const d=await r.json();if(!r.ok)throw new Error(d.error||'No se pudo conectar.');const dato={alias:d.alias,recuperacion};try{localStorage.setItem(almacenBorrador,JSON.stringify(dato));}catch{}$('enlace').value='';mostrar(dato);}catch(e){$('estado').textContent=e.message+' Si se perdió la respuesta, vuelve a cargar: comprobaremos si se abrió.';}finally{$('conectar').disabled=false;}
  };
  $('descargar').onclick=()=>{const u=URL.createObjectURL(new Blob(['Void · @'+pendiente.alias+'\nhttps://vaultvoid.app/mi-vault\nCódigo privado: '+pendiente.recuperacion+'\n'],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=u;a.download='mi-acceso-void.txt';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);};
  $('codigo-guardado').onchange=()=>{$('abrir').disabled=!$('codigo-guardado').checked;};
  $('abrir').onclick=()=>{try{localStorage.removeItem(almacenBorrador);}catch{}location.assign('/mi-vault');};
  if(pendiente?.recuperacion&&!pendiente.alias)fetch('/v1/web/entrar',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({recuperacion:pendiente.recuperacion,alias:''})}).then(async r=>{if(!r.ok)return;const d=await r.json(),dato={alias:d.alias,recuperacion:pendiente.recuperacion};try{localStorage.setItem(almacenBorrador,JSON.stringify(dato));}catch{}mostrar(dato);}).catch(()=>{});
})();
