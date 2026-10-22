/* M-15 · maduración por etapas. Se usa en el Worker y, si no está disponible,
   en turnos cortos en la página. La etapa final conserva la química de 512/192. */
(()=>{'use strict';
 const raiz=globalThis;
 function crear({lienzo,entregar,error,reloj=()=>performance.now(),programar=f=>setTimeout(f,0),cancelar=clearTimeout,presupuesto=6}){
  const trabajos=new Map();let timer=null,pausado=false,cerrado=false;
  function despertar(){if(!cerrado&&!pausado&&trabajos.size&&timer===null)timer=programar(turno);}
  function turno(){
   timer=null;if(cerrado||pausado)return;
   try{
    // Todas las vistas previas terminan antes de gastar tiempo en el detalle final.
    const lista=[...trabajos.values()].sort((a,b)=>a.etapa-b.etapa),t=lista[0];if(!t)return;
    const hasta=reloj()+presupuesto;
    if(!t.campo){
     // [22-oct, Claude] La vista previa ya madura entera: a los 640 pasos la química aún es una nube de puntos (visto en el Pixel).
     const N=t.etapa?t.N:t.N>=512?192:64;
     t.campo=raiz.VoidHuella.crear(t.lista,N,0,{detalle:1.35});t.pasos=0;
    }
    const meta=1600;
    do{t.campo.paso(1);t.pasos++;}while(t.pasos<meta&&reloj()<hasta);
    if(t.pasos===meta){
     const canvas=lienzo(t.campo.N),ctx=canvas.getContext('2d');t.campo.pintar(ctx,false);
     const img=ctx.getImageData(0,0,canvas.width,canvas.height),p=img.data;
     for(let i=0;i<p.length;i+=4){
      const luz=Math.max(p[i]-18,p[i+1]-17,p[i+2]-14);
      if(luz<3){p[i+3]=0;continue;}
      if(p[i+2]>p[i+1]*1.12&&p[i]>p[i+1]*1.12){const b=p[i+2];p[i+1]=Math.max(p[i+1],b*.85);p[i+2]=p[i+1]*.55;}
     }
     ctx.putImageData(img,0,0);entregar(t.id,canvas,!!t.etapa);
     if(t.etapa)trabajos.delete(t.id);
     else{t.etapa=1;t.campo=null;}
    }
   }catch(e){trabajos.clear();error(e);}
   despertar();
  }
  return {
   preparar(id,lista,N){trabajos.set(id,{id,lista,N,etapa:0,campo:null});despertar();},
   quitar(id){trabajos.delete(id);},
   pausar(si){pausado=si;if(si&&timer!==null){cancelar(timer);timer=null;}else despertar();},
   destruir(){cerrado=true;if(timer!==null)cancelar(timer);timer=null;trabajos.clear();}
  };
 }
 raiz.VoidCamposIslas={crear};
})();
