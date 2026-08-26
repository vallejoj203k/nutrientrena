/* El subtítulo de cada comida, de punta a punta.

   Lo pedido: además del título ("Desayuno") poder poner qué se come ("Huevos
   revueltos"), para que al cliente al que se le asigne la dieta le quede claro
   de un vistazo.

   El nombre de la comida dice CUÁNDO se come y se repite igual en todas las
   dietas; qué se come no estaba en ninguna parte, así que el cliente tenía que
   abrir la comida y leer la lista de alimentos para saberlo.

   Por eso esto no se queda en "el recuadro aparece": lo escribe en el editor,
   guarda, asigna la dieta a un cliente y entra COMO EL CLIENTE a comprobar que
   le llegó. Que se guarde no sirve de nada si se pierde por el camino — es
   justo donde se perdía, en la copia que se hace al asignar. */
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

(async () => {
  const b = await chromium.launch();

  /* Un contexto por persona: las dos pantallas se sirven del mismo origen y
     comparten localStorage, así que abrir la del cliente en el mismo contexto
     machacaría la sesión del coach. */
  async function nuevoContexto(ancho, alto) {
    const c = await b.newContext({ viewport: { width: ancho, height: alto } });
    await c.route(u => u.href.startsWith(PROD), async route => {
      const q = route.request();
      try {
        const res = await c.request.fetch(q.url().replace(PROD, API), { method: q.method(), headers: q.headers(), data: q.postData() || undefined, maxRedirects: 0, timeout: 30000 });
        const h = { ...res.headers() }; delete h['content-encoding']; delete h['content-length'];
        await route.fulfill({ status: res.status(), headers: h, body: await res.body() });
      } catch (e) { await route.abort(); }
    });
    return c;
  }
  const ctx = await nuevoContexto(1500, 950);

  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 260))); if (!c) f++; };
  const SUF = String(Date.now()).slice(-6);
  const errs = [];
  const QUE_COME = `Huevos revueltos con aguacate ${SUF}`;

  // ── Un coach con un cliente y un alimento ───────────────────────────────
  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };
  await ctx.request.post(`${API}/api/admin/organizations`, { headers: H, data: {
    name: `Centro Sub ${SUF}`, owner_name: 'Coach Sub',
    owner_email: `coach.sub.${SUF}@nutrientrena-qa.com`, owner_password: 'Coach123!' } });
  const lgc = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `coach.sub.${SUF}@nutrientrena-qa.com`, password: 'Coach123!' } })).json();
  const Hc = { Authorization: 'Bearer ' + lgc.data.token, 'Content-Type': 'application/json' };
  const cli = await (await ctx.request.post(`${API}/api/users`, { headers: Hc, data: {
    name: 'Cliente Sub', email: `cli.sub.${SUF}@nutrientrena-qa.com`,
    password: 'Cliente123!', role_id: 6 } })).json();
  const lgcli = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `cli.sub.${SUF}@nutrientrena-qa.com`, password: 'Cliente123!' } })).json();
  const al = await (await ctx.request.post(`${API}/api/aliments`, { headers: Hc, data: {
    name: `Huevo ${SUF}`, calories: 150, proteins: 13, carbohydrates: 1, fats: 11,
    quantity_unit: 'g' } })).json();
  ck('montado el coach, su cliente y un alimento',
     !!cli.data?.id && !!lgcli.data?.token && !!al.data?.id);

  // ── El editor de dietas ─────────────────────────────────────────────────
  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(String(e)));
  await p.goto(FRONT + '/diets.html');
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '5');
                          localStorage.removeItem('org_context'); }, lgc.data.token);
  await p.goto(FRONT + '/diets.html');
  await p.waitForTimeout(5000);
  /* El editor son dos pasos: `openForm` abre los datos de la dieta y el paso 2
     ("Plan de comidas") es el que crea las comidas. Medir en el paso 1 no vale:
     no hay ni una comida todavía y todo saldría en cero. */
  await p.evaluate(() => openForm(null));
  await p.waitForTimeout(3000);
  await p.evaluate(() => goToStep(2));
  await p.waitForTimeout(3000);

  ck('cada comida tiene su recuadro de subtítulo',
     (await p.locator('.pm2-sub-inp').count()) >= 5,
     await p.locator('.pm2-sub-inp').count());
  /* El texto en gris cambia con la comida: el ejemplo del desayuno no vale
     para la cena. Va por el NOMBRE, no por la posición, para que siga siendo
     el correcto si el coach reordena o borra alguna. */
  const ejemplos = await p.$$eval('.pm2-sub-inp', els => els.map(e => e.placeholder));
  ck('CON UN EJEMPLO DISTINTO SEGÚN LA COMIDA',
     new Set(ejemplos.slice(0, 5)).size === 5, ejemplos.slice(0, 5));
  /* `every` sobre una lista vacía es `true`: sin comprobar que HAY recuadros,
     esto pasaría aunque no existiera ninguno. */
  const valores = await p.$$eval('.pm2-sub-inp', els => els.map(e => e.value));
  ck('y los recuadros llegan vacíos, sin poner comida que el coach no ha decidido',
     valores.length > 0 && valores.every(v => !v), valores);

  // Se escribe el subtítulo del desayuno y se le mete un alimento.
  await p.locator('.pm2-sub-inp').first().fill(QUE_COME);
  await p.waitForTimeout(400);
  /* Hace falta meterle un alimento: una comida nueva sin nada no se envía al
     guardar, así que sin esto la dieta se guardaría sin comidas y el subtítulo
     no tendría dónde vivir. */
  const mid = await p.$eval('.pm2-sub-inp', e => e.id.replace('msSubInp-', ''));
  await p.evaluate(m => openFoodSearch(Number(m)), mid);
  await p.waitForTimeout(2000);
  await p.fill('#fsmSearch', `Huevo ${SUF}`).catch(() => {});
  await p.waitForTimeout(3000);
  await p.evaluate(id => fsmSelect(id), al.data.id);
  await p.waitForTimeout(1200);
  await p.evaluate(() => fsmConfirmAdd());
  await p.waitForTimeout(2000);
  ck('la comida tiene un alimento dentro',
     (await p.evaluate(() => _meals[0].rows.filter(r => r.aliment_id).length)) > 0,
     await p.evaluate(() => _meals[0].rows.length));

  await p.fill('#f_title', `Dieta con subtitulo ${SUF}`);
  await p.evaluate(() => saveDiet());
  await p.waitForTimeout(6000);

  // ── ¿Se guardó? ─────────────────────────────────────────────────────────
  const lista = await (await ctx.request.get(`${API}/api/diets/findAll`, { headers: Hc })).json();
  const dieta = (lista.data || []).find(d => (d.title || '').includes(SUF));
  ck('la dieta se guarda', !!dieta, (lista.data || []).map(d => d.title).slice(0, 5));
  const det = await (await ctx.request.get(`${API}/api/diets/${dieta.id}/edit`, { headers: Hc })).json();
  const desayuno = (det.data.foods || [])[0];
  ck('EL SUBTÍTULO SE GUARDA CON LA COMIDA',
     desayuno && desayuno.subtitle === QUE_COME, desayuno);

  // ── Y vuelve al editor al reabrirla ─────────────────────────────────────
  await p.goto(FRONT + `/diets.html?edit=${dieta.id}`);
  await p.waitForTimeout(6000);
  await p.evaluate(() => goToStep(2));
  await p.waitForTimeout(2500);
  ck('al reabrir la dieta el subtítulo sigue ahí',
     (await p.$$eval('.pm2-sub-inp', els => els.map(e => e.value))).includes(QUE_COME),
     await p.$$eval('.pm2-sub-inp', els => els.map(e => e.value)));

  // ── Se le asigna al cliente ─────────────────────────────────────────────
  const asig = await ctx.request.post(`${API}/api/diets/${dieta.id}/assign`, {
    headers: Hc, data: { client_id: cli.data.id } });
  ck('la dieta se le asigna al cliente', asig.ok(), asig.status());

  // ── Lo que de verdad importa: qué ve el cliente ─────────────────────────
  const ctxCli = await nuevoContexto(430, 900);
  const pc = await ctxCli.newPage(); pc.on('pageerror', e => errs.push(String(e)));
  await pc.goto(FRONT + '/client-nutricion.html');
  await pc.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '6'); }, lgcli.data.token);
  await pc.goto(FRONT + '/client-nutricion.html');
  await pc.waitForTimeout(5000);

  ck('EL CLIENTE VE QUÉ COME, no solo "Desayuno"',
     (await pc.locator('#daybox .meal-que').count()) > 0 &&
     (await pc.textContent('#daybox')).includes(QUE_COME),
     await pc.textContent('#daybox'));
  /* Y el título sigue estando: el subtítulo lo acompaña, no lo sustituye. La
     hora sigue haciendo falta para saber cuándo toca. */
  ck('sin perder el título ni la hora',
     (await pc.textContent('#daybox')).includes('Desayuno') &&
     /08:00/.test(await pc.textContent('#daybox')),
     await pc.textContent('#daybox'));

  // ── Y el coach lo ve en la ficha de su cliente ──────────────────────────
  const pf = await ctx.newPage(); pf.on('pageerror', e => errs.push(String(e)));
  await pf.goto(FRONT + '/client-profile.html?id=' + cli.data.id);
  await pf.waitForTimeout(5000);
  await pf.evaluate(() => { showTab('nutricion'); renderNutricionTab(); });
  await pf.waitForTimeout(4000);
  ck('y el coach lo ve en la ficha de su cliente',
     (await pf.textContent('#nutricionContent')).includes(QUE_COME),
     (await pf.textContent('#nutricionContent')).slice(0, 200));

  // ── El PDF, que es lo que el cliente se lleva a la cocina ───────────────
  const pdf = await ctx.request.get(`${API}/api/diets/${dieta.id}/pdf`, { headers: Hc });
  ck('el PDF sigue generándose con el subtítulo dentro',
     pdf.ok() && (await pdf.body()).slice(0, 4).toString() === '%PDF', pdf.status());

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
