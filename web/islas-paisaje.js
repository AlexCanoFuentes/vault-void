/* M-09. Terreno y agua adaptados del prototipo aprobado del 18-oct.
   Geometría agrupada, sin texturas externas; máximo ocho islas por página. */
(()=>{
'use strict';
window.VoidPaisajeIslas = function(contenedor, etiquetas, {abrir, mover, fallo}) {
if(!window.THREE)throw Error('No se pudo cargar el paisaje. Puedes usar la lista.');
const TAU=Math.PI*2, clamp=(n,a,b)=>Math.min(b,Math.max(a,n));
function semilla(s){let h=2166136261;for(const c of s){h^=c.charCodeAt(0);h=Math.imul(h,16777619);}return h>>>0;}
function random(seed){return()=>{seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
const scene=new THREE.Scene(),renderer=new THREE.WebGLRenderer({alpha:true,antialias:true,powerPreference:'high-performance'});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.outputEncoding=THREE.sRGBEncoding;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;
renderer.domElement.setAttribute('aria-hidden','true');contenedor.prepend(renderer.domElement);
const camera=new THREE.OrthographicCamera(-6,6,9,-9,.1,180),UP=new THREE.Vector3(0,22,-14).normalize(),RIGHT=new THREE.Vector3(1,0,0),DIR=new THREE.Vector3(0,14,22).normalize();
scene.add(new THREE.HemisphereLight(0xe0f1ff,0x48553c,.85));const sun=new THREE.DirectionalLight(0xffedcf,1.45);sun.position.set(-4,9,5);scene.add(sun);
const landMat=new THREE.MeshLambertMaterial({vertexColors:true,flatShading:true});
const waterMat=new THREE.ShaderMaterial({transparent:true,depthWrite:false,side:THREE.DoubleSide,uniforms:{t:{value:0}},vertexShader:`attribute float edge;varying vec3 p;varying float fade;void main(){p=position;fade=edge;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,fragmentShader:`precision mediump float;uniform float t;varying vec3 p;varying float fade;void main(){float a=sin(p.x*26.+p.z*18.+t*.8);float b=sin(p.z*31.-p.x*15.-t*.6);float c=pow(max(0.,a*b),8.);float wave=sin(p.x*7.-p.z*9.+t*.9)*.5+.5;vec3 col=mix(vec3(.035,.34,.38),vec3(.18,.72,.68),wave*.65+fade*.2);col+=vec3(.40,.55,.45)*c*.7;gl_FragColor=vec4(col,fade*.85);}`});
const shadowMat=new THREE.ShaderMaterial({transparent:true,depthWrite:false,side:THREE.DoubleSide,vertexShader:`attribute float alpha;varying float a;void main(){a=alpha;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,fragmentShader:`precision mediump float;varying float a;void main(){gl_FragColor=vec4(.045,.075,.055,a);}`});
const foamMat=new THREE.MeshBasicMaterial({color:0xb4eee0,transparent:true,opacity:.58,side:THREE.DoubleSide,depthWrite:false});
/* Todas las piezas sólidas se fusionan en UNA malla por isla. */
class Lote{
 constructor(){this.p=[];this.n=[];this.c=[];}
 geo(g,col,x=0,y=0,z=0,sx=1,sy=1,sz=1,ry=0,rz=0){let a=g.index?g.toNonIndexed():g;const m=new THREE.Matrix4().compose(new THREE.Vector3(x,y,z),new THREE.Quaternion().setFromEuler(new THREE.Euler(0,ry,rz)),new THREE.Vector3(sx,sy,sz));a.applyMatrix4(m);const c=new THREE.Color(col).convertSRGBToLinear(),p=a.attributes.position.array,n=a.attributes.normal.array;for(let i=0;i<p.length;i++)this.p.push(p[i]);for(let i=0;i<n.length;i++)this.n.push(n[i]);for(let i=0;i<p.length/3;i++)this.c.push(c.r,c.g,c.b);a.dispose();if(a!==g)g.dispose();}
 tri(a,b,c,color){const ca=new THREE.Color(color).convertSRGBToLinear(),v1=new THREE.Vector3().fromArray(a),v2=new THREE.Vector3().fromArray(b),v3=new THREE.Vector3().fromArray(c),n=v3.clone().sub(v1).cross(v2.clone().sub(v1)).normalize();for(const v of [a,c,b]){this.p.push(...v);this.n.push(n.x,n.y,n.z);this.c.push(ca.r,ca.g,ca.b);}}
 box(x,y,z,w,h,d,c,ry=0,rz=0){this.geo(new THREE.BoxGeometry(w,h,d),c,x,y,z,1,1,1,ry,rz);}
 rock(x,y,z,s,c,sx=1,sy=1,sz=1){this.geo(new THREE.DodecahedronGeometry(s,0),c,x,y,z,sx,sy,sz,x*3);}
 mesh(){const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(this.p,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(this.n,3));g.setAttribute('color',new THREE.Float32BufferAttribute(this.c,3));g.computeBoundingSphere();return new THREE.Mesh(g,landMat);}
}
const blend=(a,b,t)=>new THREE.Color(a).lerp(new THREE.Color(b),t);
function sombra(arr,x,y,z,r,stretch=1){const N=12;for(let j=0;j<3;j++){let r0=r*j/3,r1=r*(j+1)/3,a0=.22*(1-j/3)**2,a1=.22*(1-(j+1)/3)**2;for(let i=0;i<N;i++){const a=i/N*TAU,b=(i+1)/N*TAU;const p=[[x+Math.cos(a)*r0,y,z+Math.sin(a)*r0*stretch,a0],[x+Math.cos(b)*r0,y,z+Math.sin(b)*r0*stretch,a0],[x+Math.cos(b)*r1,y,z+Math.sin(b)*r1*stretch,a1],[x+Math.cos(a)*r1,y,z+Math.sin(a)*r1*stretch,a1]];for(const n of [0,1,2,0,2,3]){arr.p.push(...p[n].slice(0,3));arr.a.push(p[n][3]);}}}}
function arbol(l,sh,x,y,z,size,tipo,r,vida){const brown='#70543a',green=blend('#7f8060','#63872e',vida);sombra(sh,x+.04,y+.009,z-.025,size*.85,.6);l.geo(new THREE.CylinderGeometry(.014,.024,size*.65,6),brown,x,y+size*.32,z);
 if(tipo===0){for(let j=0;j<3;j++)l.rock(x+(j===1?-.05:j===2?.05:0),y+size*(.78+j*.09),z+(j===1?.035:0),size*.39,blend(green,'#b7be5e',j*.12),1,.88,1);}
 else if(tipo===1){for(let j=0;j<3;j++)l.geo(new THREE.ConeGeometry(size*(.39-j*.075),size*.68,7),blend('#30564a','#709457',j*.28),x,y+size*(.54+j*.24),z);}
 else{for(let j=0;j<5;j++){const a=j*TAU/5;l.geo(new THREE.SphereGeometry(1,5,3),blend('#567431','#a3ae50',r()*.5),x+Math.cos(a)*size*.24,y+size*.9,z+Math.sin(a)*size*.24,size*.34,size*.075,size*.14,-a,.2);}l.rock(x,y+size*.9,z,size*.10,'#a8a055');}}
function casa(l,sh,x,y,z,size,color,dorada,estilo=0){const w=.26*size,h=.24*size,d=.22*size;sombra(sh,x+.045,y+.008,z-.03,w*1.2,.8);l.box(x,y+.018,z,w*1.25,.036,d*1.3,'#c1b899');l.box(x,y+h*.52,z,w,h,d,estilo===1?'#d0a276':'#e5dcc0');
 const roof=dorada?'#e9b741':color;
 if(estilo===2){l.box(x,y+h+.025,z,w*1.24,.05,d*1.24,roof);l.box(x,y+h+.055,z,w*.83,.025,d*.7,'#e6d6ab');}
 else{const x0=x-w*.62,x1=x+w*.62,z0=z-d*.66,z1=z+d*.66,lo=y+h,hi=y+h+.13*size;l.tri([x0,lo,z0],[x,hi,z0],[x,hi,z1],roof);l.tri([x0,lo,z0],[x,hi,z1],[x0,lo,z1],roof);l.tri([x,hi,z0],[x1,lo,z0],[x1,lo,z1],roof);l.tri([x,hi,z0],[x1,lo,z1],[x,hi,z1],roof);l.tri([x0,lo,z1],[x,hi,z1],[x1,lo,z1],'#f0ddbc');l.tri([x1,lo,z0],[x,hi,z0],[x0,lo,z0],'#d8c2a2');for(let q=0;q<5;q++)l.box(x,y+h+.065*size,z-d*.6+q*d*.3,w*1.2,.009,.009,blend(roof,'#f6dcaa',.25));}
 l.box(x+.018*size,y+.073*size,z+d*.51,.052*size,.14*size,.012,'#4c665b');l.box(x-.077*size,y+h*.65,z+d*.515,.052*size,.066*size,.012,'#3f6767');l.box(x-.077*size,y+h*.65,z+d*.548,.006,.066*size,.007,'#f1dcb9');l.box(x+w*.512,y+h*.62,z,.012,.072*size,.066*size,'#426a6c');l.box(x-w*.26,y+h+.03,z-d*.22,.045*size,.14*size,.045*size,'#c8b99c');
 for(let j=0;j<3;j++)l.box(x+.02,y+.01+j*.012,z+d*.65+(2-j)*.028,.10,.025,.038,'#d2c09c');}
function parcela(l,sh,x,y,z,paid,r,color){l.box(x,y+.008,z,.29,.018,.22,'#bba373');l.box(x,y+.019,z,.255,.014,.18,'#67583b');for(let j=0;j<4;j++)for(let k=0;k<5;k++)l.rock(x-.09+k*.045,y+.034,z-.067+j*.043,.017,paid?'#aab959':'#7d9b43',1,.8,.7);for(const s of [-1,1])l.box(x+s*.145,y+.027,z,.012,.04,.24,'#d4c094');casa(l,sh,x+.06,y,z-.20,.6,color,paid);}
function terreno(d){const r=random(semilla(d.id)),l=new Lote(),sh={p:[],a:[]},g=new THREE.Group(),vida=Math.sqrt(d.actividad/181),dry=d.actividad<10;const warm=d.color==='#c9784e'||d.color==='#c9a151';const sx=d.forma==='alargada'?1.18:1,sz=d.forma==='alargada'?.78:1,atoll=d.forma==='atolón',phase=r()*TAU,N=60;
 const rockColor=blend(dry?'#9a917b':warm?'#b28258':'#788a83',d.color,.18),grass=dry?'#9c9977':warm?'#adac69':'#819b48',sand=warm?'#e1bd80':'#d2c79e';
 const rad=a=>1+.07*Math.sin(a*5+phase)+.035*Math.sin(a*11-phase)+.022*Math.cos(a*17);
 const elev=(x,z)=>{const dist=Math.hypot(x/sx,z/sz);if(atoll&&dist<.48)return .025;const hill=Math.max(0,-z/sz-.18)*.24*(dry?.3:1);return .065+(d.forma==='montaña'?Math.max(0,1-dist)*.85:hill)+Math.max(0,.018*Math.sin(x*9+phase)*Math.cos(z*11));};
 const point=(a,f,y)=>[Math.cos(a)*rad(a)*sx*f,y,Math.sin(a)*rad(a)*sz*f];
 // Orilla irregular, cuatro niveles de acantilado y colores por estrato.
 const levels=[{r:1,y:.05},{r:1.01,y:-.12},{r:.92,y:-.39},{r:.74,y:-.70},{r:.38,y:-.88}];
 for(let j=0;j<levels.length-1;j++)for(let i=0;i<N;i++){const a=i*TAU/N,b=(i+1)*TAU/N,A=levels[j],B=levels[j+1],p=point(a,A.r,A.y),q=point(b,A.r,A.y),u=point(b,B.r,B.y),v=point(a,B.r,B.y);for(const vv of [p,q,u,v])vv[1]+=.035*Math.sin(Math.atan2(vv[2],vv[0])*13+phase);const col=blend(rockColor,j===0?'#cbd0b0':'#263e3d',j===0?.20:j*.16).offsetHSL(0,0,(r()-.5)*.12);l.tri(p,u,q,col);l.tri(p,v,u,blend(col,'#d5c4a0',r()*.09));}
 // Superficie triangular y playa que sigue el borde del acantilado.
 const rings=atoll?[.44,.53,.65,.8,.93,1]:[0,.22,.45,.67,.83,.94,1];
 for(let j=0;j<rings.length-1;j++)for(let i=0;i<N;i++){const a=i*TAU/N,b=(i+1)*TAU/N,pts=[point(a,rings[j],0),point(b,rings[j],0),point(b,rings[j+1],0),point(a,rings[j+1],0)];pts.forEach(p=>p[1]=elev(p[0],p[2]));const c=new THREE.Color(j===rings.length-2||(atoll&&j===0)?sand:grass).offsetHSL(0,0,(r()-.5)*.08);l.tri(pts[0],pts[2],pts[1],c);l.tri(pts[0],pts[3],pts[2],blend(c,'#ced394',r()*.08));}
 const waterP=[],edges=[],foam=new Lote();
 function waterRing(inner,outer,y){for(let j=0;j<3;j++)for(let i=0;i<N;i++){const a=i*TAU/N,b=(i+1)*TAU/N,f0=inner+(outer-inner)*j/3,f1=inner+(outer-inner)*(j+1)/3;const p=[point(a,f0,y),point(b,f0,y),point(b,f1,y),point(a,f1,y)];for(const k of [0,2,1,0,3,2]){waterP.push(...p[k]);edges.push(j===2&&(k===2||k===3)?0:1);}}}
 waterRing(.96,1.19,-.035);if(atoll)waterRing(0,.48,.047);
 // Espuma en pequeños arcos, toda hecha con geometría.
 for(let i=0;i<44;i++){const a=r()*TAU,rr=atoll&&i<20?.43:1.04,p=point(a,rr,-.027),q=point(a+.04+r()*.06,rr,-.027),u=point(a,rr+.012,-.027);if(atoll&&i<20)p[1]=q[1]=u[1]=.051;foam.tri(p,q,u,'#bde7d7');}
 // Rocas de orilla, caras claras y vegetación baja.
 for(let i=0;i<48;i++){const a=i*TAU/48,rr=.96+r()*.05,p=point(a,rr,0),s=.055+r()*.065;l.rock(p[0],-.06-r()*.13,p[2],s,blend(rockColor,'#d9cfb3',r()*.45),.7+r()*.5,1.5+r(),.7+r());if(i%3===0&&!dry){const pp=point(a,.86,0);l.rock(pp[0],elev(pp[0],pp[2])+.018,pp[2],.045,blend(grass,'#486f35',.3),1.3,.5,1);}}
 // El sendero de losas conduce al edificio.
 for(let i=0;i<17;i++){const z=.68-i*.057,x=atoll?.65*sx:.05+Math.sin(i*.36)*.09,y=elev(x,z);l.box(x,y+.006,z,.10,.013,.06,blend(sand,'#f1dfb5',r()*.25),.1*Math.sin(i));}
 // Distribución estable, independiente del nombre y del número de tareas.
 const plotPos=i=>{if(atoll){const a=.25+i*TAU/8;return [Math.cos(a)*.66*sx,Math.sin(a)*.66*sz];}return [-.43+(i%3)*.35,.40-Math.floor(i/3)*.36];};
 const mainX=atoll?-.69*sx:.03,mainZ=atoll?-.05:-.34;
 // Se reservan las ocho parcelas incluso vacías para que plantar no mueva árboles anteriores.
 const reserved=Array.from({length:8},(_,i)=>plotPos(i));
 const libre=(x,z)=>!reserved.some(([px,pz])=>Math.abs(x-px)<.19&&z>pz-.31&&z<pz+.14)&&!(Math.abs(x-mainX)<.28&&Math.abs(z-mainZ)<.26);
 const sites=[];for(let i=0;i<600&&sites.length<80;i++){const a=r()*TAU,rr=(atoll?.55:.36)+r()*(atoll?.37:.55),x=Math.cos(a)*rr*sx,z=Math.sin(a)*rr*sz;if(!libre(x,z))continue;sites.push([x,elev(x,z),z]);}
 if(!sites.length){for(let i=0;i<24;i++){const a=i*TAU/24,x=Math.cos(a)*.88*sx,z=Math.sin(a)*.88*sz;sites.push([x,elev(x,z),z]);}}
 let baseTrees=dry?d.actividad>5?2:0:Math.round(7+vida*14);const done=d.tareas.filter(t=>t[1]).length;
 for(let i=0;i<baseTrees;i++){const p=sites[(i*3+9)%sites.length];arbol(l,sh,...p,.19+r()*.14,d.id==='hotel'?2:d.id==='lexlabs'?1:i%3,r,dry?.15:.8);}
 const taskMeshes=[];d.tareas.forEach((t,i)=>{if(!t[1])return;const p=sites[(i*7+4)%sites.length],tl=new Lote(),ts={p:[],a:[]};arbol(tl,ts,0,0,0,.34,i%3,r,1);const tm=tl.mesh();tm.position.set(...p);tm.userData.task=i;g.add(tm);taskMeshes.push(tm);sombra(sh,p[0]+.04,p[1]+.009,p[2],.24,.65);});
 for(let i=0;i<d.pedidas;i++){const [x,z]=plotPos(i);parcela(l,sh,x,elev(x,z)+.01,z,i<d.cobradas,r,d.color);}
 if(!dry){const x=atoll?-.69*sx:.03,z=atoll?-.05:-.34,y=elev(x,z);casa(l,sh,x,y,z,d.id==='hotel'?1.65:1.4,d.color,false,d.id==='hotel'?2:0);
  // Terraza, barandilla y escalera del edificio principal.
  l.box(x,y+.04,z+.22,.48,.04,.22,'#cbb694');for(let i=0;i<5;i++)l.box(x-.24+i*.12,y+.12,z+.31,.014,.16,.014,'#877557');l.box(x,y+.20,z+.31,.5,.018,.018,'#bba986');
  if(d.id==='void'){l.box(x-.13,y+.45,z,.07,.7,.09,'#e4dcc2');l.box(x+.13,y+.45,z,.07,.7,.09,'#e4dcc2');l.box(x,y+.83,z,.34,.09,.13,'#e2dabf');l.box(x,y+.9,z,.40,.04,.16,'#728d69');}
 }
 // Agujas de roca al fondo y muelle hacia quien mira.
 if(d.actividad>=37){for(let i=0;i<4;i++){const x=-.55+i*.29,z=-.61*sz;l.rock(x,elev(x,z)+.1,z,.14+r()*.08,blend(rockColor,'#d3d2b5',.35),.7,1.6+r(),.8);}const dx=atoll?.35:.55;for(let i=0;i<9;i++){const z=.73*sz+i*.043;l.box(dx,.12,z,.22,.026,.034,'#b29366');}for(let i=0;i<4;i++){const z=.77*sz+i*.11;for(const x of [dx-.10,dx+.10])l.box(x,-.02,z,.022,.32,.022,'#745b41');}}
 // Cascada: cintas con los reflejos animados del agua.
 if(d.actividad>=60){const x=atoll?-.17:.35,z=.96*sz;for(let j=0;j<5;j++){const xx=x+(j-2)*.025,top=.075,bt=-.72+j*.035;const p=[[xx,top,z],[xx+.026,top,z],[xx+.03,bt,z+.04],[xx-.005,bt,z+.04]];for(const k of [0,1,2,0,2,3]){waterP.push(...p[k]);edges.push(.95);}}}
 const land=l.mesh();g.add(land);
 const wg=new THREE.BufferGeometry();wg.setAttribute('position',new THREE.Float32BufferAttribute(waterP,3));wg.setAttribute('edge',new THREE.Float32BufferAttribute(edges,1));g.add(new THREE.Mesh(wg,waterMat));
 const fm=foam.mesh();fm.material=foamMat;g.add(fm);
 const sg=new THREE.BufferGeometry();sg.setAttribute('position',new THREE.Float32BufferAttribute(sh.p,3));sg.setAttribute('alpha',new THREE.Float32BufferAttribute(sh.a,1));g.add(new THREE.Mesh(sg,shadowMat));
 g.userData={taskMeshes,trees:baseTrees+done,plots:d.pedidas,gold:d.cobradas};return g;
}
let nodes=[],W=1,H=1,ppu=1,raf=0,destruido=false,visible=true,seleccion=null,drag=null,animacion=null;
let centro=new THREE.Vector3(),zoom=1,cuadros=0,marca=0;
const media=matchMedia('(prefers-reduced-motion: reduce)'),fps=document.createElement('span');
fps.className='islas-fps';fps.setAttribute('aria-hidden','true');contenedor.append(fps);
function liberar(n){scene.remove(n.root);n.root.traverse(o=>{if(o.geometry)o.geometry.dispose();});}
function dibujo(isla){
 const tareas=isla.bloques?.filter(b=>b.tipo==='tareas').flatMap(b=>b.items)||[];
 const cont=isla.bloques?.find(b=>b.tipo==='contador');
 const d={...isla,actividad:Math.min(181,37+tareas.filter(t=>t.hecho).length*5),tareas:tareas.slice(0,24).map(t=>[t.texto,t.hecho]),pedidas:cont?clamp(Math.round(cont.meta),0,8):0,cobradas:cont?clamp(Math.round(cont.valor),0,8):0};
 if(d.estilo==='serena')d.color='#'+new THREE.Color(d.color).lerp(new THREE.Color('#abbdb4'),.3).getHexString();
 if(d.estilo==='sobria'){d.color='#'+new THREE.Color(d.color).lerp(new THREE.Color('#8b8980'),.65).getHexString();d.actividad=10;}
 if(d.forma!=='archipiélago')return terreno(d);
 const grupo=new THREE.Group(),central=terreno({...d,forma:'redonda'});central.scale.setScalar(.68);grupo.add(central);
 for(const [x,z] of [[-.77,.28],[.66,.52]]){const sat=terreno({...d,id:d.id+x,forma:'redonda',tareas:[],pedidas:0,cobradas:0,actividad:10});sat.scale.setScalar(.29);sat.position.set(x,-.08,z);grupo.add(sat);}return grupo;
}
function solicitar(){if(!raf&&!destruido&&visible&&!document.hidden)raf=requestAnimationFrame(frame);}
function frame(t){
 raf=0;if(destruido||!visible||document.hidden)return;
 if(animacion){const a=clamp((t-animacion.inicio)/550,0,1),e=1-(1-a)**4;centro.lerpVectors(animacion.desde,animacion.hasta,e);zoom=animacion.zoom+(animacion.final-animacion.zoom)*e;if(a===1)animacion=null;}
 camera.zoom=zoom;camera.position.copy(centro).addScaledVector(DIR,32);camera.up.copy(UP);camera.lookAt(centro);camera.updateProjectionMatrix();camera.updateMatrixWorld();
 for(const n of nodes){n.root.visible=!seleccion||n.d.id===seleccion;if(!seleccion){n.root.position.copy(RIGHT).multiplyScalar((n.x-W/2)/ppu).addScaledVector(UP,(H/2-n.y)/ppu+(media.matches?0:Math.sin(t*.001+n.i)*.025));}}
 waterMat.uniforms.t.value=media.matches?0:t/1000;renderer.render(scene,camera);
 if(media.matches){fps.textContent='Movimiento reducido';}else{cuadros++;if(!marca)marca=t;if(t-marca>=1000){fps.textContent=Math.round(cuadros*1000/(t-marca))+' fps';cuadros=0;marca=t;}}
 if(!media.matches||animacion)solicitar();
}
function limites(n){n.x=clamp(n.x,68,W-68);n.y=clamp(n.y,60,H-60);}
function posicion(n){n.root.position.copy(RIGHT).multiplyScalar((n.x-W/2)/ppu).addScaledVector(UP,(H/2-n.y)/ppu);n.root.scale.setScalar(n.r/ppu/1.15);n.button.style.cssText=`left:${n.x-64}px;top:${n.y-46}px;width:128px;height:100px`;}
function resolver(fija){for(let paso=0;paso<6;paso++)for(const n of nodes){if(n===fija)continue;const dx=n.x-fija.x,dy=(n.y-fija.y)/.85,dist=Math.hypot(dx,dy)||1,min=n.r+fija.r+34;if(dist<min){n.x+=(dx/dist||1)*(min-dist);n.y+=dy/dist*(min-dist)*.85;limites(n);}}}
function destino(suave=false){const elegido=nodes.find(n=>n.d.id===seleccion),hasta=elegido?elegido.root.position.clone():new THREE.Vector3(),final=elegido?Math.min(3,H/170):1;if(suave&&!media.matches)animacion={inicio:performance.now(),desde:centro.clone(),hasta,zoom,final};else{animacion=null;centro.copy(hasta);zoom=final;}solicitar();}
function separar(){
 // Un archivo puede traer posiciones iguales. Ninguna isla debe tapar otra.
 for(let paso=0;paso<40;paso++)for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){
  const a=nodes[i],b=nodes[j];let dx=b.x-a.x,dy=(b.y-a.y)/.85;
  if(Math.hypot(dx,dy)<.01){dx=(j%2?1:-1);dy=(i%2?1:-1);}
  const dist=Math.hypot(dx,dy),min=132;
  if(dist<min){const empuje=(min-dist)/2;a.x-=dx/dist*empuje;a.y-=dy/dist*empuje*.85;b.x+=dx/dist*empuje;b.y+=dy/dist*empuje*.85;limites(a);limites(b);}
 }
 const choque=nodes.some((a,i)=>nodes.slice(i+1).some(b=>Math.hypot(a.x-b.x,(a.y-b.y)/.85)<128));
 if(choque){const cols=W>=660?4:2,filas=Math.max(2,Math.ceil(nodes.length/cols));for(const n of nodes){n.x=(n.i%cols+.5)*W/cols;n.y=(Math.floor(n.i/cols)+.5)*H/filas;limites(n);}}
}
function resize(){if(destruido||!contenedor.clientWidth)return;W=contenedor.clientWidth;H=contenedor.clientHeight;ppu=W/12;renderer.setSize(W,H,false);camera.left=-6;camera.right=6;camera.top=H/ppu/2;camera.bottom=-camera.top;
 const cols=W>=660?4:2,filas=Math.max(2,Math.ceil(nodes.length/cols));
 for(const n of nodes){n.r=Math.min(W/cols*.30,62);const p=n.d.posicion||{x:(n.i%cols+.5)/cols,y:(Math.floor(n.i/cols)+.5)/filas};n.x=p.x*W;n.y=p.y*H;limites(n);}if(!seleccion)separar();nodes.forEach(posicion);destino();}
function pintar(datos,id){
 for(const n of nodes)liberar(n);nodes=[];etiquetas.replaceChildren();seleccion=id;
 datos.forEach((d,i)=>{const root=new THREE.Group(),island=dibujo(d);root.add(island);scene.add(root);const b=document.createElement('button'),s=document.createElement('span');b.type='button';b.className='islas-nodo';b.dataset.id=d.id;if(d.destino)b.dataset.fija='';s.textContent=d.nombre;b.append(s);b.setAttribute('aria-label',d.nombre+(d.destino?', ir a su sección':', abrir isla. Flechas para mover'));etiquetas.append(b);nodes.push({d,i,root,island,button:b,x:0,y:0,r:40});});resize();
}
function iniciar(e){const b=e.target.closest('button');if(!b||seleccion||e.button!==0)return;const n=nodes.find(n=>n.button===b);if(n.d.destino)return;drag={n,id:e.pointerId,x:e.clientX,y:e.clientY,nx:n.x,ny:n.y,movido:false};b.setPointerCapture(e.pointerId);}
function arrastrar(e){if(!drag||drag.id!==e.pointerId)return;const d=drag;if(Math.hypot(e.clientX-d.x,e.clientY-d.y)>7)d.movido=true;if(!d.movido)return;d.n.x=d.nx+e.clientX-d.x;d.n.y=d.ny+e.clientY-d.y;limites(d.n);resolver(d.n);nodes.forEach(posicion);solicitar();}
let ignorarClick=false;
function terminar(e,cancelado=false){if(!drag||e.pointerId!==drag.id)return;const d=drag;drag=null;ignorarClick=d.movido;if(cancelado){resize();return;}if(d.movido)mover(d.n.d.id,{x:d.n.x/W,y:d.n.y/H});}
const click=e=>{if(ignorarClick&&e.detail!==0){ignorarClick=false;return;}const b=e.target.closest('button');if(b)abrir(b.dataset.id);};
const teclado=e=>{const b=e.target.closest('button');if(!b||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)||b.hasAttribute('data-fija'))return;e.preventDefault();const n=nodes.find(n=>n.button===b);n.x+=e.key==='ArrowRight'?18:e.key==='ArrowLeft'?-18:0;n.y+=e.key==='ArrowDown'?18:e.key==='ArrowUp'?-18:0;limites(n);resolver(n);nodes.forEach(posicion);solicitar();mover(n.d.id,{x:n.x/W,y:n.y/H});};
etiquetas.addEventListener('pointerdown',iniciar);etiquetas.addEventListener('pointermove',arrastrar);const up=e=>terminar(e),cancel=e=>terminar(e,true);etiquetas.addEventListener('pointerup',up);etiquetas.addEventListener('pointercancel',cancel);etiquetas.addEventListener('lostpointercapture',cancel);etiquetas.addEventListener('click',click);etiquetas.addEventListener('keydown',teclado);
let giro=null;
renderer.domElement.addEventListener('pointerdown',e=>{if(!seleccion)return;giro={id:e.pointerId,x:e.clientX};renderer.domElement.setPointerCapture(e.pointerId);});
renderer.domElement.addEventListener('pointermove',e=>{if(!giro||giro.id!==e.pointerId)return;const n=nodes.find(n=>n.d.id===seleccion);if(n){n.island.rotation.y+=(e.clientX-giro.x)*.009;giro.x=e.clientX;solicitar();}});
renderer.domElement.addEventListener('pointerup',()=>giro=null);renderer.domElement.addEventListener('pointercancel',()=>giro=null);
const pausa=()=>{cancelAnimationFrame(raf);raf=0;marca=0;cuadros=0;if(!document.hidden)solicitar();};
const reducir=()=>{waterMat.uniforms.t.value=0;destino();pausa();};
document.addEventListener('visibilitychange',pausa);media.addEventListener('change',reducir);
const ro=new ResizeObserver(resize);ro.observe(contenedor);
const io=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;if(visible)solicitar();else{cancelAnimationFrame(raf);raf=0;marca=0;cuadros=0;}});io.observe(contenedor);
renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();fallo('El navegador ha pausado el paisaje. Puedes seguir en la lista.');});
return {pintar,seleccionar(id){seleccion=id;destino(true);},destruir(){destruido=true;cancelAnimationFrame(raf);ro.disconnect();io.disconnect();document.removeEventListener('visibilitychange',pausa);media.removeEventListener('change',reducir);etiquetas.removeEventListener('pointerdown',iniciar);etiquetas.removeEventListener('pointermove',arrastrar);etiquetas.removeEventListener('pointerup',up);etiquetas.removeEventListener('pointercancel',cancel);etiquetas.removeEventListener('lostpointercapture',cancel);etiquetas.removeEventListener('click',click);etiquetas.removeEventListener('keydown',teclado);nodes.forEach(liberar);[landMat,waterMat,shadowMat,foamMat].forEach(m=>m.dispose());renderer.dispose();renderer.domElement.remove();fps.remove();etiquetas.replaceChildren();}};
};
})();
