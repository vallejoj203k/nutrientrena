/* Progreso · Resumen: el alto de la gráfica y de dónde salen los números.

   La gráfica de peso se dibuja en un SVG que se estira al ancho de su caja
   conservando la proporción del lienzo. Con un lienzo casi cuadrado eso
   significaba que, cuanto más ancha la pantalla, más ALTA la gráfica: en un
   monitor normal ocupaba casi el doble que en el diseño. Es un fallo que no
   se ve leyendo el código —el alto no está escrito en ningún sitio, sale de
   la proporción— así que hace falta un navegador que lo mida.

   Y las líneas de fuerza: antes eran una polilínea fija, la misma para todos
   los ejercicios, que subía siempre. Enseñaba progreso aunque no lo hubiera.
*/
const { chromium } = require('../_pw');

const HOY = Date.now();
const dias = n => new Date(HOY - n * 86400000).toISOString().slice(0, 10);

const CK = [                                     // la API los da del más nuevo al más viejo
  { checkin_date: dias(0),   weight: 78.4, energy: 8, effort: 7, hunger: 4, sleep: 7, notes: 'Semana buena' },
  { checkin_date: dias(30),  weight: 79.1 },
  { checkin_date: dias(60),  weight: 79.8 },
  { checkin_date: dias(110), weight: 80.2 },
];
const CLIENTE = { start_date: dias(119) };
const META = { target_weight: 72.5 };

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.setViewportSize({ width: 1280, height: 1400 });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/resumen.html');
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };

  await p.evaluate(([c, d, t]) => __pinta(c, d, t), [CK, CLIENTE, META]);

  // ── El alto: lo que pidió el cliente ─────────────────────────────────────
  const alto = await p.evaluate(() =>
    document.querySelector('.pg-chart-left svg').getBoundingClientRect().height);
  ck('la grafica NO se dispara de alto', alto <= 260, alto);
  ck('pero sigue siendo una grafica legible', alto >= 180, alto);

  // El fallo era justo este: la gráfica ocupa todo el ancho, y era el ancho el
  // que decidía el alto. Con la caja ancha de verdad el alto no puede moverse.
  const anchoSvg = await p.evaluate(() =>
    document.querySelector('.pg-chart-left svg').getBoundingClientRect().width);
  ck('la grafica ocupa el ancho disponible', anchoSvg > 900, anchoSvg);
  ck('y ese ancho no arrastra el alto', alto <= 260, { anchoSvg, alto });

  // ── Los números ──────────────────────────────────────────────────────────
  const stats = await p.$$eval('.pg-stat-card', ns => ns.map(n => ({
    v: n.querySelector('.pg-stat-val').textContent.trim(),
    l: n.querySelector('.pg-stat-lbl').textContent.trim(),
    ico: !!n.querySelector('.pg-stat-ico svg'),
  })));
  ck('cinco tarjetas de cabecera', stats.length === 5, stats);
  ck('cada tarjeta lleva su icono', stats.every(s => s.ico), stats);
  ck('peso inicio es el check-in mas antiguo', stats[0].v === '80.2 kg', stats[0]);
  ck('peso actual es el mas reciente', stats[1].v === '78.4 kg', stats[1]);
  ck('perdido = 80.2 - 78.4', stats[2].v === '-1.8 kg', stats[2]);
  ck('semanas desde el inicio del plan', stats[3].v === '17', stats[3]);
  ck('ritmo real = perdido / semanas', stats[4].v === '0.11 kg/s', stats[4]);

  const obj = await p.textContent('.pg-obj-card');
  ck('el objetivo sale del plan', obj.includes('72.5 kg'), obj);
  ck('a perder = actual - objetivo', obj.includes('5.9 kg'), obj);
  ck('estimacion en semanas', obj.includes('56 sem'), obj);   // 5.9 / 0.106 kg-sem

  // ── La fuerza sale de lo levantado, no de una linea inventada ────────────
  const FZ = [
    { nombre: 'Press banca', tipo: 'peso_reps', sesiones: [
      { fecha: dias(20), peso_top: 70, reps_top: 8, series: 3 },
      { fecha: dias(13), peso_top: 72.5, reps_top: 8, series: 3 },
      { fecha: dias(6),  peso_top: 77.5, reps_top: 6, series: 4 }] },
    { nombre: 'Plancha', tipo: 'tiempo', sesiones: [
      { fecha: dias(20), segundos: 40, tiempo: '0:40', series: 3 },
      { fecha: dias(6),  segundos: 75, tiempo: '1:15', series: 3 }] },
    { nombre: 'Remo', tipo: 'peso_reps', sesiones: [
      { fecha: dias(9), peso_top: 60, reps_top: 10, series: 4 }] },
  ];
  await p.evaluate(([c, d, t, fz]) => __pinta(c, d, t, fz), [CK, CLIENTE, META, FZ]);

  const tarj = await p.$$eval('.pg-exercise-card', ns => ns.map(n => ({
    n: n.querySelector('.pg-ex-name').textContent.trim(),
    v: n.querySelector('.pg-ex-val').textContent.trim(),
    r: n.querySelector('.pg-ex-rep').textContent.trim(),
    pts: (n.querySelector('polyline') || {}).getAttribute
      ? n.querySelector('polyline').getAttribute('points') : null,
  })));
  ck('una tarjeta por ejercicio', tarj.length === 3, tarj);
  ck('el peso es el de la ultima sesion', tarj[0].v === '77.5 kg', tarj[0]);
  ck('y las reps son las de ESE levantamiento', tarj[0].r === '4×6', tarj[0]);
  ck('un ejercicio por tiempo se lee en minutos', tarj[1].v === '1:15', tarj[1]);
  ck('y no finge un peso', !tarj[1].v.includes('kg'), tarj[1]);

  // Dos ejercicios distintos no pueden tener la misma línea: era el fallo.
  ck('cada linea es la del ejercicio', tarj[0].pts !== tarj[1].pts, tarj.map(t => t.pts));
  const ys = tarj[0].pts.split(' ').map(s => parseFloat(s.split(',')[1]));
  ck('la linea sube porque el peso sube', ys[0] > ys[ys.length - 1], ys);
  ck('con una sola sesion no se dibuja tendencia', tarj[2].pts === null, tarj[2]);

  // ── Los enlaces llevan de verdad a su pestaña ────────────────────────────
  await p.click('#pg-res-fuerza .pg-ver-mas');
  ck('"Ver detalle" abre Fuerza',
    await p.isVisible('#pg-pane-fuerza') && !(await p.isVisible('#pg-pane-resumen')));
  ck('y marca su pestaña en la barra',
    (await p.textContent('.pg-stab.active')).trim() === 'Fuerza',
    await p.textContent('.pg-stab.active'));

  await p.evaluate(([c, d, t, fz]) => { __pinta(c, d, t, fz); showProgresoSubtab('resumen', document.querySelector('.pg-stab')); }, [CK, CLIENTE, META, FZ]);
  const verHist = await p.$$('.pg-ver-mas');
  await verHist[verHist.length - 1].click();
  ck('"Ver historial" abre Check-ins', await p.isVisible('#pg-pane-checkins'));

  // ── Sin datos, sin inventos ──────────────────────────────────────────────
  await p.evaluate(() => __pinta([], {}, null, []));
  const vacio = await p.textContent('#pg-pane-resumen');
  ck('sin check-ins lo dice', vacio.includes('Sin datos de peso registrados'), vacio);
  ck('sin objetivo no inventa un peso', !/\b0\.0 kg\b/.test(vacio), vacio);
  ck('sin sesiones no pinta lineas', await p.locator('.pg-exercise-card').count() === 0);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
