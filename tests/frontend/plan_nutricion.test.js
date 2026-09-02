/* El panel del plan de alimentación: la cabecera y las comidas.

   Rehecho para que se vea como el diseño. Lo que se comprueba no es que sea
   bonito —eso se mira— sino que las cifras que enseña son las de las comidas
   que tiene debajo:

     · Las cuatro cifras de la cabecera se SUMAN de los alimentos, no se leen
       de lo que se escribió al crear la dieta. Si un alimento cambia de
       cantidad, leerlas dejaría una cabecera diciendo 2100 kcal sobre los
       gramos de otro plan.
     · Y cada fila lleva SU unidad. Antes ponía "g" a todo: un huevo salía
       como "1 g" con las kcal de una unidad entera.
*/
const { chromium } = require('../_pw');

// 100 g de avena (389 kcal/100g) y 2 huevos grandes (74 kcal por UNIDAD).
const AVENA  = { name: 'Avena', calories: 389, proteins: 16.9, carbohydrates: 66.3, fats: 6.9, quantity: 100, quantity_unit: 'g' };
const HUEVO  = { name: 'Huevo Grande (L)', calories: 74, proteins: 6.3, carbohydrates: 0.4, fats: 5, quantity: 1, quantity_unit: 'ud' };
const LECHE  = { name: 'Leche', calories: 42, proteins: 3.4, carbohydrates: 4.8, fats: 1, quantity: 100, quantity_unit: 'ml' };

const DIETA = {
  title: 'Recomposicion', diet_type: 'Equilibrada',
  // `calories` a propósito EQUIVOCADO: la cabecera tiene que sumar las
  // comidas, no creerse este número.
  calories: 9999,
  foods: [
    { name: 'Desayuno', detail: [
      { quantity_calc: 100, aliment: AVENA },
      { quantity_calc: 2, aliment: HUEVO }] },
    { name: 'Comida', detail: [
      { quantity_calc: 200, aliment: LECHE }] },
  ],
};

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.setViewportSize({ width: 940, height: 1000 });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/plan.html');
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };
  const stats = () => p.$$eval('.nplan-stat', ns => ns.map(n => ({
    v: n.querySelector('.nplan-stat-v').textContent.trim(),
    l: n.querySelector('.nplan-stat-l').textContent.trim(),
  })));

  await p.evaluate(d => __pinta(d), DIETA);

  // ── La cabecera ──────────────────────────────────────────────────────────
  ck('lleva el rotulo del plan',
    (await p.textContent('.nplan-hero-eye')).trim() === 'Plan de alimentación');
  // 389 + 74×2 = 537 del desayuno; 42/100×200 = 84 de la comida. Total 621.
  ck('el titulo lleva el nombre y las kcal SUMADAS',
    (await p.textContent('.nplan-hero-t')).trim() === 'Recomposicion · 621kcal',
    await p.textContent('.nplan-hero-t'));
  ck('y el subtitulo, tipo y comidas',
    (await p.textContent('.nplan-hero-s')).trim() === 'Equilibrada · 2 comidas/día',
    await p.textContent('.nplan-hero-s'));

  const st = await stats();
  ck('cuatro cifras', st.length === 4, st);
  ck('en el orden del diseño',
    st.map(x => x.l).join(',') === 'Calorías,Proteínas,Carbohidratos,Grasas', st.map(x => x.l));
  ck('LAS KCAL SE SUMAN, no se cree el numero de la dieta', st[0].v === '621', st[0]);
  // 16.9 + 6.3×2 = 29.5 → 30, más 3.4/100×200 = 6.8 → 36.3 → 36
  ck('las proteinas tambien se suman', st[1].v === '36', st[1]);
  ck('los carbos', st[2].v === '77', st[2]);   // 66.3 + 0.8 + 9.6 = 76.7
  ck('y las grasas', st[3].v === '19', st[3]); // 6.9 + 10 + 2 = 18.9

  // ── Las comidas ──────────────────────────────────────────────────────────
  const comidas = await p.$$eval('.nmeal', ns => ns.map(n => ({
    nombre: n.querySelector('.nmeal-pill').textContent.trim(),
    hora: (n.querySelector('.nmeal-time') || {}).textContent,
    kcal: n.querySelector('.nmeal-kcal').textContent.trim(),
    cabeceras: Array.from(n.querySelectorAll('th')).map(t => t.textContent.trim()),
    filas: Array.from(n.querySelectorAll('tbody tr')).map(tr =>
      Array.from(tr.children).map(td => td.textContent.trim())),
  })));
  ck('una tarjeta por comida', comidas.length === 2, comidas.length);
  ck('con su nombre en la pastilla', comidas[0].nombre === 'Desayuno', comidas[0]);
  ck('su hora', (comidas[0].hora || '').includes('08:00'), comidas[0]);
  ck('y sus kcal', comidas[0].kcal === '537 kcal', comidas[0]);
  ck('la tabla lleva las tres columnas',
    comidas[0].cabeceras.join(',') === 'Producto,Cantidad,Unidad', comidas[0].cabeceras);

  ck('la avena va en gramos',
    comidas[0].filas[0].join('|') === 'Avena|100|g', comidas[0].filas[0]);
  ck('EL HUEVO VA EN UNIDADES, no en gramos',
    comidas[0].filas[1].join('|') === 'Huevo Grande (L)|2|ud', comidas[0].filas[1]);
  ck('y la leche en mililitros',
    comidas[1].filas[0].join('|') === 'Leche|200|ml', comidas[1].filas[0]);

  // ── Los botones ──────────────────────────────────────────────────────────
  const btns = await p.$$eval('.nplan-hero-btn', ns => ns.map(n => n.textContent.trim()));
  ck('estan editar, PDF y borrar', btns.length === 3 && btns[0] === 'Editar' && btns[1] === 'PDF', btns);
  await p.locator('.nplan-hero-btn').nth(0).click();
  await p.locator('.nplan-hero-btn').nth(1).click();
  await p.locator('.nplan-hero-btn').nth(2).click();
  ck('y hacen lo que dicen',
    (await p.evaluate(() => window.__acciones)).join() === 'editar,pdf,borrar',
    await p.evaluate(() => window.__acciones));

  // ── Mirando un día del menú semanal ──────────────────────────────────────
  await p.evaluate(d => __pinta(d, true, 'Martes'), DIETA);
  ck('el subtitulo dice de que dia se trata',
    (await p.textContent('.nplan-hero-s')).includes('Martes'), await p.textContent('.nplan-hero-s'));

  // ── Sin datos, sin inventos ──────────────────────────────────────────────
  await p.evaluate(() => __pinta({ title: 'Vacía', foods: [] }));
  ck('una dieta sin comidas no inventa cifras',
    (await stats()).map(x => x.v).join(',') === '0,0,0,0', await stats());
  ck('ni dice "0 comidas/día"',
    !(await p.textContent('.nplan-hero-s')).includes('comida'), await p.textContent('.nplan-hero-s'));

  await p.evaluate(() => __pinta({ title: 'Solo una', foods: [{ name: 'Cena', detail: [] }] }));
  ck('una comida sin alimentos lo dice',
    (await p.textContent('.nmeal-t')).includes('Sin alimentos en esta comida'),
    await p.textContent('.nmeal-t'));

  // ── Escapado ─────────────────────────────────────────────────────────────
  await p.evaluate(() => __pinta({ title: '<img src=x>', foods: [
    { name: '<b>x</b>', detail: [{ quantity_calc: 1, aliment: { name: '<i>y</i>', calories: 1, quantity: 1 } }] }] }));
  const html = await p.innerHTML('#plan');
  ck('escapa el HTML', html.includes('&lt;img') && html.includes('&lt;i&gt;y'), html.slice(0, 200));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
