/* M-09. Datos privados en la caja, con la cookie del dueño y revisión por cambio.
   Nunca se copia el contenido de las islas a localStorage. */
(()=>{
'use strict';
const $=id=>document.getElementById(id),clonar=d=>JSON.parse(JSON.stringify(d));
const fijas=[
 {id:'fija_hablar',nombre:'Conversaciones',destino:'hablar',color:'#2eaca8',forma:'atolón'},
 {id:'fija_comunidad',nombre:'Comunidad',destino:'comunidad',color:'#75984b',forma:'archipiélago'},
 {id:'fija_modelos',nombre:'Mis cuentas',destino:'modelos',color:'#538bb7',forma:'montaña'},
 {id:'fija_cuidar',nombre:'Lo tuyo, a mano',destino:'cuidar',color:'#c9784e',forma:'alargada'}
];
const formas=['redonda','alargada','montaña','atolón','archipiélago'],estilos=['viva','serena','sobria'];
let registros=[],danadas=[],generacion=0,lectura=0,activo=false,disponible=false,cargando=false,pendientes=0;
// Vista del mapa: huellas por defecto; islas en 3D si la persona lo elige. Se recuerda en el aparato (solo la vista, nunca contenido).
let vista=(()=>{try{return localStorage.getItem('void-vista-mapa')==='islas'?'islas':'huellas';}catch{return 'huellas';}})(),cargando3d=null;
function cargar3d(){if(window.VoidPaisajeIslas)return Promise.resolve();if(cargando3d)return cargando3d;
 const script=src=>new Promise((ok,mal)=>{const s=document.createElement('script');s.src=src;s.onload=ok;s.onerror=()=>mal(Error('No se pudo cargar la vista de islas. Sigues en la de huellas.'));document.head.append(s);});
 cargando3d=script('/vendor/three/three.min.js').then(()=>script('/islas-paisaje.js')).catch(e=>{cargando3d=null;throw e;});return cargando3d;}
let paisaje=null,lista=false,pagina=0,actual=null,cola=Promise.resolve(),origen=null;
const api=(ruta,datos)=>window.VoidEspacio.api('islas/'+ruta,datos);
function aviso(texto){$('islas-estado').textContent=texto;}
function destruirPaisaje(){paisaje?.destruir();paisaje=null;}
function cerrarDialogos(){for(const id of ['islas-crear','islas-confirmar'])if($(id).open)$(id).close();}
function limpiar(){generacion++;lectura++;activo=false;disponible=false;cargando=false;pendientes=0;registros=[];danadas=[];actual=null;pagina=0;cola=Promise.resolve();cerrarDialogos();destruirPaisaje();$('islas-panel').replaceChildren();$('islas-panel').hidden=true;$('islas-lista').replaceChildren();$('islas-danadas').textContent='';$('islas-danadas').hidden=true;$('islas-vistas').hidden=true;$('islas-recargar').hidden=true;$('islas-nueva').disabled=true;}
function noDisponible(texto){limpiar();$('islas').hidden=false;aviso(texto+' Tus secciones siguen debajo.');}
function falloPaisaje(texto){destruirPaisaje();lista=true;aviso(texto);pintarVistas();}
function controles(){
 $('islas-nueva').disabled=!disponible||pendientes>0||cargando||registros.length+danadas.length>=40;
 $('islas-recargar').disabled=pendientes>0||cargando;
 $('islas-crear-form').querySelector('fieldset').disabled=pendientes>0;
 $('islas-borrar-si').disabled=pendientes>0;
 $('islas-panel').querySelector('fieldset')?.toggleAttribute('disabled',pendientes>0);
 $('islas-etiquetas').inert=pendientes>0;
 $('islas').setAttribute('aria-busy',String(cargando||pendientes>0));
}
function todas(){return [...fijas,...registros.map(r=>r.isla)];}
function pintarVistas(){
 $('islas-lista-boton').textContent=lista?'Ver mapa':'Ver lista';$('islas-lista-boton').setAttribute('aria-pressed',String(lista));
 $('islas-mapa-grupo').hidden=lista;$('islas-lista').hidden=!lista;$('islas-gestos').hidden=lista;
 $('islas-distribucion').classList.toggle('islas-en-detalle',!!actual);
 if(lista){destruirPaisaje();return;}
 if(!disponible)return;
 try{
  $('islas-vista-boton').textContent=vista==='islas'?'Ver como huellas':'Ver como islas';
  $('islas-gestos').textContent=vista==='islas'?'Toca una isla para abrirla. Arrastra tus islas para moverlas, o usa las flechas del teclado. Dentro puedes girarlas con el dedo.':'Toca una huella para abrirla. Su forma sale de lo que tiene dentro: crece con lo que guardas y brilla con lo que tocaste hace poco.';
  if(vista==='islas'&&!window.VoidPaisajeIslas){cargar3d().then(pintarVistas,e=>{vista='huellas';aviso(e.message);pintarVistas();});return;}
  if(!paisaje)paisaje=vista==='islas'?window.VoidPaisajeIslas($('islas-mapa'),$('islas-etiquetas'),{abrir,mover,fallo:falloPaisaje}):window.VoidHuellasIslas($('islas-mapa'),$('islas-etiquetas'),{abrir,fallo:falloPaisaje});
  const datos=todas();if(actual)pagina=Math.floor(datos.findIndex(d=>d.id===actual)/8);
  pagina=Math.max(0,Math.min(pagina,Math.ceil(datos.length/8)-1));
  paisaje.pintar(datos.slice(pagina*8,pagina*8+8),actual);
  const paginas=$('islas-paginas');paginas.replaceChildren();
  if(datos.length>8){paginas.append(boton('Página anterior',()=>{pagina--;pintarVistas();},pagina===0));const texto=document.createElement('span');texto.textContent=`${pagina+1} de ${Math.ceil(datos.length/8)}`;paginas.append(texto,boton('Página siguiente',()=>{pagina++;pintarVistas();},pagina>=Math.ceil(datos.length/8)-1));}
 }catch{falloPaisaje('No se pudo dibujar el paisaje. Puedes seguir en la lista.');}
}
function pintar(){
 $('islas-lista').replaceChildren();
 for(const d of todas()){
  const li=document.createElement('li'),b=d.destino?document.createElement('a'):document.createElement('button'),punto=document.createElement('span'),nombre=document.createElement('span'),tipo=document.createElement('small');
  punto.className='islas-punto';punto.style.setProperty('--isla-color',d.color);punto.setAttribute('aria-hidden','true');nombre.textContent=d.nombre;tipo.textContent=d.destino?'Sección':'Privada';
  if(d.destino)b.href='#'+d.destino;else b.type='button';
  b.dataset.id=d.id;b.append(punto,nombre,tipo);b.onclick=e=>{e.preventDefault();abrir(d.id);};li.append(b);$('islas-lista').append(li);
 }
 $('islas-vistas').hidden=!disponible;
 $('islas-danadas').hidden=danadas.length===0;$('islas-danadas').textContent=danadas.map(d=>'Hay una isla que no se puede leer: '+d.archivo+'.').join(' ');
 pintarVistas();controles();
}
async function recargar(mensaje){
 if(!activo||pendientes>0||cargando)return;
 const g=generacion,l=++lectura;cargando=true;controles();aviso('Cargando tus islas…');
 try{
  const d=await api('listar');if(g!==generacion||l!==lectura)return;
  if(!Array.isArray(d.islas)||!Array.isArray(d.danadas))throw Error('La respuesta de las islas no se pudo leer.');
  registros=d.islas;danadas=d.danadas;disponible=true;
  if(actual&&!registros.some(r=>r.isla.id===actual))volver(false);
  if(actual)editor();pintar();aviso(mensaje||(registros.length+danadas.length>=40?'Ya tienes 40 islas. Puedes abrirlas y cambiarlas.':'Tus islas son privadas y se guardan en tu vault.'));
  $('islas-recargar').hidden=false;
 }catch(e){if(g!==generacion||l!==lectura)return;tratarError(e,false);}
 finally{if(g===generacion&&l===lectura){cargando=false;controles();}}
}
function tratarError(e,escritura){
 if(e.status===401){limpiar();$('islas').hidden=true;return;}
 if(e.dormida){noDisponible('Tu espacio está dormido. Despiértalo para ver tus islas.');return;}
 if(e.status===423){noDisponible('Tu candado está cerrado. Ábrelo para ver tus islas.');return;}
 if(!escritura){disponible=false;destruirPaisaje();$('islas-vistas').hidden=true;$('islas-nueva').disabled=true;$('islas-recargar').hidden=false;}
 const texto=e.status===503?'Las islas todavía no están disponibles en esta caja.':e.message||'No pudimos conectar con tus islas.';
 aviso(texto+(escritura?' El cambio no se ha confirmado. Puedes volver a guardarlo.':' Tus secciones siguen debajo.'));
}
// Las operaciones se encadenan. La revisión se lee al ejecutar, nunca al encolar.
function cambiar(operacion){
 if(!activo||!disponible)return Promise.resolve(false);
 const g=generacion;pendientes++;controles();
 const trabajo=cola.then(async()=>{
  if(g!==generacion)return false;
  aviso('Guardando tu isla…');
  try{const resultado=await operacion(()=>g===generacion);return g===generacion&&resultado!==false;}
  catch(e){if(g!==generacion)return false;
   if(e.status===409&&!e.dormida){
    cerrarDialogos();disponible=false;aviso('La isla cambió en otro sitio. Recargando la versión guardada…');
    // Invalida también cualquier gesto en espera que partiera de la versión anterior.
    const id=actual;limpiar();activo=true;actual=id;await recargar('La isla cambió en otro sitio. Hemos recargado la versión guardada. Revisa tus cambios antes de repetirlos.');
   }else tratarError(e,true);
   return false;
  }finally{if(g===generacion){pendientes--;controles();}}
 });
 cola=trabajo.catch(()=>false);return trabajo;
}
function validarTamano(isla){if(new TextEncoder().encode(JSON.stringify(isla)).length>64*1024-256)throw Error('Esta isla se acerca al límite de 64 KiB. Acorta el texto antes de guardar.');}
async function guardar(isla,revision,vigente){
 isla.publica=false;validarTamano(isla);
 const d=await api('guardar',{isla,revision});if(!vigente())return false;
 if(d.guardado!==true||typeof d.revision!=='string')throw Error('No pudimos confirmar el guardado. Recarga las islas antes de repetirlo.');
 const indice=registros.findIndex(r=>r.isla.id===isla.id),registro={isla,revision:d.revision};if(indice<0)registros.push(registro);else registros[indice]=registro;
 pintar();aviso('Isla guardada.');return true;
}
function mover(id,posicion){
 cambiar(async vigente=>{const r=registros.find(r=>r.isla.id===id);if(!r)return false;const d=clonar(r.isla);d.posicion=posicion;await guardar(d,r.revision,vigente);if(vigente())$('islas-etiquetas').querySelector(`[data-id="${id}"]`)?.focus({preventScroll:true});});
}
function boton(texto,accion,deshabilitado=false){const b=document.createElement('button');b.type='button';b.textContent=texto;b.disabled=deshabilitado;b.onclick=accion;return b;}
function campo(padre,texto,nombre,valor,tipo='text',maximo){
 const label=document.createElement('label'),input=document.createElement(tipo==='textarea'?'textarea':'input');
 if(tipo!=='textarea')input.type=tipo;input.name=nombre;input.value=valor;if(maximo)input.maxLength=maximo;label.append(document.createTextNode(texto),input);padre.append(label);return input;
}
function opciones(padre,texto,nombre,valor,valores){const label=document.createElement('label'),select=document.createElement('select');select.name=nombre;for(const v of valores){const o=document.createElement('option');o.value=v;o.textContent=v[0].toUpperCase()+v.slice(1);select.append(o);}select.value=valor;label.append(document.createTextNode(texto),select);padre.append(label);}
function abrir(id){
 const fija=fijas.find(d=>d.id===id);
 if(fija){window.VoidEspacio.zona(fija.destino);const n=$(fija.destino);n.tabIndex=-1;n.focus({preventScroll:true});n.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});return;}
 if(!disponible||pendientes)return;
 origen=document.activeElement;actual=id;editor();pintarVistas();$('islas-volver').focus({preventScroll:true});
}
function volver(foco=true){actual=null;$('islas-panel').hidden=true;$('islas-panel').replaceChildren();pintarVistas();if(foco){if(origen?.isConnected)origen.focus({preventScroll:true});else{const b=$('islas-lista').querySelector('[data-id]');(lista?b:$('islas-lista-boton'))?.focus({preventScroll:true});}}}
function leerEditor(form,isla){
 const d=clonar(isla),v=n=>form.elements.namedItem(n).value;
 d.nombre=v('nombre').trim();d.color=v('color');d.forma=v('forma');d.estilo=v('estilo');
 d.bloques.forEach((b,i)=>{
  if(b.tipo==='nota')b.texto=v('nota-'+i);
  if(b.tipo==='contador'){b.valor=Number(v('valor-'+i));b.meta=Number(v('meta-'+i));b.unidad=v('unidad-'+i);}
  if(b.tipo==='tareas')b.items.forEach((t,j)=>{t.texto=v(`tarea-${i}-${j}`).trim();t.hecho=form.elements.namedItem(`hecho-${i}-${j}`).checked;});
 });return d;
}
function editor(){
 const r=registros.find(r=>r.isla.id===actual);if(!r)return;const isla=r.isla,panel=$('islas-panel');panel.hidden=false;panel.replaceChildren();
 const vuelta=boton('Volver al archipiélago',()=>volver());vuelta.id='islas-volver';panel.append(vuelta);
 const h=document.createElement('h3');h.id='islas-panel-titulo';h.textContent=isla.nombre;panel.append(h);
 const pista=document.createElement('p');pista.className='secundario';pista.textContent='Privada. Los cambios se guardan al salir de cada campo. También puedes pulsar Guardar cambios.';panel.append(pista);
 const form=document.createElement('form'),fs=document.createElement('fieldset');form.append(fs);panel.append(form);
 const ajustes=document.createElement('div');ajustes.className='islas-personalizar';fs.append(ajustes);
 campo(ajustes,'Nombre','nombre',isla.nombre,'text',80).required=true;campo(ajustes,'Color','color',isla.color,'color');
 opciones(ajustes,'Forma','forma',isla.forma,formas);opciones(ajustes,'Estilo','estilo',isla.estilo,estilos);
 const guardarEditor=mutar=>{
  if(!form.reportValidity()||pendientes)return;
  const d=leerEditor(form,isla);if(mutar)mutar(d);
  if(!d.nombre||d.bloques.some(b=>b.tipo==='tareas'&&b.items.some(t=>!t.texto))){aviso('Pon un nombre y un texto en cada tarea antes de guardar.');return;}
  const foco=document.activeElement?.name;
  cambiar(async vigente=>{const registro=registros.find(r=>r.isla.id===d.id);if(!registro)return false;const ok=await guardar(d,registro.revision,vigente);if(ok&&actual===d.id){editor();if(foco)$('islas-panel').querySelector(`[name="${foco}"]`)?.focus({preventScroll:true});}return ok;});
 };
 isla.bloques.forEach((b,i)=>{
  const seccion=document.createElement('div');seccion.className='islas-bloque';const titulo=document.createElement('h4');titulo.textContent=b.titulo||({nota:'Nota',tareas:'Tareas',contador:'Contador',enlace:'Enlace',tabla:'Tabla'}[b.tipo]);seccion.append(titulo);fs.append(seccion);
  if(b.tipo==='nota')campo(seccion,'Tu nota','nota-'+i,b.texto,'textarea',65536);
  if(b.tipo==='contador'){
   const valor=campo(seccion,'Valor','valor-'+i,b.valor,'number');valor.min=-1e9;valor.max=1e9;valor.step='any';valor.required=true;
   const meta=campo(seccion,'Meta','meta-'+i,b.meta,'number');meta.min=0;meta.max=1e9;meta.step='any';meta.required=true;
   campo(seccion,'Unidad','unidad-'+i,b.unidad,'text',40);
   const fila=document.createElement('div');fila.className='fila';fila.append(boton('Restar uno',()=>{valor.value=Number(valor.value)-1;guardarEditor();},b.valor<=-1e9),boton('Sumar uno',()=>{valor.value=Number(valor.value)+1;guardarEditor();},b.valor>=1e9));seccion.append(fila);
  }
  if(b.tipo==='tareas'){
   b.items.forEach((t,j)=>{
    const fila=document.createElement('div');fila.className='islas-tarea';const label=document.createElement('label'),check=document.createElement('input');check.type='checkbox';check.name=`hecho-${i}-${j}`;check.checked=t.hecho;check.setAttribute('aria-label','Hecha: '+t.texto);
    const texto=document.createElement('input');texto.type='text';texto.value=t.texto;texto.maxLength=1000;texto.required=true;texto.name=`tarea-${i}-${j}`;texto.setAttribute('aria-label','Texto de la tarea '+(j+1));label.append(check,texto);fila.append(label,boton('Quitar',()=>guardarEditor(d=>d.bloques[i].items.splice(j,1))));seccion.append(fila);
   });
   const nueva=campo(seccion,'Nueva tarea','nueva-'+i,'','text',1000);nueva.placeholder='Algo que quieras hacer';
   const anadir=boton('Añadir tarea',()=>{const texto=nueva.value.trim();if(texto)guardarEditor(d=>d.bloques[i].items.push({texto,hecho:false}));else nueva.focus();},b.items.length>=200);seccion.append(anadir);
   nueva.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();anadir.click();}};
  }
  if(b.tipo==='enlace'){
   // Solo una dirección HTTP(S) sin credenciales puede convertirse en enlace.
   try{const u=new URL(b.url);if(!['http:','https:'].includes(u.protocol)||u.username||u.password)throw Error();const a=document.createElement('a');a.href=u.href;a.textContent=b.url;a.target='_blank';a.rel='noopener noreferrer';seccion.append(a);}catch{seccion.append(document.createTextNode('Este enlace no se puede abrir.'));}
  }
  if(b.tipo==='tabla'){
   const caja=document.createElement('div'),tabla=document.createElement('table');caja.className='islas-tabla';caja.tabIndex=0;caja.setAttribute('role','region');caja.setAttribute('aria-label',b.titulo||'Tabla');const head=document.createElement('thead'),tr=document.createElement('tr');for(const c of b.columnas){const th=document.createElement('th');th.scope='col';th.textContent=c;tr.append(th);}head.append(tr);tabla.append(head);const body=document.createElement('tbody');for(const fila of b.filas){const tr=document.createElement('tr');for(const c of fila){const td=document.createElement('td');td.textContent=c;tr.append(td);}body.append(tr);}tabla.append(body);caja.append(tabla);seccion.append(caja);
  }
 });
 const acciones=document.createElement('div');acciones.className='islas-guardar fila';const guardarBoton=document.createElement('button');guardarBoton.className='principal';guardarBoton.textContent='Guardar cambios';acciones.append(guardarBoton);fs.append(acciones);
 form.onsubmit=e=>{e.preventDefault();guardarEditor();};form.onchange=e=>{if(!e.target.name?.startsWith('nueva-'))guardarEditor();};
 const publicar=boton('Publicar como estrella · pronto',()=>{},true);panel.append(publicar,boton('Borrar isla',()=>{
  $('islas-borrar-texto').textContent=`Se borrará «${isla.nombre}» con sus tareas, notas y contadores. ¿Quieres borrarla?`;$('islas-borrar-estado').textContent='';$('islas-confirmar').showModal();
 }));controles();
}
function plantilla(nombre,tipo){
 const n=registros.length+4,cols=$('islas-mapa').clientWidth>=660?4:2,slot=n%8;
 const d={formato:1,id:'isla-'+crypto.randomUUID(),nombre,icono:'',color:'#75984b',forma:'redonda',estilo:'viva',posicion:{x:(slot%cols+.5)/cols,y:(Math.floor(slot/cols)+.5)/(8/cols)},publica:false,plantilla:tipo,bloques:[]};
 if(tipo!=='notas@1')d.bloques.push({id:'tareas',tipo:'tareas',titulo:tipo==='semana@1'?'Esta semana':'Próximos pasos',items:[]});
 if(tipo==='proyecto@1')d.bloques.push({id:'avance',tipo:'contador',titulo:'Avance',valor:0,meta:10,unidad:'pasos'});
 d.bloques.push({id:'nota',tipo:'nota',titulo:'Notas',texto:''});return d;
}
$('islas-lista-boton').onclick=()=>{if(actual)volver(false);lista=!lista;pintarVistas();};
$('islas-vista-boton').onclick=()=>{vista=vista==='islas'?'huellas':'islas';try{localStorage.setItem('void-vista-mapa',vista);}catch{}destruirPaisaje();lista=false;pintarVistas();};
$('islas-recargar').onclick=()=>recargar();
$('islas-nueva').onclick=()=>{$('islas-crear-form').reset();$('islas-crear-estado').textContent='';$('islas-crear').showModal();};
$('islas-cancelar-crear').onclick=()=>$('islas-crear').close();
$('islas-crear-form').onsubmit=async e=>{
 e.preventDefault();if(pendientes)return;const f=e.currentTarget,nombre=f.elements.nombre.value.trim();if(!nombre){f.elements.nombre.focus();return;}
 const d=plantilla(nombre,f.elements.plantilla.value);$('islas-crear-estado').textContent='Creando tu isla…';
 const ok=await cambiar(vigente=>guardar(d,null,vigente));if(ok){$('islas-crear').close();abrir(d.id);}else if($('islas-crear').open)$('islas-crear-estado').textContent=$('islas-estado').textContent;
};
$('islas-borrar-no').onclick=()=>$('islas-confirmar').close();
$('islas-borrar-si').onclick=async()=>{
 if(pendientes||!actual)return;const id=actual;$('islas-borrar-estado').textContent='Borrando tu isla…';
 const ok=await cambiar(async vigente=>{const r=registros.find(r=>r.isla.id===id);if(!r)return false;const d=await api('borrar',{id,revision:r.revision});if(!vigente())return false;if(d.borrado!==true)throw Error('No pudimos confirmar el borrado. Recarga las islas.');registros=registros.filter(r=>r.isla.id!==id);return true;});
 if(ok){$('islas-confirmar').close();volver(false);pintar();aviso('Isla borrada.');$('islas-nueva').focus();}else if($('islas-confirmar').open)$('islas-borrar-estado').textContent=$('islas-estado').textContent;
};
addEventListener('keydown',e=>{if(e.key==='Escape'&&actual&&!$('islas-confirmar').open&&!$('islas-crear').open){e.preventDefault();volver();}});
addEventListener('void-abrir',()=>{limpiar();$('islas').hidden=false;aviso('Mirando tus islas…');});
addEventListener('void-salir',()=>{limpiar();$('islas').hidden=true;});
function estadoEspacio(est){
 if(!window.VoidEspacio.dueno)return;
 if(!est.abierto){noDisponible('Tu candado está cerrado. Ábrelo para ver tus islas.');return;}
 if(!est.despierta){noDisponible('Tu espacio está dormido. Despiértalo para ver tus islas.');return;}
 $('islas').hidden=false;if(!activo){activo=true;recargar();}
}
addEventListener('void-estado-espacio',e=>estadoEspacio(e.detail));
if(window.VoidEspacio?.dueno){$('islas').hidden=false;if(window.VoidEspacio.situacion)estadoEspacio(window.VoidEspacio.situacion);}
})();
