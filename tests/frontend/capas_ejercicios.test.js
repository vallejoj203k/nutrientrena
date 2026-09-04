/* Qué queda encima de qué en la pantalla de ejercicios.

   Al previsualizar el vídeo de un ejercicio desde su ficha, el vídeo salía
   POR DETRÁS de la ficha: se veía media ventana negra asomando por un lado y
   no había forma de darle al play. El cajón de detalle estaba en una capa más
   alta que la ventana del vídeo, y el vídeo se abre DESDE el cajón.

   Lo que hay que dejar sujeto:

     · Que el vídeo tape a la ficha, y también al formulario a pantalla
       completa, que es el otro sitio desde donde se abre.
     · Que los avisos se vean con un panel abierto: los errores al subir un
       vídeo o una imagen saltan justo ahí, y detrás del panel no los lee
       nadie.
*/
const { chromium } = require('../_pw');

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.setViewportSize({ width: 1280, height: 800 });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/capas-ejercicios.html');
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };
  const encima = sel => p.evaluate(s => __encima(s), sel);
  const capa = sel => p.evaluate(s => parseInt(getComputedStyle(document.querySelector(s)).zIndex) || 0, sel);

  // ── El caso reportado: el vídeo desde la ficha ───────────────────────────
  await p.evaluate(() => __abreCajon());
  await p.waitForTimeout(450);
  ck('el cajón de detalle está delante', await encima('#xvPanel') === 'cajon');

  await p.evaluate(() => __abreVideo());
  await p.waitForTimeout(300);
  ck('EL VIDEO TAPA A LA FICHA, no al revés',
    await encima('#videoOverlay .modal') === 'video', await encima('#videoOverlay .modal'));
  ck('y también donde está la ficha', await encima('#xvPanel') === 'video', await encima('#xvPanel'));
  ck('se puede pulsar el vídeo',
    await p.locator('#videoOverlay .modal-close').isVisible());

  // ── Y desde el formulario a pantalla completa ────────────────────────────
  await p.evaluate(() => __abreFormulario());
  await p.waitForTimeout(400);
  ck('el vídeo también tapa al formulario',
    await encima('#videoOverlay .modal') === 'video', await encima('#videoOverlay .modal'));

  // ── Los avisos, por encima de todo ───────────────────────────────────────
  // Los errores al subir un vídeo o una imagen saltan desde dentro del
  // formulario: por debajo de él no los ve nadie.
  await p.evaluate(() => __avisa());
  await p.waitForTimeout(350);
  ck('UN AVISO SE VE CON UN PANEL ABIERTO',
    await encima('#toast') === 'toast', await encima('#toast'));

  // ── Y el orden queda dicho en el CSS ─────────────────────────────────────
  const zv = await capa('#videoOverlay'), zc = await capa('#xvPanel'), zf = await capa('#xfPanel');
  ck('el vídeo va por encima de los dos paneles', zv > zc && zv > zf, { zv, zc, zf });
  ck('y el aviso por encima del vídeo', await capa('#toast') > zv, await capa('#toast'));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
