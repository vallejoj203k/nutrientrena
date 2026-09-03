/* Progreso · Fotos: la comparativa y el historial de tomas.

   Arriba se comparan dos fechas del MISMO ángulo, porque comparar un frente
   con una espalda no compara nada. Abajo, el historial enseña lo que mandó el
   cliente cada día —tenga uno, dos o los tres ángulos— para poder llevar
   cualquier toma a la comparativa sin buscarla en el desplegable.

   Lo que hay que dejar sujeto:

     · Que las dos listas sean independientes: el filtro del historial no
       cambia lo que se está comparando arriba.
     · Que pulsar una foto de espalda ponga la comparativa EN espalda. Si no,
       se elige una foto y arriba sigue viéndose otra cosa.
     · Y que los botones del grupo no dejen un hueco: si esa fecha no tiene
       foto del ángulo que está puesto, se cambia a uno que sí tenga.
*/
const { chromium } = require('../_pw');

const ck = (fecha, peso, frente, lateral, espalda) => ({
  checkin_date: fecha, weight: peso,
  photo_url: frente || null, photo2: lateral || null, photo3: espalda || null,
});

// Seis tomas, como el diseño. La de enero solo tiene frente.
const CKS = [
  ck('2026-01-08', 80.2, 'f1.jpg'),
  ck('2026-02-05', 79.8, 'f2.jpg', 'l2.jpg', 'e2.jpg'),
  ck('2026-02-19', 79.1, 'f3.jpg', 'l3.jpg', 'e3.jpg'),
  ck('2026-03-05', 78.9, 'f4.jpg', 'l4.jpg', 'e4.jpg'),
  ck('2026-04-02', 78.4, 'f5.jpg', 'l5.jpg', 'e5.jpg'),
];

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.setViewportSize({ width: 1100, height: 1100 });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/fotoscoach.html');
  let f = 0;
  const t = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };
  const estado = () => p.evaluate(() => __estado());
  const grupos = () => p.$$eval('.ft-grupo', ns => ns.map(n => ({
    fecha: n.querySelector('.ft-grupo-f').textContent.trim(),
    peso: (n.querySelector('.ft-grupo-p') || {}).textContent,
    tags: Array.from(n.querySelectorAll('.ft-tag')).map(x => x.textContent.trim()),
  })));

  await p.evaluate(c => __pinta(c), CKS);

  // ── La franja de comparación ─────────────────────────────────────────────
  const franja = (await p.textContent('.ft-franja')).replace(/\s+/g, ' ').trim();
  t('dice qué fechas se comparan',
    franja.includes('2026-01-08') && franja.includes('2026-04-02'), franja);
  t('y con qué vista', franja.includes('vista Frente'), franja);
  t('el peso, de una a otra', franja.includes('80.2') && franja.includes('78.4 kg'), franja);
  // 78.4 − 80.2 = −1.8; y −1.8/80.2 = −2.2 %.
  t('la diferencia en kilos', franja.includes('-1.8 kg'), franja);
  t('Y EN PORCENTAJE, que no dice lo mismo', franja.includes('-2.2%'), franja);
  t('bajar se marca en verde',
    (await p.getAttribute('.ft-franja .dif', 'class')).includes('baja'),
    await p.getAttribute('.ft-franja .dif', 'class'));

  // La etiqueta va sobre la foto, no en un pie aparte.
  const sobre = await p.$$eval('.ft-sobre', ns => ns.map(n => n.textContent.replace(/\s+/g, ' ').trim()));
  t('cada foto lleva su ángulo y su fecha encima',
    sobre.length === 2 && sobre[0].includes('Frente') && sobre[0].includes('2026-01-08'), sobre);

  // ── El historial ─────────────────────────────────────────────────────────
  let gs = await grupos();
  t('un grupo por fecha', gs.length === 5, gs.length);
  t('de la más reciente a la más antigua',
    gs.map(g => g.fecha).join(',') === '2026-04-02,2026-03-05,2026-02-19,2026-02-05,2026-01-08',
    gs.map(g => g.fecha));
  t('con las tres tomas de ese día',
    gs[0].tags.join(',') === 'Frente,Lateral,Espalda', gs[0].tags);
  t('y su peso', (gs[0].peso || '').includes('78.4'), gs[0]);
  // La de enero solo tenía frente: se enseña lo que hay, no tres huecos.
  t('una fecha con una sola foto enseña una',
    gs[4].tags.join(',') === 'Frente', gs[4].tags);
  t('cada grupo ofrece usarlo como inicial o como actual',
    await p.locator('.ft-grupo').first().locator('.ft-usar button').count() === 2);

  // ── El filtro del historial es SUYO ──────────────────────────────────────
  await p.locator('.ft-hist .ft-ang', { hasText: 'Lateral' }).click();
  gs = await grupos();
  t('filtrando por lateral solo sale la lateral',
    gs.every(g => g.tags.join(',') === 'Lateral'), gs.map(g => g.tags));
  // La toma de enero no tiene lateral: como el diseño, esa fecha desaparece.
  t('y la fecha sin esa foto desaparece',
    !gs.some(g => g.fecha === '2026-01-08') && gs.length === 4, gs.map(g => g.fecha));
  t('PERO LA COMPARATIVA DE ARRIBA NO SE MUEVE',
    (await estado()).angulo === 'frente', await estado());
  t('y la franja lo sigue diciendo',
    (await p.textContent('.ft-franja')).includes('vista Frente'));

  await p.locator('.ft-hist .ft-ang', { hasText: 'Todos' }).click();
  t('volver a Todos las trae de vuelta', (await grupos()).length === 5);

  // ── Llevar una toma a la comparativa ─────────────────────────────────────
  // Pulsar una foto de espalda cambia también el ángulo de arriba: si no, se
  // elige una foto y la comparativa sigue enseñando otra cosa.
  await p.locator('.ft-grupo').nth(2).locator('.ft-toma').nth(2).click();
  let e = await estado();
  t('pulsar una foto la pone como ACTUAL', e.act === '2026-02-19', e);
  t('Y CAMBIA LA VISTA A SU ANGULO', e.angulo === 'espalda', e);
  t('la franja lo refleja', (await p.textContent('.ft-franja')).includes('vista Espalda'),
    await p.textContent('.ft-franja'));

  // Los botones del grupo no dicen el ángulo: manda el que ya está puesto.
  await p.evaluate(c => __pinta(c), CKS);
  await p.locator('.ft-grupo').nth(1).locator('.ft-usar button').first().click();
  e = await estado();
  t('"Usar como inicial" cambia la inicial', e.ini === '2026-03-05', e);
  t('y respeta el ángulo que estaba puesto', e.angulo === 'frente', e);
  t('sin tocar la actual', e.act === '2026-04-02', e);

  await p.evaluate(c => __pinta(c), CKS);
  await p.locator('.ft-grupo').nth(2).locator('.ft-usar button').nth(1).click();
  e = await estado();
  t('"Usar como actual" cambia la actual', e.act === '2026-02-19', e);

  // Si esa fecha no tiene foto del ángulo puesto, se cambia a uno que sí:
  // un hueco donde debería haber una comparación no compara nada.
  await p.evaluate(c => __pinta(c), CKS);
  await p.locator('.ft-hist .ft-ang', { hasText: 'Espalda' }).click();  // no mueve la de arriba
  await p.evaluate(() => { _ftAngulo = 'espalda'; _renderPgFotos(); });
  await p.locator('.ft-grupo', { hasText: '2026-01-08' }).count();      // enero no tiene espalda
  await p.evaluate(() => { _ftHistFiltro = 'todos'; _renderPgFotos(); });
  await p.locator('.ft-grupo').last().locator('.ft-usar button').first().click();
  e = await estado();
  t('una fecha sin ese ángulo cambia la vista a la que sí tiene',
    e.ini === '2026-01-08' && e.angulo === 'frente', e);

  // ── Sin fotos ────────────────────────────────────────────────────────────
  await p.evaluate(() => __pinta([{ checkin_date: '2026-01-01', weight: 80 }]));
  t('sin fotos se dice y no se pinta el historial',
    (await p.textContent('#pg-pane-fotos')).includes('Todavía no ha enviado fotos')
    && await p.locator('.ft-hist').count() === 0, await p.textContent('#pg-pane-fotos'));

  // Una sola toma: no hay comparación, pero el historial sí.
  await p.evaluate(() => __pinta([{ checkin_date: '2026-01-08', weight: 80.2, photo_url: 'f.jpg' }]));
  t('con una sola toma el historial sale igual',
    (await grupos()).length === 1, await grupos());
  t('y la franja no inventa una diferencia',
    !(await p.textContent('.ft-franja')).includes('kg') ||
    (await p.locator('.ft-franja .dif').count()) === 0, await p.textContent('.ft-franja'));

  t('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
