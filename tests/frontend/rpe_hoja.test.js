/* La hoja del RPE, en la pantalla de entrenar del cliente.

   "RPE" es jerga de entrenador. El cliente tenía una casilla pidiéndole un
   número del 1 al 10 sin decirle de qué, así que o la dejaba vacía o ponía
   cualquier cosa — y un número inventado es peor que un hueco, porque el
   coach no puede distinguirlo de uno real.

   Ahora se le dice cuántas repeticiones le quedaban, que es lo que sí sabe.
   Lo que hay que comprobar es que ese cambio es solo de lenguaje: el número
   que se guarda tiene que seguir siendo el RPE de siempre, porque el coach lo
   lee como tal y el RIR de la pantalla de Fuerza sale de él con 10 − RPE.

   Y que nada se guarda hasta pulsar el botón: la barra se mueve mientras se
   busca el valor, y cada roce no puede ser una respuesta.
*/
const { chromium } = require('../_pw');

const EJ = () => ([
  { name: 'Press banca', target: '8-10', rest: 90, note: '', sets: [
    { reps: '10', kg: '60', rpe: '', done: false },
    { reps: '8', kg: '65', rpe: '8', done: true }] },
  { name: 'Remo', target: '12', rest: 60, note: '', sets: [
    { reps: '', kg: '', rpe: '', done: false }] },
]);

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.setViewportSize({ width: 420, height: 820 });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/rpe.html');
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };
  const abierta = () => p.evaluate(() => document.getElementById('rpeBack').classList.contains('open'));
  const series = () => p.evaluate(() => __series());
  const val = () => p.textContent('#rpeVal');

  /* Abrir la hoja y ESPERAR a que termine de subir. La hoja entra con una
     transición, así que medirla antes de que llegue arriba da coordenadas de
     donde ya no está: el arrastre caía fuera de la barra y la prueba fallaba
     una vez de cada tantas, que es peor que fallar siempre. */
  async function abrir(n){
    await p.locator('.ws-rpe').nth(n).click();
    await p.waitForFunction(() => {
      const t = getComputedStyle(document.querySelector('.rpe-hoja')).transform;
      return t === 'none' || /matrix\(1, 0, 0, 1, 0, 0\)/.test(t);
    });
  }

  await p.evaluate(e => __pinta(e), EJ());

  // ── La casilla ya no pide un número a pelo ───────────────────────────────
  ck('la casilla de RPE es un boton', await p.locator('.ws-rpe').count() === 3,
    await p.locator('.ws-rpe').count());
  const textos = await p.$$eval('.ws-rpe', ns => ns.map(n => n.textContent.trim()));
  ck('sin marcar se ve una raya, no un cero', textos[0] === '—', textos);
  ck('y lo ya marcado se sigue viendo', textos[1] === '8', textos);

  // ── Se abre y dice de qué serie habla ────────────────────────────────────
  ck('la hoja empieza cerrada', !(await abierta()));
  await abrir(0);
  ck('tocar la casilla abre la hoja', await abierta());
  ck('dice de que serie se trata',
    (await p.textContent('#rpeSerie')).replace(/\s+/g, ' ').trim() === 'Serie 1 · 10 reps × 60kg',
    await p.textContent('#rpeSerie'));

  // ── Los tres textos van juntos ───────────────────────────────────────────
  ck('sin valor previo arranca en 7.5', (await val()) === '7.5', await val());
  ck('con su etiqueta', (await p.textContent('#rpeEti')) === 'Exigente', await p.textContent('#rpeEti'));
  // Es la definición: RIR = 10 − RPE. Un 7,5 son 2-3 repeticiones de margen.
  ck('y con lo que de verdad se pregunta',
    (await p.textContent('#rpeDesc')) === 'Te quedan 2-3 reps por hacer',
    await p.textContent('#rpeDesc'));

  // ── La barra ─────────────────────────────────────────────────────────────
  const barra = await p.evaluate(() => {
    const r = document.getElementById('rpeRango');
    return { tipo: r.type, min: r.min, max: r.max, paso: r.step, v: r.value };
  });
  ck('es una barra deslizable de verdad', barra.tipo === 'range', barra);
  ck('de 6 a 10, de medio en medio',
    barra.min === '6' && barra.max === '10' && barra.paso === '0.5', barra);
  ck('y arranca donde marca el numero', barra.v === '7.5', barra);

  // Arrastrar con el teclado es la misma barra: dos pasos suben un punto.
  await p.focus('#rpeRango');
  await p.keyboard.press('ArrowRight');
  await p.keyboard.press('ArrowRight');
  ck('moverla cambia el numero', (await val()) === '8.5', await val());
  ck('y el texto la sigue', (await p.textContent('#rpeEti')) === 'Duro',
    await p.textContent('#rpeEti'));
  ck('y la descripcion tambien',
    (await p.textContent('#rpeDesc')) === 'Te quedan 1-2 reps por hacer',
    await p.textContent('#rpeDesc'));

  // Un arrastre de verdad con el ratón, extremo a extremo.
  const caja = await p.locator('#rpeRango').boundingBox();
  await p.mouse.move(caja.x + caja.width / 2, caja.y + caja.height / 2);
  await p.mouse.down();
  await p.mouse.move(caja.x + caja.width, caja.y + caja.height / 2, { steps: 8 });
  await p.mouse.up();
  ck('arrastrando hasta el final se llega al 10', (await val()) === '10', await val());
  ck('que es el fallo', (await p.textContent('#rpeEti')) === 'Al fallo');
  await p.mouse.move(caja.x + caja.width / 2, caja.y + caja.height / 2);
  await p.mouse.down(); await p.mouse.move(caja.x, caja.y + caja.height / 2, { steps: 8 }); await p.mouse.up();
  ck('y hasta el principio, al 6', (await val()) === '6', await val());

  // ── Los botones de abajo dicen lo mismo que la barra ─────────────────────
  const chips = await p.$$eval('.rpe-chip', ns => ns.map(n => n.textContent.trim()));
  ck('estan los nueve valores', chips.join(',') === '6,6.5,7,7.5,8,8.5,9,9.5,10', chips);
  await p.locator('.rpe-chip').nth(3).click();          // 7.5
  ck('tocar un numero lo elige', (await val()) === '7.5', await val());
  ck('y lo marca', await p.$$eval('.rpe-chip', ns => ns.findIndex(n => n.classList.contains('sel'))) === 3,
    await p.$$eval('.rpe-chip', ns => ns.map(n => n.className)));
  ck('la barra se mueve con el',
    await p.evaluate(() => document.getElementById('rpeRango').value) === '7.5');

  // ── Nada se guarda hasta pulsar el boton ─────────────────────────────────
  ck('MOVER LA BARRA NO GUARDA NADA', (await series())[0][0] === '', await series());
  await p.click('.rpe-guardar');
  ck('la hoja se cierra al guardar', !(await abierta()));
  ck('SE GUARDA EL NUMERO DE RPE, no otra cosa', (await series())[0][0] === '7.5', await series());
  ck('y no toca las demas series',
    (await series())[0][1] === '8' && (await series())[1][0] === '', await series());
  ck('la casilla lo enseña', (await p.$$eval('.ws-rpe', ns => ns[0].textContent.trim())) === '7.5');

  // Cerrar sin guardar deja la serie como estaba.
  await abrir(0);
  await p.locator('.rpe-chip').last().click();          // 10
  await p.click('.rpe-x');
  ck('la X cierra sin guardar', !(await abierta()) && (await series())[0][0] === '7.5', await series());

  await abrir(0);
  await p.locator('.rpe-chip').last().click();
  await p.keyboard.press('Escape');
  ck('escape tampoco guarda', (await series())[0][0] === '7.5', await series());

  await abrir(0);
  await p.locator('.rpe-chip').last().click();
  await p.mouse.click(210, 40);                          // fuera de la hoja
  ck('ni tocar fuera', !(await abierta()) && (await series())[0][0] === '7.5', await series());

  // ── Lo ya puesto sale como estaba ────────────────────────────────────────
  await abrir(1);                                        // esa serie tiene un 8
  ck('abre en el valor que ya tenia', (await val()) === '8', await val());
  ck('y con ese marcado',
    await p.$$eval('.rpe-chip', ns => ns.findIndex(n => n.classList.contains('sel'))) === 4);
  await p.click('.rpe-x');

  // Cada casilla es la suya: la del segundo ejercicio no escribe en la primera.
  await abrir(2);
  ck('una serie sin datos lo dice con interrogantes',
    (await p.textContent('#rpeSerie')).includes('? reps × ?kg'), await p.textContent('#rpeSerie'));
  await p.locator('.rpe-chip').first().click();          // 6
  await p.click('.rpe-guardar');
  ck('cada casilla escribe en su propia serie',
    (await series())[1][0] === '6' && (await series())[0][0] === '7.5', await series());

  // ── Sube desde abajo ─────────────────────────────────────────────────────
  // No es un adorno: una hoja que aparece de golpe en mitad de la pantalla no
  // se lee como algo que se pueda cerrar deslizando.
  const forma = await p.evaluate(() => {
    const h = document.querySelector('.rpe-hoja');
    return { abajo: getComputedStyle(document.querySelector('.rpe-back')).alignItems,
             mueve: getComputedStyle(h).transitionProperty.includes('transform') };
  });
  ck('la hoja se ancla abajo', forma.abajo === 'flex-end', forma);
  ck('y entra deslizandose', forma.mueve, forma);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
