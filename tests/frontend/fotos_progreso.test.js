/* Quitar una foto de progreso subida por error, desde la pantalla del cliente.

   Antes no se podía: una foto equivocada se quedaba en su progreso y en la
   bandeja del coach para siempre. Es una acción sin deshacer —la foto se borra
   también del almacén—, así que lo que hay que comprobar no es solo que el
   botón exista, sino que no borra nada hasta que la persona lo confirma, y que
   borra la del ángulo que está mirando y no otra.
*/
const { chromium } = require('../_pw');

const FOTO = (id, fecha, kg) => ({ id, date: fecha, url: 'https://x.test/' + id + '.jpg', weight: kg });

const DOS = { stats: { weeks: 8 }, weight: { delta: -2.1 }, photos: {
  frontal: [FOTO('ck-vieja', '2026-06-01', 80.2), FOTO('ck-nueva', '2026-08-01', 78.1)],
  lateral: [FOTO('ck-lat', '2026-08-01', 78.1)],
  espalda: [], total: 3 } };

const UNA = { stats: { weeks: 1 }, weight: {}, photos: {
  frontal: [FOTO('ck-sola', '2026-08-01', 78.1)], lateral: [], espalda: [], total: 1 } };

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/fotos.html');
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };
  const llamadas = () => p.evaluate(() => window.__llamadas.filter(l => l.metodo === 'DELETE'));

  // ── El botón está donde tiene que estar ──────────────────────────────────
  await p.evaluate(d => __pinta(d, 'frontal'), DOS);
  ck('cada foto lleva su boton de quitar', await p.locator('.cmp-del').count() === 2,
    await p.locator('.cmp-del').count());

  // Una foto sin id no se puede borrar: el boton no debe salir, porque un
  // boton que no puede funcionar es peor que no tenerlo.
  await p.evaluate(() => __pinta({ stats: {}, weight: {}, photos: {
    frontal: [{ date: '2026-08-01', url: 'https://x.test/a.jpg' }], total: 1 } }, 'frontal'));
  ck('sin id no se pinta el boton', await p.locator('.cmp-del').count() === 0);

  // ── No borra nada sin confirmar ──────────────────────────────────────────
  await p.evaluate(d => __pinta(d, 'frontal'), DOS);
  await p.locator('.cmp-del').first().click();
  ck('pide confirmacion antes de borrar', await p.isVisible('#askBack'));
  ck('y NO ha borrado nada todavia', (await llamadas()).length === 0, await llamadas());

  await p.click('.ask-btns button');            // Cancelar
  ck('cancelar cierra el aviso', !(await p.isVisible('#askBack')));
  ck('y sigue sin borrar nada', (await llamadas()).length === 0, await llamadas());
  ck('la foto sigue ahi', await p.locator('.cmp-del').count() === 2);

  // ── Al confirmar, borra LA QUE SE PIDIO ──────────────────────────────────
  await p.locator('.cmp-del').first().click();
  await p.click('#askSi');
  await p.waitForFunction(() => window.__recargado > 0);
  const l = await llamadas();
  ck('borra una sola foto', l.length === 1, l);
  ck('la de la foto pulsada, no otra', l[0].url.includes('/checkin/ck-vieja/'), l[0]);
  ck('y del angulo que se esta mirando', l[0].url.endsWith('/foto/frontal'), l[0]);
  ck('se recarga el progreso al terminar', await p.evaluate(() => window.__recargado) === 1);
  ck('el aviso se cierra solo', !(await p.isVisible('#askBack')));
  ck('y lo dice', (await p.evaluate(() => window.__toast)) === 'Foto quitada',
    await p.evaluate(() => window.__toast));

  // La segunda foto es otra: el id que se manda tiene que cambiar.
  await p.evaluate(() => { window.__llamadas = []; });
  await p.evaluate(d => __pinta(d, 'frontal'), DOS);
  await p.locator('.cmp-del').nth(1).click();
  await p.click('#askSi');
  await p.waitForFunction(() => window.__recargado > 1);
  ck('cada boton borra su propia foto',
    (await llamadas())[0].url.includes('/checkin/ck-nueva/'), await llamadas());

  // Y en otra pestaña, el ángulo cambia.
  await p.evaluate(() => { window.__llamadas = []; });
  await p.evaluate(d => __pinta(d, 'lateral'), DOS);
  await p.locator('.cmp-del').first().click();
  await p.click('#askSi');
  await p.waitForFunction(() => window.__recargado > 2);
  ck('en lateral se pide borrar la lateral',
    (await llamadas())[0].url.endsWith('/foto/lateral'), await llamadas());

  // ── Si el servidor dice que no ───────────────────────────────────────────
  await p.evaluate(() => { window.__falla = true; window.__llamadas = []; });
  await p.evaluate(d => __pinta(d, 'frontal'), DOS);
  const antes = await p.evaluate(() => window.__recargado);
  await p.locator('.cmp-del').first().click();
  await p.click('#askSi');
  await p.waitForFunction(() => window.__toast === 'No se pudo quitar la foto');
  ck('un fallo se avisa, no se traga', await p.evaluate(() => window.__err) === true);
  ck('y no finge que se borro', await p.evaluate(() => window.__recargado) === antes);
  ck('el boton vuelve a poder pulsarse',
    !(await p.evaluate(() => document.getElementById('askSi').disabled)));
  await p.evaluate(() => { window.__falla = false; });

  // ── Con una sola foto no hay comparacion que fingir ──────────────────────
  await p.evaluate(d => __pinta(d, 'frontal'), UNA);
  ck('una sola foto se enseña una vez', await p.locator('.cmp-ph img').count() === 1,
    await p.locator('.cmp-ph img').count());
  ck('y con un solo boton de quitar', await p.locator('.cmp-del').count() === 1);
  const txt = await p.textContent('#photos');
  ck('sin fingir un antes y un despues', !txt.includes('Inicio vs Ahora'), txt);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
