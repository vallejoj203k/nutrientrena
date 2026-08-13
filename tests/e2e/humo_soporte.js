/* Soporte, el circuito entero contra la app real.

   Lo que se comprueba no es "la pantalla pinta": es que el bucle se cierre.
   Un coach abre una incidencia desde su panel → aparece en la bandeja de
   Alzum → Alzum contesta → el coach lee la respuesta sin salir de su pantalla.
   Si cualquiera de los cuatro pasos falla, la sección es decorado.

   Y lo mismo con los comunicados: se escriben en el panel, y el aviso tiene
   que salirle al coach de la audiencia correcta y a nadie más. */
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

(async () => {
  const b = await chromium.launch();
  // Un contexto POR SESIÓN, no dos pestañas del mismo.
  //
  // El panel de coach y el de plataforma se sirven desde el mismo origen, así
  // que comparten localStorage: con un solo contexto, poner el token del
  // super-admin borra el del coach y la segunda mitad de la prueba se ejecuta
  // suplantando a quien no toca. Costó un rato entenderlo.
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
  const ctx = await nuevoContexto();          // el super-admin
  const ctxCoach = await nuevoContexto();     // el coach
  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 240))); if (!c) f++; };

  const SUF = String(Date.now()).slice(-6);
  const lg = await (await ctx.request.post(`${API}/api/auth/login`, { data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const token = lg.data.token, H = { Authorization: 'Bearer ' + token };
  const post = async (path, data, h) => (await ctx.request.post(`${API}/api${path}`, { data, headers: h || H })).json();

  // Dos cuentas: una activa y otra en prueba. Hacen falta para comprobar que
  // la audiencia de un comunicado significa algo.
  const cuenta = async (nombre, correo, estado) => {
    const c = await post('/admin/organizations', { name: nombre, state: estado,
      owner_name: nombre + ' Coach', owner_email: correo, owner_password: 'Centro123!' });
    const l = await (await ctx.request.post(`${API}/api/auth/login`, { data: { email: correo, password: 'Centro123!' } })).json();
    return { id: c.data.id, token: l.data.token };
  };
  const activa = await cuenta(`Centro Activo ${SUF}`, `activo.${SUF}@qa-soporte.com`, 'activa');
  const prueba = await cuenta(`Centro Prueba ${SUF}`, `prueba.${SUF}@qa-soporte.com`, 'prueba');
  ck('dos cuentas de prueba creadas', !!activa.id && !!prueba.id);

  // ── 1. El coach abre la incidencia desde SU panel ────────────────────────
  const pc = await ctxCoach.newPage(); const errsC = []; pc.on('pageerror', e => errsC.push(String(e)));
  await pc.goto(FRONT + '/dashboard.html');
  await pc.evaluate(t => { localStorage.setItem('token', t); localStorage.removeItem('org_context'); localStorage.removeItem('comunicados_cerrados'); }, activa.token);
  await pc.goto(FRONT + '/dashboard.html');
  await pc.locator('#sopBtn').waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});

  ck('el coach tiene un botón de ayuda', await pc.locator('#sopBtn').isVisible());
  await pc.click('#sopBtn');
  await pc.waitForTimeout(700);
  await pc.fill('#sopAsunto', `No me deja asignar una rutina ${SUF}`);
  await pc.fill('#sopCuerpo', 'Le doy a asignar y no pasa nada.');
  await pc.selectOption('#sopPrio', 'alta');
  await pc.click('#sopEnviar');
  await pc.waitForTimeout(2000);
  ck('la incidencia queda registrada y se la enseña al coach',
     (await pc.textContent('#sopMios')).includes(`No me deja asignar una rutina ${SUF}`),
     await pc.textContent('#sopMios'));

  // ── 2. Llega a la bandeja de Alzum, con su cuenta y su prioridad ─────────
  const pa = await ctx.newPage(); const errsA = []; pa.on('pageerror', e => errsA.push(String(e)));
  await pa.goto(FRONT + '/admin/index.html');
  await pa.evaluate(t => { localStorage.setItem('token', t); localStorage.removeItem('org_context'); }, token);
  await pa.goto(FRONT + '/admin/index.html');
  await pa.locator('.s-item').first().waitFor({ state: 'visible', timeout: 20000 });
  // Se navega pulsando en el menú, no cambiando el hash: ir de
  // /admin/index.html a /admin/index.html#soporte es un salto DENTRO del mismo
  // documento, así que la página no se recarga y se queda en Visión general.
  await pa.click('.s-item:has-text("Soporte")');
  // Y se espera a que la bandeja esté pintada en vez de dormir un rato fijo: el
  // panel encadena /admin/me y luego /admin/support/*, y el tiempo que tarde
  // eso no es asunto de la prueba.
  await pa.locator('.tk').first().waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});

  ck('la sección Soporte carga', (await pa.textContent('#titulo')).trim() === 'Soporte',
     await pa.textContent('#titulo'));
  const bandeja = await pa.textContent('#contenido');
  ck('el ticket del coach llega a la bandeja', bandeja.includes(`No me deja asignar una rutina ${SUF}`), bandeja.slice(0, 200));
  ck('con su cuenta y su prioridad', bandeja.includes(`Centro Activo ${SUF}`) && bandeja.includes('alta'));

  // ── 3. Alzum responde, y el ticket pasa a "En curso" solo ────────────────
  await pa.click(`.tk:has-text("No me deja asignar una rutina ${SUF}")`);
  await pa.waitForTimeout(1400);
  ck('se abre la conversación', await pa.locator('#respTexto').isVisible());
  ck('con lo que escribió el coach', (await pa.textContent('.hilo')).includes('Le doy a asignar y no pasa nada.'));
  await pa.fill('#respTexto', 'Ya está arreglado, prueba otra vez.');
  await pa.click('button:has-text("Responder")');
  await pa.waitForTimeout(2200);
  const trasResponder = await pa.textContent('#contenido');
  ck('responder pasa el ticket a En curso solo', trasResponder.includes('En curso'), trasResponder.slice(0, 200));

  // ── 4. El coach lee la respuesta sin salir de su pantalla ────────────────
  await pc.reload();
  await pc.locator('#sopBtn').waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});
  await pc.click('#sopBtn');
  await pc.locator('#sopMios .r').first().waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});
  ck('EL COACH LEE LA RESPUESTA DE ALZUM',
     (await pc.textContent('#sopMios')).includes('Ya está arreglado, prueba otra vez.'),
     await pc.textContent('#sopMios'));

  // ── Aislamiento: la cuenta de al lado no ve nada de esto ─────────────────
  const ajena = await (await ctx.request.get(`${API}/api/support/tickets`,
    { headers: { Authorization: 'Bearer ' + prueba.token } })).json();
  ck('LA CUENTA DE AL LADO NO VE EL TICKET',
     !(ajena.data || []).some(t => t.subject.includes(SUF)), ajena.data);

  // ── Comunicados: borrador invisible, publicado visible, audiencia real ───
  await pa.click('.fam:has-text("Comunicados")');
  await pa.waitForTimeout(600);
  await pa.click('button:has-text("+ Nuevo comunicado")');
  await pa.waitForTimeout(500);
  await pa.fill('#comT', `Mantenimiento del domingo ${SUF}`);
  await pa.fill('#comB', 'De 03:00 a 04:00 la plataforma podría no estar disponible.');
  await pa.selectOption('#comA', 'activos');
  await pa.click('#comBtn');
  await pa.waitForTimeout(1600);
  const coms = await pa.textContent('#contenido');
  ck('el comunicado nace en borrador', coms.includes(`Mantenimiento del domingo ${SUF}`) && coms.includes('Borrador'));

  const leidosPor = async (tk) => ((await (await ctx.request.get(`${API}/api/support/announcements`,
    { headers: { Authorization: 'Bearer ' + tk } })).json()).data || []).map(a => a.title);
  ck('en borrador no lo ve nadie', !(await leidosPor(activa.token)).some(t => t.includes(SUF)));

  pa.on('dialog', d => d.accept());
  await pa.click(`.com:has-text("${SUF}") button:has-text("Publicar")`);
  await pa.waitForTimeout(1800);
  ck('publicado, lo ve la cuenta de la audiencia',
     (await leidosPor(activa.token)).some(t => t.includes(SUF)), await leidosPor(activa.token));
  ck('y NO lo ve una cuenta fuera de la audiencia',
     !(await leidosPor(prueba.token)).some(t => t.includes(SUF)), await leidosPor(prueba.token));

  // Y le sale de verdad por pantalla al coach, no solo por API
  await pc.reload();
  await pc.locator('[data-comunicado]').waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});
  ck('el aviso le sale al coach en su panel, no solo por API',
     (await pc.locator(`[data-comunicado]:has-text("${SUF}")`).count()) === 1,
     await pc.textContent('body').then(t => t.slice(0, 160)));
  ck('con el texto del comunicado',
     (await pc.textContent('[data-comunicado]')).includes('De 03:00 a 04:00'));

  // Cerrarlo lo calla para siempre: un aviso que reaparece en cada pantalla
  // deja de leerse a la tercera. Se comprueba que no vuelve ESTE, no que no
  // hay ninguno: en una base reutilizada puede haber avisos de otras rondas.
  await pc.click('[data-comunicado] .x');
  await pc.reload();
  await pc.locator('#sopBtn').waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});
  await pc.waitForTimeout(1500);
  const sigue = await pc.locator(`[data-comunicado]:has-text("${SUF}")`).count();
  ck('cerrado, no vuelve a salir', sigue === 0, sigue);

  ck('sin errores de JS', errsC.length === 0 && errsA.length === 0, { errsC, errsA });
  await b.close(); process.exit(f ? 1 : 0);
})();
