/* Las tarjetas de partida del plan de comidas.

   Al abrir el paso 2 el editor rellenaba con comidas vacías hasta llegar a
   cinco. Cada vez. Con una dieta de cuatro comidas eso ponía una quinta vacía,
   y sobre todo: al borrar una comida y volver al plan, aparecía otra en su
   sitio. Parecía que el borrado no se guardaba —el coach lo intentaba una y
   otra vez— cuando lo que pasaba es que el editor la inventaba de nuevo.

   Lo que hay que dejar sujeto:

     · Que una dieta guardada entre al plan con SUS comidas y ninguna más.
     · Que una comida borrada no vuelva al volver a entrar.
     · Y que una dieta nueva y en blanco siga arrancando con sus tarjetas: sin
       ninguna, el coach entra a un plan vacío y sin dónde escribir.
*/
const { chromium } = require('../_pw');

const comida = (id, nombre, nAlimentos) => ({
  id, name: nombre, time: '08:00',
  detail: Array.from({ length: nAlimentos }, (_, i) => ({ id: i + 1 })),
});

// Como la dieta de la captura: cuatro comidas de verdad.
const GUARDADA = [
  comida(11, 'Desayuno', 3), comida(12, 'Media mañana', 1),
  comida(13, 'Comida', 4), comida(14, 'Cena', 4),
];

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/comidas.html');
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };
  const comidas = () => p.evaluate(() => __comidas());
  const alPlan = () => p.evaluate(() => goToStep(2));
  const alPaso1 = () => p.evaluate(() => goToStep(1));

  // ── Una dieta guardada ───────────────────────────────────────────────────
  await p.evaluate(fs => __abrirGuardada(fs), GUARDADA);
  await alPlan();
  let cs = await comidas();
  ck('entra al plan con las comidas de la dieta y ninguna mas',
    cs.length === 4, cs.map(c => c.nombre));
  ck('y son las suyas, con sus alimentos',
    cs.map(c => c.nombre).join(',') === 'Desayuno,Media mañana,Comida,Cena', cs);

  // ── Borrar una comida ────────────────────────────────────────────────────
  await p.evaluate(() => __quitar(3));          // la Cena
  ck('al borrarla quedan tres', (await comidas()).length === 3, await comidas());

  await alPaso1();
  await alPlan();
  cs = await comidas();
  ck('Y AL VOLVER AL PLAN NO REAPARECE', cs.length === 3, cs.map(c => c.nombre));
  ck('sigue sin estar la que se borro',
    !cs.some(c => c.nombre === 'Cena'), cs.map(c => c.nombre));

  // Entrar y salir varias veces tampoco las va acumulando.
  await alPaso1(); await alPlan(); await alPaso1(); await alPlan();
  ck('ni entrando y saliendo varias veces', (await comidas()).length === 3, await comidas());

  // Borrarlas todas y volver: tampoco se rellenan solas.
  await p.evaluate(() => { __quitar(0); __quitar(0); __quitar(0); });
  await alPaso1(); await alPlan();
  ck('vaciarla del todo tampoco las trae de vuelta',
    (await comidas()).length === 0, await comidas());

  // ── Una dieta nueva SÍ arranca con tarjetas ──────────────────────────────
  await p.evaluate(() => __nueva());
  await alPlan();
  ck('una dieta nueva arranca con sus cinco tarjetas',
    (await comidas()).length === 5, await comidas());
  ck('y vacias, que no hay nada que copiar',
    (await comidas()).every(c => c.filas === 0 && !c.db_id), await comidas());

  await alPaso1(); await alPlan();
  ck('volver a entrar no las duplica', (await comidas()).length === 5, await comidas());

  // Y en una dieta nueva, borrar una tampoco la hace volver.
  await p.evaluate(() => __quitar(0));
  await alPaso1(); await alPlan();
  ck('tambien en una dieta nueva se respeta lo borrado',
    (await comidas()).length === 4, await comidas());

  // ── Abrir otra dieta después ─────────────────────────────────────────────
  // La siembra se rearma al abrir el formulario: si no, la segunda dieta nueva
  // de la sesión entraría al plan sin ninguna tarjeta.
  await p.evaluate(() => __nueva());
  await alPlan();
  ck('la siguiente dieta nueva vuelve a arrancar con cinco',
    (await comidas()).length === 5, await comidas());

  await p.evaluate(fs => __abrirGuardada(fs), GUARDADA);
  await alPlan();
  ck('y una guardada abierta despues sigue con las suyas',
    (await comidas()).length === 4, await comidas());

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
