/* «Soy invitado», el circuito entero contra la app real.

   Lo que pidió el cliente: invitar a alguien desde el panel sin conocer su
   contraseña, y que esa persona la cree desde la pantalla de acceso sin
   depender de que le llegue un correo.

   Se comprueban las dos mitades y la costura entre ellas:
   invitar → copiar el código → reclamar la cuenta en el login → entrar.

   Y lo que NO puede pasar: que baste con el correo. Sin esa comprobación, esta
   pantalla sería una forma de quedarse con la cuenta de super-admin de otro. */
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

(async () => {
  const b = await chromium.launch();
  // Un contexto por sesión: el panel y el login comparten origen, y por tanto
  // localStorage. Con uno solo, el token del super-admin pisaría al invitado.
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
  const ctx = await nuevoContexto(), ctxInv = await nuevoContexto();
  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 240))); if (!c) f++; };

  const SUF = String(Date.now()).slice(-6);
  const correo = `invitado.${SUF}@alzum.io`;
  const lg = await (await ctx.request.post(`${API}/api/auth/login`, { data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const token = lg.data.token;

  // ── 1. Invitar desde el panel, sin escribirle contraseña ────────────────
  const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto(FRONT + '/admin/index.html');
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.removeItem('org_context'); }, token);
  await p.goto(FRONT + '/admin/index.html');
  await p.locator('.s-item').first().waitFor({ state: 'visible', timeout: 20000 });
  await p.click('.s-item:has-text("Equipo Alzum")');
  await p.locator('button:has-text("+ Invitar miembro")').waitFor({ state: 'visible', timeout: 20000 });

  await p.click('button:has-text("+ Invitar miembro")');
  await p.waitForTimeout(500);
  await p.fill('#miemNombre', 'Segundo Super');
  await p.fill('#miemEmail', correo);
  await p.selectOption('#miemRol', '1');       // Super-admin
  await p.click('#miemBtn');                    // sin contraseña, a propósito

  await p.locator('#capaCodigo.on').waitFor({ state: 'visible', timeout: 20000 });
  const codigo = (await p.textContent('#codValor')).trim();
  ck('el panel enseña el código de invitación', /^[A-Z0-9]{4}-[A-Z0-9]{4}$/.test(codigo), codigo);
  ck('y avisa de que solo se ve ahora',
     (await p.textContent('#capaCodigo')).includes('Solo se enseña'));
  // Por texto y no por `.btn`: dentro del modal hay dos botones y el primero
  // es "Copiar", así que el genérico dejaba el modal abierto.
  await p.click('#capaCodigo button:has-text("Entendido")');
  await p.locator('#capaCodigo.on').waitFor({ state: 'hidden', timeout: 10000 });

  // ── 2. LO QUE NO PUEDE PASAR: reclamarla solo con el correo ─────────────
  const sinCodigo = await ctx.request.post(`${API}/api/auth/accept-invitation`, {
    data: { email: correo, code: '', password: 'Robada123!' }, failOnStatusCode: false });
  ck('SIN CÓDIGO NO SE RECLAMA LA CUENTA', sinCodigo.status() === 400, sinCodigo.status());
  const malCodigo = await ctx.request.post(`${API}/api/auth/accept-invitation`, {
    data: { email: correo, code: 'AAAA-1111', password: 'Robada123!' }, failOnStatusCode: false });
  ck('ni con un código inventado', malCodigo.status() === 400, malCodigo.status());
  const robada = await ctx.request.post(`${API}/api/auth/login`,
    { data: { email: correo, password: 'Robada123!' }, failOnStatusCode: false });
  ck('y la cuenta sigue cerrada', robada.status() === 401, robada.status());

  // ── 3. El invitado la reclama desde el login ────────────────────────────
  const pi = await ctxInv.newPage(); const errsI = []; pi.on('pageerror', e => errsI.push(String(e)));
  await pi.goto(FRONT + '/login.html');
  await pi.waitForTimeout(900);

  ck('el login ofrece "Soy invitado"', await pi.locator('button:has-text("Soy invitado")').isVisible());
  ck('y el panel de invitado empieza escondido',
     !(await pi.locator('#invitadoPanel').isVisible()));

  await pi.click('button:has-text("Soy invitado")');
  await pi.waitForTimeout(400);
  ck('al pulsarlo aparece el formulario', await pi.locator('#invEmail').isVisible());

  // Las dos contraseñas tienen que coincidir: nadie más la conoce, así que una
  // errata dejaría la cuenta bloqueada.
  await pi.fill('#invEmail', correo);
  await pi.fill('#invCodigo', codigo.toLowerCase());   // en minúsculas, a propósito
  await pi.fill('#invClave', 'MiPropia2026!');
  await pi.fill('#invClave2', 'otra-distinta');
  await pi.click('#invBtn');
  await pi.waitForTimeout(700);
  ck('avisa si las dos contraseñas no coinciden',
     (await pi.textContent('#errorMsg')).includes('no coinciden'), await pi.textContent('#errorMsg'));

  await pi.fill('#invClave2', 'MiPropia2026!');
  await pi.click('#invBtn');
  await pi.waitForTimeout(3500);

  // ── 4. Entra solo, sin volver a escribir nada ───────────────────────────
  ck('ENTRA DIRECTO TRAS CREAR SU CONTRASEÑA', !pi.url().includes('login.html'), pi.url());

  const suyo = await ctx.request.post(`${API}/api/auth/login`,
    { data: { email: correo, password: 'MiPropia2026!' }, failOnStatusCode: false });
  ck('y su contraseña funciona a partir de ahora', suyo.status() === 200, suyo.status());

  if (suyo.status() === 200) {
    const j = await suyo.json();
    const me = await ctx.request.get(`${API}/api/admin/me`,
      { headers: { Authorization: 'Bearer ' + j.data.token }, failOnStatusCode: false });
    ck('es super-admin de verdad, no solo una cuenta con clave', me.status() === 200, me.status());
    const d = await me.json();
    ck('con las diez secciones', (d.data.secciones || []).length === 10, (d.data.secciones || []).length);
  }

  // ── 5. El código es de un solo uso ──────────────────────────────────────
  const reuso = await ctx.request.post(`${API}/api/auth/accept-invitation`, {
    data: { email: correo, code: codigo, password: 'Otra123!' }, failOnStatusCode: false });
  ck('el código no vale una segunda vez', reuso.status() === 400, reuso.status());

  // ── 6. Y ahora hay DOS super-admin: el bloqueo del último se levanta ────
  await p.click('.s-item:has-text("Equipo Alzum")');
  await p.waitForTimeout(1800);
  const equipo = await p.textContent('#contenido');
  ck('el nuevo aparece ya como activo', equipo.includes(correo) && /Justo ahora|Hace/.test(equipo),
     equipo.slice(0, 200));

  ck('sin errores de JS', errs.length === 0 && errsI.length === 0, { errs, errsI });
  await b.close(); process.exit(f ? 1 : 0);
})();
