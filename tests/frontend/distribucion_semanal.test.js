/* El carril de Nutrición: la distribución semanal y las dietas del plan.

   Antes era una cosa O la otra: con menú semanal salían los siete días, y sin
   él, la lista de dietas. Enseñar solo una mitad obliga a recordar la otra —
   mirando los días no se sabe cuántas dietas hay ni cómo se llaman, y mirando
   las dietas no se sabe qué come el cliente el jueves.

   Lo que hay que dejar sujeto:

     · Que cada día diga la dieta que le toca DE VERDAD, y que un día sin
       dieta lo diga en vez de quedarse en blanco pareciendo un fallo.
     · Que el carril y el modal de distribución llamen IGUAL a la misma dieta.
       Dos nombres para lo mismo es lo que hace dudar de si son lo mismo.
     · Y que una dieta que ya no está en la lista del cliente no borre el día:
       se dice lo que se sabe de ella, no se finge que el día está libre.
*/
const { chromium } = require('../_pw');

const DIETAS = [
  { id: 'd1', title: 'Recomposicion', calories: 2100, foods: [1, 2, 3, 4, 5] },
  { id: 'd2', title: 'Deficit moderado', calories: 1800, foods: [1, 2, 3, 4] },
  { id: 'd3', title: 'Volumen limpio', calories: 2800, foods: [1, 2, 3, 4, 5] },
];

// Como los devuelve `_nutMenuDays()`: un objeto indexado por día, no un array.
const SEMANA = (ids) => {
  const o = {};
  ids.forEach((id, i) => { o[i] = id ? { diet_id: id, diet_title: 'x' } : { diet_id: null }; });
  return o;
};

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.setViewportSize({ width: 400, height: 1000 });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/distribucion.html');
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };
  const filas = () => p.$$eval('.nut-dist-row', ns => ns.map(n => ({
    abv: n.querySelector('.nut-dist-abv').textContent.trim(),
    lbl: n.querySelector('.nut-dist-lbl').textContent.trim(),
    vacio: n.classList.contains('vacio'),
    sel: n.classList.contains('sel'),
  })));
  const clicks = () => p.evaluate(() => window.__clicks);

  // El reparto del prototipo: tres dietas rotando por los siete días.
  const rota = ['d1', 'd2', 'd3', 'd1', 'd2', 'd3', 'd1'];
  await p.evaluate(([d, s]) => __pinta(d, s), [DIETAS, SEMANA(rota)]);

  // ── Los siete días, con su dieta ─────────────────────────────────────────
  let fs = await filas();
  ck('estan los siete dias', fs.length === 7, fs.length);
  ck('en orden, de lunes a domingo',
    fs.map(x => x.abv).join(',') === 'LUN,MAR,MIÉ,JUE,VIE,SÁB,DOM', fs.map(x => x.abv));
  ck('el lunes dice su dieta', fs[0].lbl === 'Día 1 · Recomposicion · 2100kcal', fs[0]);
  ck('el martes la suya', fs[1].lbl === 'Día 2 · Deficit moderado · 1800kcal', fs[1]);
  ck('y el jueves repite la del lunes', fs[3].lbl === fs[0].lbl, [fs[3], fs[0]]);

  // La etiqueta sale de la MISMA función que usa el modal de distribución.
  const delModal = await p.evaluate(d => _wdEtiqueta(d[0], 0), DIETAS);
  ck('el carril y el modal la llaman igual', fs[0].lbl === delModal, { carril: fs[0].lbl, modal: delModal });

  // ── Las dietas del plan ──────────────────────────────────────────────────
  const tarj = await p.$$eval('.nut-diet-item', ns => ns.map(n => ({
    n: n.querySelector('.nut-diet-name').textContent.trim(),
    sub: n.querySelector('.nut-diet-sub').textContent.trim(),
    meta: (n.querySelector('.nut-diet-meta') || {}).textContent,
  })));
  ck('una tarjeta por dieta', tarj.length === 3, tarj);
  ck('numeradas Día 1, 2 y 3', tarj.map(t => t.n).join(',') === 'Día 1,Día 2,Día 3', tarj.map(t => t.n));
  ck('con su nombre y sus kcal', tarj[0].sub === 'Recomposicion · 2100kcal', tarj[0]);
  ck('y cuantas comidas tiene', (tarj[0].meta || '').trim() === '5 comidas · 2100 kcal', tarj[0]);
  ck('y el boton de añadir', await p.locator('.nut-diet-add').count() === 1);

  // ── Un día sin dieta lo dice ─────────────────────────────────────────────
  await p.evaluate(([d, s]) => __pinta(d, s), [DIETAS, SEMANA(['d1', null, 'd3', null, null, null, 'd1'])]);
  fs = await filas();
  ck('el dia sin dieta se marca', fs[1].vacio && !fs[0].vacio, fs.slice(0, 2));
  ck('Y LO DICE, no se queda en blanco', fs[1].lbl === 'Sin asignar', fs[1]);

  // ── Una dieta que ya no está en la lista ─────────────────────────────────
  // Si el día se pintara vacío, el coach creería que ese día está libre.
  const fuera = { 0: { diet_id: 'zz', diet_title: 'Dieta antigua' } };
  for (let i = 1; i < 7; i++) fuera[i] = { diet_id: null };
  await p.evaluate(([d, s]) => __pinta(d, s), [DIETAS, fuera]);
  fs = await filas();
  ck('una dieta que ya no esta en la lista no vacia el dia',
    !fs[0].vacio && fs[0].lbl === 'Dieta antigua', fs[0]);

  // ── Sin distribución guardada ────────────────────────────────────────────
  await p.evaluate(d => __pinta(d, null), DIETAS);
  fs = await filas();
  ck('los dias siguen estando', fs.length === 7, fs.length);
  ck('todos sin asignar', fs.every(x => x.vacio && x.lbl === 'Sin asignar'), fs);
  ck('y las dietas tambien se ven', await p.locator('.nut-diet-item').count() === 3);
  // Un día que no hace nada al pulsarlo parece estropeado: lleva a ponerla.
  await p.locator('.nut-dist-row').first().click();
  ck('tocar un dia sin distribucion lleva a ponerla',
    (await clicks()).join() === 'distribucion', await clicks());

  // ── A dónde lleva cada cosa ──────────────────────────────────────────────
  await p.evaluate(([d, s]) => __pinta(d, s), [DIETAS, SEMANA(rota)]);
  await p.locator('.nut-dist-row').nth(3).click();
  ck('tocar el jueves selecciona el jueves', (await clicks()).join() === 'dia:3', await clicks());

  await p.evaluate(([d, s]) => __pinta(d, s), [DIETAS, SEMANA(rota)]);
  await p.locator('.nut-diet-item').nth(2).click();
  ck('tocar una dieta la selecciona', (await clicks()).join() === 'dieta:2', await clicks());

  await p.evaluate(([d, s]) => __pinta(d, s), [DIETAS, SEMANA(rota)]);
  await p.click('.nut-dist-edit');
  ck('el lapiz abre la distribucion', (await clicks()).join() === 'distribucion', await clicks());

  await p.evaluate(([d, s]) => __pinta(d, s), [DIETAS, SEMANA(rota)]);
  await p.click('.nut-diet-add');
  ck('y el boton añade una dieta', (await clicks()).join() === 'anadir', await clicks());

  // ── Qué sale marcado ─────────────────────────────────────────────────────
  await p.evaluate(([d, s]) => __pinta(d, s, 'dia', 2), [DIETAS, SEMANA(rota)]);
  fs = await filas();
  ck('mirando un dia, se marca ese dia', fs.filter(x => x.sel).length === 1 && fs[2].sel, fs);
  ck('y ninguna dieta', await p.locator('.nut-diet-item.sel').count() === 0);

  await p.evaluate(([d, s]) => __pinta(d, s, 'dieta', 1), [DIETAS, SEMANA(rota)]);
  fs = await filas();
  ck('mirando una dieta, ningun dia sale marcado', fs.every(x => !x.sel), fs);
  ck('y solo esa dieta',
    await p.$$eval('.nut-diet-item', ns => ns.findIndex(n => n.classList.contains('sel'))) === 1);

  // ── Sin dietas asignadas ─────────────────────────────────────────────────
  await p.evaluate(() => __pinta([], null));
  ck('sin dietas no se cae', (await filas()).length === 7);
  ck('y ofrece añadir la primera', await p.locator('.nut-diet-add').count() === 1);

  // ── Escapado ─────────────────────────────────────────────────────────────
  await p.evaluate(() => __pinta([{ id: 'x', title: '<img src=x onerror=alert(1)>', calories: 100, foods: [] }],
    { 0: { diet_id: 'x' } }));
  ck('escapa el HTML del nombre',
    (await p.innerHTML('#carril')).includes('&lt;img'), (await p.textContent('.nut-dist-lbl')));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
