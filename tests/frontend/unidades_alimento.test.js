/* La unidad del alimento, allí donde se enseña.

   El coach abría el previo de una dieta y leía "Big Mac · 1g". El mismo
   alimento, dos clics más allá en el editor, decía "1 ud" y sus 590 kcal.
   Ninguna de las dos pantallas daba error: la del previo preguntaba solo por
   `quantity_type`, que los alimentos del catálogo nuevo no tienen, y al no
   encontrarlo caía en "g" por defecto. Un valor por defecto callado convierte
   "no lo sé" en una afirmación falsa, y esa es la peor forma de fallar.

   La unidad se deducía a mano en seis pantallas. Ahora sale de un solo sitio,
   y esto comprueba las dos cosas: la función, y el previo real de diets.html.
*/
const { chromium } = require('../_pw');

// Tal como los devuelve la API después de la carga del catálogo.
const BIGMAC   = { name: 'Big Mac', calories: 590, quantity: 1, quantity_unit: 'ud' };
const HUEVO    = { name: 'Huevo de gallina', calories: 153, quantity: 100, quantity_unit: 'g' };
const YOGUR    = { name: 'Yogur de frutilla', calories: 60.4, quantity: 200, quantity_unit: 'ml' };
// Y uno de los antiguos, que la lleva en la relación y con la etiqueta larga.
const VIEJO    = { name: 'Huevo viejo', calories: 74, quantity: 1,
                   quantity_type: { description: 'Unidad' } };

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/unidades.html');
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };
  const u = al => p.evaluate(a => window.macrosAlimento.unidadDe(a), al);

  // ── La función ───────────────────────────────────────────────────────────
  ck('la unidad del catalogo se respeta', await u(BIGMAC) === 'ud', await u(BIGMAC));
  ck('los gramos siguen siendo gramos', await u(HUEVO) === 'g', await u(HUEVO));
  ck('y los mililitros no se vuelven gramos', await u(YOGUR) === 'ml', await u(YOGUR));
  ck('un alimento antiguo la trae en la relacion', await u(VIEJO) === 'ud', await u(VIEJO));

  // Las mismas unidades escritas de otra forma son la misma unidad. Si no, el
  // catálogo se vería con "gr" y "g" mezclados según de dónde saliera la fila.
  const igual = [['gr', 'g'], ['gramos', 'g'], ['u', 'ud'], ['unidad', 'ud'],
                 ['Unidad', 'ud'], ['UD', 'ud'], ['tz', 'ud'], ['mililitros', 'ml']];
  for (const [escrito, esperado] of igual) {
    const r = await u({ quantity_unit: escrito });
    ck(`"${escrito}" se lee como "${esperado}"`, r === esperado, r);
  }

  // Sin dato, gramos: es lo que vale para casi todo el catálogo. Pero SOLO
  // cuando de verdad no hay dato, no cuando el dato está en el otro campo.
  ck('sin unidad, gramos', await u({ name: 'X' }) === 'g', await u({ name: 'X' }));
  ck('sin alimento no revienta', await u(null) === 'g', await u(null));
  // Una unidad que no conocemos se enseña tal cual, no se traduce a gramos.
  ck('una unidad rara no se convierte en gramos',
    await u({ quantity_unit: 'cucharada' }) === 'cucharada',
    await u({ quantity_unit: 'cucharada' }));

  // ── El previo real de diets.html ─────────────────────────────────────────
  await p.evaluate(([bm, hu, yo]) => __previo({ foods: [
    { name: 'Desayuno', time: '08:00:00', detail: [
      { quantity: 1, aliment: bm },
      { quantity: 100, aliment: hu },
      { quantity: 200, aliment: yo },
    ] },
  ] }), [BIGMAC, HUEVO, YOGUR]);

  const filas = await p.$$eval('.dpp-food-row', ns => ns.map(n => ({
    t: n.querySelector('.dpp-food-name').textContent.trim(),
    k: n.querySelector('.dpp-food-kcal').textContent.trim(),
  })));
  ck('tres alimentos en el previo', filas.length === 3, filas);
  ck('AHORA el Big Mac es una unidad', filas[0].t === 'Big Mac · 1 ud', filas[0]);
  ck('y sigue valiendo 590 kcal, no 5.9', filas[0].k === '590 kcal', filas[0]);
  ck('el huevo por peso son gramos', filas[1].t === 'Huevo de gallina · 100 g', filas[1]);
  ck('y el yogur, mililitros', filas[2].t === 'Yogur de frutilla · 200 ml', filas[2]);
  ck('ninguna fila miente diciendo gramos',
    !filas.some(x => /Big Mac.*\bg\b/.test(x.t)), filas.map(x => x.t));

  // Una comida sin alimentos no debe inventar una fila vacía.
  await p.evaluate(() => __previo({ foods: [{ name: 'Cena', detail: [] }] }));
  ck('comida vacia no pinta filas', await p.locator('.dpp-food-row').count() === 0);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
