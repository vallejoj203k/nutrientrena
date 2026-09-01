/* La hoja del RPE, en la pantalla de entrenar del cliente.

   "RPE" es jerga de entrenador. El cliente tenía una casilla pidiéndole un
   número del 1 al 10 sin decirle de qué, así que o la dejaba vacía o ponía
   cualquier cosa — y un número inventado es peor que un hueco, porque el
   coach no puede distinguirlo de uno real.

   Ahora se le pregunta por lo que sí sabe: cuántas repeticiones más habría
   podido hacer. Lo que hay que comprobar es que ese cambio es solo de
   lenguaje: el número que se guarda tiene que seguir siendo el RPE de
   siempre, porque el coach lo lee como tal y el RIR de la pantalla de Fuerza
   sale de él con 10 − RPE.
*/
const { chromium } = require('../_pw');

const EJ = () => ([
  { name: 'Press banca', target: '8-10', rest: 90, note: '', sets: [
    { reps: '10', kg: '60', rpe: '', done: false },
    { reps: '8', kg: '65', rpe: '8', done: true }] },
  { name: 'Remo', target: '12', rest: 60, note: '', sets: [
    { reps: '12', kg: '40', rpe: '', done: false }] },
]);

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.setViewportSize({ width: 420, height: 780 });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/rpe.html');
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };
  const abierta = () => p.evaluate(() => document.getElementById('rpeBack').classList.contains('open'));

  await p.evaluate(e => __pinta(e), EJ());

  // ── La casilla ya no pide un número a pelo ───────────────────────────────
  ck('la casilla de RPE es un boton', await p.locator('.ws-rpe').count() === 3,
    await p.locator('.ws-rpe').count());
  ck('ya no queda un campo donde teclear el numero',
    await p.locator('input.ws-in').count() === 6, await p.locator('input.ws-in').count());
  const textos = await p.$$eval('.ws-rpe', ns => ns.map(n => n.textContent.trim()));
  ck('sin marcar se ve una raya, no un cero', textos[0] === '—', textos);
  ck('y lo ya marcado se sigue viendo', textos[1] === '8', textos);

  // ── Se abre y explica ────────────────────────────────────────────────────
  ck('la hoja empieza cerrada', !(await abierta()));
  await p.locator('.ws-rpe').first().click();
  ck('tocar la casilla abre la hoja', await abierta());

  const hoja = await p.textContent('.rpe-hoja');
  ck('pregunta en cristiano', hoja.includes('¿Cuánto te ha costado?'), hoja);
  ck('y explica que eso es el RPE', hoja.includes('RPE'), hoja);
  ck('habla de repeticiones, que es lo que la persona sabe',
    hoja.includes('repeticiones'), hoja);

  const opts = await p.$$eval('.rpe-opt', ns => ns.map(n => ({
    n: n.querySelector('.rpe-n').textContent.trim(),
    t: n.querySelector('.rpe-txt b').textContent.trim(),
    d: n.querySelector('.rpe-txt span').textContent.trim(),
  })));
  ck('la escala va de mas duro a mas suave',
    opts.map(o => o.n).join(',') === '10,9,8,7,6,5', opts.map(o => o.n));
  ck('el 10 es el fallo', opts[0].d.includes('ni una más'), opts[0]);
  // Es la definición: RIR = 10 − RPE. Un 9 son 1 repetición en recámara.
  ck('el 9 dice UNA repeticion de margen', /\b1 repetici/.test(opts[1].d), opts[1]);
  ck('el 8 dice DOS', opts[2].d.includes('2'), opts[2]);
  ck('el 7 dice TRES', opts[3].d.includes('3'), opts[3]);

  // ── Elegir guarda el número de siempre ───────────────────────────────────
  await p.locator('.rpe-opt').nth(2).click();          // "Duro" → 8
  ck('la hoja se cierra al elegir', !(await abierta()));
  let series = await p.evaluate(() => __series());
  ck('SE GUARDA EL NUMERO DE RPE, no otra cosa', series[0][0] === '8', series);
  ck('y no toca las demas series', series[0][1] === '8' && series[1][0] === '', series);
  ck('la casilla lo enseña', (await p.$$eval('.ws-rpe', ns => ns[0].textContent.trim())) === '8');

  // Cada casilla es la suya: la del segundo ejercicio no puede escribir en la
  // del primero.
  await p.locator('.ws-rpe').nth(2).click();
  await p.locator('.rpe-opt').first().click();          // 10
  series = await p.evaluate(() => __series());
  ck('cada casilla escribe en su propia serie',
    series[1][0] === '10' && series[0][0] === '8', series);

  // ── Lo ya puesto sale marcado ────────────────────────────────────────────
  await p.locator('.ws-rpe').nth(1).click();           // esa serie tiene un 8
  ck('la opcion actual sale marcada',
    (await p.$$eval('.rpe-opt', ns => ns.findIndex(n => n.classList.contains('sel')))) === 2,
    await p.$$eval('.rpe-opt', ns => ns.map(n => n.className)));

  // ── Se puede dejar sin marcar ────────────────────────────────────────────
  await p.click('#rpeQuitar');
  series = await p.evaluate(() => __series());
  ck('se puede quitar lo puesto', series[0][1] === '', series);

  // ── Cerrar sin elegir no cambia nada ─────────────────────────────────────
  await p.locator('.ws-rpe').first().click();
  await p.mouse.click(210, 60);                        // fuera de la hoja
  ck('tocar fuera cierra la hoja', !(await abierta()));
  ck('y no cambia el valor', (await p.evaluate(() => __series()))[0][0] === '8');

  await p.locator('.ws-rpe').first().click();
  await p.keyboard.press('Escape');
  ck('escape tambien cierra', !(await abierta()));
  ck('sin tocar el valor', (await p.evaluate(() => __series()))[0][0] === '8');

  // ── El "?" de la cabecera explica sin editar nada ────────────────────────
  await p.locator('.ws-ayuda').first().click();
  ck('el "?" abre la explicacion', await abierta());
  ck('pero ahi no se elige nada',
    await p.evaluate(() => Array.from(document.querySelectorAll('.rpe-opt')).every(o => o.disabled)));
  ck('ni se ofrece quitar un valor que no se esta editando',
    await p.evaluate(() => document.getElementById('rpeQuitar').style.display === 'none'));
  await p.keyboard.press('Escape');
  ck('y el entreno sigue igual',
    JSON.stringify(await p.evaluate(() => __series())) === JSON.stringify([['8', ''], ['10']]),
    await p.evaluate(() => __series()));

  // ── Sube desde abajo ─────────────────────────────────────────────────────
  // No es un adorno: una hoja que aparece de golpe en mitad de la pantalla no
  // se lee como algo que se pueda cerrar deslizando.
  const caja = await p.evaluate(() => {
    const h = document.querySelector('.rpe-hoja'), s = getComputedStyle(h);
    return { abajo: getComputedStyle(document.querySelector('.rpe-back')).alignItems,
             mueve: s.transitionProperty.includes('transform') };
  });
  ck('la hoja se ancla abajo', caja.abajo === 'flex-end', caja);
  ck('y entra deslizandose', caja.mueve, caja);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
