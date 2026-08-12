/* Dar de alta un entrenador desde el panel, contra la app real.

   Es lo que el cliente pidió para cerrar la fase, y lo que ANTES no se podía:
   POST /organizations fijaba el dueño como quien llamaba. */
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
  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 240))); if (!c) f++; };

  const SUF = String(Date.now()).slice(-6);
  const lg = await (await ctx.request.post(`${API}/api/auth/login`, { data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const token = lg.data.token;

  await p.goto(FRONT + '/admin/index.html');
  await p.evaluate(t => localStorage.setItem('token', t), token);
  await p.goto(FRONT + '/admin/index.html#organizaciones');
  await p.waitForTimeout(1800);

  ck('la sección Coaches carga', (await p.textContent('#titulo')).trim() === 'Coaches');
  ck('empieza sin cuentas', (await p.textContent('#contenido')).includes('Todavía no hay cuentas'));

  // ── Dar de alta NutriEntrena con su dueño
  await p.click('button:has-text("+ Nueva cuenta")');
  await p.waitForTimeout(400);
  ck('se abre el formulario de alta', await p.locator('#capaAlta.on').count() === 1);
  ck('avisa del riesgo de dejar a un entrenador sin cuenta',
     (await p.textContent('.aviso')).includes('catálogo común'));

  const correo = `oswal.${SUF}@nutrientrena-qa.com`;
  await p.fill('#altaNombre', 'NutriEntrena');
  await p.fill('#altaPais', 'España');
  await p.fill('#altaDuenoNombre', 'Oswal Serrano');
  await p.fill('#altaDuenoEmail', correo);
  await p.fill('#altaDuenoClave', 'Centro123!');
  await p.click('#altaBtn');
  await p.waitForTimeout(1800);

  ck('la cuenta aparece en el listado', (await p.textContent('#contenido')).includes('NutriEntrena'));
  ck('con su dueño y país', (await p.textContent('#contenido')).includes('Oswal Serrano') && (await p.textContent('#contenido')).includes('España'));
  ck('en estado Activa', (await p.locator('.badge.b-activa').count()) >= 1);
  ck('plan y MRR salen vacíos, no inventados',
     (await p.textContent('#contenido')).includes('Plan y MRR llegarán con la pasarela'));

  // ── LO IMPORTANTE: su contenido queda dentro de la cuenta
  const lg2 = await (await ctx.request.post(`${API}/api/auth/login`, { data: { email: correo, password: 'Centro123!' } })).json();
  ck('el entrenador creado puede entrar', !!lg2.data?.token, lg2);
  const rr = await (await ctx.request.post(`${API}/api/routines`, {
    data: { name: 'Rutina de NutriEntrena' },
    headers: { Authorization: 'Bearer ' + lg2.data.token } })).json();
  ck('SU CONTENIDO QUEDA EN SU CUENTA, no en el catálogo común',
     rr.data && rr.data.organization_id !== null, rr.data && rr.data.organization_id);

  // ── Suspender y reactivar
  p.on('dialog', d => d.accept());
  await p.click('button:has-text("Suspender")');
  await p.waitForTimeout(1500);
  ck('suspender cambia el estado', (await p.locator('.badge.b-suspendida').count()) >= 1);
  await p.click('button:has-text("Reactivar")');
  await p.waitForTimeout(1500);
  ck('reactivar lo devuelve', (await p.locator('.badge.b-activa').count()) >= 1);

  // ── Filtros
  await p.click('button.pill:has-text("En prueba")');
  await p.waitForTimeout(300);
  ck('el filtro deja el listado vacío si no hay ninguna', (await p.textContent('#contenido')).includes('Ninguna cuenta con ese filtro'));
  await p.click('button.pill:has-text("Todas")');
  await p.waitForTimeout(300);
  ck('y vuelve al pulsar Todas', (await p.textContent('#contenido')).includes('NutriEntrena'));

  // ── Visión general con datos reales
  await p.click('.s-item:nth-child(1)');
  await p.waitForTimeout(1500);
  const v = await p.textContent('#contenido');
  ck('Visión general cuenta las cuentas reales', /Coaches \/ cuentas/i.test(v) && v.includes('NutriEntrena'), v.slice(0, 150));
  ck('y marca MRR y tickets como pendientes', v.includes('Requiere la pasarela de pago') && v.includes('Requiere el módulo de soporte'));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
