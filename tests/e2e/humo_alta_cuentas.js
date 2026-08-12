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
  // No se asume base vacía: la prueba debe valer con datos previos.
  ck('la tabla de cuentas se pinta', await p.locator('#contenido table').count() === 1);

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
  // Filtrar por estado: solo deben quedar filas de ESE estado, haya las que haya.
  const filas = () => p.locator('#contenido tbody tr').count();
  const todas = await filas();
  await p.click('button.pill:has-text("Activa")');
  await p.waitForTimeout(300);
  const activas = await p.locator('#contenido .badge.b-activa').count();
  ck('filtrar por Activa deja solo cuentas activas', (await filas()) === activas && activas >= 1, { activas });
  await p.click('button.pill:has-text("Todas")');
  await p.waitForTimeout(300);
  ck('y vuelve al pulsar Todas', (await filas()) === todas, { todas });

  // ── Visión general con datos reales
  await p.click('.s-item:nth-child(1)');
  await p.waitForTimeout(1500);
  const v = await p.textContent('#contenido');
  ck('Visión general cuenta las cuentas reales', /Coaches \/ cuentas/i.test(v) && v.includes('NutriEntrena'), v.slice(0, 150));
  ck('y marca MRR y tickets como pendientes', v.includes('Requiere la pasarela de pago') && v.includes('Requiere el módulo de soporte'));

  // ── Ficha de la cuenta
  await p.click('.s-item:nth-child(2)');
  await p.waitForTimeout(1200);
  await p.click('button:has-text("Ver ficha")');
  await p.waitForTimeout(900);
  ck('la ficha se abre', await p.locator('#capaFicha.on').count() === 1);
  // Se comprueba la ESTRUCTURA, no un nombre concreto: la fila que se abre
  // depende del orden del listado y de lo que haya en la base.
  const fi = await p.textContent('#fichaCuerpo');
  ck('muestra dueño, estado, país, alta y equipo',
     ['Dueño','Estado','País','Alta'].every(t => fi.includes(t)) && /Equipo \(\d+\)/.test(fi), fi.slice(0, 160));
  ck('el equipo lista al menos al dueño', (await p.locator('#fichaCuerpo .badge.b-prueba').count()) >= 1);
  ck('avisa de lo que falta', fi.includes('pasarela de pago'));
  await p.click('#capaFicha .btn.ghost');
  await p.waitForTimeout(300);

  // ── Selector del contexto en la BARRA LATERAL, como la captura del cliente
  ck('el selector está en la barra lateral', await p.evaluate(() => {
    const c = document.querySelector('.ctx-card');
    return !!c && c.closest('.side') !== null;
  }));
  ck('la tarjeta "Tu rol" aparece', await p.locator('#rolCard').isVisible());

  // ── Ver el panel como otro rol
  ck('existe "ver el panel como"', await p.locator('#verComo').isVisible());
  const ops2 = await p.locator('#verComoSel option').allTextContents();
  ck('ofrece los roles del equipo', ops2.some(o => /Editor de contenido/i.test(o)), ops2);
  const idEditor = await p.evaluate(() => [...document.querySelectorAll('#verComoSel option')]
    .find(o => /Editor de contenido/i.test(o.textContent))?.value);
  await p.selectOption('#verComoSel', idEditor);
  await p.waitForTimeout(700);
  const navPrev = await p.locator('.s-item span').allTextContents();
  ck('previsualizar como editor deja solo Contenido global',
     navPrev.length === 1 && /Contenido global/.test(navPrev[0]), navPrev);
  ck('y avisa de que es una vista previa', await p.locator('#avisoPreview').isVisible());
  await p.click('#avisoPreview button');
  await p.waitForTimeout(700);
  ck('se puede volver a la vista propia', (await p.locator('.s-item span').allTextContents()).length === 10);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
