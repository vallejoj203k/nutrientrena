/* El desplegable de micronutrientes al añadir un alimento a la dieta.

   Lo que hay que dejar sujeto:

     · Que salga lo que el alimento TIENE, agrupado, y nada más: una cabecera
       "VITAMINAS" sin nada debajo ocupa sitio para decir que no hay nada.
     · Que el % VRN esté bien. Es lo que hace legible un "210 mg de fósforo",
       y si el porcentaje miente es peor que no ponerlo.
     · Que los valores sean los del alimento y la cabecera diga de qué porción
       habla: escalarlos con la ración sin decirlo llevaría a leer "40% VRN de
       selenio" en una ración de 10 g.
     · Y que un alimento sin ningún dato no abra un desplegable vacío.
*/
const { chromium } = require('../_pw');

// Pechuga de pollo, como el diseño: los micros van en la ficha aparte.
const POLLO = {
  id: 'a1', name: 'Pechuga de pollo', group_food_id: 3,
  calories: 165, proteins: 31, carbohydrates: 0, fats: 3.6,
  quantity: 100, quantity_unit: 'g',
  description: {
    vitb3: 13.7, vitb6: 0.8,
    phosphorus: 210, potassium: 256, sodium: 74, zinc: 1, selenium: 22,
    saturated_fats: 1.0,
  },
};

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.setViewportSize({ width: 480, height: 1000 });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/micros.html');
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };
  const filas = () => p.$$eval('.fsm-mic-fila', ns => ns.map(n => ({
    nombre: n.querySelector('.fsm-mic-nom').textContent.trim(),
    valor: n.querySelector('.fsm-mic-val').textContent.replace(/\s+/g, ' ').trim(),
    vrn: n.querySelector('.fsm-mic-vrn').textContent.trim(),
  })));
  const abierto = () => p.evaluate(() => !document.querySelector('.fsm-mic-body').hidden);

  await p.evaluate(a => __pinta(a), POLLO);

  // Elegir un alimento tiene que pintarlo: si la pantalla no llama al módulo,
  // no hay nada más que medir.
  const hay = await p.locator('.fsm-mic').count();
  ck('AL ELEGIR UN ALIMENTO APARECE EL PANEL', hay === 1, hay);
  if (!hay) { await b.close(); process.exit(1); }

  // ── La cabecera ──────────────────────────────────────────────────────────
  const cab = (await p.textContent('.fsm-mic-t')).replace(/\s+/g, ' ').trim();
  ck('dice de qué porción habla', cab === 'Micronutrientes (100 g)', cab);
  ck('y cuántos datos hay', (await p.textContent('.fsm-mic-n')).trim() === '8 datos',
    await p.textContent('.fsm-mic-n'));

  // ── Cerrado de entrada ───────────────────────────────────────────────────
  ck('arranca cerrado', !(await abierto()));
  ck('y no se leen los datos con él cerrado',
    !(await p.locator('.fsm-mic-fila').first().isVisible()));

  // ── Abrirlo ──────────────────────────────────────────────────────────────
  await p.click('.fsm-mic-head');
  ck('al pulsar se abre', await abierto());
  const titulos = await p.$$eval('.fsm-mic-grupo-t', ns => ns.map(n => n.textContent.trim()));
  ck('agrupado y en el orden del diseño',
    titulos.join(',') === 'Vitaminas,Minerales,Otros', titulos);

  const fs = await filas();
  ck('salen los ocho datos y ninguno más', fs.length === 8, fs.length);
  ck('no aparecen los que el alimento no tiene',
    !fs.some(x => x.nombre === 'Vitamina C' || x.nombre === 'Hierro'), fs.map(x => x.nombre));

  // ── Las cifras y el % VRN ────────────────────────────────────────────────
  const por = n => fs.find(x => x.nombre === n);
  // 13.7 de 16 mg/día = 85.6 % -> 86
  ck('la B3, con su unidad', por('Vitamina B3').valor === '13.7 mg', por('Vitamina B3'));
  ck('Y SU % VRN', por('Vitamina B3').vrn === '86% VRN', por('Vitamina B3'));
  // 210 de 700 mg = 30 %
  ck('el fósforo', por('Fósforo').valor === '210 mg' && por('Fósforo').vrn === '30% VRN', por('Fósforo'));
  // 256 de 2000 mg = 12.8 -> 13 %
  ck('el potasio', por('Potasio').vrn === '13% VRN', por('Potasio'));
  // 22 de 55 mcg = 40 %. Y va en microgramos, no en miligramos.
  ck('el selenio va en mcg', por('Selenio').valor === '22.0 mcg', por('Selenio'));
  ck('y su VRN cuenta en mcg', por('Selenio').vrn === '40% VRN', por('Selenio'));
  // 1 g de 20 g = 5 %
  ck('las grasas saturadas van en gramos',
    por('Grasas saturadas').valor === '1.00 g' && por('Grasas saturadas').vrn === '5% VRN',
    por('Grasas saturadas'));
  // Tres cifras significativas, para poder leer la columna de un vistazo.
  ck('tres cifras significativas', por('Vitamina B6').valor === '0.800 mg', por('Vitamina B6'));

  // ── Lo que no tiene referencia, no lleva porcentaje ──────────────────────
  await p.evaluate(a => __pinta(Object.assign({}, a, { id: 'a2',
    description: { cholesterol: 85, water: 65, glycemic_index: 0 } })), POLLO);
  await p.click('.fsm-mic-head');
  const sinRef = await filas();
  ck('el colesterol y el agua no se inventan un VRN',
    sinRef.every(x => x.vrn === ''), sinRef);
  ck('el índice glucémico no lleva unidad',
    (sinRef.find(x => x.nombre === 'Índice glucémico') || {}).valor === '0',
    sinRef.find(x => x.nombre === 'Índice glucémico'));

  // ── Los valores NO se escalan con la ración ──────────────────────────────
  await p.evaluate(a => __pinta(a), POLLO);
  await p.evaluate(() => fsmSetQty(200));
  let r = await p.evaluate(() => __racion());
  ck('la ración sí se escala', r.k === '330' && r.p === '62', r);
  ck('PERO LOS MICROS SIGUEN SIENDO LOS DEL ALIMENTO',
    (await filas()).find(x => x.nombre === 'Fósforo').valor === '210 mg', await filas());
  ck('y la cabecera lo dice',
    (await p.textContent('.fsm-mic-t')).includes('(100 g)'), await p.textContent('.fsm-mic-t'));

  // ── Un alimento medido por unidades ──────────────────────────────────────
  await p.evaluate(a => __pinta(Object.assign({}, a, { id: 'a3', name: 'Huevo',
    quantity: 1, quantity_unit: 'ud' })), POLLO);
  ck('la porción se dice en su unidad',
    (await p.textContent('.fsm-mic-t')).includes('(1 ud)'), await p.textContent('.fsm-mic-t'));

  // ── La fibra, en el aporte de la ración ──────────────────────────────────
  await p.evaluate(a => __pinta(Object.assign({}, a, { id: 'a4', fiber: 2.2 })), POLLO);
  await p.evaluate(() => fsmSetQty(200));
  ck('la fibra sale con los demás macros', (await p.evaluate(() => __racion())).fib === '4.4',
    await p.evaluate(() => __racion()));

  // ── Sin micros, sin desplegable ──────────────────────────────────────────
  await p.evaluate(a => __pinta({ id: 'a5', name: 'Agua', calories: 0, quantity: 100 }), POLLO);
  ck('un alimento sin datos no abre un desplegable vacío',
    await p.locator('.fsm-mic').count() === 0
    && (await p.getAttribute('#fsmMicros', 'style')).includes('display: none'),
    await p.locator('.fsm-mic').count());

  // Y volver a uno que sí tiene lo trae de vuelta: el panel se repinta.
  await p.evaluate(a => __pinta(a), POLLO);
  ck('y al volver a uno con datos reaparece', await p.locator('.fsm-mic').count() === 1);

  // ── Se queda abierto al mirar otro alimento ──────────────────────────────
  await p.click('.fsm-mic-head');
  await p.evaluate(a => __pinta(Object.assign({}, a, { id: 'a6' })), POLLO);
  ck('abierto sigue abierto en el siguiente alimento', await abierto());

  // ── Escapado ─────────────────────────────────────────────────────────────
  await p.evaluate(() => __pinta({ id: 'a7', name: '<img src=x>', quantity: 100,
    quantity_unit: '<b>g</b>', description: { zinc: 1 } }));
  ck('escapa el HTML',
    (await p.innerHTML('#fsmMicros')).includes('&lt;b&gt;g'),
    await p.innerHTML('#fsmMicros'));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
