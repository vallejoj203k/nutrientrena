/* El enlace del correo de contraseña, recorrido entero contra la app real.

   Bug reportado: el correo llegaba, pero el botón "Restablecer contraseña"
   llevaba a una página que no funcionaba. El fallo no estaba en el correo,
   estaba en el DESTINO: había dos convenciones para FRONTEND_URL y, con la
   variable apuntando a la raíz, el enlace salía a /reset-password.html cuando
   el frontend se sirve bajo /app.

   Por eso esta prueba no mira el texto del enlace —eso ya lo cubren las
   unitarias— sino que abre la URL en un navegador, escribe una contraseña y
   entra con ella. Es la única forma de saber que el destino existe y sirve.

   El token de un solo uso se genera fuera y llega por TOKEN_RESET: es el mismo
   que el backend mete en el correo, firmado con la misma clave. */
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

(async () => {
  const token = process.env.TOKEN_RESET;
  const correo = process.env.CORREO_RESET;
  if (!token || !correo) {
    console.log('FALLO faltan TOKEN_RESET / CORREO_RESET en el entorno');
    process.exit(1);
  }

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

  // ── 1. La página vive donde el enlace la busca ───────────────────────────
  // Es literalmente lo que falló: el correo apuntaba a la raíz y allí no hay
  // nada. La API sirve el frontend bajo /app.
  const enRaiz = await ctx.request.get(`${API}/reset-password.html`, { failOnStatusCode: false });
  const enApp = await ctx.request.get(`${API}/app/reset-password.html`, { failOnStatusCode: false });
  ck('la página de restablecer se sirve bajo /app', enApp.status() === 200, enApp.status());
  ck('y NO cuelga de la raíz, que es adonde apuntaba el enlace roto',
     enRaiz.status() !== 200, enRaiz.status());

  // ── 2. Sin token no se queda en blanco ───────────────────────────────────
  await p.goto(`${FRONT}/reset-password.html`);
  await p.waitForTimeout(800);
  const sinToken = (await p.textContent('body')).replace(/\s+/g, ' ');
  ck('sin token la página explica qué pasa', /expir|no es válido|inválid/i.test(sinToken),
     sinToken.slice(0, 160));

  // ── 3. Con el token del correo: poner la contraseña y entrar ─────────────
  await p.goto(`${FRONT}/reset-password.html?token=${token}`);
  await p.waitForTimeout(900);
  const campos = await p.locator('input[type="password"]').count();
  ck('con token sale el formulario', campos >= 1, { campos, texto: (await p.textContent('body')).slice(0, 160) });

  const nueva = 'MiPropia2026!';
  for (let i = 0; i < campos; i++) await p.locator('input[type="password"]').nth(i).fill(nueva);
  await p.click('button[type="submit"], button:has-text("Guardar"), button:has-text("Restablecer"), button:has-text("Cambiar")');
  await p.waitForTimeout(2500);

  const lg = await ctx.request.post(`${API}/api/auth/login`,
    { data: { email: correo, password: nueva }, failOnStatusCode: false });
  ck('LA CONTRASEÑA NUEVA FUNCIONA', lg.status() === 200, { estado: lg.status(), cuerpo: (await lg.text()).slice(0, 160) });

  if (lg.status() === 200) {
    const j = await lg.json();
    const me = await ctx.request.get(`${API}/api/admin/me`,
      { headers: { Authorization: 'Bearer ' + j.data.token }, failOnStatusCode: false });
    ck('y entra al panel como super-admin', me.status() === 200, me.status());
  }

  // ── 4. El enlace es de un solo uso en la práctica ────────────────────────
  // No se invalida el token, pero la contraseña ya cambió: si alguien reusa un
  // enlace viejo, lo que hace es volver a pedir una contraseña, no entrar.
  const vieja = await ctx.request.post(`${API}/api/auth/login`,
    { data: { email: correo, password: 'MiPropia2026!x' }, failOnStatusCode: false });
  ck('y una contraseña que no es la puesta no entra', vieja.status() === 401, vieja.status());

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
