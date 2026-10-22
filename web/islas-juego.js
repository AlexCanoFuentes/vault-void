/* M-15 · KERNEL 82 · Codex · 22-oct-2026. Dos distancias, la misma materia.
   Cada campo madura en turnos cortos y se congela. No hay un bucle de química permanente.
   Esta vista es opcional: islas.js recupera VoidHuellasIslas si falla. */
(()=>{
'use strict';
let cercaRecordado=false;
window.VoidJuegoIslas=function(contenedor,etiquetas,{abrir,mover,esconder,delVault,fallo}){
  if(!window.VoidHuella||!window.VoidPlano||!window.VoidVacio||!window.VoidCamposIslas)throw Error('No se pudo cargar el juego de huellas.');
  const reducido=matchMedia('(prefers-reduced-motion: reduce)'),eventos=new AbortController();let eventosNodos=new AbortController();
  const escuchar=(n,t,f,o={})=>n.addEventListener(t,f,{...o,signal:eventos.signal});
  const crear=(tag,clase,texto)=>{const n=document.createElement(tag);n.className=clase;if(texto)n.textContent=texto;return n;};
  const boton=(clase,texto,accion)=>{const b=crear('button',clase,texto);b.type='button';b.onclick=accion;return b;};
  const decorado=crear('div','islas-juego-decorado');decorado.setAttribute('aria-hidden','true');
  const fondo=crear('canvas','islas-plano');decorado.append(fondo);const ctxFondo=fondo.getContext('2d');if(!ctxFondo)throw Error('Sin lienzo');
  const lejos=crear('button','islas-lejos islas-huella-grande');lejos.type='button';lejos.setAttribute('aria-label','Entrar en mis islas tocando mi huella');
  const NGrande=512;
  const grande=crear('canvas','islas-huellas');grande.width=grande.height=NGrande;grande.setAttribute('aria-hidden','true');lejos.append(grande);
  const ctxGrande=grande.getContext('2d');if(!ctxGrande)throw Error('No se pudo dibujar tu huella.');
  const entrada=crear('nav','islas-menu-entrada');entrada.setAttribute('aria-label','Menú de mi huella');
  const entrar=boton('islas-acercar islas-juego-principal','Entrar',()=>zoom(true));
  entrada.append(entrar,boton('islas-juego-comunidad','Comunidad',()=>abrir('fija_comunidad')),boton('islas-juego-cuentas','Mis cuentas',()=>abrir('fija_modelos')));
  // La oferta y sus cambios los decide instalar.js (también las instrucciones de Safari).
  const instalacion=crear('div','islas-juego-instalar');instalacion.hidden=true;
  document.getElementById('islas-vistas').after(instalacion);
  const volver=boton('islas-alejar','Volver',()=>zoom(false));
  const donde=crear('span','islas-donde','Tu huella'),masBoton=boton('islas-mas','Más',mas);
  function mas(){const h=document.getElementById('islas-titulo');h.tabIndex=-1;h.scrollIntoView({behavior:'instant',block:'start'});h.focus({preventScroll:true});}
  const menu=crear('div','islas-menu-isla');menu.hidden=true;menu.setAttribute('role','group');
  const abrirIsla=boton('islas-juego-principal','Abrir',()=>{if(elegida)abrir(elegida);});
  const moverIsla=boton('','Mover',()=>modoMover());
  const ocultar=boton('','Esconder',()=>{if(elegida&&!etiquetas.inert)esconder?.(elegida);});
  const cerrar=boton('islas-juego-cerrar','Volver',()=>seleccionar(null,true));
  menu.append(abrirIsla,moverIsla,ocultar,cerrar);
  const estado=crear('p','islas-juego-estado');estado.setAttribute('role','status');
  if(!cercaRecordado)contenedor.classList.add('islas-primera-visita');contenedor.dataset.publicacion='cargando';contenedor.prepend(decorado,lejos);contenedor.append(entrada,volver,donde,masBoton,menu,estado);contenedor.classList.add('vista-juego');
  const zona=crear('div','islas-zona-inicial');zona.setAttribute('aria-hidden','true');document.body.prepend(zona);
  document.body.classList.add('modo-plano','plano-visible');
  window.VoidInstalar?.montar(instalacion);
  const instalar=instalacion.querySelector('button');if(instalar)instalar.textContent='Instalar';
  let cerca=cercaRecordado,destruido=false,elegida=null,enMovimiento=null,datos=[],firmaGrande='',viaje=0,rafParallax=0,tecla=null;
  let pan=null,gesto=null,desplazamiento={x:0,y:0};
  let todasIslas=[],detalleAnterior=false,primeraPintura=true;
  let W=innerWidth,H=innerHeight,publico=null,propia=null,origen={x:0,y:0},vista={x:0,y:0,s:1},anterior=null,vuelo=null,rafMundo=0,visible=true;
  const L=360;
  const plano=()=>VoidPlano.crear({x:vista.x+desplazamiento.x,y:vista.y+desplazamiento.y,s:vista.s},W,H);
  const escala=()=>Math.min(W/(cerca?400:650),H/600,2);
  const cartelGrande=()=>{const r=plano().cartel(origen,Math.min(W*.94,H*.52,440)/vista.s);if(r)r.y+=r.h/2-H*.1;return r;};
  function activo(){return !destruido&&visible&&!document.hidden&&!document.querySelector('dialog[open]');}
  function despertar(){if(activo()){contenedor.classList.remove('islas-en-pausa');if(!rafMundo)rafMundo=requestAnimationFrame(mundo);motorPausa(false);}}
  function parar(){contenedor.classList.add('islas-en-pausa');cancelarGesto();cancelarTecla();if(pan&&contenedor.hasPointerCapture(pan.id))contenedor.releasePointerCapture(pan.id);pan=null;dedos.clear();distancia0=0;motorPausa(true);cancelAnimationFrame(rafMundo);cancelAnimationFrame(rafParallax);rafMundo=rafParallax=0;contenedor.dataset.trabajando='false';}
  function mundo(now){
    rafMundo=0;if(!activo())return;
    try{
      if(vuelo){const t=Math.min(1,(now-vuelo.t)/650),e=1-(1-t)**3;for(const k of ['x','y','s'])vista[k]=vuelo.de[k]+(vuelo.a[k]-vuelo.de[k])*e;if(t===1)vuelo=null;}
      contenedor.dataset.camara=JSON.stringify(vista);
      ctxFondo.setTransform(fondo.width/W,0,0,fondo.height/H,0,0);ctxFondo.clearRect(0,0,W,H);
      const v={x:vista.x+desplazamiento.x,y:vista.y+desplazamiento.y,s:vista.s};let pendiente=false;
      if(publico){pendiente=publico.avanzar(v,W,H,true,false);publico.omitir(propia);publico.pintar(ctxFondo,v,W,H,now,true);}
      else plano().reticula(ctxFondo);
      const r=cartelGrande();if(r){lejos.style.left=r.x+'px';lejos.style.top=r.y+'px';lejos.style.width=r.w+'px';lejos.style.height=r.h+'px';}
      for(const b of etiquetas.children)posicionar(b,b._sitio||sitio(porId(b.dataset.id)));
      contenedor.dataset.trabajando=String(!!(pendiente||vuelo||trabajos.size));
      if(pendiente||vuelo)despertar();
    }catch{fallo('No se pudo dibujar el plano.');}
  }
  function tam(){W=innerWidth;H=innerHeight;const dpr=Math.min(devicePixelRatio||1,2);fondo.width=Math.round(W*dpr);fondo.height=Math.round(H*dpr);vista.s=escala();distribuir();despertar();}
  escuchar(window,'resize',tam);
  const regresar=boton('islas-regresar','Mundo',()=>zona.scrollIntoView({block:'start',behavior:'instant'}));document.getElementById('islas-titulo').parentElement.append(regresar);
  const observador=new IntersectionObserver(es=>{visible=es[0].isIntersecting;document.body.classList.toggle('plano-visible',visible);if(visible)despertar();else{cancelarGesto();cancelarTecla();parar();}}, {threshold:.05});observador.observe(zona);
  const dialogos=new MutationObserver(()=>{if(activo())despertar();else parar();});dialogos.observe(document.body,{subtree:true,attributes:true,attributeFilter:['open']});
  const peticion=new AbortController();
  async function cargarPublico(){
    try{let lista=[],cursor=null;const vistos=new Set();do{
      const r=await fetch('https://red.vaultvoid.app/v1/huellas'+(cursor?'?cursor='+encodeURIComponent(cursor):''),{headers:{accept:'application/json'},signal:peticion.signal});if(!r.ok)throw Error('red');const d=await r.json();if(!Array.isArray(d.huellas))throw Error('respuesta');lista.push(...d.huellas);cursor=d.siguiente||null;if(cursor&&vistos.has(cursor))throw Error('paginación');vistos.add(cursor);
    }while(cursor);
    if(destruido)return;publico=VoidVacio.crear(lista,{plano:true});propia=publico.territorios.find(t=>t.alias===window.VoidEspacio.dueno?.alias)||null;
    origen=propia?{x:propia.x,y:propia.y}:{x:0,y:0};contenedor.dataset.origen=JSON.stringify(origen);vista.x=origen.x;vista.y=origen.y;anterior=null;
    contenedor.dataset.publicacion=propia?'publicada':'no-publicada';if(propia){quitarCampo(grande);preparar(grande,ctxGrande,[propia.entrada],NGrande);}
    distribuir();
    despertar();
    }catch(e){if(destruido)return;contenedor.dataset.publicacion='error';donde.textContent='Sin conexión';estado.textContent='No se pudo cargar el lienzo público. Tus islas siguen disponibles.';}
  }
  const cache=new Map(),trabajos=new Map();
  let motor=null,worker=null,secuencia=0;
  const dedos=new Map();let distancia0=0,suprimirClick=0;
  const FIJAS={fija_hablar:{x:.18,y:.2},fija_comunidad:{x:.82,y:.2},fija_modelos:{x:.18,y:.82},fija_cuidar:{x:.82,y:.82}};
  const sitio=d=>d.destino?FIJAS[d.id]||{x:.5,y:.5}:d.posicion||{x:.5,y:.5};
  const limitar=(v,min,max)=>Math.min(max,Math.max(min,v));
  const porId=id=>datos.find(d=>d.id===id);
  const nodo=id=>[...etiquetas.children].find(b=>b.dataset.id===id);
  function tono(hex){
    const n=parseInt(String(hex).slice(1),16),r=(n>>16&255)/255,g=(n>>8&255)/255,b=(n&255)/255,max=Math.max(r,g,b),min=Math.min(r,g,b),d=max-min;
    if(!d)return 80;const h=max===r?((g-b)/d)%6:max===g?(b-r)/d+2:(r-g)/d+4;return (h*60+360)%360;
  }
  function cifras(d,puesto){
    if(d.destino)return {dias:150,pulso:40,decisiones:3,proyectos:3,calladas:0,tono:tono(d.color)};
    let hechas=0,pendientes=0,otros=0;
    for(const b of d.bloques||[]){
      if(b.tipo==='tareas')for(const t of b.items)t.hecho?hechas++:pendientes++;
      else if(b.tipo==='tabla')otros+=b.filas.length;
      else if(b.tipo==='nota')otros+=b.texto.trim()?1:0;
      else otros++;
    }
    const fecha=Date.parse(d.actualizado),edad=Number.isFinite(fecha)?Math.max(0,Math.floor((Date.now()-fecha)/864e5)):(delVault(d.id)?puesto*3:30);
    return {dias:Math.min(365,160+30*(hechas+pendientes+otros)),pulso:Math.max(18,60-2*edad),decisiones:hechas+1,proyectos:pendientes+otros+1,calladas:0,tono:tono(d.color)};
  }
  function materia(d,i,pos){return {alias:d.id,semilla:d.id,pos,huella:cifras(d,i)};}
  function recibir(id,imagen,lista){
    const t=trabajos.get(id);if(!t||destruido){imagen.close?.();return;}
    t.ctx.clearRect(0,0,t.N,t.N);t.ctx.drawImage(imagen,0,0,t.N,t.N);imagen.close?.();
    t.canvas.dataset.quimica=lista?'lista':'visible';
    if(!t.canvas.dataset.visibleDesde)t.canvas.dataset.visibleDesde=String(performance.now());
    if(lista)trabajos.delete(id);despertar();
  }
  function local(){
    worker?.terminate();worker=null;
    motor=VoidCamposIslas.crear({
      lienzo:N=>{const c=document.createElement('canvas');c.width=c.height=N;return c;},
      entregar:recibir,error:()=>fallo('No se pudo completar el juego de huellas.'),presupuesto:4
    });
    for(const [id,t] of trabajos)motor.preparar(id,t.lista,t.N);
    motor.pausar(!activo());
  }
  function iniciarMotor(){
    if(motor||worker)return;
    if(typeof Worker==='undefined'||typeof OffscreenCanvas==='undefined'){local();return;}
    try{
      worker=new Worker('/islas-campos-worker.js');
      worker.onmessage=({data:d})=>{if(d.error)local();else recibir(d.id,d.bitmap,d.lista);};
      worker.onerror=e=>{e.preventDefault();local();};
    }catch{local();}
  }
  function motorPausa(si){motor?.pausar(si);worker?.postMessage({tipo:'pausa',si});}
  function quitarCampo(canvas){
    for(const [id,t] of trabajos)if(t.canvas===canvas){trabajos.delete(id);motor?.quitar(id);worker?.postMessage({tipo:'quitar',id});}
  }
  function preparar(canvas,ctx,lista,N){
    iniciarMotor();const id=++secuencia;canvas.dataset.quimica='preparando';delete canvas.dataset.visibleDesde;
    canvas.dataset.inicio=String(performance.now());trabajos.set(id,{canvas,ctx,lista,N});
    if(worker)worker.postMessage({tipo:'preparar',id,lista,N});else motor.preparar(id,lista,N);
    motorPausa(!activo());despertar();
  }
  escuchar(document,'visibilitychange',()=>{if(document.hidden)parar();else despertar();});
  // El tamaño es común en el mundo: lo reduce la distancia, nunca una celda de pantalla.
  let lugares=new Map();
  function distribuir(){
    if(!datos.length)return;
    lugares=VoidJuegoIslas.distribucion(W,H,datos.map(d=>({id:d.id,posicion:sitio(d)})),origen);
  }
  function cartelIsla(b,s){const d=porId(b.dataset.id),base=lugares.get(d.id);if(!base)return null;const pos=sitio(d);return plano().cartel({x:base.x+L*(s.x-pos.x),y:base.y+L*(s.y-pos.y)},base.lado);}
  function posicionar(b,s){const r=cartelIsla(b,s);if(!r){b.style.visibility='hidden';return;}b.style.visibility='';b.style.left=r.x+'px';b.style.top=r.y+'px';b.style.width=r.w+'px';b.style.height=r.h+'px';b.style.zIndex=String(Math.round(10000-r.z));b.dataset.profundidad=String(r.z);b.style.setProperty('--brillo','1.25');b.style.setProperty('--par-x',desplazamiento.x+'px');}
  function nivel(){
    contenedor.classList.toggle('de-cerca',cerca);contenedor.dataset.nivel=elegida?'3':cerca?'2':'1';
    entrada.hidden=cerca||!!elegida;volver.hidden=!cerca||!!elegida;donde.textContent=elegida?porId(elegida).nombre:cerca?'Tus islas':contenedor.dataset.publicacion==='error'?'Sin conexión':'Tu huella';lejos.disabled=cerca;lejos.hidden=cerca;lejos.setAttribute('aria-hidden',String(cerca));
    etiquetas.setAttribute('aria-hidden',String(!cerca));
    contenedor.closest('#islas-mapa-grupo')?.classList.toggle('islas-grupo-dentro',cerca);
  }
  function zoom(si){
    if(destruido||cerca===si)return;
    cancelarGesto();cancelarTecla();seleccionar(null);clearTimeout(viaje);
    if(si)anterior={...vista};const meta=si?{x:origen.x,y:origen.y,s:Math.min(W/400,H/600,2)}:anterior||{x:origen.x,y:origen.y,s:Math.min(W/650,H/600,2)};
    if(reducido.matches)vista={...meta};else vuelo={de:{...vista},a:meta,t:performance.now()};
    cerca=cercaRecordado=si;if(si)contenedor.classList.remove('islas-primera-visita');nivel();despertar();
    contenedor.classList.toggle('islas-viajando',si&&!reducido.matches);
    estado.textContent=si?'Tus islas. Toca una para ver sus opciones.':'Tu huella reúne tus islas.';
    (si?volver:entrar).focus({preventScroll:true});
    if(si&&!reducido.matches)viaje=setTimeout(()=>contenedor.classList.remove('islas-viajando'),760);
    else contenedor.classList.remove('islas-viajando');
  }
  lejos.onclick=()=>{if(performance.now()>=suprimirClick)zoom(true);};nivel();
  function seleccionar(id,foco=false){
    if(etiquetas.inert&&id)return;
    const anterior=elegida;elegida=id;enMovimiento=null;
    contenedor.classList.toggle('islas-con-seleccion',!!id);contenedor.classList.remove('islas-moviendo');
    for(const b of etiquetas.children){const si=b.dataset.id===id;b.classList.toggle('islas-delante',si);b.setAttribute('aria-pressed',String(si));b.setAttribute('aria-expanded',String(si));}
    menu.hidden=!id;volver.hidden=!cerca||!!id;entrada.hidden=cerca||!!id;donde.textContent=id?porId(id).nombre:cerca?'Tus islas':'Tu huella';contenedor.dataset.nivel=id?'3':cerca?'2':'1';
    if(id){
      const d=porId(id);menu.setAttribute('aria-label','Opciones de '+d.nombre);
      moverIsla.hidden=!!d.destino;ocultar.hidden=!!d.destino||!delVault(id);
      estado.textContent=d.nombre;abrirIsla.focus({preventScroll:true});
    }else if(foco)nodo(anterior)?.focus({preventScroll:true});
  }
  function modoMover(){
    if(!elegida||etiquetas.inert)return;const id=elegida;seleccionar(null);enMovimiento=id;
    contenedor.classList.add('islas-moviendo');nodo(id)?.focus({preventScroll:true});
    estado.textContent='Arrastra la isla dentro de la retícula o usa las flechas. Pulsa Escape para terminar.';
  }
  // Busca un hueco válido también en los bordes y en grupos de varias islas.
  function libre(id,x,y){
    const valido=p=>todasIslas.every(d=>d.id===id||Math.hypot(sitio(d).x-p.x,sitio(d).y-p.y)>=.125);
    const redondear=p=>({x:Math.round(p.x*1000)/1000,y:Math.round(p.y*1000)/1000});
    const p=redondear({x:limitar(x,.08,.92),y:limitar(y,.12,.86)});if(valido(p))return p;
    for(let r=.02;r<1.3;r+=.02)for(let a=0;a<Math.PI*2;a+=Math.PI/12){
      const q=redondear({x:limitar(p.x+Math.cos(a)*r,.08,.92),y:limitar(p.y+Math.sin(a)*r,.12,.86)});if(valido(q))return q;
    }
    return sitio(porId(id));
  }
  function cancelarTecla(){
    if(!tecla)return;clearTimeout(tecla.timer);delete tecla.b._sitio;posicionar(tecla.b,sitio(tecla.d));tecla=null;
  }
  function cancelarGesto(){
    if(!gesto)return;const g=gesto;gesto=null;g.b.classList.remove('arrastrando');delete g.b._sitio;posicionar(g.b,sitio(g.d));
    if(g.b.hasPointerCapture(g.id))g.b.releasePointerCapture(g.id);
  }
  function guardarTecla(){
    if(!tecla)return;const t=tecla;tecla=null;clearTimeout(t.timer);delete t.b._sitio;
    if(!etiquetas.inert)mover(t.d.id,t.pos);
  }
  function arrastrable(b,d){
    const escuchar=(n,t,f)=>n.addEventListener(t,f,{signal:eventosNodos.signal});
    escuchar(b,'pointerdown',e=>{
      if(e.button!==0||etiquetas.inert||!cerca||dedos.size>1)return;
      const ancla=plano().inversa(e.clientX,e.clientY);if(!ancla)return;cancelarTecla();gesto={b,d,id:e.pointerId,x:e.clientX,y:e.clientY,ancla,arrastrando:false};
    });
    escuchar(b,'pointermove',e=>{
      const g=gesto;if(!g||g.b!==b||g.id!==e.pointerId)return;
      if(!g.arrastrando&&Math.hypot(e.clientX-g.x,e.clientY-g.y)<10)return;
      if(!g.arrastrando){g.arrastrando=true;seleccionar(null);b.setPointerCapture(e.pointerId);b.classList.add('arrastrando');}
      const q=plano().inversa(e.clientX,e.clientY);if(!q)return;const p=sitio(d);b._sitio={x:p.x+(q.x-g.ancla.x)/L,y:p.y+(q.y-g.ancla.y)/L};posicionar(b,b._sitio);
    });
    const soltar=(e,vale)=>{
      const g=gesto;if(!g||g.b!==b||g.id!==e.pointerId)return;gesto=null;
      if(b.hasPointerCapture(e.pointerId))b.releasePointerCapture(e.pointerId);
      b.classList.remove('arrastrando');if(!g.arrastrando){if(!vale){b.dataset.recienMovida='1';setTimeout(()=>delete b.dataset.recienMovida,350);}return;}
      // Se consume también el clic posterior a una suelta inválida o cancelada.
      b.dataset.recienMovida='1';setTimeout(()=>delete b.dataset.recienMovida,350);
      const r=contenedor.getBoundingClientRect(),dentro=e.clientX>=r.left&&e.clientX<=r.right&&e.clientY>=r.top&&e.clientY<=r.bottom,q=b._sitio||sitio(d),x=q.x,y=q.y;delete b._sitio;
      if(!vale||!dentro||etiquetas.inert||x<.08||x>.92||y<.12||y>.86){posicionar(b,sitio(d));return;}
      const pos=libre(d.id,x,y);posicionar(b,pos);enMovimiento=null;contenedor.classList.remove('islas-moviendo');mover(d.id,pos);
    };
    escuchar(b,'pointerup',e=>soltar(e,true));escuchar(b,'pointercancel',e=>soltar(e,false));
    escuchar(b,'lostpointercapture',e=>{if(gesto?.id===e.pointerId)soltar(e,false);});
    escuchar(b,'keydown',e=>{
      const paso={ArrowLeft:[-.03,0],ArrowRight:[.03,0],ArrowUp:[0,-.03],ArrowDown:[0,.03]}[e.key];
      if(!paso||etiquetas.inert||!cerca)return;e.preventDefault();
      if(tecla&&tecla.b!==b)guardarTecla();
      if(elegida)seleccionar(null);const s=b._sitio||sitio(d),pos=libre(d.id,s.x+paso[0],s.y+paso[1]);
      b._sitio=pos;posicionar(b,pos);if(tecla)clearTimeout(tecla.timer);
      tecla={b,d,pos,timer:setTimeout(guardarTecla,450)};
    });
    escuchar(b,'blur',()=>{if(tecla?.b===b)guardarTecla();});
  }
  function parallax(){
    rafParallax=0;if(destruido)return;
    despertar();
  }
  function desplazar(x,y){if(!activo()||reducido.matches)return;desplazamiento=VoidPlano.paralaje(x,y);despertar();}
  // Conserva el pellizco y la rueda con Ctrl de la vista anterior.
  const distancia=()=>{const [a,b]=[...dedos.values()];return Math.hypot(a.x-b.x,a.y-b.y);};
  escuchar(contenedor,'pointerdown',e=>{
    dedos.set(e.pointerId,{x:e.clientX,y:e.clientY});
    if(dedos.size===2){suprimirClick=performance.now()+1000;cancelarGesto();cancelarTecla();pan=null;distancia0=distancia();}
  },{capture:true});
  escuchar(contenedor,'pointermove',e=>{
    if(!dedos.has(e.pointerId))return;dedos.set(e.pointerId,{x:e.clientX,y:e.clientY});
    if(dedos.size===2&&distancia0){const d=distancia()-distancia0;if((d>50&&!cerca)||(d< -50&&cerca)){zoom(d>0);distancia0=0;}}
  },{capture:true});
  const soltarDedo=e=>{dedos.delete(e.pointerId);if(dedos.size<2)distancia0=0;};
  escuchar(contenedor,'pointerup',soltarDedo);escuchar(contenedor,'pointercancel',soltarDedo);
  escuchar(contenedor,'wheel',e=>{if(!e.ctrlKey)return;e.preventDefault();if(e.deltaY)zoom(e.deltaY<0);},{passive:false});
  escuchar(contenedor,'pointerdown',e=>{
    if(!cerca||e.button!==0||e.target.closest('button')||etiquetas.inert||dedos.size>1)return;
    seleccionar(null);pan={id:e.pointerId,x:e.clientX,y:e.clientY,previo:desplazamiento};contenedor.setPointerCapture(e.pointerId);
  });
  escuchar(contenedor,'pointermove',e=>{if(pan?.id===e.pointerId)desplazar(pan.previo.x+(e.clientX-pan.x)*.16,pan.previo.y+(e.clientY-pan.y)*.16);});
  const soltarPan=e=>{if(pan?.id!==e.pointerId)return;pan=null;if(contenedor.hasPointerCapture(e.pointerId))contenedor.releasePointerCapture(e.pointerId);};
  escuchar(contenedor,'pointerup',soltarPan);escuchar(contenedor,'pointercancel',soltarPan);escuchar(contenedor,'lostpointercapture',()=>{pan=null;});
  // Nunca se pide permiso. Los navegadores que no entregan orientación usan el fondo arrastrable.
  escuchar(window,'deviceorientation',e=>{if(cerca&&activo()&&!pan&&!gesto&&!document.hidden&&!reducido.matches&&Number.isFinite(e.gamma)&&Number.isFinite(e.beta))desplazar(e.gamma*.5,(e.beta-35)*.3);});
  escuchar(reducido,'change',()=>{clearTimeout(viaje);contenedor.classList.remove('islas-viajando');if(vuelo){vista={...vuelo.a};vuelo=null;}desplazamiento={x:0,y:0};despertar();});
  escuchar(contenedor,'keydown',e=>{
    if(e.key!=='Escape')return;
    if(gesto||tecla){e.preventDefault();cancelarGesto();cancelarTecla();}
    else if(elegida||enMovimiento){e.preventDefault();const id=elegida||enMovimiento;seleccionar(null);nodo(id)?.focus({preventScroll:true});}
    else if(cerca){e.preventDefault();zoom(false);}
  });
  const ocupado=new MutationObserver(()=>{for(const b of menu.querySelectorAll('button'))b.disabled=etiquetas.inert;if(etiquetas.inert){cancelarGesto();cancelarTecla();}});
  ocupado.observe(etiquetas,{attributes:true,attributeFilter:['inert']});
  function pintar(nuevos,actual,todas=nuevos){
    W=innerWidth;H=innerHeight;
    if(primeraPintura&&!actual&&!location.hash)zona.scrollIntoView({block:'start',behavior:'instant'});primeraPintura=false;
    cancelarGesto();cancelarTecla();datos=nuevos;todasIslas=todas;if(detalleAnterior&&!actual)zona.scrollIntoView({block:'start',behavior:'instant'});detalleAnterior=!!actual;
    eventosNodos.abort();eventosNodos=new AbortController();
    if(elegida&&!porId(elegida))seleccionar(null);
    const foco=etiquetas.contains(document.activeElement)?document.activeElement.closest('[data-id]')?.dataset.id:null;
    const materias=todas.map((d,i)=>{const p=sitio(d);return materia(d,i,{x:.5+(p.x-.5)*.34,y:.5+(p.y-.5)*.34});});
    const firma=JSON.stringify(materias);
    if(firma!==firmaGrande&&!propia){
      firmaGrande=firma;
      // Un guardado puede llegar mientras el campo anterior sigue madurando.
      quitarCampo(grande);
      preparar(grande,ctxGrande,materias,NGrande);
    }
    distribuir();const fragmento=document.createDocumentFragment(),ids=new Set();
    for(const [i,d] of datos.entries()){
      ids.add(d.id);const m=materia(d,todas.findIndex(x=>x.id===d.id),{x:.5,y:.5}),clave=JSON.stringify(m);
      let c=cache.get(d.id);
      if(!c||c.clave!==clave){
        if(c){c.canvas.width=c.canvas.height=0;c.canvas._mascara=null;}
        if(c)quitarCampo(c.canvas);
        const canvas=crear('canvas','islas-huella-pequena');canvas.width=canvas.height=192;canvas.setAttribute('aria-hidden','true');
        const ctx=canvas.getContext('2d');if(!ctx)throw Error('No se pudo dibujar una isla.');
        c={canvas,clave};cache.set(d.id,c);preparar(canvas,ctx,[m],192);
      }
      const b=boton('islas-huella-etiqueta islas-juego-isla','',e=>{if(b.dataset.recienMovida||performance.now()<suprimirClick)return;seleccionar(d.id);});
      b.dataset.id=d.id;
      b.disabled=!!actual;b.setAttribute('aria-label',d.nombre);b.setAttribute('aria-expanded',String(d.id===elegida));b.setAttribute('aria-pressed',String(d.id===elegida));b.classList.toggle('islas-delante',d.id===(actual||elegida));
      const nombre=crear('span','islas-juego-nombre',d.nombre);b.append(c.canvas,nombre);posicionar(b,sitio(d));
      if(d.destino)b.dataset.fija='1';else{b.setAttribute('aria-description','Toca para ver las opciones. Arrastra o usa las flechas para moverla.');arrastrable(b,d);}
      fragmento.append(b);
    }
    for(const [id,c] of cache)if(!ids.has(id)){cache.delete(id);c.canvas.width=c.canvas.height=0;c.canvas._mascara=null;quitarCampo(c.canvas);}
    etiquetas.replaceChildren(fragmento);parallax();
    if(actual&&!cerca)zoom(true);if(actual)requestAnimationFrame(()=>{if(destruido||!detalleAnterior)return;const h=document.getElementById('islas-panel-titulo');h?.scrollIntoView({block:'start',behavior:'instant'});});despertar();if(foco)nodo(foco)?.focus({preventScroll:true});
    nivel();
  }
  tam();cargarPublico();
  return {pintar,seleccionar:()=>{},destruir(){
    destruido=true;peticion.abort();observador.disconnect();dialogos.disconnect();parar();publico?.destruir();zona.remove();regresar.remove();document.body.classList.remove('modo-plano','plano-visible');for(const c of cache.values()){c.canvas.width=c.canvas.height=0;c.canvas._mascara=null;}grande.width=grande.height=0;grande._mascara=null;eventos.abort();eventosNodos.abort();ocupado.disconnect();worker?.terminate();motor?.destruir();cancelAnimationFrame(rafParallax);clearTimeout(viaje);cancelarTecla();cancelarGesto();trabajos.clear();cache.clear();
    for(const n of [decorado,lejos,entrada,volver,donde,masBoton,menu,estado,instalacion])n.remove();etiquetas.replaceChildren();etiquetas.removeAttribute('aria-hidden');
    contenedor.classList.remove('vista-juego','de-cerca','islas-viajando','islas-con-seleccion','islas-moviendo','islas-en-pausa','islas-primera-visita');delete contenedor.dataset.nivel;delete contenedor.dataset.publicacion;delete contenedor.dataset.trabajando;delete contenedor.dataset.camara;delete contenedor.dataset.origen;
    contenedor.closest('#islas-mapa-grupo')?.classList.remove('islas-grupo-dentro');
  }};
};
// En ventanas bajas se muestran menos islas, con las mismas flechas del HUD.
window.VoidJuegoIslas.capacidad=(W,H)=>H<640?3:H<700?4:W<400?7:8;
// Parte de O + L·(posición − .5). Solo aparta un cartel si no cabe o pisa otro.
// Los candidatos se buscan en pantalla y se devuelven al suelo con su inversa;
// todos conservan un único tamaño físico. El paralaje sigue siendo perspectiva.
window.VoidJuegoIslas.distribucion=function(W,H,datos,origen={x:0,y:0}){
  const s=Math.min(W/400,H/600,2),p=window.VoidPlano.crear({...origen,s},W,H),L=360;
  const arriba=140,abajo=H-(W<=380?148:88),margen=12;
  // [22-oct, Claude] Con perspectiva fuerte el paralaje mueve más lo cercano que lo lejano: dos carteles que no se
  // tocan con la cámara quieta pueden pisarse al arrastrar. Se comprueban en las dos esquinas del paralaje.
  const camaras=[[0,0],[-18,-14],[18,14]].map(([dx,dy])=>dx?window.VoidPlano.crear({x:origen.x+dx,y:origen.y+dy,s},W,H):p);
  const objetivos=datos.map(d=>{const t={x:origen.x+L*(d.posicion.x-.5),y:origen.y+L*(d.posicion.y-.5)};return {...d,t,q:p.proyectar(t.x,t.y)};}).sort((a,b)=>b.t.y-a.t.y||a.id.localeCompare(b.id));
  const caja=(cam,a,lado)=>{const r=cam.cartel(a,lado);return r&&{x:r.x-10,y:r.y,w:r.w+20,h:r.h+25};};
  const pisan=(c,b)=>!(c.x+c.w+10<=b.x||b.x+b.w+10<=c.x||c.y+c.h+12<=b.y||b.y+b.h+12<=c.y);
  // En pantallas bajas no siempre caben sin rozarse: antes de rendirse, carteles de 36 px y, al final, roces.
  // Lanzar aquí tumbaba el juego entero en los móviles pequeños.
  for(const [minimo,solape] of [[44,true],[36,true],[36,false]])
  for(let lado=Math.min(160,W*.32)/s;lado>=24;lado*=.92){
    const lugares=new Map(),cajas=[];
    function candidato(x,y){
      const a=p.inversa(x,y);if(!a)return null;const r=p.cartel(a,lado);if(r.w<minimo)return null;
      const c=caja(p,a,lado);
      if(c.x<margen||c.x+c.w>W-margen||c.y<arriba||c.y+c.h>abajo)return null;
      const todas=camaras.map(cam=>caja(cam,a,lado));if(todas.some(k=>!k))return null;
      if(solape&&cajas.some(bs=>todas.some((k,i)=>pisan(k,bs[i]))))return null;
      return {a,todas};
    }
    for(const d of objetivos){
      let mejor=candidato(d.q.x,d.q.y),coste=mejor?0:Infinity;
      if(!mejor)for(let y=arriba+44;y<abajo-24;y+=8)for(let x=margen+32;x<W-margen-32;x+=8){
        const dist=(x-d.q.x)**2+(y-d.q.y)**2;if(dist>=coste)continue;
        const c=candidato(x,y);if(c){mejor=c;coste=dist;}
      }
      if(!mejor)break;lugares.set(d.id,{...mejor.a,lado});cajas.push(mejor.todas);
    }
    if(lugares.size===datos.length)return lugares;
  }
  throw Error('No hay espacio para los carteles.');
};
})();
