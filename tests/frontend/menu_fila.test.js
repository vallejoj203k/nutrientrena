/* El menú de "…" de una fila, en las tablas de la Librería.

   Se abría y no se veía. La causa no estaba en el menú sino en la tabla:
   `.lib-table` lleva `overflow:hidden` para redondear las esquinas y
   `.lib-table-wrap` lleva `overflow-y:auto` para desplazarse, y una caja con
   `overflow` recorta a sus hijos posicionados. Con una sola dieta en la
   tabla no se veía absolutamente nada.

   Por eso esto se comprueba con la tabla de verdad y su CSS de verdad: con
   una tabla de mentira el fallo no se reproduce.

   Y por eso la comprobación no mira dónde CREE el menú que está —eso no
   cambiaba, el rectángulo era el mismo estando recortado—, sino qué hay
   pintado en ese punto de la pantalla. Es lo único que distingue "está ahí"
   de "se ve".
*/
const { chromium } = require('../_pw');

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.setViewportSize({ width: 1200, height: 700 });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/menu.html');
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };

  /* ¿Se VE de verdad? Se pregunta al navegador qué hay pintado en el centro
     de cada opción del menú. Si sale la opción, se ve y se puede pulsar; si
     sale la tabla, está recortada debajo. */
  const seVe = () => p.evaluate(() => {
    const dd = document.querySelector('.lib-menu-dd.open');
    if (!dd) return { abierto: false };
    const items = Array.from(dd.querySelectorAll('.lib-menu-item'));
    const tapados = items.filter(it => {
      const r = it.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return true;
      const en = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return !(en && dd.contains(en));
    });
    const r = dd.getBoundingClientRect();
    return {
      abierto: true, items: items.length, tapados: tapados.length,
      dentro: r.top >= 0 && r.bottom <= window.innerHeight
              && r.left >= 0 && r.right <= window.innerWidth,
      caja: { top: Math.round(r.top), bottom: Math.round(r.bottom) },
    };
  });

  // ── Una tabla con una sola fila: el caso de la captura ───────────────────
  await p.evaluate(() => __soloUna());
  await p.locator('.mas-btn').first().click();
  let v = await seVe();
  ck('el menu se abre', v.abierto, v);
  ck('SE VE ENTERO, no lo recorta la tabla', v.tapados === 0, v);
  ck('y cae dentro de la ventana', v.dentro, v);

  // Y se puede pulsar de verdad, que es para lo que está.
  await p.locator('.lib-menu-dd.open .lib-menu-item').first().click({ timeout: 2000 });
  ck('sus opciones se pueden pulsar', true);

  // ── Con muchas filas y desplazamiento ────────────────────────────────────
  await p.reload();
  await p.locator('.mas-btn').first().click();
  v = await seVe();
  ck('con la tabla llena tambien se ve', v.tapados === 0 && v.dentro, v);

  // La última fila: abajo no cabe, así que el menú tiene que abrirse hacia
  // arriba en vez de salirse por el borde inferior.
  await p.evaluate(() => { const w = document.getElementById('wrap'); w.scrollTop = w.scrollHeight; });
  await p.locator('.mas-btn').last().click();
  v = await seVe();
  ck('el menu de la ultima fila no se sale por abajo', v.dentro, v);
  ck('y tampoco lo recorta nadie', v.tapados === 0, v);
  const btnAbajo = await p.locator('.mas-btn').last().boundingBox();
  ck('se ha abierto hacia arriba', v.caja.bottom <= btnAbajo.y + 2, { v, btnAbajo });

  // ── Comportamiento del menú ──────────────────────────────────────────────
  await p.reload();
  await p.locator('.mas-btn').nth(0).click();
  ck('solo hay un menu abierto', await p.locator('.lib-menu-dd.open').count() === 1);
  await p.locator('.mas-btn').nth(3).click();
  ck('abrir otro cierra el anterior', await p.locator('.lib-menu-dd.open').count() === 1,
    await p.locator('.lib-menu-dd.open').count());
  await p.locator('.mas-btn').nth(3).click();
  ck('el mismo boton lo cierra', await p.locator('.lib-menu-dd.open').count() === 0);

  await p.locator('.mas-btn').nth(0).click();
  await p.keyboard.press('Escape');
  ck('escape lo cierra', await p.locator('.lib-menu-dd.open').count() === 0);

  await p.locator('.mas-btn').nth(0).click();
  await p.mouse.click(600, 400);
  ck('tocar fuera lo cierra', await p.locator('.lib-menu-dd.open').count() === 0);

  /* Al desplazar se cierra: el menú está anclado a una fila que se mueve, y
     uno flotando sobre otra fila señalaría a la dieta equivocada — el peor
     final para un menú que tiene un "Eliminar". */
  await p.locator('.mas-btn').nth(0).click();
  await p.evaluate(() => { const w = document.getElementById('wrap'); w.scrollTop = 300; w.dispatchEvent(new Event('scroll')); });
  ck('al desplazar la tabla se cierra', await p.locator('.lib-menu-dd.open').count() === 0);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
