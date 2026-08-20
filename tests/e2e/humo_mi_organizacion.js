/* "Mi Organización": añadir un coach al equipo y poder CORREGIRLO después.

   Lo que se veía: se añadía a alguien y ya no se le podía cambiar nada. El
   lápiz abría solo los permisos, y la ficha ni siquiera enseñaba su correo
   —ponía un "Coach empleado" fijo, igual para todos—, así que un email mal
   escrito al darle de alta no se veía ni se podía arreglar.

   Se prueba contra la aplicación de verdad porque lo que falla aquí no es una
   función suelta: es que el diálogo traiga los datos puestos, que guardarlos
   los guarde de verdad y que la contraseña nueva sea la que abre la puerta. */
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
  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };

  // Una cuenta con su dueño, como en producción
  const org = await (await ctx.request.post(`${API}/api/admin/organizations`, { headers: H, data: {
    name: `Centro Equipo ${SUF}`, owner_name: 'Dueño Equipo',
    owner_email: `duenio.eq.${SUF}@nutrientrena-qa.com`, owner_password: 'Duenio123!' } })).json();
  ck('cuenta de prueba creada', !!org.data?.id, org);
  const lgd = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `duenio.eq.${SUF}@nutrientrena-qa.com`, password: 'Duenio123!' } })).json();

  await p.goto(FRONT + '/mi-organizacion.html');
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '2');
                          localStorage.removeItem('org_context'); }, lgd.data.token);
  await p.goto(FRONT + '/mi-organizacion.html');
  await p.locator('button:has-text("Añadir coach")').first().waitFor({ state: 'visible', timeout: 25000 });

  // ── Alta ────────────────────────────────────────────────────────────────
  const malo = `ana.mal.${SUF}@nutrientrena-qa.com`;
  await p.click('button:has-text("Añadir coach")');
  await p.locator('#newCoachName').waitFor({ state: 'visible', timeout: 15000 });
  await p.fill('#newCoachName', 'Ana');
  await p.fill('#newCoachLastName', 'Pérez');
  await p.fill('#newCoachEmail', malo);
  await p.fill('#newCoachPassword', 'Coach123!');
  await p.click('#footerNext');
  await p.waitForTimeout(600);
  await p.click('#footerSave');
  await p.locator('.card-email').first().waitFor({ state: 'visible', timeout: 20000 });
  ck('el coach se añade al equipo', (await p.locator('.card-name').first().textContent()).includes('Ana'));
  ck('Y LA FICHA DICE SU CORREO, no un texto fijo',
     (await p.locator('.card-email').first().textContent()).trim() === malo,
     await p.locator('.card-email').first().textContent());

  // ── Editar ──────────────────────────────────────────────────────────────
  await p.locator('[onclick^="openEditMember"]').first().click();
  await p.locator('#newCoachName').waitFor({ state: 'visible', timeout: 15000 });
  ck('el diálogo abre en los DATOS, con lo suyo puesto',
     (await p.inputValue('#newCoachName')) === 'Ana' &&
     (await p.inputValue('#newCoachLastName')) === 'Pérez' &&
     (await p.inputValue('#newCoachEmail')) === malo,
     { n: await p.inputValue('#newCoachName'), e: await p.inputValue('#newCoachEmail') });
  ck('la contraseña viene vacía y dice qué significa dejarla así',
     (await p.inputValue('#newCoachPassword')) === '' &&
     await p.locator('#newCoachPasswordHint').isVisible());

  const bueno = `ana.bien.${SUF}@nutrientrena-qa.com`;
  await p.fill('#newCoachName', 'Ana María');
  await p.fill('#newCoachEmail', bueno);
  await p.fill('#newCoachPhone', '600111222');
  await p.fill('#newCoachPassword', 'NuevaClave1!');
  await p.click('#footerNext');
  await p.waitForTimeout(600);
  await p.click('#footerSave');
  await p.waitForTimeout(2500);

  await p.reload();
  await p.locator('.card-email').first().waitFor({ state: 'visible', timeout: 25000 });
  ck('SE PUEDE CORREGIR EL NOMBRE Y EL CORREO',
     (await p.locator('.card-name').first().textContent()).includes('Ana María') &&
     (await p.locator('.card-email').first().textContent()).trim() === bueno,
     { n: await p.locator('.card-name').first().textContent(),
       e: await p.locator('.card-email').first().textContent() });

  // Lo que de verdad importa de cambiar la contraseña: que sea la que abre.
  const nueva = await (await ctx.request.post(`${API}/api/auth/login`,
    { data: { email: bueno, password: 'NuevaClave1!' } })).json();
  const vieja = await ctx.request.post(`${API}/api/auth/login`,
    { data: { email: bueno, password: 'Coach123!' }, failOnStatusCode: false });
  ck('LA CONTRASEÑA NUEVA ES LA QUE VALE', !!nueva.data?.token);
  ck('y la vieja deja de valer', vieja.status() >= 400, vieja.status());

  // ── Y el teléfono también se guardó ─────────────────────────────────────
  const miembros = await (await ctx.request.get(
    `${API}/api/organizations/${org.data.id}/members`,
    { headers: { Authorization: 'Bearer ' + lgd.data.token } })).json();
  ck('el teléfono se guarda', (miembros.data || [])[0]?.phone === '600111222', miembros.data);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
