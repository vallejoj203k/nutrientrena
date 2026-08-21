/* El panel de inicio del coach, contra la aplicación de verdad.

   Se rehizo con el diseño del cliente. Lo que importa comprobar aquí no es que
   se parezca a la imagen —eso se ve mirando— sino que los números que enseña
   sean los de verdad, porque un panel de inicio que miente es peor que uno
   feo: el coach decide a quién atender mirándolo.

   El fallo que motivó buena parte de esto: la pantalla pedía
   `/api/users?role_id=3`, una ruta que NO EXISTE. Devolvía 405, la respuesta
   se descartaba en un `catch` y el panel de "clientes sin plan" salía siempre
   vacío, hubiera los que hubiera. Nadie se entera de eso mirando la pantalla:
   parece que no hay trabajo pendiente. */
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

  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 240))); if (!c) f++; };
  const errs = [];

  const lg = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const H = { Authorization: 'Bearer ' + lg.data.token };

  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(String(e)));
  await p.goto(FRONT + '/dashboard.html');
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '1'); }, lg.data.token);
  await p.goto(FRONT + '/dashboard.html');
  await p.locator('.kpi-card').first().waitFor({ state: 'visible', timeout: 25000 });
  await p.waitForTimeout(9000);

  // ── La forma que pidió el cliente ────────────────────────────────────────
  ck('cuatro indicadores', (await p.locator('.kpi-card').count()) === 4);
  ck('con las etiquetas del diseño',
     JSON.stringify(await p.locator('.kpi-label').allTextContents()) ===
     '["Clientes activos","Nuevos este mes","Check-ins por revisar","Planes pendientes"]',
     await p.locator('.kpi-label').allTextContents());
  ck('el saludo cambia con la hora y lleva el nombre',
     /^(Buenos días|Buenas tardes|Buenas noches), /.test((await p.textContent('#greetMsg')).trim()),
     await p.textContent('#greetMsg'));
  ck('la fecha dice cuántas cosas hay hoy',
     /·\s+(\d+ acci[óo]n|\d+ acciones|Nada pendiente)/.test(await p.textContent('#todayDate')),
     await p.textContent('#todayDate'));
  ck('está el botón de Ayuda arriba', await p.locator('.head-ayuda').isVisible());

  /* Se decidió con el cliente: la fila de accesos rápidos se quita, y NINGUNA
     entrada del menú se pierde aunque el diseño enseñe menos. */
  ck('la fila de accesos rápidos ya no está', (await p.locator('.quick-btn').count()) === 0);
  const menu = await p.locator('.sidebar-nav .nav-item').allTextContents();
  const limpio = menu.map(t => t.trim().split('\n')[0].trim());
  for (const entrada of ['Formularios', 'Notas', 'Progreso', 'Analíticas', 'Mi Organización']) {
    ck(`"${entrada}" sigue en el menú`, limpio.some(t => t.includes(entrada)), limpio);
  }

  // ── Los números son los de verdad ────────────────────────────────────────
  const cart = await (await ctx.request.get(`${API}/api/users/clients/portfolio`, { headers: H })).json();
  const band = await (await ctx.request.get(`${API}/api/checkins/bandeja`, { headers: H })).json();
  const sinPlan = cart.data.clients.filter(c => c.sin_plan && c.lifecycle_status === 'activo');

  const kpis = await p.locator('.kpi-val').allTextContents();
  ck('«Clientes activos» coincide con la cartera',
     kpis[0] === String(cart.data.stats.activos), { pantalla: kpis[0], api: cart.data.stats.activos });
  ck('«Check-ins por revisar» coincide con la bandeja',
     kpis[2] === String(band.data.recibidos.length), { pantalla: kpis[2], api: band.data.recibidos.length });
  ck('«PLANES PENDIENTES» COINCIDE — el panel que salía vacío',
     kpis[3] === String(sinPlan.length), { pantalla: kpis[3], api: sinPlan.length });
  ck('y hay de verdad clientes sin plan en la base, si no esto no probaría nada',
     sinPlan.length > 0, sinPlan.length);

  // ── La lista ─────────────────────────────────────────────────────────────
  ck('la lista de clientes sin plan NO está vacía',
     (await p.locator('.client-row').count()) > 0);
  ck('la insignia dice cuántos son',
     (await p.textContent('#noPlanCount')).trim() === sinPlan.length + (sinPlan.length === 1 ? ' pendiente' : ' pendientes'),
     await p.textContent('#noPlanCount'));
  ck('cada fila ofrece crear el plan',
     (await p.locator('.client-row .btn-assign').count()) === (await p.locator('.client-row').count()));
  /* Se enseña primero a quien lleva más tiempo esperando: es el que peor lo
     está pasando y el que antes se va. */
  const dias = await p.locator('.client-row').evaluateAll(fs => fs.map(el => {
    const m = (el.textContent || '').match(/Alta hace (\d+) día/);
    return m ? Number(m[1]) : 0;
  }));
  ck('los que llevan más esperando salen primero',
     dias.every((d, i) => i === 0 || dias[i - 1] >= d), dias);

  // ── La agenda ────────────────────────────────────────────────────────────
  /* El diseño enseña CINCO DÍAS seguidos, no los cinco próximos eventos: un
     día vacío también es información —ahí cabe una sesión— y saltárselo hace
     creer que la semana está más llena de lo que está. */
  ck('salen los cinco días, con hueco o sin él',
     (await p.locator('.event-date-box').count()) === 5,
     await p.locator('.event-date-box').count());
  ck('el primero está marcado como HOY',
     (await p.locator('.event-date-box').first().textContent()).toUpperCase().includes('HOY'));
  ck('y el segundo como MAÑANA',
     (await p.locator('.event-date-box').nth(1).textContent()).toUpperCase().includes('MAÑANA'));
  ck('se puede abrir el calendario', await p.locator('a.btn-pie[href="events.html"]').isVisible());

  // ── Móvil ────────────────────────────────────────────────────────────────
  const movil = await b.newContext({ viewport: { width: 390, height: 800 } });
  await movil.route(u => u.href.startsWith(PROD), async route => {
    const q = route.request();
    try {
      const res = await movil.request.fetch(q.url().replace(PROD, API), { method: q.method(), headers: q.headers(), data: q.postData() || undefined, maxRedirects: 0, timeout: 30000 });
      const h = { ...res.headers() }; delete h['content-encoding']; delete h['content-length'];
      await route.fulfill({ status: res.status(), headers: h, body: await res.body() });
    } catch (e) { await route.abort(); }
  });
  const m = await movil.newPage(); m.on('pageerror', e => errs.push(String(e)));
  await m.goto(FRONT + '/dashboard.html');
  await m.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '1'); }, lg.data.token);
  await m.goto(FRONT + '/dashboard.html');
  await m.waitForTimeout(8000);
  ck('en móvil no se sale nada por los lados', await m.evaluate(() =>
     document.documentElement.scrollWidth <= window.innerWidth + 1));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
