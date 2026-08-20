/* El desplegable de "Librería" tiene que ser el MISMO en todas las páginas.

   Lo que pasó: el comportamiento estaba copiado y pegado en 31 páginas y otras
   dos —"Mi Organización" y "Equipo"— se habían quedado con la versión vieja,
   un enlace suelto a library.html sin desplegable. Nadie se entera de algo así
   hasta que compara dos pantallas, que es justo lo que hace este humo.

   Se recorre una muestra de cada tipo de página —las dos que estaban mal, una
   de la Librería, el panel, el chat, los clientes— y se comprueba que en todas
   el menú se despliega con las mismas cuatro familias y abre el mismo panel
   con las mismas pantallas. */
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

const PAGINAS = [
  'mi-organizacion.html',   // se había quedado sin desplegable
  'coaches.html',           // idem
  'contratos.html',         // tenía su propia copia, ya divergida
  'rutinas.html',
  'dashboard.html',
  'chat.html',
  'clients.html',
];

(async () => {
  const b = await chromium.launch(); const ctx = await b.newContext({ viewport: { width: 1400, height: 900 } });
  await ctx.route(u => u.href.startsWith(PROD), async route => {
    const q = route.request(); const url = q.url().replace(PROD, API);
    try {
      const res = await ctx.request.fetch(url, { method: q.method(), headers: q.headers(), data: q.postData() || undefined, maxRedirects: 0, timeout: 20000 });
      const h = { ...res.headers() }; delete h['content-encoding']; delete h['content-length'];
      await route.fulfill({ status: res.status(), headers: h, body: await res.body() });
    } catch (e) { await route.abort(); }
  });

  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 220))); if (!c) f++; };

  const lg = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  // El token se pone antes de cada carga: alguna página echa a login si al
  // arrancar no lo encuentra.
  await ctx.addInitScript(t => {
    try { localStorage.setItem('token', t); localStorage.setItem('role_id', '1');
          localStorage.removeItem('org_context'); } catch (e) {}
  }, lg.data.token);

  const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(String(e)));
  const referencia = { familias: null, pantallas: null };

  for (const pg of PAGINAS) {
    await p.goto(FRONT + '/' + pg);
    await p.waitForTimeout(2200);
    if (p.url().includes('login')) { ck(`${pg}: no echa a login`, false, p.url()); continue; }

    ck(`${pg}: Librería es un desplegable, no un enlace suelto`,
       (await p.locator('#navLibrary').count()) === 1 &&
       (await p.locator('a.nav-item[href="library.html"]').count()) === 0);

    // Alguna página (Documentos) ya viene con el menú abierto: pulsar lo cerraría.
    if (!(await p.locator('#librarySub.open').count())) await p.click('#navLibrary');
    await p.locator('#librarySub.open').waitFor({ state: 'visible', timeout: 8000 }).catch(() => {});
    await p.waitForTimeout(600);

    const familias = await p.locator('#librarySub .nav-sub-item').allTextContents();
    const limpio = familias.map(t => t.trim());
    if (!referencia.familias) referencia.familias = limpio;
    ck(`${pg}: las mismas familias que el resto`,
       JSON.stringify(limpio) === JSON.stringify(referencia.familias), limpio);

    await p.click('.nav-sub-item:has-text("Nutrición")');
    await p.locator('#flyoutPanel').waitFor({ state: 'visible', timeout: 8000 }).catch(() => {});
    await p.waitForTimeout(400);
    const pantallas = await p.locator('.flyout-item').allTextContents();
    if (!referencia.pantallas) referencia.pantallas = pantallas;
    ck(`${pg}: el panel abre las mismas pantallas`,
       (await p.locator('#flyoutPanel').isVisible()) &&
       JSON.stringify(pantallas) === JSON.stringify(referencia.pantallas), pantallas);

    // Cerrar por código: el fondo ocupa la pantalla entera y pulsar donde está
    // invisible acaba pulsando lo que haya debajo.
    await p.evaluate(() => { try { closeFlyout(); } catch (e) {} });
    await p.waitForTimeout(250);
  }

  ck('y "Catálogos" está en todas, que es lo que faltaba en la copia vieja',
     (referencia.pantallas || []).some(t => t.includes('Catálogos')), referencia.pantallas);
  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
