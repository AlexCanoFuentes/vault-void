/* KERNEL 82 · Codex · 21-oct-2026. Dos distancias, la misma materia.
   Cada campo madura en turnos cortos y se congela. No hay un bucle de química permanente.
   Esta vista es opcional: islas.js recupera VoidHuellasIslas si falla. */
(()=>{
'use strict';
let cercaRecordado=false;
window.VoidJuegoIslas=function(contenedor,etiquetas,{abrir,mover,esconder,delVault,fallo}){
  if(!window.VoidHuella)throw Error('No se pudo cargar el juego de huellas.');
  const reducido=matchMedia('(prefers-reduced-motion: reduce)'),eventos=new AbortController();let eventosNodos=new AbortController();
  const escuchar=(n,t,f,o={})=>n.addEventListener(t,f,{...o,signal:eventos.signal});
  const crear=(tag,clase,texto)=>{const n=document.createElement(tag);n.className=clase;if(texto)n.textContent=texto;return n;};
  const boton=(clase,texto,accion)=>{const b=crear('button',clase,texto);b.type='button';b.onclick=accion;return b;};
  const decorado=crear('div','islas-juego-decorado');decorado.setAttribute('aria-hidden','true');
  decorado.append(crear('div','islas-reticula'),crear('div','islas-orbita islas-orbita-uno'),crear('div','islas-orbita islas-orbita-dos'));
  const lejos=crear('button','islas-lejos islas-huella-grande');lejos.type='button';lejos.setAttribute('aria-label','Entrar en mis islas tocando mi huella');
  const grande=crear('canvas','islas-huellas');grande.width=grande.height=128;grande.setAttribute('aria-hidden','true');lejos.append(grande);
  const ctxGrande=grande.getContext('2d');if(!ctxGrande)throw Error('No se pudo dibujar tu huella.');
  const entrada=crear('nav','islas-menu-entrada');entrada.setAttribute('aria-label','Menú de mi huella');
  const entrar=boton('islas-acercar islas-juego-principal','Entrar en mis islas',()=>zoom(true));
  entrada.append(entrar,boton('islas-juego-comunidad','Comunidad',()=>abrir('fija_comunidad')),boton('islas-juego-cuentas','Mis cuentas',()=>abrir('fija_modelos')));
  // La oferta y sus cambios los decide instalar.js (también las instrucciones de Safari).
  const instalacion=crear('div','islas-juego-instalar');instalacion.hidden=true;
  entrada.append(instalacion);
  const volver=boton('islas-alejar','‹ Volver a mi huella',()=>zoom(false));
  const menu=crear('div','islas-menu-isla');menu.hidden=true;menu.setAttribute('role','group');
  const abrirIsla=boton('islas-juego-principal','Abrir',()=>{if(elegida)abrir(elegida);});
  const moverIsla=boton('','Mover',()=>modoMover());
  const ocultar=boton('','Esconder',()=>{if(elegida&&!etiquetas.inert)esconder?.(elegida);});
  const cerrar=boton('islas-juego-cerrar','Cerrar menú',()=>seleccionar(null,true));
  menu.append(abrirIsla,moverIsla,ocultar,cerrar);
  const estado=crear('p','islas-juego-estado');estado.setAttribute('role','status');
  contenedor.prepend(decorado,lejos);contenedor.append(entrada,volver,menu,estado);contenedor.classList.add('vista-juego');
  window.VoidInstalar?.montar(instalacion);
  const instalar=instalacion.querySelector('button');if(instalar)instalar.textContent='Instalar';
  let cerca=cercaRecordado,destruido=false,elegida=null,enMovimiento=null,datos=[],firmaGrande='',viaje=0,raf=0,rafParallax=0,tecla=null;
  let pan=null,gesto=null,desplazamiento={x:0,y:0};
  const cache=new Map(),trabajos=[];
  const dedos=new Map();let distancia0=0;
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
  function pintarCampo(campo,ctx){
    campo.pintar(ctx,false);
    // El motor compartido pinta fondo opaco. Aquí la retícula debe verse entre los surcos.
    const img=ctx.getImageData(0,0,campo.N,campo.N),p=img.data;
    for(let i=0;i<p.length;i+=4){
      const luz=Math.max(p[i]-18,p[i+1]-17,p[i+2]-14);
      if(luz<3){p[i+3]=0;continue;}
      // Paleta de esta escena: ámbar, verde y turquesa, sin surcos morados.
      if(p[i+2]>p[i+1]*1.12&&p[i]>p[i+1]*1.12){const b=p[i+2];p[i+1]=Math.max(p[i+1],b*.85);p[i+2]=p[i+1]*.55;}
    }
    ctx.putImageData(img,0,0);
  }
  function quimica(){
    if(destruido||document.hidden){raf=0;return;}
    const hasta=performance.now()+5;
    try{
      do{
        const t=trabajos[0];if(!t)break;
        t.campo.paso(16);t.pasos+=16;
        if(t.pasos>=1600){pintarCampo(t.campo,t.ctx);t.canvas.dataset.quimica='lista';trabajos.shift();}
      }while(performance.now()<hasta);
    }catch{fallo('No se pudo completar el juego de huellas.');return;}
    raf=trabajos.length?requestAnimationFrame(quimica):0;
  }
  function preparar(canvas,ctx,lista,N){
    const campo=VoidHuella.crear(lista,N,0,{detalle:N===64?1.7:1.35});canvas.dataset.quimica='preparando';
    trabajos.push({campo,ctx,canvas,pasos:0});if(!raf)raf=requestAnimationFrame(quimica);
  }
  escuchar(document,'visibilitychange',()=>{if(!document.hidden&&trabajos.length&&!raf)raf=requestAnimationFrame(quimica);});
  function posicionar(b,s){b.style.left=s.x*100+'%';b.style.top=s.y*100+'%';}
  function nivel(){
    contenedor.classList.toggle('de-cerca',cerca);contenedor.dataset.nivel=cerca?'2':'1';
    entrada.hidden=cerca;volver.hidden=!cerca;lejos.disabled=cerca;lejos.setAttribute('aria-hidden',String(cerca));
    etiquetas.setAttribute('aria-hidden',String(!cerca));
    contenedor.closest('#islas-mapa-grupo')?.classList.toggle('islas-grupo-dentro',cerca);
  }
  function zoom(si){
    if(destruido||cerca===si)return;
    cancelarGesto();cancelarTecla();seleccionar(null);clearTimeout(viaje);
    cerca=cercaRecordado=si;nivel();
    contenedor.classList.toggle('islas-viajando',si&&!reducido.matches);
    estado.textContent=si?'Tus islas. Toca una para ver sus opciones.':'Tu huella reúne tus islas.';
    (si?volver:entrar).focus({preventScroll:true});
    if(si&&!reducido.matches)viaje=setTimeout(()=>contenedor.classList.remove('islas-viajando'),760);
    else contenedor.classList.remove('islas-viajando');
  }
  lejos.onclick=()=>zoom(true);nivel();
  function seleccionar(id,foco=false){
    if(etiquetas.inert&&id)return;
    const anterior=elegida;elegida=id;enMovimiento=null;
    contenedor.classList.toggle('islas-con-seleccion',!!id);contenedor.classList.remove('islas-moviendo');
    for(const b of etiquetas.children){const si=b.dataset.id===id;b.classList.toggle('islas-delante',si);b.setAttribute('aria-pressed',String(si));b.setAttribute('aria-expanded',String(si));}
    menu.hidden=!id;
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
    const valido=p=>datos.every(d=>d.id===id||Math.hypot(sitio(d).x-p.x,sitio(d).y-p.y)>=.125);
    const redondear=p=>({x:Math.round(p.x*1000)/1000,y:Math.round(p.y*1000)/1000});
    const p=redondear({x:limitar(x,.08,.92),y:limitar(y,.12,.86)});if(valido(p))return p;
    for(let r=.02;r<1.3;r+=.02)for(let a=0;a<Math.PI*2;a+=Math.PI/12){
      const q=redondear({x:limitar(p.x+Math.cos(a)*r,.08,.92),y:limitar(p.y+Math.sin(a)*r,.12,.86)});if(valido(q))return q;
    }
    return sitio(porId(id));
  }
  function cancelarTecla(){
    if(!tecla)return;clearTimeout(tecla.timer);posicionar(tecla.b,sitio(tecla.d));delete tecla.b._sitio;tecla=null;
  }
  function cancelarGesto(){
    if(!gesto)return;const g=gesto;gesto=null;g.b.classList.remove('arrastrando');posicionar(g.b,sitio(g.d));
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
      cancelarTecla();gesto={b,d,id:e.pointerId,x:e.clientX,y:e.clientY,arrastrando:false};
    });
    escuchar(b,'pointermove',e=>{
      const g=gesto;if(!g||g.b!==b||g.id!==e.pointerId)return;
      if(!g.arrastrando&&Math.hypot(e.clientX-g.x,e.clientY-g.y)<10)return;
      if(!g.arrastrando){g.arrastrando=true;seleccionar(null);b.setPointerCapture(e.pointerId);b.classList.add('arrastrando');}
      const r=contenedor.getBoundingClientRect();posicionar(b,{x:limitar((e.clientX-r.left)/r.width,.08,.92),y:limitar((e.clientY-r.top)/r.height,.12,.86)});
    });
    const soltar=(e,vale)=>{
      const g=gesto;if(!g||g.b!==b||g.id!==e.pointerId)return;gesto=null;
      if(b.hasPointerCapture(e.pointerId))b.releasePointerCapture(e.pointerId);
      b.classList.remove('arrastrando');if(!g.arrastrando)return;
      // Se consume también el clic posterior a una suelta inválida o cancelada.
      b.dataset.recienMovida='1';setTimeout(()=>delete b.dataset.recienMovida,350);
      const r=contenedor.getBoundingClientRect(),x=(e.clientX-r.left)/r.width,y=(e.clientY-r.top)/r.height;
      if(!vale||etiquetas.inert||x<0||x>1||y<0||y>1){posicionar(b,sitio(d));return;}
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
    const x=reducido.matches?0:desplazamiento.x,y=reducido.matches?0:desplazamiento.y;
    for(const b of etiquetas.children){const p=Number(b.dataset.profundidad);b.style.setProperty('--par-x',x*p+'px');b.style.setProperty('--par-y',y*p+'px');}
  }
  function desplazar(x,y){desplazamiento={x:limitar(x,-18,18),y:limitar(y,-14,14)};if(!rafParallax)rafParallax=requestAnimationFrame(parallax);}
  // Conserva el pellizco y la rueda con Ctrl de la vista anterior.
  const distancia=()=>{const [a,b]=[...dedos.values()];return Math.hypot(a.x-b.x,a.y-b.y);};
  escuchar(contenedor,'pointerdown',e=>{
    dedos.set(e.pointerId,{x:e.clientX,y:e.clientY});
    if(dedos.size===2){cancelarGesto();cancelarTecla();pan=null;distancia0=distancia();}
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
  escuchar(window,'deviceorientation',e=>{if(cerca&&!pan&&!gesto&&!document.hidden&&!reducido.matches&&Number.isFinite(e.gamma)&&Number.isFinite(e.beta))desplazar(e.gamma*.5,(e.beta-35)*.3);});
  escuchar(reducido,'change',()=>{clearTimeout(viaje);contenedor.classList.remove('islas-viajando');desplazar(0,0);});
  escuchar(contenedor,'keydown',e=>{
    if(e.key!=='Escape')return;
    if(gesto||tecla){e.preventDefault();cancelarGesto();cancelarTecla();}
    else if(elegida||enMovimiento){e.preventDefault();const id=elegida||enMovimiento;seleccionar(null);nodo(id)?.focus({preventScroll:true});}
    else if(cerca){e.preventDefault();zoom(false);}
  });
  const ocupado=new MutationObserver(()=>{for(const b of menu.querySelectorAll('button'))b.disabled=etiquetas.inert;if(etiquetas.inert){cancelarGesto();cancelarTecla();}});
  ocupado.observe(etiquetas,{attributes:true,attributeFilter:['inert']});
  function pintar(nuevos,actual,todas=nuevos){
    cancelarGesto();cancelarTecla();datos=nuevos;
    eventosNodos.abort();eventosNodos=new AbortController();
    if(elegida&&!porId(elegida))seleccionar(null);
    const foco=etiquetas.contains(document.activeElement)?document.activeElement.closest('[data-id]')?.dataset.id:null;
    const materias=todas.map((d,i)=>{const p=sitio(d);return materia(d,i,{x:.5+(p.x-.5)*.34,y:.5+(p.y-.5)*.34});});
    const firma=JSON.stringify(materias);
    if(firma!==firmaGrande){
      firmaGrande=firma;
      // Un guardado puede llegar mientras el campo anterior sigue madurando.
      for(let i=trabajos.length-1;i>=0;i--)if(trabajos[i].canvas===grande)trabajos.splice(i,1);
      preparar(grande,ctxGrande,materias,128);
    }
    const fragmento=document.createDocumentFragment(),ids=new Set();
    for(const [i,d] of datos.entries()){
      ids.add(d.id);const m=materia(d,todas.findIndex(x=>x.id===d.id),{x:.5,y:.5}),clave=JSON.stringify(m);
      let c=cache.get(d.id);
      if(!c||c.clave!==clave){
        if(c)for(let j=trabajos.length-1;j>=0;j--)if(trabajos[j].canvas===c.canvas)trabajos.splice(j,1);
        const canvas=crear('canvas','islas-huella-pequena');canvas.width=canvas.height=64;canvas.setAttribute('aria-hidden','true');
        const ctx=canvas.getContext('2d');if(!ctx)throw Error('No se pudo dibujar una isla.');
        c={canvas,clave};cache.set(d.id,c);preparar(canvas,ctx,[m],64);
      }
      const b=boton('islas-huella-etiqueta islas-juego-isla','',()=>{if(!b.dataset.recienMovida)seleccionar(d.id);});
      b.dataset.id=d.id;b.dataset.profundidad=String(.3+(i%4)*.22);b.style.setProperty('--escala',String(.72+(i%4)*.09));b.style.setProperty('--desenfoque',(3-i%4)*.25+'px');
      b.disabled=!!actual;b.setAttribute('aria-label',d.nombre);b.setAttribute('aria-expanded',String(d.id===elegida));b.setAttribute('aria-pressed',String(d.id===elegida));b.classList.toggle('islas-delante',d.id===(actual||elegida));
      const nombre=crear('span','islas-juego-nombre',d.nombre);b.append(c.canvas,nombre);posicionar(b,sitio(d));
      if(d.destino)b.dataset.fija='1';else{b.setAttribute('aria-description','Toca para ver las opciones. Arrastra o usa las flechas para moverla.');arrastrable(b,d);}
      fragmento.append(b);
    }
    for(const [id,c] of cache)if(!ids.has(id)){cache.delete(id);for(let i=trabajos.length-1;i>=0;i--)if(trabajos[i].canvas===c.canvas)trabajos.splice(i,1);}
    etiquetas.replaceChildren(fragmento);parallax();
    if(actual&&!cerca)zoom(true);if(foco)nodo(foco)?.focus({preventScroll:true});
    nivel();
  }
  return {pintar,seleccionar:()=>{},destruir(){
    destruido=true;eventos.abort();eventosNodos.abort();ocupado.disconnect();cancelAnimationFrame(raf);cancelAnimationFrame(rafParallax);clearTimeout(viaje);cancelarTecla();cancelarGesto();trabajos.length=0;cache.clear();
    for(const n of [decorado,lejos,entrada,volver,menu,estado])n.remove();etiquetas.replaceChildren();etiquetas.removeAttribute('aria-hidden');
    contenedor.classList.remove('vista-juego','de-cerca','islas-viajando','islas-con-seleccion','islas-moviendo');delete contenedor.dataset.nivel;
    contenedor.closest('#islas-mapa-grupo')?.classList.remove('islas-grupo-dentro');
  }};
};
})();
