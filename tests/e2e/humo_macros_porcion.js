/* Las kcal de un alimento que no va por 100 g, en las pantallas.

   Lo reportado: dos huevos en una dieta contaban 1,5 kcal en vez de 148. La
   fórmula dividía entre 100 a ciegas, y un huevo grande son 74 kcal por UNIDAD.
   Fallaba en las dos direcciones: el cacito de proteína (117 kcal por 29 g) se
   quedaba corto y el yogur griego (176 por 125 g) se pasaba.

   Las pruebas de Python cubren el servidor. Esto cubre lo otro: la cuenta
   estaba copiada en unos cuarenta sitios, la mayoría en el navegador, y el
   editor de dietas enseña sus propios totales SIN preguntarle al servidor. Si
   solo se hubiera arreglado el backend, el coach seguiría viendo 1,5 mientras
   guarda 148.

   Y lo que más protege: que un alimento por 100 g siga dando EXACTAMENTE lo de
   antes. Son casi todo el catálogo. */
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1500, height: 950 } });
  await ctx.route(u => u.href.startsWith(PROD), async route => {
    const q = route.request();
    try {
      const res = await ctx.request.fetch(q.url().replace(PROD, API), { method: q.method(), headers: q.headers(), data: q.postData() || undefined, maxRedirects: 0, timeout: 30000 });
      const h = { ...res.headers() }; delete h['content-encoding']; delete h['content-length'];
      await route.fulfill({ status: res.status(), headers: h, body: await res.body() });
    } catch (e) { await route.abort(); }
  });

  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 260))); if (!c) f++; };
  const SUF = String(Date.now()).slice(-6);
  const errs = [];

  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };
  await ctx.request.post(`${API}/api/admin/organizations`, { headers: H, data: {
    name: `Centro Por ${SUF}`, owner_name: 'Coach Por',
    owner_email: `coach.por.${SUF}@nutrientrena-qa.com`, owner_password: 'Coach123!' } });
  const lgc = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `coach.por.${SUF}@nutrientrena-qa.com`, password: 'Coach123!' } })).json();
  const Hc = { Authorization: 'Bearer ' + lgc.data.token, 'Content-Type': 'application/json' };

  /* Dos alimentos que son el caso de cada lado: uno por unidad y otro por 100 g. */
  const huevo = await (await ctx.request.post(`${API}/api/aliments`, { headers: Hc, data: {
    name: `Huevo Grande ${SUF}`, calories: 74, proteins: 6.3, carbohydrates: 0.4,
    fats: 5.2, quantity: 1, quantity_unit: 'ud' } })).json();
  const pollo = await (await ctx.request.post(`${API}/api/aliments`, { headers: Hc, data: {
    name: `Pollo ${SUF}`, calories: 165, proteins: 31, carbohydrates: 0, fats: 3.6,
    quantity: 100, quantity_unit: 'g' } })).json();
  ck('creados el huevo (por unidad) y el pollo (por 100 g)',
     !!huevo.data?.id && !!pollo.data?.id, { huevo: huevo.data, pollo: pollo.data });
  ck('y el huevo guarda su porción de 1 unidad',
     huevo.data.quantity === 1 && huevo.data.quantity_unit === 'ud', huevo.data);

  // ── La cuenta, en el navegador ──────────────────────────────────────────
  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(String(e)));
  await p.goto(FRONT + '/diets.html');
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '5');
                          localStorage.removeItem('org_context'); }, lgc.data.token);
  await p.goto(FRONT + '/diets.html');
  await p.waitForTimeout(5000);

  ck('la pantalla carga el módulo compartido de macros',
     await p.evaluate(() => typeof window.macrosAlimento === 'object'));

  const cuentas = await p.evaluate(() => ({
    porUnidad: window.macrosAlimento.escalar(74, { quantity: 1 }, 2),
    por100: window.macrosAlimento.escalar(165, { quantity: 100 }, 150),
    sinDato: window.macrosAlimento.escalar(200, { quantity: null }, 50),
    cero: window.macrosAlimento.escalar(100, { quantity: 0 }, 10),
  }));
  ck('DOS HUEVOS SON 148 KCAL, no 1,5', cuentas.porUnidad === 148, cuentas);
  ck('y 150 g de pollo siguen siendo 247,5 EXACTAMENTE como antes',
     cuentas.por100 === 247.5, cuentas);
  ck('un alimento sin porción se sigue dividiendo entre 100',
     cuentas.sinDato === 100, cuentas);
  /* Una porción de cero dividiría entre cero y llenaría la pantalla de
     "Infinity" — y no solo esa fila, la dieta entera. */
  ck('y una porción de cero no revienta la cuenta', cuentas.cero === 10, cuentas);

  // ── El editor, que enseña sus propios totales ───────────────────────────
  await p.evaluate(() => openForm(null));
  await p.waitForTimeout(3000);
  await p.evaluate(() => goToStep(2));
  await p.waitForTimeout(3000);

  async function meter(alimentId, cantidad) {
    const mid = await p.$eval('.pm2-card', e => e.id.replace('pm2Card-', ''));
    await p.evaluate(m => openFoodSearch(Number(m)), mid);
    await p.waitForTimeout(2000);
    await p.evaluate(id => fsmSelect(id), alimentId);
    await p.waitForTimeout(1000);
    await p.evaluate(q => fsmSetQty(q), cantidad);
    await p.waitForTimeout(800);
    return mid;
  }

  await meter(huevo.data.id, 2);
  const previo = await p.evaluate(() => document.getElementById('fsmPorK').textContent);
  ck('EL PREVIO DEL BUSCADOR YA DICE 148 al poner dos huevos',
     Number(previo) === 148, previo);
  await p.evaluate(() => fsmConfirmAdd());
  await p.waitForTimeout(2500);

  const totalHuevos = await p.evaluate(() => {
    const t = document.getElementById('tot_kcal');
    return t ? Number(String(t.textContent).replace(/[^\d.]/g, '')) : null;
  });
  ck('y el TOTAL DE LA DIETA que enseña el editor, también',
     totalHuevos === 148, totalHuevos);

  // ── El otro lado: lo de 100 g no se ha movido ───────────────────────────
  await p.evaluate(() => openForm(null));
  await p.waitForTimeout(2500);
  await p.evaluate(() => goToStep(2));
  await p.waitForTimeout(2500);
  await meter(pollo.data.id, 150);
  const previoPollo = await p.evaluate(() => document.getElementById('fsmPorK').textContent);
  ck('150 G DE POLLO SIGUEN DANDO 248, como toda la vida',
     Number(previoPollo) === 248, previoPollo);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
