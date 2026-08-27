/* La lista de la compra a partir del plan nutricional.

   El plan dice qué come el cliente; la lista dice qué compra. La diferencia
   está en las cuentas, y son las cuentas lo que puede salir mal de formas que
   nadie nota hasta estar en el supermercado:

     · el mismo alimento aparece en varias comidas y en varios días, y hay que
       juntarlo en un solo renglón;
     · pero solo se puede sumar lo que comparte unidad: "2 ud" + "150 g" no son
       152 de nada;
     · y los decimales de coma flotante salen a la pantalla si nadie los
       redondea: 0.1 + 0.2 = 0.30000000000000004. */
const { chromium } = require('../_pw');

const COMIDA = (nombre, cant, unidad, cat) => ({ name: nombre, quantity: cant, unit: unidad, category: cat });

// Dos días con dieta y uno sin, que es como llega un plan de verdad.
const DIAS = [
  { name: 'Lunes', has_diet: true, meals: [
    { name: 'Desayuno', foods: [COMIDA('Avena', 80, 'g', 'Cereales y granos'),
                                COMIDA('Plátano', 1, 'ud', 'Frutas')] },
    { name: 'Comida', foods: [COMIDA('Pechuga de pollo', 120, 'g', 'Aves'),
                              COMIDA('Avena', 20, 'g', 'Cereales y granos')] },
  ] },
  { name: 'Martes', has_diet: true, meals: [
    { name: 'Comida', foods: [COMIDA('Pechuga de pollo', 200, 'g', 'Aves'),
                              COMIDA('Plátano', 2, 'ud', 'Frutas')] },
  ] },
  { name: 'Miércoles', has_diet: false, meals: [
    { name: 'Comida', foods: [COMIDA('No debería salir', 999, 'g', 'Aves')] } ] },
];

(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/lista.html');
  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };

  const lista = (dias, dia) => p.evaluate(([d, i]) => listaCompra.listaDeCompra(d, i), [dias, dia === undefined ? null : dia]);
  const fmt = (c, u) => p.evaluate(([a, b]) => listaCompra.formatearCantidad(a, b), [c, u]);
  const plano = g => g.flatMap(x => x.items.map(i => `${i.nombre} ${i.cantidad}${i.unidad}`));

  // ── Un día ───────────────────────────────────────────────────────────────
  const lunes = await lista(DIAS, 0);
  ck('EL MISMO ALIMENTO EN DOS COMIDAS SE JUNTA',
    plano(lunes).includes('Avena 100g'), plano(lunes));
  ck('el lunes son 3 renglones, no 4', plano(lunes).length === 3, plano(lunes));
  ck('agrupado por categoría del catálogo',
    JSON.stringify(lunes.map(g => g.categoria)) === '["Aves","Cereales y granos","Frutas"]',
    lunes.map(g => g.categoria));

  // ── La semana ────────────────────────────────────────────────────────────
  const semana = await lista(DIAS);
  ck('LA SEMANA SUMA LOS DÍAS', plano(semana).includes('Pechuga de pollo 320g'), plano(semana));
  ck('un día SIN dieta no entra en la compra',
    !JSON.stringify(semana).includes('No debería salir'), plano(semana));
  ck('las unidades sueltas también se suman', plano(semana).includes('Plátano 3ud'), plano(semana));

  // ── Lo que NO se puede sumar ─────────────────────────────────────────────
  const mixto = await lista([{ has_diet: true, meals: [{ foods: [
    COMIDA('Huevo', 2, 'ud', 'Huevos'), COMIDA('Huevo', 150, 'g', 'Huevos')] }] }]);
  ck('GRAMOS Y UNIDADES NO SE SUMAN EN UN NÚMERO SIN SENTIDO',
    plano(mixto).length === 2 && plano(mixto).includes('Huevo 2ud') && plano(mixto).includes('Huevo 150g'),
    plano(mixto));

  // ── Los decimales ────────────────────────────────────────────────────────
  const dec = await lista([{ has_diet: true, meals: [{ foods: [
    COMIDA('Aceite', 0.1, 'g', 'Aceites'), COMIDA('Aceite', 0.2, 'g', 'Aceites')] }] }]);
  ck('0,1 + 0,2 no sale como 0.30000000000000004',
    dec[0].items[0].cantidad === 0.3, dec[0].items[0].cantidad);

  // ── Sin categoría ────────────────────────────────────────────────────────
  const sin = await lista([{ has_diet: true, meals: [{ foods: [
    { name: 'Suelto', quantity: 10, unit: 'g' }, COMIDA('Manzana', 1, 'ud', 'Frutas')] }] }]);
  ck('lo que no tiene categoría va a "Otros", no se reparte a ojo',
    sin.map(g => g.categoria).join() === 'Frutas,Otros', sin.map(g => g.categoria));

  // ── Bordes ───────────────────────────────────────────────────────────────
  ck('un plan vacío da una lista vacía', (await lista([])).length === 0);
  ck('sin días con dieta, lista vacía',
    (await lista([{ has_diet: false, meals: [] }])).length === 0);
  const anon = await lista([{ has_diet: true, meals: [{ foods: [
    { name: '  ', quantity: 5, unit: 'g' }, COMIDA('Arroz', 50, 'g', 'Cereales')] }] }]);
  ck('un alimento sin nombre no ocupa un renglón en blanco',
    plano(anon).length === 1, plano(anon));

  // ── Cómo se escribe la cantidad ──────────────────────────────────────────
  ck('1400 g se leen como 1,4 kg', await fmt(1400, 'g') === '1,4 kg', await fmt(1400, 'g'));
  ck('1400 ml se leen como 1,4 l', await fmt(1400, 'ml') === '1,4 l', await fmt(1400, 'ml'));
  ck('por debajo del kilo se queda en gramos', await fmt(840, 'g') === '840 g', await fmt(840, 'g'));
  ck('las unidades NO se convierten a kilos', await fmt(1400, 'ud') === '1400 ud', await fmt(1400, 'ud'));
  ck('sin decimales cuando no los hay', await fmt(7, 'ud') === '7 ud', await fmt(7, 'ud'));

  // ── El texto que se descarga ─────────────────────────────────────────────
  const txt = await p.evaluate(g => listaCompra.listaComoTexto(g, 'Lunes'), lunes);
  ck('el fichero lleva las categorías y las cantidades',
    txt.includes('CEREALES Y GRANOS') && txt.includes('Avena — 100 g'), txt);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
