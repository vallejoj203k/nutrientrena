const { chromium } = require('../_pw');
(async () => {
  // Huso negativo a proposito: es donde el bug clasico de UTC se manifiesta
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ timezoneId: 'America/Bogota' });
  const page = await ctx.newPage();
  const errs = []; page.on('pageerror', e => errs.push(String(e)));
  await page.goto('file://' + __dirname + '/fechas.html');
  let fallos = 0;
  const check = (n,c,x)=>{console.log((c?'OK   ':'FALLO ')+n+(c?'':' -> '+JSON.stringify(x)));if(!c)fallos++;};
  const set = async (id,v)=>{await page.fill('#'+id,v);};
  const get = id=>page.inputValue('#'+id);

  // 12 semanas desde el 3 ago 2026 -> 26 oct 2026
  await set('dt_start','2026-08-03');
  await page.evaluate(()=>{document.getElementById('dt_weeks').value='12';onWeeksInput();});
  check('12 semanas calcula el fin', await get('dt_end') === '2026-10-26', await get('dt_end'));

  // Cambiar el inicio arrastra el fin manteniendo las 12 semanas
  await page.evaluate(()=>{document.getElementById('dt_start').value='2026-09-01';onStartDateInput();});
  check('mover el inicio arrastra el fin', await get('dt_end') === '2026-11-24', await get('dt_end'));

  // Cambiar el fin a mano recalcula las semanas
  await page.evaluate(()=>{document.getElementById('dt_end').value='2026-10-06';onEndDateInput();});
  check('fin a mano recalcula semanas', await get('dt_weeks') === '5', await get('dt_weeks'));

  // Fin anterior al inicio -> semanas vacias, no negativas
  await page.evaluate(()=>{document.getElementById('dt_end').value='2026-08-01';onEndDateInput();});
  check('fin anterior al inicio no da semanas negativas', await get('dt_weeks') === '', await get('dt_weeks'));

  // Sin inicio, escribir semanas no revienta ni inventa fecha
  await page.evaluate(()=>{document.getElementById('dt_start').value='';document.getElementById('dt_end').value='';document.getElementById('dt_weeks').value='8';onWeeksInput();});
  check('sin fecha de inicio no inventa el fin', await get('dt_end') === '', await get('dt_end'));

  // Ida y vuelta: semanas -> fin -> semanas da lo mismo (sin desfase por UTC)
  await page.evaluate(()=>{document.getElementById('dt_start').value='2026-01-15';document.getElementById('dt_weeks').value='6';onWeeksInput();});
  const fin = await get('dt_end');
  await page.evaluate(()=>{onEndDateInput();});
  check('ida y vuelta estable en huso negativo', await get('dt_weeks') === '6', {fin, semanas: await get('dt_weeks')});

  check('sin errores de JS', errs.length === 0, errs);
  await browser.close();
  process.exit(fallos?1:0);
})();
