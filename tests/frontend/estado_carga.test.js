const { chromium } = require('/opt/node22/lib/node_modules/playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  const errs=[]; p.on('pageerror',e=>errs.push(String(e)));
  await p.goto('file://'+__dirname+'/carga.html');
  let f=0; const ck=(n,c,x)=>{console.log((c?'OK   ':'FALLO ')+n+(c?'':' -> '+JSON.stringify(x)));if(!c)f++;};

  await p.evaluate(()=>_entSetLoading('Asignando plan de entrenamiento',
    ['Copiando la rutina al cliente','Cargando los días y ejercicios']));
  const t = await p.textContent('#entrenamientoContent');
  ck('el mensaje aparece en entrenamiento', t.includes('Asignando plan de entrenamiento'));
  ck('ya NO se ve el estado vacio', !t.includes('Sin plan de entrenamiento'));

  // Animacion: SVG en linea, no video, y sin peticiones de red
  ck('la animacion es SVG en linea', await p.locator('#entrenamientoContent svg').count()===1);
  ck('NO hay etiqueta video', await p.locator('#entrenamientoContent video').count()===0);
  const imgs = await p.evaluate(()=>document.querySelectorAll('#entrenamientoContent img,#entrenamientoContent video,#entrenamientoContent [src]').length);
  ck('cero recursos externos que descargar', imgs===0, imgs);
  const anim = await p.evaluate(()=>getComputedStyle(document.querySelector('.ent-loading-fill')).animationName);
  ck('la barra anima de verdad', anim==='entSlide', anim);

  // Pasos
  ck('se pintan los 2 pasos', await p.locator('.ent-step').count()===2);
  ck('arranca marcando el primer paso', await p.locator('.ent-step.doing').textContent()==='Copiando la rutina al cliente');
  await p.evaluate(()=>_entLoadingStep(1));
  ck('avanzar marca el segundo en curso', await p.locator('.ent-step.doing').textContent()==='Cargando los días y ejercicios');
  ck('y el primero queda hecho', await p.locator('.ent-step.done').count()===1);

  // Sin pasos sigue valiendo
  await p.evaluate(()=>_nutSetLoading('Asignando dieta'));
  const t2 = await p.textContent('#nutricionContent');
  ck('tambien funciona en nutricion', t2.includes('Asignando dieta'));
  ck('sin pasos cae al texto de siempre', t2.includes('Un momento…'), t2);

  // Avanzar pasos cuando la pantalla ya no esta no debe reventar
  await p.evaluate(()=>{document.getElementById('nutricionContent').innerHTML='';_nutLoadingStep(1);});
  ck('avanzar sin pantalla no revienta', errs.length===0, errs);

  await p.evaluate(()=>_entSetLoading('<img src=x onerror=alert(1)>',['<b>uno</b>']));
  const h = await p.innerHTML('#entrenamientoContent');
  ck('escapa el titulo', h.includes('&lt;img'));
  ck('escapa los pasos', h.includes('&lt;b&gt;uno'));

  ck('sin errores de JS', errs.length===0, errs);
  await b.close(); process.exit(f?1:0);
})();
