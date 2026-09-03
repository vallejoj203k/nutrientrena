/* El creador de recetas: la tarjeta de alimentos crece con lo que tiene.

   Según se añadían alimentos, el botón de "Añadir alimento" se iba escondiendo
   por debajo del borde de la tarjeta hasta desaparecer: no había forma de
   añadir el siguiente. La tarjeta vive en una columna flex con scroll y, como
   recorta sus esquinas (`overflow:hidden`), se dejaba comprimir por debajo de
   su contenido en vez de alargar el scroll de la columna.

   Lo que hay que dejar sujeto:

     · Que el botón siga DENTRO de la tarjeta con muchos alimentos, que es
       justo cuando dejaba de verse.
     · Que la tarjeta mida lo que mide su tabla, y no menos.
     · Y que lo que no cabe se alcance con el scroll de la columna, no que se
       recorte y se pierda.
*/
const { chromium } = require('../_pw');

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  // Una pantalla de portátil, que es donde se veía: en un monitor alto cabe
  // todo y no se nota.
  await p.setViewportSize({ width: 1280, height: 720 });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/receta.html');
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };

  const medidas = () => p.evaluate(() => {
    const btn = document.querySelector('.rcp-addrow .rcp-addlink').getBoundingClientRect();
    const tarjeta = document.querySelectorAll('.sec-card')[0];
    const caja = tarjeta.getBoundingClientRect();
    const tabla = document.querySelector('.rcp-tbl').getBoundingClientRect();
    const col = document.querySelector('.fv-main');
    return {
      botonAbajo: Math.round(btn.bottom), tarjetaAbajo: Math.round(caja.bottom),
      tarjetaAlto: Math.round(caja.height), tablaAlto: Math.round(tabla.height),
      scroll: col.scrollHeight, visible: col.clientHeight,
    };
  });

  for (const n of [3, 6, 12, 25]) {
    await p.evaluate(x => __pinta(x), n);
    const m = await medidas();
    ck(`con ${n} alimentos el boton sigue DENTRO de la tarjeta`,
      m.botonAbajo <= m.tarjetaAbajo, m);
    ck(`con ${n} alimentos la tarjeta mide lo que su tabla`,
      m.tarjetaAlto >= m.tablaAlto, m);
  }

  // Lo que no cabe se alcanza bajando, no se pierde.
  await p.evaluate(() => __pinta(25));
  let m = await medidas();
  ck('la columna scrollea en vez de recortar', m.scroll > m.visible, m);
  await p.evaluate(() => { document.querySelector('.fv-main').scrollTop = 99999; });
  ck('y bajando del todo se llega al boton',
    await p.locator('.rcp-addrow .rcp-addlink').isVisible());
  ck('el boton responde', await p.evaluate(() => {
    document.querySelector('.rcp-addrow .rcp-addlink').click();
    return !!window.__abierto;
  }));

  // La tarjeta de "Preparación" tampoco se come a la de arriba.
  ck('la preparacion queda debajo, no encima',
    await p.evaluate(() => {
      const c = document.querySelectorAll('.sec-card');
      return c[1].getBoundingClientRect().top >= c[0].getBoundingClientRect().bottom - 1;
    }));

  // Y con pocos alimentos nada cambia: la tarjeta no se estira de más.
  await p.evaluate(() => __pinta(2));
  m = await medidas();
  ck('con dos alimentos la tarjeta se ajusta a su contenido',
    m.tarjetaAlto < 340, m);

  // Sin alimentos sale el aviso con su propio botón.
  await p.evaluate(() => { _ingrRows = []; renderIngrTable(); });
  ck('sin alimentos se explica y se puede añadir',
    (await p.textContent('.rcp-empty')).includes('Aún no hay alimentos')
    && await p.locator('.rcp-empty .rcp-addlink').isVisible());

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
