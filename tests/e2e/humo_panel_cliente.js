/* El panel del cliente, conducido como lo usa un cliente.

   Dos cosas que solo se ven usándolo:

     · La tira de siete días era adorno. Se podía cambiar de semana con las
       flechas, pero los círculos NO tenían onclick: el entrenamiento y el menú
       de abajo eran siempre los de hoy. Por API no se nota —el endpoint
       respondía bien—; se nota al pulsar y ver que no pasa nada.

     · Un formulario programado por el coach solo ofrecía "Marcar hecho". O
       sea: la única salida era decir que lo habías rellenado sin rellenarlo.
*/
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

const rutear = ctx => ctx.route(u => u.href.startsWith(PROD), async route => {
  const q = route.request();
  try {
    const res = await ctx.request.fetch(q.url().replace(PROD, API), { method: q.method(), headers: q.headers(), data: q.postData() || undefined, maxRedirects: 0, timeout: 30000 });
    const h = { ...res.headers() }; delete h['content-encoding']; delete h['content-length'];
    await route.fulfill({ status: res.status(), headers: h, body: await res.body() });
  } catch (e) { await route.abort(); }
});

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 480, height: 900 } });
  await rutear(ctx);

  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 240))); if (!c) f++; };
  const SUF = String(Date.now()).slice(-6);
  const errs = [];

  // ── Un coach con su cliente ──────────────────────────────────────────────
  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };
  await ctx.request.post(`${API}/api/admin/organizations`, { headers: H, data: {
    name: `Centro Cli ${SUF}`, owner_name: 'Coach Cli',
    owner_email: `coach.cli.${SUF}@nutrientrena-qa.com`, owner_password: 'Coach123!' } });
  const lgc = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `coach.cli.${SUF}@nutrientrena-qa.com`, password: 'Coach123!' } })).json();
  const Hc = { Authorization: 'Bearer ' + lgc.data.token, 'Content-Type': 'application/json' };
  const cli = await (await ctx.request.post(`${API}/api/users`, { headers: Hc, data: {
    name: 'Cliente Panel', email: `cli.panel.${SUF}@nutrientrena-qa.com`,
    password: 'Cliente123!', role_id: 6 } })).json();
  ck('cliente de prueba creado', !!cli.data, cli);
  const detCli = cli.data.id || cli.data.user_detail_id || cli.data.detail_id;

  // Una plantilla de formulario y la tarea que la programa para hoy.
  const plantilla = await (await ctx.request.post(`${API}/api/form-templates`, { headers: Hc, data: {
    title: `Check in ${SUF}`, category: 'checkin',
    fields: [{ label: '¿Cómo has dormido?', field_type: 'text', field_key: 'sueno', order: 0, required: true }] } })).json();
  ck('plantilla de formulario creada', !!plantilla.data?.id, plantilla);
  const hoy = new Date().toISOString().slice(0, 10);
  const tarea = await (await ctx.request.post(`${API}/api/calendar-tasks`, { headers: Hc, data: {
    client_user_detail_id: detCli, task_date: hoy, task_type: 'formulario',
    title: 'Formulario Check in',
    requirements: { form_template_id: plantilla.data.id, form_name: `Check in ${SUF}` } } })).json();
  ck('el coach programa el formulario para hoy', !!tarea.data?.id, tarea);

  // ── Entra el cliente ─────────────────────────────────────────────────────
  const lgcli = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `cli.panel.${SUF}@nutrientrena-qa.com`, password: 'Cliente123!' } })).json();
  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(String(e)));
  await p.goto(FRONT + '/client-home.html');
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '6'); }, lgcli.data.token);
  await p.goto(FRONT + '/client-home.html');
  await p.locator('.wk-card').waitFor({ state: 'visible', timeout: 25000 });
  await p.waitForTimeout(2500);

  // ── La tira de días ──────────────────────────────────────────────────────
  ck('la tira enseña siete días', (await p.locator('.wk-day').count()) === 7);
  const tituloHoy = await p.locator('.today-head .t').textContent();
  ck('empieza en hoy', (await p.locator('.today-pill').textContent()).trim() === 'Hoy',
     await p.locator('.today-pill').textContent());

  /* Pulsar el lunes. Lo que se comprueba es el SÍNTOMA que se veía: que al
     pulsar no pasaba nada porque el círculo no tenía onclick. */
  await p.locator('.wk-day').first().click();
  await p.waitForTimeout(2500);
  const tituloOtro = await p.locator('.today-head .t').textContent();
  ck('PULSAR UN DÍA CAMBIA LO QUE SE VE', tituloOtro !== tituloHoy,
     { antes: tituloHoy, despues: tituloOtro });
  ck('y se marca cuál se está mirando',
     (await p.locator('.wk-circle.sel, .wk-circle.today').count()) >= 1);
  ck('con una salida para volver a hoy', await p.locator('.today-pill.volver').isVisible());

  await p.click('.today-pill.volver');
  await p.waitForTimeout(2500);
  ck('y volver funciona', (await p.locator('.today-head .t').textContent()) === tituloHoy,
     await p.locator('.today-head .t').textContent());

  // ── El formulario ────────────────────────────────────────────────────────
  const fila = p.locator('.req-item').filter({ hasText: 'Check in' }).first();
  await fila.waitFor({ state: 'visible', timeout: 15000 });
  ck('EL FORMULARIO SE PUEDE ABRIR, no solo "marcar hecho"',
     (await fila.locator('a.req-go').count()) === 1 &&
     (await fila.locator('button.req-go').count()) === 0,
     await fila.textContent());
  ck('y el botón dice rellenar', (await fila.locator('a.req-go').textContent()).includes('Rellenar'),
     await fila.locator('a.req-go').textContent());

  const destino = await fila.locator('a.req-go').getAttribute('href');
  ck('lleva a la página de rellenar el formulario', /public\/form\.html\?id=/.test(destino), destino);

  await fila.locator('a.req-go').click();

  /* La página lleva dentro los tres estados —cargando, error, formulario— y
     solo enseña uno. Mirar el texto del body los ve TODOS, así que hay que
     preguntar por lo VISIBLE; si no, la prueba canta "no encontrado" teniendo
     el formulario delante. Me pasó escribiéndola. */
  await p.locator('#evalForm').waitFor({ state: 'visible', timeout: 25000 }).catch(() => {});
  ck('LA PÁGINA DEL FORMULARIO ABRE DE VERDAD',
     await p.locator('#evalForm').isVisible(), p.url());
  ck('no sale el error de enlace caducado',
     !(await p.locator('#stateError').isVisible()));

  const titulos = await p.evaluate(() => Array.from(document.querySelectorAll('h1,h2,h3'))
    .filter(e => e.offsetParent !== null).map(e => e.textContent.trim()));
  ck('y es el formulario que programó el coach',
     titulos.some(t => t.includes(SUF)), titulos);
  ck('con sus preguntas dentro',
     (await p.locator('#evalForm input, #evalForm textarea, #evalForm select').count()) >= 1);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
