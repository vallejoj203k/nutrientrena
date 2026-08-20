/* La bandeja de check-ins, contra la aplicación de verdad.

   El circuito completo, que es lo que no se puede comprobar por API: el coach
   le pone al cliente una tarea de check-in en el calendario, el cliente la
   cumple desde su pantalla, y al coach le aparece en "Recibidos por revisar"
   con las cuatro puntuaciones y los adjuntos. Al marcarlo revisado baja a
   "Revisados hoy", y al recargar SIGUE ahí: antes esa marca solo vivía en una
   variable de JavaScript y al refrescar todo volvía a estar pendiente.

   Se comprueba también el otro lado del calendario del cliente: una tarea de
   check-in ya no ofrece la casilla de "marcar hecha", porque darla por
   cumplida sin enviar nada le borraba al coach la señal de que faltaba. */
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

const rutear = ctx => ctx.route(u => u.href.startsWith(PROD), async route => {
  const q = route.request(); const url = q.url().replace(PROD, API);
  try {
    const res = await ctx.request.fetch(url, { method: q.method(), headers: q.headers(), data: q.postData() || undefined, maxRedirects: 0, timeout: 20000 });
    const h = { ...res.headers() }; delete h['content-encoding']; delete h['content-length'];
    await route.fulfill({ status: res.status(), headers: h, body: await res.body() });
  } catch (e) { await route.abort(); }
});

const hoy = () => new Date().toISOString().slice(0, 10);

(async () => {
  const b = await chromium.launch();
  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 260))); if (!c) f++; };
  const SUF = String(Date.now()).slice(-6);
  const errs = [];

  const ctx = await b.newContext({ viewport: { width: 1500, height: 950 } }); await rutear(ctx);
  const J = async (m, p, data, tok) => (await ctx.request.fetch(`${API}${p}`, {
    method: m, data, headers: { 'Content-Type': 'application/json', ...(tok ? { Authorization: 'Bearer ' + tok } : {}) }
  })).json();

  // ── Un centro, su coach y un cliente suyo ────────────────────────────────
  const adm = await J('POST', '/api/auth/login', { email: 'admin@nutrientrena.com', password: 'Admin123!' });
  const T = adm.data.token;
  const org = await J('POST', '/api/admin/organizations', {
    name: `Centro CI ${SUF}`, owner_name: 'Coach CI',
    owner_email: `coach.ci.${SUF}@nutrientrena-qa.com`, owner_password: 'Coach123!' }, T);
  ck('centro de prueba creado', !!org.data?.id, org);
  const lgc = await J('POST', '/api/auth/login',
    { email: `coach.ci.${SUF}@nutrientrena-qa.com`, password: 'Coach123!' });
  const Tc = lgc.data.token;
  const cli = await J('POST', '/api/users', {
    name: 'Lucia', last_name: 'Prueba', email: `cli.ci.${SUF}@nutrientrena-qa.com`,
    password: 'Cliente123!', role_id: 6 }, Tc);
  const detCli = cli.data?.id;   // `id` es el user_detail; `user_id` es otra cosa
  ck('cliente creado y colgando del coach', !!detCli, cli);

  // El coach le pide un check-in para HOY.
  const tarea = await J('POST', '/api/calendar-tasks', {
    client_user_detail_id: detCli, task_date: hoy(),
    task_type: 'checkin', title: 'Check-in semanal' }, Tc);
  ck('la tarea de check-in queda puesta en el calendario', !!tarea.data?.id, tarea);

  // ── El coach: todavía no ha llegado nada ─────────────────────────────────
  const p = await ctx.newPage(); p.on('pageerror', e => errs.push('coach: ' + e));
  await p.goto(FRONT + '/checkins.html');
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '2');
                          localStorage.removeItem('org_context'); }, Tc);
  await p.goto(FRONT + '/checkins.html');
  await p.locator('#revWaitingCards .ci-card').first().waitFor({ state: 'visible', timeout: 25000 });

  ck('sale en "esperando que envíen" porque le tocaba hoy',
     (await p.textContent('#revWaitingCards')).includes('Lucia') &&
     (await p.textContent('#revWaitingCards')).includes('Le toca hoy'),
     await p.textContent('#revWaitingCards'));
  ck('y no hay nada por revisar', (await p.locator('#revReceivedCards .ci-card').count()) === 0);

  /* ── El cliente lo envía desde su pantalla ──────────────────────────────
     En OTRO contexto de navegador: el token vive en localStorage y el
     localStorage es del origen, no de la pestaña. Con las dos sesiones en el
     mismo contexto, entrar como cliente le quitaba la sesión al coach y la
     bandeja se quedaba vacía por un 403, no por no haber nada. */
  const lgcli = await J('POST', '/api/auth/login',
    { email: `cli.ci.${SUF}@nutrientrena-qa.com`, password: 'Cliente123!' });
  const ctxCli = await b.newContext({ viewport: { width: 1400, height: 950 } }); await rutear(ctxCli);
  const p2 = await ctxCli.newPage(); p2.on('pageerror', e => errs.push('cliente: ' + e));
  await p2.goto(FRONT + '/client-progreso.html');
  await p2.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '6'); }, lgcli.data.token);
  await p2.goto(FRONT + '/client-progreso.html');
  await p2.locator('#feelToggle').waitFor({ state: 'visible', timeout: 25000 });

  await p2.fill('#wInput', '68.4');
  await p2.click('#wBtn');
  await p2.waitForTimeout(2000);

  await p2.click('#feelToggle');
  await p2.locator('#f_energy').waitFor({ state: 'visible', timeout: 15000 });
  ck('las cuatro preguntas están, y solo esas cuatro',
     (await p2.locator('#feelForm input[type=range]').count()) === 4);
  await p2.locator('#f_energy').fill('9');
  await p2.locator('#f_effort').fill('7');
  await p2.locator('#f_hunger').fill('3');
  await p2.locator('#f_sleep').fill('8');
  ck('el número que se ve va siguiendo a la barra',
     (await p2.textContent('#f-v-energy')) === '9', await p2.textContent('#f-v-energy'));
  await p2.click('#feelBtn');
  await p2.waitForTimeout(2500);

  await ctxCli.close();

  // ── El coach: ya le ha llegado ───────────────────────────────────────────
  await p.reload();
  await p.locator('#revReceivedCards .ci-card').first().waitFor({ state: 'visible', timeout: 25000 });
  const recibido = await p.textContent('#revReceivedCards');
  ck('el check-in aparece en "por revisar"', recibido.includes('Lucia'), recibido);
  ck('con el peso que mandó', recibido.includes('68.4 kg'), recibido);
  ck('Y CON LAS CUATRO PUNTUACIONES, que es lo que no existía',
     ['Energía 9', 'Esfuerzo 7', 'Hambre 3', 'Descanso 8'].every(t => recibido.includes(t)),
     recibido);
  ck('ya no se le reclama', (await p.locator('#revWaitingCards .ci-card').count()) === 0);

  // ── Revisarlo ────────────────────────────────────────────────────────────
  await p.click('#revReceivedCards .btn-ver');
  await p.locator('#reviewModal.open').waitFor({ state: 'visible', timeout: 15000 });
  await p.waitForTimeout(2500);
  ck('la ficha se abre con las puntuaciones desglosadas',
     (await p.textContent('#rmMetrics')).includes('Energía'), await p.textContent('#rmMetrics'));

  await p.fill('#rmCoachNotes', 'Buena semana, seguimos igual.');
  await p.click('#btnMarkDone');
  await p.waitForTimeout(3000);
  ck('baja a "Revisados hoy"',
     (await p.locator('#revDoneSection').isVisible()) &&
     (await p.textContent('#revDoneCards')).includes('Lucia'),
     await p.textContent('#revDoneCards'));
  ck('y sale de "por revisar"', (await p.locator('#revReceivedCards .ci-card').count()) === 0);

  /* Lo importante: antes esto vivía en una variable de la página. */
  await p.reload();
  await p.waitForTimeout(4000);
  ck('AL RECARGAR SIGUE REVISADO',
     (await p.locator('#revDoneSection').isVisible()) &&
     (await p.locator('#revReceivedCards .ci-card').count()) === 0,
     { done: await p.locator('#revDoneSection').isVisible(),
       pend: await p.locator('#revReceivedCards .ci-card').count() });

  /* ── Y en el calendario del cliente ──────────────────────────────────────
     Un check-in no se "marca hecho": con la casilla genérica el cliente lo
     daba por cumplido sin mandar nada y al coach le desaparecía de "esperando
     que envíen" sin haber recibido un peso. */
  const cli2 = await J('POST', '/api/users', {
    name: 'Marco', last_name: 'Prueba', email: `cli2.ci.${SUF}@nutrientrena-qa.com`,
    password: 'Cliente123!', role_id: 6 }, Tc);
  await J('POST', '/api/calendar-tasks', {
    client_user_detail_id: cli2.data.id, task_date: hoy(),
    task_type: 'checkin', title: 'Check-in semanal' }, Tc);
  await J('POST', '/api/calendar-tasks', {
    client_user_detail_id: cli2.data.id, task_date: hoy(),
    task_type: 'cardio', title: '40 min de bici' }, Tc);
  const lg2 = await J('POST', '/api/auth/login',
    { email: `cli2.ci.${SUF}@nutrientrena-qa.com`, password: 'Cliente123!' });
  const ctx2 = await b.newContext({ viewport: { width: 1400, height: 950 } }); await rutear(ctx2);
  const p3 = await ctx2.newPage(); p3.on('pageerror', e => errs.push('calendario: ' + e));
  await p3.goto(FRONT + '/client-calendario.html');
  await p3.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '6'); }, lg2.data.token);
  await p3.goto(FRONT + '/client-calendario.html');
  await p3.locator('.det-task').first().waitFor({ state: 'visible', timeout: 25000 });
  await p3.waitForTimeout(800);

  const tareaCi = p3.locator('.det-task').filter({ hasText: 'Check-in' }).first();
  ck('el check-in del calendario manda a enviarlo, no a marcarlo',
     (await tareaCi.locator('a.det-link').count()) === 1 &&
     (await tareaCi.locator('.det-chk').count()) === 0,
     await tareaCi.innerHTML().catch(() => '—'));
  const tareaBici = p3.locator('.det-task').filter({ hasText: 'bici' }).first();
  ck('y las demás tareas se siguen marcando como siempre',
     (await tareaBici.locator('.det-chk').count()) === 1,
     await tareaBici.innerHTML().catch(() => '—'));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
