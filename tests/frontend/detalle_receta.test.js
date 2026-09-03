/* El panel de detalle de la receta.

   Enseñaba "Ingrediente · 200g" en todas las líneas —la receta solo sabía a
   qué id apuntaba cada ingrediente, no cómo se llamaba— y la preparación no
   salía por ninguna parte: para leer los pasos había que abrir el editor.

   Lo que hay que dejar sujeto:

     · Que cada línea diga QUÉ ingrediente es y cuánto, con su unidad.
     · Que la preparación salga, en pasos y numerada una sola vez.
     · Que un ingrediente cuyo alimento ya no está se diga, en vez de colarse
       como uno más sin nombre.
     · Y que los cuatro macros lleven los iconos de siempre.
*/
const { chromium } = require('../_pw');

const RECETA = {
  id: 7, name: 'Arroz con pollo', meal_type: 'Comida', organization_id: 'o1',
  prep_time: 30, servings: 2, image: 'foto.jpg',
  calories: 540, proteins: 42, carbs: 65, fats: 12,
  instructions: 'Cuece el arroz en agua con sal.\nSalpimienta el pollo y dóralo.\nAñade la cebolla y el ajo.',
  details: [
    { id: 1, order: 0, aliment_id: 'a1', quantity: 250,
      aliment: { id: 'a1', name: 'Pechuga de pollo', quantity: 100, quantity_unit: 'g' } },
    { id: 2, order: 1, aliment_id: 'a2', quantity: 160, notes: 'en crudo',
      aliment: { id: 'a2', name: 'Arroz blanco', quantity: 100, quantity_unit: 'g' } },
    { id: 3, order: 2, aliment_id: 'a3', quantity: 1,
      aliment: { id: 'a3', name: 'Pimiento rojo', quantity: 1, quantity_unit: 'ud' } },
    { id: 4, order: 3, aliment_id: 'a4', quantity: 10,
      aliment: { id: 'a4', name: 'Aceite de oliva virgen', quantity: 100, quantity_unit: 'ml' } },
  ],
};

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.setViewportSize({ width: 1100, height: 900 });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/detalle-receta.html');
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };
  const ingredientes = () => p.$$eval('.rdp-ingr', ns => ns.map(n => ({
    nombre: n.querySelector('.rdp-ingr-nm').textContent.trim(),
    cantidad: n.querySelector('.rdp-ingr-q').textContent.replace(/\s+/g, ' ').trim(),
  })));

  await p.evaluate(r => __pinta(r), RECETA);

  // ── La cabecera ──────────────────────────────────────────────────────────
  ck('el titulo', (await p.textContent('#rdpTitle')).trim() === 'Arroz con pollo');
  ck('el tiempo y las raciones',
    (await p.textContent('#rdpSub')).trim() === '30 min · 2 raciones', await p.textContent('#rdpSub'));

  // ── Ingredientes ─────────────────────────────────────────────────────────
  const ing = await ingredientes();
  ck('sale un ingrediente por linea', ing.length === 4, ing.length);
  ck('CON SU NOMBRE, no "Ingrediente"',
    ing.map(x => x.nombre).join(' | ') ===
    'Pechuga de pollo | Arroz blanco | Pimiento rojo | Aceite de oliva virgen', ing.map(x => x.nombre));
  ck('y su cantidad', ing[0].cantidad === '250 g', ing[0]);
  ck('cada uno en SU unidad, no todo en gramos',
    ing[2].cantidad === '1 ud' && ing[3].cantidad === '10 ml', [ing[2], ing[3]]);
  ck('la nota del ingrediente se enseña',
    ing[1].cantidad === '160 g (en crudo)', ing[1]);
  ck('el rotulo dice para cuantas raciones son',
    (await p.textContent('#rdpIngrSec')).trim() === 'Ingredientes · 2 raciones',
    await p.textContent('#rdpIngrSec'));

  // ── Preparación ──────────────────────────────────────────────────────────
  const pasos = await p.$$eval('.rdp-paso', ns => ns.map(n => n.textContent.trim()));
  ck('LA PREPARACION SALE', pasos.length === 3, pasos);
  ck('en pasos, numerados', pasos[0].startsWith('1') && pasos[1].startsWith('2'), pasos);
  ck('con lo que escribio el autor',
    pasos[0].includes('Cuece el arroz en agua con sal.'), pasos[0]);

  // Si el autor ya los numeró, no se numeran dos veces.
  await p.evaluate(r => __pinta(Object.assign({}, r, {
    instructions: '1. Cuece el arroz\n2) Dora el pollo\n- Sirve' })), RECETA);
  const pasos2 = await p.$$eval('.rdp-paso', ns => ns.map(n => n.textContent.trim()));
  ck('un paso ya numerado no sale con dos numeros',
    pasos2[0] === '1Cuece el arroz' && pasos2[1] === '2Dora el pollo', pasos2);
  ck('y una viñeta tampoco', pasos2[2] === '3Sirve', pasos2);

  // ── Los macros ───────────────────────────────────────────────────────────
  await p.evaluate(r => __pinta(r), RECETA);
  const macros = await p.$$eval('.rdp-macro', ns => ns.map(n => ({
    val: n.querySelector('.rdp-macro-val').textContent.trim(),
    lbl: n.querySelector('.rdp-macro-lbl').textContent.trim(),
    color: n.querySelector('svg').getAttribute('stroke'),
    trazos: n.querySelectorAll('svg path').length,
  })));
  ck('las cuatro cifras',
    macros.map(m => m.val).join(',') === '540,42g,65g,12g', macros.map(m => m.val));
  ck('con sus rotulos',
    macros.map(m => m.lbl).join(',') === 'Kcal,Prot,Carb,Grasa', macros.map(m => m.lbl));
  // Los mismos iconos y colores que el editor de dietas y el buscador de
  // alimentos: antes eran una cruz y un circulo, que no son nada.
  ck('LOS ICONOS DE SIEMPRE, cada uno con su color',
    macros.map(m => m.color).join(',') === '#F97316,#EF4444,#D97706,#3B82F6',
    macros.map(m => m.color));
  ck('y son los dibujos de verdad, no una cruz',
    macros[2].trazos === 4 && macros[3].trazos === 1, macros.map(m => m.trazos));

  // ── Lo que falta ─────────────────────────────────────────────────────────
  await p.evaluate(r => __pinta(Object.assign({}, r, { instructions: '   ' })), RECETA);
  ck('sin preparacion no se deja el rotulo suelto',
    await p.locator('#rdpPrepWrap').isVisible() === false);

  await p.evaluate(r => __pinta(Object.assign({}, r, { details: [] })), RECETA);
  ck('sin ingredientes tampoco', await p.locator('#rdpIngrWrap').isVisible() === false);

  // Un alimento borrado del catálogo: la línea existe pero no tiene nombre.
  await p.evaluate(r => __pinta(Object.assign({}, r, {
    details: [{ id: 9, order: 0, aliment_id: 'zz', quantity: 100, aliment: null }] })), RECETA);
  ck('un alimento que ya no esta se dice',
    (await p.textContent('.rdp-ingr')).includes('no disponible'), await p.textContent('.rdp-ingr'));

  // ── Escapado ─────────────────────────────────────────────────────────────
  await p.evaluate(r => __pinta(Object.assign({}, r, {
    instructions: '<img src=x onerror=alert(1)>',
    details: [{ id: 1, order: 0, aliment_id: 'a', quantity: 1,
                aliment: { name: '<b>ojo</b>', quantity: 1, quantity_unit: 'g' } }] })), RECETA);
  const html = await p.innerHTML('.rdp-body');
  ck('escapa el HTML', html.includes('&lt;b&gt;ojo') && html.includes('&lt;img'), html.slice(0, 120));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
