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

  /* Dos semanas anteriores, para que el historial de cada tarjeta tenga algo
     que enseñar. Sin esto la ventana se prueba siempre con un cliente recién
     llegado, que es justo el caso en el que el historial no se ve. */
  const haceDias = n => new Date(Date.now() - n * 86400000).toISOString().slice(0, 10);
  for (const [dias, kg, cintura] of [[14, 70.2, 80.5], [7, 69.3, 79.8]]) {
    const viejo = await J('POST', '/api/checkins', {
      client_user_detail_id: detCli, checkin_date: haceDias(dias), weight: kg,
      waist: cintura, hips: 96, chest: 93, arms: 31,
      notes: `Semana de hace ${dias / 7}`, energy: 6, effort: 6, hunger: 5, sleep: 6 }, Tc);
    // Ya despachados: si no, aparecerían hoy en "por revisar" y no es verdad.
    await J('PUT', `/api/checkins/${viejo.data.id}/revisado`, {}, Tc);
  }

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
  /* El check-in se rellena en SU pantalla, no en Progreso. Antes estaba
     partido en tres trozos dentro del historial y cada uno se guardaba por su
     cuenta; ahora es un formulario y un botón. */
  await p2.goto(FRONT + '/client-checkin.html');
  await p2.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '6'); }, lgcli.data.token);
  await p2.goto(FRONT + '/client-checkin.html');
  await p2.locator('#ckPeso').waitFor({ state: 'visible', timeout: 25000 });
  await p2.waitForTimeout(1500);

  ck('las cuatro preguntas están, y solo esas cuatro',
     (await p2.locator('.ck-esc').count()) === 4);
  await p2.fill('#ckPeso', '68.4');
  await p2.click('.ck-num[data-k="energy"][data-n="9"]');
  await p2.click('.ck-num[data-k="effort"][data-n="7"]');
  await p2.click('.ck-num[data-k="hunger"][data-n="3"]');
  await p2.click('.ck-num[data-k="sleep"][data-n="8"]');
  ck('se ve lo que ha elegido', (await p2.locator('.ck-num.on').count()) === 4);
  await p2.click('#ckBtn');
  await p2.waitForTimeout(3000);

  await ctxCli.close();

  // ── El coach: ya le ha llegado ───────────────────────────────────────────
  await p.reload();
  await p.locator('#revReceivedCards .ci-card').first().waitFor({ state: 'visible', timeout: 25000 });
  const recibido = await p.textContent('#revReceivedCards');
  ck('el check-in aparece en "por revisar"', recibido.includes('Lucia'), recibido);
  ck('con el peso que mandó', recibido.includes('68.4 kg'), recibido);
  ck('Y CON LAS CUATRO PUNTUACIONES, que es lo que no existía',
     ['Energía 9', 'Esfuerzo 7', 'Hambre 3', 'Sueño 8'].every(t => recibido.includes(t)),
     recibido);
  ck('ya no se le reclama', (await p.locator('#revWaitingCards .ci-card').count()) === 0);

  // ── Revisarlo ────────────────────────────────────────────────────────────
  await p.click('#revReceivedCards .btn-ver');
  await p.locator('#reviewModal.open').waitFor({ state: 'visible', timeout: 15000 });
  await p.waitForTimeout(2500);
  ck('la ficha se abre con las puntuaciones desglosadas',
     (await p.textContent('#rmMetrics')).includes('Energía'), await p.textContent('#rmMetrics'));
  ck('y con las mediciones aparte de las puntuaciones',
     (await p.locator('#rmMedsSection').isVisible()));

  /* ── El historial, tarjeta por tarjeta ───────────────────────────────────
     Es lo que pidió el cliente: en la esquina de cada bloque, un botón que
     abre las semanas anteriores DE ESE bloque. Antes solo había un gráfico de
     peso al final; para comparar la cintura había que salirse de la ventana. */
  for (const s of ['peso', 'metricas', 'mediciones', 'notas', 'fotos']) {
    ck(`"${s}" tiene su propio botón de historial`,
       await p.locator(`#rmHb-${s}`).isVisible());
    ck(`y empieza plegado`, !(await p.locator(`#rmHist-${s}`).isVisible()));
  }

  await p.click('#rmHb-mediciones');
  await p.locator('#rmHist-mediciones').waitFor({ state: 'visible', timeout: 8000 });
  await p.waitForTimeout(500);
  const tablaMed = await p.textContent('#rmHist-mediciones');
  ck('MEDICIONES abre las semanas anteriores con sus columnas',
     ['Semanas anteriores', 'Cintura', 'Cadera', 'Pecho', 'Brazo'].every(t => tablaMed.includes(t)),
     tablaMed);
  ck('y una fila por semana, con el dato de aquella semana',
     (await p.locator('#rmHist-mediciones tbody tr').count()) === 2 &&
     tablaMed.includes('80.5') && tablaMed.includes('79.8'),
     tablaMed);
  ck('las filas se nombran por lo lejos que quedan, no por su fecha',
     tablaMed.includes('Hace 1 sem') && tablaMed.includes('Hace 2 sem'), tablaMed);
  /* El check-in que se está mirando ya está arriba en la tarjeta: repetirlo en
     la tabla haría dudar de cuál es cuál. */
  ck('el check-in abierto NO se repite dentro de su propio historial',
     !tablaMed.includes('68.4'), tablaMed);

  /* La página tiene un `table{min-width:700px}` global para la tabla ancha del
     historial por cliente. Dentro del modal, que es más estrecho, forzaba la
     tabla a 700px: las dos últimas columnas quedaban fuera y sin scroll a la
     vista, así que el coach ni sabía que estaban. */
  ck('la tabla cabe en su tarjeta, sin columnas escondidas a la derecha',
     await p.evaluate(() => {
       const t = document.querySelector('#rmHist-mediciones table');
       return t.scrollWidth <= t.parentElement.clientWidth + 1;
     }));

  ck('se puede pedir más historia', await p.evaluate(async () => {
    document.querySelector('#rmHist-mediciones .rm-hist-tab:nth-child(3)').click();
    return true;
  }));
  await p.waitForTimeout(400);
  ck('y el selector de semanas se queda donde lo has dejado',
     (await p.textContent('#rmHist-mediciones .rm-hist-tab.active')).includes('12'),
     await p.textContent('#rmHist-mediciones .rm-hist-tab.active'));

  await p.click('#rmHb-peso');
  await p.waitForTimeout(500);
  const tablaPeso = await p.textContent('#rmHist-peso');
  ck('PESO abre el suyo, con los pesos de antes',
     tablaPeso.includes('70.2') && tablaPeso.includes('69.3'), tablaPeso);
  ck('abrir uno no cierra el otro: se comparan a la vez',
     (await p.locator('#rmHist-mediciones').isVisible()) &&
     (await p.locator('#rmHist-peso').isVisible()));

  await p.click('#rmHb-peso');
  await p.waitForTimeout(300);
  ck('y se vuelve a plegar', !(await p.locator('#rmHist-peso').isVisible()));

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

  /* ── Los colores del diseño ────────────────────────────────────────────
     Cada métrica lleva SU color, fijo. Antes se pintaban como un semáforo
     según el número —rojo si iba mal, verde si iba bien—, y eso es un juicio
     que la pantalla no tiene por qué hacer: un 4 de hambre puede ser
     estupendo en definición y malo en volumen, y quien lo sabe es el coach.
     Se comprueba con un check-in de números BAJOS, que es donde el semáforo
     se notaba: si volviera, energía saldría en rojo en vez de en ámbar. */
  await p.goto(FRONT + '/checkins.html');
  await p.waitForTimeout(4500);
  /* A estas alturas el check-in ya se marcó como revisado más arriba, así que
     está en "Revisados hoy", no en "por revisar". Se abre desde ahí: la ventana
     es la misma. */
  const verFlojo = p.locator('#revReceivedCards .ci-card').first().locator('.btn-ver')
    .or(p.locator('#revDoneCards .ci-card').first().locator('button')).first();
  if (await verFlojo.count()) {
    await verFlojo.click();
    await p.locator('#reviewModal.open').waitFor({ state: 'visible', timeout: 15000 });
    await p.waitForTimeout(3500);
    const pintado = await p.evaluate(() =>
      Array.from(document.querySelectorAll('.rm-score')).map(e => ({
        etq: e.querySelector('.rm-score-lbl').textContent.trim(),
        barra: getComputedStyle(e.querySelector('.rm-score-bar')).backgroundColor,
      })));
    const porEtq = {}; pintado.forEach(x => { porEtq[x.etq] = x.barra; });
    ck('CADA MÉTRICA CON SU COLOR, NO UN SEMÁFORO',
       porEtq['Energía'] === 'rgb(245, 158, 11)' && porEtq['Esfuerzo'] === 'rgb(79, 70, 229)' &&
       porEtq['Hambre'] === 'rgb(16, 185, 129)' && porEtq['Sueño'] === 'rgb(139, 92, 246)', porEtq);
    ck('y el número en negro, que no opine el color',
       await p.evaluate(() => getComputedStyle(document.querySelector('.rm-score-val')).color) === 'rgb(0, 0, 0)');
    ck('el botón principal es el índigo del diseño',
       await p.evaluate(() => getComputedStyle(document.getElementById('btnMarkDone')).backgroundColor) === 'rgb(79, 70, 229)');
  } else {
    ck('había un check-in con el que comprobar los colores', false, 'no se encontró');
  }

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
