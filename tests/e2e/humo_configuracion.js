/* Configuración de la plataforma, contra la app real.

   Lo que se comprueba no es que los valores se guarden —eso es lo fácil— sino
   que HACEN algo. Un panel lleno de interruptores que no gobiernan nada es
   peor que no tenerlos: se toca uno creyendo que ha pasado algo y no.

   El caso fuerte es el mantenimiento: se enciende desde el panel y, sin
   recargar nada del backend, un coach deja de poder guardar y ve el aviso. */
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

(async () => {
  const b = await chromium.launch();
  // Un contexto por sesión: el panel de coach y el de plataforma comparten
  // origen y por tanto localStorage.
  const nuevoContexto = async () => {
    const c = await b.newContext();
    await c.route(u => u.href.startsWith(PROD), async route => {
      const req = route.request(); const url = req.url().replace(PROD, API);
      try {
        const res = await c.request.fetch(url, { method: req.method(), headers: req.headers(), data: req.postData() || undefined, maxRedirects: 0, timeout: 20000 });
        const h = { ...res.headers() }; delete h['content-encoding']; delete h['content-length'];
        await route.fulfill({ status: res.status(), headers: h, body: await res.body() });
      } catch (e) { await route.abort(); }
    });
    return c;
  };
  const ctx = await nuevoContexto(), ctxCoach = await nuevoContexto();
  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 240))); if (!c) f++; };

  const SUF = String(Date.now()).slice(-6);
  const lg = await (await ctx.request.post(`${API}/api/auth/login`, { data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const token = lg.data.token, H = { Authorization: 'Bearer ' + token };

  const cuenta = await (await ctx.request.post(`${API}/api/admin/organizations`, {
    data: { name: `Centro Config ${SUF}`, state: 'activa', owner_name: 'Config Coach',
            owner_email: `config.${SUF}@qa-cfg.com`, owner_password: 'Centro123!' }, headers: H })).json();
  const lgc = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `config.${SUF}@qa-cfg.com`, password: 'Centro123!' } })).json();
  const HC = { Authorization: 'Bearer ' + lgc.data.token };
  ck('cuenta de prueba creada', !!cuenta.data?.id, cuenta);

  const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto(FRONT + '/admin/index.html');
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.removeItem('org_context'); }, token);
  await p.goto(FRONT + '/admin/index.html');
  await p.locator('.s-item').first().waitFor({ state: 'visible', timeout: 20000 });
  await p.click('.s-item:has-text("Configuración")');
  await p.locator('#cfgNombre').waitFor({ state: 'visible', timeout: 20000 });

  ck('la sección Configuración carga', (await p.textContent('#titulo')).trim() === 'Configuración');
  ck('avisa de que el registro abierto todavía no gobierna nada',
     (await p.textContent('#contenido')).includes('Hoy no hay página pública de alta'));

  // ── Guardar marca y contacto, y que le llegue al coach ───────────────────
  await p.fill('#cfgNombre', `Alzum ${SUF}`);
  await p.fill('#cfgCorreo', `ayuda.${SUF}@alzum.io`);
  await p.fill('#cfgDias', '21');
  await p.click('#cfgBtn');
  await p.waitForTimeout(1800);
  ck('los ajustes se guardan', (await p.textContent('#cfgEstado')).includes('Guardado'),
     await p.textContent('#cfgEstado'));

  const suyos = await (await ctx.request.get(`${API}/api/platform/settings`, { headers: HC })).json();
  ck('el coach recibe el nombre y el correo de soporte',
     suyos.data.platform_name === `Alzum ${SUF}` && suyos.data.support_email === `ayuda.${SUF}@alzum.io`,
     suyos.data);
  ck('y NO recibe lo que no es asunto suyo',
     !('trial_days' in suyos.data) && !('open_registration' in suyos.data), suyos.data);

  // ── Los días de prueba se convierten en una fecha ────────────────────────
  const enPrueba = await (await ctx.request.post(`${API}/api/admin/organizations`, {
    data: { name: `Centro Prueba ${SUF}`, state: 'prueba', owner_name: 'Prueba Coach',
            owner_email: `prueba.${SUF}@qa-cfg.com`, owner_password: 'Centro123!' }, headers: H })).json();
  const faltan = Math.round((new Date(enPrueba.data.trial_ends_at) - Date.now()) / 86400000);
  ck('una cuenta en prueba nace con su fecha de fin', faltan >= 20 && faltan <= 21,
     { trial_ends_at: enPrueba.data.trial_ends_at, faltan });

  // ── Mantenimiento: el caso que importa ──────────────────────────────────
  const pc = await ctxCoach.newPage(); const errsC = []; pc.on('pageerror', e => errsC.push(String(e)));
  await pc.goto(FRONT + '/dashboard.html');
  await pc.evaluate(t => { localStorage.setItem('token', t); localStorage.removeItem('org_context'); }, lgc.data.token);
  await pc.goto(FRONT + '/dashboard.html');
  await pc.locator('#sopBtn').waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});
  ck('sin mantenimiento el coach no ve ningún aviso', await pc.locator('#sopMant').count() === 0);
  // El título arranca con un valor por defecto y se corrige cuando responde
  // /platform/settings; se espera a eso en vez de mirar una sola vez.
  await pc.waitForFunction(
    n => (document.querySelector('#sopCapa h3') || {}).textContent?.includes(n),
    `Alzum ${SUF}`, { timeout: 15000 }).catch(() => {});
  ck('el panel de ayuda lleva el nombre configurado',
     (await pc.textContent('#sopCapa h3')).includes(`Alzum ${SUF}`), await pc.textContent('#sopCapa h3'));

  const antes = await ctx.request.post(`${API}/api/trainings`, { data: { name: `Antes ${SUF}` }, headers: HC });
  ck('antes del mantenimiento el coach puede guardar', antes.status() === 200, antes.status());

  p.on('dialog', d => d.accept());
  await p.click('#cfgMantenimiento');
  await p.click('#cfgBtn');
  await p.waitForTimeout(2000);

  const durante = await ctx.request.post(`${API}/api/trainings`, { data: { name: `Durante ${SUF}` }, headers: HC });
  ck('EL MANTENIMIENTO BLOQUEA DE VERDAD LAS ESCRITURAS', durante.status() === 503, durante.status());
  const leer = await ctx.request.get(`${API}/api/trainings/findAll`, { headers: HC });
  ck('pero seguir leyendo sí se puede', leer.status() === 200, leer.status());

  await pc.reload();
  await pc.locator('#sopMant').waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});
  ck('y el coach ve el aviso en su panel', await pc.locator('#sopMant').isVisible());
  ck('con un texto que explica qué puede y qué no',
     (await pc.textContent('#sopMant')).includes('no se guardarán'), await pc.textContent('#sopMant'));

  // Apagarlo tiene efecto inmediato: en medio de una incidencia, esperar a que
  // caduque una caché es lo peor que puede pasar.
  await p.click('#cfgMantenimiento');
  await p.click('#cfgBtn');
  await p.waitForTimeout(2000);
  const despues = await ctx.request.post(`${API}/api/trainings`, { data: { name: `Despues ${SUF}` }, headers: HC });
  ck('apagarlo se nota al instante', despues.status() === 200, despues.status());

  await pc.reload();
  await pc.locator('#sopBtn').waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});
  ck('y el aviso desaparece', await pc.locator('#sopMant').count() === 0);

  ck('sin errores de JS', errs.length === 0 && errsC.length === 0, { errs, errsC });
  await b.close(); process.exit(f ? 1 : 0);
})();
