/* La pantalla de acceso, contra la aplicación de verdad.

   Se rehízo con el diseño que pidió el cliente: una tarjeta centrada en vez de
   la pantalla partida con la foto a la izquierda. Un rediseño de login es de
   los cambios que más fácil rompen algo sin que se note, porque la pantalla
   solo se prueba a fondo cuando alguien no puede entrar.

   Lo que se comprueba aquí y no se puede comprobar por API:

     · Que se pueda ENTRAR, que es lo único que esta página tiene que hacer.
     · Que "Soy invitado" siga estando. No aparece en el diseño del cliente, y
       era una funcionalidad pedida hace una semana: rehacer la pantalla
       copiando el mockup a ciegas la habría borrado.
     · Que cada rol acabe en SU panel.
     · Que el ojo enseñe la contraseña, y que recordar el correo funcione al
       volver.
*/
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

const rutear = ctx => ctx.route(u => u.href.startsWith(PROD), async route => {
  const q = route.request(); const url = q.url().replace(PROD, API);
  try {
    const res = await ctx.request.fetch(url, { method: q.method(), headers: q.headers(), data: q.postData() || undefined, maxRedirects: 0, timeout: 20000 });
    const h = { ...res.headers() }; delete h['content-encoding']; delete h['content-length'];
    await route.fulfill({ status: res.status(), headers: h, body: await res.body() });
  } catch (e) { await route.abort(); }
});

(async () => {
  const b = await chromium.launch();
  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 240))); if (!c) f++; };
  const SUF = String(Date.now()).slice(-6);
  const errs = [];

  const ctx = await b.newContext({ viewport: { width: 1400, height: 900 } });
  await rutear(ctx);
  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(String(e)));

  await p.goto(FRONT + '/login.html');
  await p.locator('#loginBtn').waitFor({ state: 'visible', timeout: 20000 });
  await p.waitForTimeout(1200);

  // ── Lo que pidió el cliente ───────────────────────────────────────────────
  ck('el título y el subtítulo son los del diseño',
     (await p.textContent('#tituloAcceso')).trim() === 'Bienvenido de nuevo' &&
     (await p.textContent('#subtituloAcceso')).includes('panel de coach'),
     await p.textContent('#subtituloAcceso'));
  ck('los campos llevan etiqueta, no solo marca de agua',
     (await p.locator('label[for="emailInput"]').textContent()).includes('Correo') &&
     (await p.locator('label[for="passInput"]').textContent()).includes('Contraseña'));
  ck('"¿Olvidaste tu contraseña?" está junto a la contraseña',
     await p.locator('.campo-cab a').first().isVisible());
  ck('el botón dice "Iniciar sesión"', (await p.textContent('#btnText')).trim() === 'Iniciar sesión');
  ck('está la línea de ayuda con soporte', await p.locator('#enlaceSoporte').isVisible());

  /* El correo de soporte se configura en el panel; si estuviera tecleado en el
     HTML, cambiar la configuración no cambiaría este enlace. */
  const cfg = await (await ctx.request.get(`${API}/api/public/plataforma`)).json();
  ck('el enlace de soporte sale de la configuración, no del HTML',
     (await p.getAttribute('#enlaceSoporte', 'href')) === 'mailto:' + cfg.data.support_email,
     await p.getAttribute('#enlaceSoporte', 'href'));

  // La tarjeta va centrada, no pegada a un lado como en la versión partida.
  ck('la tarjeta va centrada en la pantalla', await p.evaluate(() => {
    const r = document.querySelector('.tarjeta').getBoundingClientRect();
    return Math.abs((r.left + r.right) / 2 - window.innerWidth / 2) < 12;
  }));

  // ── Lo que NO estaba en el diseño y no se puede perder ────────────────────
  ck('"SOY INVITADO" SIGUE ESTANDO', await p.locator('#invitadoEnlace button').isVisible());
  await p.click('#invitadoEnlace button');
  await p.waitForTimeout(500);
  ck('y abre su formulario', await p.locator('#invCodigo').isVisible());
  /* Dos formularios de contraseña a la vez es la forma más fácil de escribir
     en el que no es. */
  ck('mientras tanto el acceso normal se esconde',
     !(await p.locator('#accesoPanel').isVisible()));
  await p.click('#invitadoPanel .pie a');
  await p.waitForTimeout(400);
  ck('y se puede volver', await p.locator('#accesoPanel').isVisible() &&
     (await p.textContent('#tituloAcceso')).trim() === 'Bienvenido de nuevo');

  // ── El ojo ────────────────────────────────────────────────────────────────
  await p.fill('#passInput', 'Admin123!');
  ck('la contraseña empieza oculta', (await p.getAttribute('#passInput', 'type')) === 'password');
  await p.click('#btnOjo');
  ck('EL OJO LA ENSEÑA', (await p.getAttribute('#passInput', 'type')) === 'text');
  await p.click('#btnOjo');
  ck('y la vuelve a ocultar', (await p.getAttribute('#passInput', 'type')) === 'password');

  // ── Entrar ────────────────────────────────────────────────────────────────
  await p.fill('#emailInput', 'admin@nutrientrena.com');
  await p.check('#recordarme');
  await p.click('#loginBtn');
  await p.waitForURL(/dashboard|admin/, { timeout: 25000 }).catch(() => {});
  ck('UN SUPERADMIN ENTRA Y LLEGA A SU PANEL', /dashboard|admin/.test(p.url()), p.url());
  ck('y queda la sesión guardada',
     !!(await p.evaluate(() => localStorage.getItem('token'))));

  // ── Recordar el correo ────────────────────────────────────────────────────
  await p.evaluate(() => { localStorage.removeItem('token'); localStorage.removeItem('role_id'); });
  await p.goto(FRONT + '/login.html');
  await p.locator('#loginBtn').waitFor({ state: 'visible', timeout: 20000 });
  await p.waitForTimeout(800);
  ck('al volver, el correo está puesto',
     (await p.inputValue('#emailInput')) === 'admin@nutrientrena.com' &&
     (await p.isChecked('#recordarme')),
     await p.inputValue('#emailInput'));
  ck('pero la contraseña NO se recuerda', (await p.inputValue('#passInput')) === '');

  // Desmarcar tiene que olvidarlo de verdad.
  await p.uncheck('#recordarme');
  await p.fill('#passInput', 'Admin123!');
  await p.click('#loginBtn');
  await p.waitForURL(/dashboard|admin/, { timeout: 25000 }).catch(() => {});
  await p.evaluate(() => localStorage.removeItem('token'));
  await p.goto(FRONT + '/login.html');
  await p.waitForTimeout(1200);
  ck('y si lo desmarcas, se olvida', (await p.inputValue('#emailInput')) === '',
     await p.inputValue('#emailInput'));

  // ── Un error se ve ────────────────────────────────────────────────────────
  await p.fill('#emailInput', 'admin@nutrientrena.com');
  await p.fill('#passInput', 'esta-no-es');
  await p.click('#loginBtn');
  await p.waitForTimeout(2500);
  ck('una contraseña mala se dice, no se traga en silencio',
     await p.locator('#errorMsg').isVisible() &&
     (await p.textContent('#errorMsg')).trim().length > 0,
     await p.textContent('#errorMsg'));

  // ── Un cliente final acaba en SU sitio, no en el del coach ────────────────
  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };
  await ctx.request.post(`${API}/api/users`, { headers: H, data: {
    name: 'Cliente Login', email: `cli.login.${SUF}@nutrientrena-qa.com`,
    password: 'Cliente123!', role_id: 6 } });

  await p.evaluate(() => localStorage.clear());
  await p.goto(FRONT + '/login.html');
  await p.locator('#loginBtn').waitFor({ state: 'visible', timeout: 20000 });
  await p.fill('#emailInput', `cli.login.${SUF}@nutrientrena-qa.com`);
  await p.fill('#passInput', 'Cliente123!');
  await p.click('#loginBtn');
  await p.waitForURL(/client-home/, { timeout: 25000 }).catch(() => {});
  ck('UN CLIENTE ACABA EN SU PANEL, no en el del coach',
     p.url().includes('client-home'), p.url());

  // ── En el móvil se sigue pudiendo entrar ──────────────────────────────────
  const movil = await b.newContext({ viewport: { width: 390, height: 780 } });
  await rutear(movil);
  const m = await movil.newPage(); m.on('pageerror', e => errs.push(String(e)));
  await m.goto(FRONT + '/login.html');
  await m.locator('#loginBtn').waitFor({ state: 'visible', timeout: 20000 });
  await m.waitForTimeout(700);
  ck('en móvil no se sale nada por los lados', await m.evaluate(() =>
     document.documentElement.scrollWidth <= window.innerWidth + 1));
  ck('y el botón de entrar se ve sin desplazar',
     await m.locator('#loginBtn').isVisible());
  /* 16px o menos hace que iOS dé un salto de zoom al tocar el campo, y luego
     la pantalla se queda descuadrada. */
  ck('los campos no provocan zoom en iOS', await m.evaluate(() =>
     parseFloat(getComputedStyle(document.getElementById('emailInput')).fontSize) >= 16));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
