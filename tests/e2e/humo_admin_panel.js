/* El panel de plataforma contra la app real. */
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

(async () => {
  const b = await chromium.launch(); const ctx = await b.newContext();
  await ctx.route(u => u.href.startsWith(PROD), async route => {
    const req = route.request(); const url = req.url().replace(PROD, API);
    try {
      const res = await ctx.request.fetch(url, { method: req.method(), headers: req.headers(), data: req.postData() || undefined, maxRedirects: 0, timeout: 20000 });
      const h = { ...res.headers() }; delete h['content-encoding']; delete h['content-length'];
      await route.fulfill({ status: res.status(), headers: h, body: await res.body() });
    } catch (e) { await route.abort(); }
  });
  const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(String(e)));
  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 220))); if (!c) f++; };

  const SUF = String(Date.now()).slice(-6);
  const lg = await (await ctx.request.post(`${API}/api/auth/login`, { data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const token = lg.data.token, H = { Authorization: 'Bearer ' + token };
  const post = async (path, data) => (await ctx.request.post(`${API}/api${path}`, { data, headers: H })).json();

  await post('/users', { name: 'Dueño panel', email: `duenio.panel.${SUF}@nutrientrena-qa.com`, password: 'Duenio123!', role_id: 2 });
  const org = await post('/organizations', { name: `Centro Panel ${SUF}` });
  ck('organización de prueba creada', !!org.data?.id, org);

  // ── Super-admin
  await p.goto(FRONT + '/admin/index.html');
  await p.evaluate(t => localStorage.setItem('token', t), token);
  await p.goto(FRONT + '/admin/index.html');
  await p.waitForTimeout(1500);

  ck('el panel carga', await p.locator('#layout').isVisible());
  const secs = await p.locator('.s-item span').allTextContents();
  ck('las 10 secciones del documento', secs.length === 10, secs);
  ck('empieza en Visión general', (await p.textContent('#titulo')).trim() === 'Visión general');
  ck('la barra lateral usa la tinta oscura del documento',
     (await p.evaluate(() => getComputedStyle(document.querySelector('.side')).backgroundColor)) === 'rgb(16, 20, 30)');

  // Selector de contexto ARRIBA, no abajo
  const arriba = await p.evaluate(() => {
    const sel = document.getElementById('ctxSel');
    return sel && sel.getBoundingClientRect().top < 90;
  });
  ck('el selector de contexto está en la barra superior', arriba);
  const ops = await p.locator('#ctxSel option').allTextContents();
  ck('ofrece Plataforma Alzum y las organizaciones', ops[0] === 'Plataforma Alzum' && ops.length >= 2, ops);

  await p.click('.s-item:nth-child(6)');
  await p.waitForTimeout(200);
  ck('navegar entre secciones funciona', (await p.textContent('#titulo')).includes('Contenido'), await p.textContent('#titulo'));
  ck('la sección queda marcada como activa', await p.locator('.s-item.active').count() === 1);

  // Cambiar de contexto lleva al panel de coach
  const orgId = org.data.id;
  await p.selectOption('#ctxSel', orgId);
  await p.waitForTimeout(1500);
  ck('elegir una organización lleva al panel de coach', p.url().includes('dashboard.html'), p.url());
  ck('y deja puesto ese contexto', await p.evaluate(() => localStorage.getItem('org_context')) === orgId);

  // ── Un coach no entra
  const c = await post('/users', { name: 'Coach fuera', email: `coach.fuera.${SUF}@nutrientrena-qa.com`, password: 'Coach123!', role_id: 5 });
  const lg2 = await (await ctx.request.post(`${API}/api/auth/login`, { data: { email: `coach.fuera.${SUF}@nutrientrena-qa.com`, password: 'Coach123!' } })).json();
  const p2 = await ctx.newPage();
  await p2.goto(FRONT + '/admin/index.html');
  await p2.evaluate(t => localStorage.setItem('token', t), lg2.data.token);
  await p2.goto(FRONT + '/admin/index.html');
  await p2.waitForTimeout(1200);
  ck('un coach ve el aviso de sin acceso', await p2.locator('#sinAcceso').isVisible());
  ck('y no ve el panel', !(await p2.locator('#layout').isVisible()));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
