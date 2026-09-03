/* "Información nutricional completa": lo que suma el menú del día.

   Mientras se monta la dieta se ven las kcal y los macros, pero los
   micronutrientes no salían por ninguna parte. Esta ventana los enseña
   sumados de todas las comidas.

   Lo que hay que dejar sujeto:

     · Que mande a sumar TODOS los alimentos de TODAS las comidas, con las
       cantidades que hay puestas en ese momento —también en una dieta sin
       guardar— y ninguna fila a medio rellenar.
     · Que lo que no se sabe no se enseñe como un cero, y que se diga cuántos
       alimentos no aportan datos: una suma coja que parece completa engaña.
     · Y que un fallo se diga, en vez de dejar la ventana en blanco, que
       parecería un plan sin nada.
*/
const { chromium } = require('../_pw');

// Dos comidas: dos alimentos puestos, uno sin elegir y otro sin cantidad.
const COMIDAS = [
  { id: 1, name: 'Desayuno', rows: [
      { id: 1, aliment_id: 'a1', quantity: '100' },
      { id: 2, aliment_id: null, quantity: '50' },
    ] },
  { id: 2, name: 'Comida', rows: [
      { id: 3, aliment_id: 'a2', quantity: '200' },
      { id: 4, aliment_id: 'a3', quantity: '' },
    ] },
];

const RESPUESTA = {
  calories: 1439.2, proteins: 88.1, carbohydrates: 120.5, fats: 55.2,
  micros: { fiber: 12.3, iron: 8.4, sodium: 900, vitc: 45, saturated_fats: 6.1 },
  con_datos: 2, sin_datos: 1, no_encontrados: [],
};

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.setViewportSize({ width: 1100, height: 950 });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/resumen-dia.html');
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };
  const abrir = async () => {
    await p.click('.rn-abrir');
    await p.waitForFunction(() => !document.querySelector('.rn-cargando'));
  };
  const filas = () => p.$$eval('.rn-cuerpo .fsm-mic-fila', ns => ns.map(n => ({
    nombre: n.querySelector('.fsm-mic-nom').textContent.trim(),
    valor: n.querySelector('.fsm-mic-val').textContent.replace(/\s+/g, ' ').trim(),
    vrn: n.querySelector('.fsm-mic-vrn').textContent.trim(),
  })));

  await p.evaluate(c => __comidas(c), COMIDAS);
  await p.evaluate(r => { window.__respuesta = r; }, RESPUESTA);
  await abrir();

  // ── Qué se manda a sumar ─────────────────────────────────────────────────
  const l = await p.evaluate(() => window.__llamadas);
  ck('pide la suma al servidor', l.length === 1 && l[0].url.includes('/aliments/resumen-nutricional'), l);
  ck('MANDA LOS ALIMENTOS DE TODAS LAS COMIDAS',
    JSON.stringify(l[0].cuerpo.items) === JSON.stringify([
      { aliment_id: 'a1', quantity: 100 }, { aliment_id: 'a2', quantity: 200 }]), l[0].cuerpo);
  ck('una fila sin alimento no cuenta',
    !l[0].cuerpo.items.some(x => !x.aliment_id), l[0].cuerpo.items);
  ck('ni una sin cantidad',
    !l[0].cuerpo.items.some(x => !x.quantity), l[0].cuerpo.items);

  // ── Los macros del día ───────────────────────────────────────────────────
  const macros = await p.$$eval('.rn-macro', ns => ns.map(n => ({
    lbl: n.querySelector('.rn-macro-t').textContent.trim(),
    val: n.querySelector('.rn-macro-v').textContent.trim(),
  })));
  ck('las cinco cifras del diseño',
    macros.map(m => m.lbl).join(',') === 'Calorías,Proteínas,Carbohidratos,Grasas,Fibra',
    macros.map(m => m.lbl));
  ck('con lo que suma el día', macros[0].val === '1439 kcal', macros[0]);
  ck('y la fibra sale de los micros', macros[4].val === '12.3 g', macros[4]);

  // ── Los micronutrientes ──────────────────────────────────────────────────
  const fs = await filas();
  ck('salen los micros sumados', fs.length === 4, fs);
  ck('agrupados', (await p.$$eval('.rn-cuerpo .fsm-mic-grupo-t', ns => ns.map(n => n.textContent.trim())))
    .join(',') === 'Vitaminas,Minerales,Otros');
  const por = n => fs.find(x => x.nombre === n);
  ck('el hierro, con su unidad', por('Hierro').valor === '8.40 mg', por('Hierro'));
  // 8.4 de 14 mg/día = 60 %. Para un día entero, el % VRN es justo lo que se
  // quiere leer: cuánto del día cubre el plan.
  ck('Y SU % DEL DIA', por('Hierro').vrn === '60% VRN', por('Hierro'));
  ck('la vitamina C', por('Vitamina C').vrn === '56% VRN', por('Vitamina C'));
  ck('LA FIBRA NO SE REPITE ABAJO, que ya está en las tarjetas',
    !fs.some(x => x.nombre === 'Fibra'), fs.map(x => x.nombre));
  ck('y lo que nadie registró no aparece',
    !fs.some(x => x.nombre === 'Zinc' || x.nombre === 'Calcio'), fs.map(x => x.nombre));

  // ── Lo que falta se dice ─────────────────────────────────────────────────
  ck('avisa de los alimentos sin ficha',
    (await p.textContent('.rn-falta')).includes('1 alimento del plan no tiene'),
    await p.textContent('.rn-falta'));
  ck('y explica qué es el % VRN',
    (await p.textContent('.rn-pie')).includes('valor de referencia diario'));

  await p.evaluate(() => { window.__respuesta = Object.assign({}, window.__respuesta, { sin_datos: 0 }); });
  await p.click('.rn-x'); await abrir();
  ck('sin alimentos huérfanos no se avisa de nada',
    await p.locator('.rn-falta').count() === 0);

  // ── Sin micros en el plan ────────────────────────────────────────────────
  await p.click('.rn-x');
  await p.evaluate(() => { window.__respuesta = { calories: 300, proteins: 20, micros: {}, sin_datos: 3 }; });
  await abrir();
  ck('un plan sin micros lo dice, no enseña una lista vacía',
    (await p.textContent('.rn-vacio')).includes('no tienen micronutrientes registrados'),
    await p.textContent('.rn-vacio'));
  ck('pero los macros siguen saliendo',
    (await p.textContent('.rn-macro-v')).includes('300'));

  // ── Sin nada puesto no se molesta al servidor ────────────────────────────
  await p.click('.rn-x');
  await p.evaluate(() => { __comidas([{ id: 1, name: 'Desayuno', rows: [] }]); window.__llamadas = []; });
  await abrir();
  ck('un plan vacío no llama al servidor', (await p.evaluate(() => window.__llamadas)).length === 0);
  ck('y la ventana lo dice igual',
    (await p.textContent('.rn-vacio')).includes('no tienen micronutrientes'));

  // ── Si falla ─────────────────────────────────────────────────────────────
  await p.click('.rn-x');
  await p.evaluate(c => { __comidas(c); window.__falla = true; }, COMIDAS);
  await p.click('.rn-abrir');
  await p.waitForFunction(() => document.body.textContent.includes('No se ha podido'));
  ck('UN FALLO SE DICE, no se deja la ventana en blanco',
    (await p.textContent('#rnBody')).includes('No se ha podido calcular'));
  ck('y se puede reintentar',
    await p.locator('#rnBody .rn-abrir').count() === 1);
  await p.evaluate(() => { window.__falla = false; });
  await p.click('#rnBody .rn-abrir');
  await p.waitForFunction(() => document.querySelectorAll('.rn-macro').length > 0);
  ck('reintentar vuelve a pedirlo', (await p.evaluate(() => window.__llamadas)).length >= 2);

  // ── Cerrar ───────────────────────────────────────────────────────────────
  ck('la ventana está abierta', await p.locator('.rn-overlay.open').count() === 1);
  await p.keyboard.press('Escape');
  ck('escape la cierra', await p.locator('.rn-overlay.open').count() === 0);
  await abrir();
  await p.click('.rn-overlay', { position: { x: 5, y: 5 } });
  ck('y tocar fuera también', await p.locator('.rn-overlay.open').count() === 0);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
