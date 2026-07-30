const { chromium } = require('/opt/node22/lib/node_modules/playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e)));
  await page.goto('file://' + __dirname + '/harness.html');

  let fallos = 0;
  const check = (n, c, extra) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(extra))); if (!c) fallos++; };

  check('render inicial', JSON.stringify(await page.evaluate(() => __orden())) === '["Lunes","Martes","Miércoles"]');
  check('el asa existe', await page.locator('.day-chip').first().locator('.day-grip').count() === 1);

  // Arrastrar Lunes por debajo de Miércoles
  // pos: 'antes' suelta en la mitad superior de la tarjeta destino, 'despues' en la inferior
  async function arrastrar(desde, hasta, pos) {
    const g = page.locator('.day-chip').nth(desde).locator('.day-grip');
    const t = page.locator('.day-chip').nth(hasta);
    const gb = await g.boundingBox(), tb = await t.boundingBox();
    await page.mouse.move(gb.x + gb.width/2, gb.y + gb.height/2);
    await page.mouse.down();
    await page.mouse.move(gb.x + gb.width/2, gb.y + 20, { steps: 5 });
    const y = pos === 'antes' ? tb.y + 4 : tb.y + tb.height - 4;
    await page.mouse.move(tb.x + tb.width/2, y, { steps: 12 });
    await page.mouse.up();
    await page.waitForTimeout(120);
  }

  await arrastrar(0, 2, 'despues');
  check('Lunes baja al final', JSON.stringify(await page.evaluate(() => __orden())) === '["Martes","Miércoles","Lunes"]', await page.evaluate(() => __orden()));
  check('la seleccion sigue al dia arrastrado', await page.evaluate(() => __sel()) === 2, await page.evaluate(() => __sel()));

  // Volver a subirlo
  await arrastrar(2, 0, 'antes');
  check('vuelve arriba', JSON.stringify(await page.evaluate(() => __orden())) === '["Lunes","Martes","Miércoles"]', await page.evaluate(() => __orden()));
  check('la seleccion vuelve con el', await page.evaluate(() => __sel()) === 0, await page.evaluate(() => __sel()));

  // Un clic en el asa sin mover no debe reordenar
  const g = page.locator('.day-chip').nth(1).locator('.day-grip');
  const gb = await g.boundingBox();
  await page.mouse.move(gb.x + gb.width/2, gb.y + gb.height/2);
  await page.mouse.down(); await page.mouse.up();
  await page.waitForTimeout(80);
  check('un clic sin mover no reordena', JSON.stringify(await page.evaluate(() => __orden())) === '["Lunes","Martes","Miércoles"]');

  // Clic normal en una tarjeta sigue seleccionando
  await page.locator('.day-chip').nth(1).click();
  await page.waitForTimeout(60);
  check('el clic normal sigue seleccionando', await page.evaluate(() => __sel()) === 1, await page.evaluate(() => __sel()));

  // No queda fantasma suelto
  check('no queda fantasma en el DOM', await page.evaluate(() => document.querySelectorAll('body > .day-chip').length) === 0);
  check('sin errores de JS', errs.length === 0, errs);

  await browser.close();
  process.exit(fallos ? 1 : 0);
})();
