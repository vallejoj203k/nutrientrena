/* Las series recomendadas del ejercicio llegan a la rutina.

   La ficha del ejercicio guarda series, repeticiones y descanso recomendados
   ("se muestran en la ficha del ejercicio", dice el propio formulario). Al
   añadir ese ejercicio a una rutina, las casillas salían vacías: el coach las
   volvía a escribir a mano, una por una, teniéndolas delante en la ficha.

   El banco de `tests/frontend/` comprueba la regla, pero se inventa el
   catálogo: pasaría igual aunque `/trainings/search` no devolviera esos
   campos. Aquí se recorre el camino entero — se crea el ejercicio con sus
   recomendaciones, se abre el constructor de verdad y se mira lo que sale
   escrito en las casillas. */
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

  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 300))); if (!c) f++; };
  const errs = [];

  const SUF = String(Date.now()).slice(-6);
  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  if (!adm.data) { console.log('FALLO no se pudo entrar como admin', adm); process.exit(1); }
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };

  const NOMBRE = `Remo con banda ${SUF}`;
  await ctx.request.post(`${API}/api/trainings`, { headers: H, data: {
    name: NOMBRE, rec_series: '3', rec_reps: '10', rec_rest: '60' } });

  // Lo que el constructor recibe: si la API no devolviera estos campos, el
  // banco de pruebas seguiría en verde y la pantalla saldría vacía.
  const cat = await (await ctx.request.get(
    `${API}/api/trainings/search?search=${encodeURIComponent(NOMBRE)}&per_page=5`, { headers: H })).json();
  const ficha = (cat.data.data || [])[0];
  ck('la búsqueda devuelve las recomendaciones',
    ficha && ficha.rec_series === '3' && ficha.rec_reps === '10' && ficha.rec_rest === '60', ficha);

  const p = await ctx.newPage();
  p.on('pageerror', e => errs.push(String(e)));
  await p.goto(`${FRONT}/rutinas.html`);
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '1'); }, adm.data.token);
  await p.goto(`${FRONT}/rutinas.html`);
  await p.waitForTimeout(4000);

  // Rutina nueva → un bloque → añadir el ejercicio desde el selector real.
  await p.evaluate(() => openForm());
  await p.waitForTimeout(2000);
  await p.evaluate(() => wizardNext());
  await p.waitForTimeout(2000);
  // Una rutina nueva no trae días: sin uno, `days_list[0]` no existe y el
  // constructor revienta antes de llegar a lo que se quiere medir.
  await p.evaluate(() => { if (!routineData.days_list.length) addDay(); selectDay(0); });
  await p.waitForTimeout(600);
  await p.evaluate(() => addBlock('normal'));
  await p.waitForTimeout(600);
  await p.evaluate(() => openPicker(0));
  await p.waitForTimeout(2500);
  await p.fill('#pickerSearch', NOMBRE);
  await p.waitForTimeout(600);
  ck('el ejercicio aparece en el selector', await p.locator('#pickerResults .pk-card').count() >= 1);
  await p.locator('#pickerResults .pk-card').first().click();
  await p.waitForTimeout(800);

  const fila = p.locator('#blocksList .ex-row2').first();
  const casillas = await fila.locator('.ex-cell input').evaluateAll(ns => ns.map(n => n.value));
  // Orden de las casillas: series, reps, descanso, (intensidad es un select), valor, notas.
  ck('SERIES sale con la recomendada', casillas[0] === '3', casillas);
  ck('REPS sale con la recomendada', casillas[1] === '10', casillas);
  ck('DESC. sale con el descanso recomendado', casillas[2] === '60', casillas);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
