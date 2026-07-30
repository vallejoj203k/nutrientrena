const { chromium } = require('/opt/node22/lib/node_modules/playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  const errs=[]; p.on('pageerror',e=>errs.push(String(e)));
  await p.goto('file://'+__dirname+'/carga.html');
  let f=0; const ck=(n,c,x)=>{console.log((c?'OK   ':'FALLO ')+n+(c?'':' -> '+JSON.stringify(x)));if(!c)f++;};

  await p.evaluate(()=>_entSetLoading('Asignando plan de entrenamiento'));
  ck('el mensaje aparece en entrenamiento', (await p.textContent('#entrenamientoContent')).includes('Asignando plan de entrenamiento'));
  ck('ya NO se ve el estado vacio', !(await p.textContent('#entrenamientoContent')).includes('Sin plan de entrenamiento'));
  ck('hay spinner', await p.locator('#entrenamientoContent .ent-loading-spin').count() === 1);
  const anim = await p.evaluate(()=>getComputedStyle(document.querySelector('.ent-loading-spin')).animationName);
  ck('el spinner gira de verdad', anim === 'spin', anim);

  await p.evaluate(()=>_nutSetLoading('Asignando dietas'));
  ck('tambien funciona en nutricion', (await p.textContent('#nutricionContent')).includes('Asignando dietas'));

  await p.evaluate(()=>_entSetLoading('<img src=x onerror=alert(1)>'));
  ck('el texto se escapa', (await p.innerHTML('#entrenamientoContent')).includes('&lt;img'));

  ck('sin errores de JS', errs.length===0, errs);
  await b.close(); process.exit(f?1:0);
})();
