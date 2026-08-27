/* La sección de Nutrición de la ficha del cliente: las tres tarjetas y el
   cambio de modo.

   Lo que solo se ve aquí, con la aplicación entera levantada:

     · que las tres tarjetas se pinten y la calculadora se pliegue;
     · que confirmar el cambio de modo LLEGUE a la base, no solo pinte el
       radio en otro sitio — una pantalla que se marca sola y no guarda es la
       peor forma de este fallo, porque parece que funciona;
     · y que después lleve al calendario, que es donde se trabaja a partir de
       ahí. */
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1440, height: 950 } });
  await ctx.route(u => u.href.startsWith(PROD), async route => {
    const q = route.request();
    try {
      const res = await ctx.request.fetch(q.url().replace(PROD, API), { method: q.method(), headers: q.headers(), data: q.postData() || undefined, maxRedirects: 0, timeout: 30000 });
      const h = { ...res.headers() }; delete h['content-encoding']; delete h['content-length'];
      await route.fulfill({ status: res.status(), headers: h, body: await res.body() });
    } catch (e) { await route.abort(); }
  });

  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 300))); if (!c) f++; };
  const errs = [];

  const SUF = String(Date.now()).slice(-6);
  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  if (!adm.data) { console.log('FALLO no se pudo entrar como admin', adm); process.exit(1); }
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };

  const cli = await (await ctx.request.post(`${API}/api/users`, { headers: H, data: {
    name: 'Carlos Modo', email: `cli.modo.${SUF}@nutrientrena-qa.com`,
    password: 'Cliente123!', role_id: 6, height: 178, weight: 78.4, age: 32 } })).json();
  const cid = cli.data.id;

  const p = await ctx.newPage();
  p.on('pageerror', e => errs.push(String(e)));
  await p.goto(`${FRONT}/client-profile.html?id=${cid}`);
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '1'); }, adm.data.token);
  await p.goto(`${FRONT}/client-profile.html?id=${cid}`);
  await p.waitForTimeout(6000);
  await p.evaluate(() => { showTab('nutricion'); renderNutricionTab(); });
  await p.waitForTimeout(2500);

  // ── Las tres tarjetas ────────────────────────────────────────────────────
  ck('están las tres tarjetas', await p.locator('#nutricionContent .nsec').count() === 3,
    await p.locator('#nutricionContent .nsec').count());
  ck('el plan semanal sale como el activo',
    (await p.locator('.nmodo.on .nmodo-nm').textContent()).includes('Plan semanal'),
    await p.locator('.nmodo.on .nmodo-nm').textContent());
  ck('y el calendario, en pausa',
    (await p.locator('.nmodo:not(.on) .nmodo-tag').textContent()).includes('En pausa'));
  ck('el hueco del plan invita a asignar la primera dieta',
    await p.locator('.nplan-empty h4').textContent() === 'Sin plan de alimentación',
    await p.locator('.nplan-empty h4').textContent());

  // ── La calculadora, plegada y con resumen ────────────────────────────────
  ck('la calculadora empieza plegada', await p.locator('#nutCalcCard.open').count() === 0);
  const resumen = await p.textContent('#nutCalcResumen');
  ck('el resumen dice las kcal y las comidas sin abrirla',
    /\d+ kcal/.test(resumen) && /· \d+ comidas/.test(resumen), resumen);
  // "0 comidas" era el fallo: el campo se llama mealCount, no meals.
  ck('el número de comidas NO es cero', !/· 0 comidas/.test(resumen), resumen);
  await p.click('.ncalc-head');
  await p.waitForTimeout(500);
  ck('al pulsar se abre', await p.locator('#nutCalcCard.open').count() === 1);
  ck('y dentro está el planificador de siempre',
    await p.locator('#nutCalcCard .np-card').count() >= 3,
    await p.locator('#nutCalcCard .np-card').count());

  // ── Cambiar de modo ──────────────────────────────────────────────────────
  await p.click('.nmodo:not(.on)');
  await p.waitForTimeout(600);
  ck('pide confirmación antes de cambiar', await p.locator('#cmodoBack.open').count() === 1);
  const texto = await p.textContent('#cmodoTexto');
  ck('la ventana explica que el otro modo queda en pausa y no se borra',
    texto.includes('quedará en pausa') && texto.includes('no se borra'), texto);

  // Cancelar NO cambia nada: es lo que promete el botón.
  await p.click('#cmodoBack .btn-ghost');
  await p.waitForTimeout(400);
  let est = await (await ctx.request.get(`${API}/api/users/${cid}/edit`, { headers: H })).json();
  ck('cancelar no cambia el modo', (est.data.nutrition_mode || 'semanal') === 'semanal',
    est.data.nutrition_mode);

  await p.click('.nmodo:not(.on)');
  await p.waitForTimeout(500);
  await p.click('#cmodoOk');
  await p.waitForTimeout(2500);

  est = await (await ctx.request.get(`${API}/api/users/${cid}/edit`, { headers: H })).json();
  ck('CONFIRMAR GUARDA EL MODO EN LA BASE, no solo en la pantalla',
    est.data.nutrition_mode === 'calendario', est.data.nutrition_mode);
  // Con `count() >= 1 || ...` esta comprobación pasaba aunque el cambio hubiera
  // fallado: hay que mirar qué pestaña está activa, no si el nodo existe.
  const pestaña = await p.evaluate(() =>
    [...document.querySelectorAll('.tab-pane')].filter(n => n.classList.contains('active')).map(n => n.id));
  ck('y lleva al calendario, que es donde se trabaja a partir de ahí',
    pestaña.length === 1 && pestaña[0] === 'tab-calendario', pestaña);

  // ── Y al volver, el modo se recuerda ─────────────────────────────────────
  await p.goto(`${FRONT}/client-profile.html?id=${cid}`);
  await p.waitForTimeout(6000);
  await p.evaluate(() => { showTab('nutricion'); renderNutricionTab(); });
  await p.waitForTimeout(2500);
  ck('al recargar, el calendario sale como activo',
    (await p.locator('.nmodo.on .nmodo-nm').textContent()).includes('Calendario'),
    await p.locator('.nmodo.on .nmodo-nm').textContent());

  // ── Al llegar al calendario, el tipo viene fijado en Nutrición ───────────
  await p.evaluate(() => { showTab('calendario'); renderCalendarioTab(); });
  await p.waitForTimeout(2000);
  await p.evaluate(() => openCalTaskModal());
  await p.waitForTimeout(1200);
  ck('el aviso dice que se está programando la nutrición',
    await p.locator('.cal-enfoque').count() === 1);
  const tipos = await p.$$eval('#calTypeList .cal-type-lbl', ns => ns.map(n => n.textContent.trim()));
  ck('SOLO SE OFRECE NUTRICIÓN, no se puede crear otra cosa sin querer',
    tipos.length === 1 && /nutric/i.test(tipos[0]), tipos);
  ck('y el tipo elegido ya es nutrición',
    await p.evaluate(() => _calNewType) === 'nutricion', await p.evaluate(() => _calNewType));

  // Pero es una ayuda, no una jaula.
  await p.click('.cal-enfoque-link');
  await p.waitForTimeout(1000);
  const todos = await p.$$eval('#calTypeList .cal-type-lbl', ns => ns.map(n => n.textContent.trim()));
  ck('se puede salir del enfoque y crear otro tipo', todos.length > 1, todos);
  await p.evaluate(() => closeCalTaskModal());

  // ── Volver a semanal, que es donde estaba el fallo ───────────────────────
  // `renderNutricionTab` releía el modo de `clientData`, que es el perfil de
  // cuando se abrió la página: al repintar volvía al modo viejo.
  await p.evaluate(() => { showTab('nutricion'); renderNutricionTab(); });
  await p.waitForTimeout(2000);
  ck('tras ir y volver del calendario, el modo NO se revierte solo',
    (await p.locator('.nmodo.on .nmodo-nm').textContent()).includes('Calendario'),
    await p.locator('.nmodo.on .nmodo-nm').textContent());

  await p.evaluate(() => pedirCambioModo('semanal'));
  await p.waitForTimeout(600);
  ck('se puede volver al plan semanal', await p.locator('#cmodoBack.open').count() === 1);
  await p.click('#cmodoOk');
  await p.waitForTimeout(2500);
  await p.click('#tab-nutricion-btn');
  await p.waitForTimeout(2500);
  const dentro = (await p.innerHTML('#nutricionContent')).length;
  // El fallo reportado: la sección se quedaba en blanco al volver.
  ck('LA SECCIÓN NO SE QUEDA EN BLANCO AL VOLVER', dentro > 2000, dentro);
  ck('y el plan semanal vuelve a salir como activo',
    (await p.locator('.nmodo.on .nmodo-nm').textContent()).includes('Plan semanal'),
    await p.locator('.nmodo.on .nmodo-nm').textContent());

  // ── El caso que faltaba: un cliente con MENÚ SEMANAL ────────────────────
  //
  // Aquí se cayó de verdad. `_nutMenuDays()` devuelve un OBJETO indexado por
  // día, no un array, y llamarle `.filter` reventaba el pintado entero: la
  // sección se quedaba en blanco. Solo pasaba con menú asignado — con el
  // cliente sin dietas y con una dieta suelta funcionaba, que es justo por
  // donde yo lo había probado.
  const gf = await (await ctx.request.post(`${API}/api/groupFood`, {
    headers: H, data: { name: `Aves ${SUF}` } })).json();
  const al = await (await ctx.request.post(`${API}/api/aliments`, { headers: H, data: {
    name: `Pollo ${SUF}`, group_food_id: gf.data.id, calories: 120,
    quantity: 100, quantity_unit: 'g' } })).json();
  const die = await (await ctx.request.post(`${API}/api/diets`, {
    headers: H, data: { title: `Plan ${SUF}` } })).json();
  await ctx.request.put(`${API}/api/diets/${die.data.id}/update`, { headers: H, data: {
    id: die.data.id, title: `Plan ${SUF}`, foods: [{ name: 'Desayuno', time: '08:00',
      detail: [{ aliment_id: al.data.id, quantity_calc: 150, order: 0 }] }] } });
  const menu = await (await ctx.request.post(`${API}/api/weekly-menus`, { headers: H, data: {
    name: `Menú ${SUF}`,
    days: [0, 1, 2].map(i => ({ day_index: i, name: null, diet_id: die.data.id })) } })).json();
  const asg = await ctx.request.post(`${API}/api/weekly-menus/${menu.data.id}/assign`, {
    headers: H, data: { client_id: cid } });
  ck('el menú semanal se ha podido asignar', asg.ok(), asg.status());

  await p.goto(`${FRONT}/client-profile.html?id=${cid}`);
  await p.waitForTimeout(6000);
  await p.click('#tab-nutricion-btn');
  await p.waitForTimeout(3500);
  const conMenu = await p.innerHTML('#nutricionContent');
  ck('CON MENÚ SEMANAL LA SECCIÓN NO SE QUEDA EN BLANCO',
    !conMenu.includes('No se ha podido cargar') && conMenu.includes('Plan de alimentación'),
    conMenu.length);
  ck('y el contador de dietas cuenta los días del menú',
    /Plan de alimentación · 3 dietas/.test(conMenu),
    (conMenu.match(/Plan de alimentación · [^<]*/) || [])[0]);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
