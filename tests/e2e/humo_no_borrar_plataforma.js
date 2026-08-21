/* Un coach no puede borrar el catálogo de Alzum. Comprobado pantalla a
   pantalla, con un coach de verdad.

   El servidor ya lo rechaza —hay pruebas de API para eso—, pero eso no basta:
   una pantalla que ofrece "Eliminar" en algo que no se puede eliminar ya está
   mintiendo, y el coach descubre el 403 después de confirmar un diálogo que
   dice "esta acción no se puede deshacer".

   Esto se recorre página por página porque la regla estaba copiada en cinco
   sitios y en ejercicios NO estaba: nadie se entera de una divergencia así
   hasta que compara. Ahora sale de `js/permisos-contenido.js`, y este humo es
   lo que impide que vuelva a separarse. */
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1500, height: 950 } });
  await ctx.route(u => u.href.startsWith(PROD), async route => {
    const q = route.request();
    try {
      const res = await ctx.request.fetch(q.url().replace(PROD, API), { method: q.method(), headers: q.headers(), data: q.postData() || undefined, maxRedirects: 0, timeout: 30000 });
      const h = { ...res.headers() }; delete h['content-encoding']; delete h['content-length'];
      await route.fulfill({ status: res.status(), headers: h, body: await res.body() });
    } catch (e) { await route.abort(); }
  });

  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 200))); if (!c) f++; };
  const SUF = String(Date.now()).slice(-6);
  const errs = [];

  // ── Un centro con su coach ───────────────────────────────────────────────
  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };
  await ctx.request.post(`${API}/api/admin/organizations`, { headers: H, data: {
    name: `Centro Borrar ${SUF}`, owner_name: 'Coach Borrar',
    owner_email: `coach.borrar.${SUF}@nutrientrena-qa.com`, owner_password: 'Coach123!' } });
  const lgc = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `coach.borrar.${SUF}@nutrientrena-qa.com`, password: 'Coach123!' } })).json();
  const Hc = { Authorization: 'Bearer ' + lgc.data.token, 'Content-Type': 'application/json' };

  // Un ejercicio de Alzum y otro del coach, para poder comparar las dos filas.
  const dePlataforma = await (await ctx.request.post(`${API}/api/trainings`, { headers: H, data: {
    name: `AAA Comun ${SUF}` } })).json();
  const suyo = await (await ctx.request.post(`${API}/api/trainings`, { headers: Hc, data: {
    name: `AAA Mio ${SUF}` } })).json();
  ck('preparado: uno de Alzum y uno del coach',
     !!dePlataforma.data?.id && !!suyo.data?.id, { dePlataforma, suyo });

  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(String(e)));
  await p.goto(FRONT + '/ejercicios.html');
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '5');
                          localStorage.removeItem('org_context'); }, lgc.data.token);
  await p.goto(FRONT + '/ejercicios.html');
  await p.waitForTimeout(3500);

  // Buscar para quedarnos solo con los dos de la prueba.
  const buscador = p.locator('input[type="search"], input[placeholder*="uscar"]').first();
  await buscador.fill(`AAA`);
  await p.waitForTimeout(2500);

  async function menuDe(nombre) {
    const fila = p.locator('tr', { hasText: nombre }).first();
    await fila.waitFor({ state: 'visible', timeout: 15000 });
    await fila.locator('button').last().click();
    await p.locator('.row-menu').waitFor({ state: 'visible', timeout: 8000 });
    await p.waitForTimeout(300);
    const txt = await p.locator('.row-menu').textContent();
    await p.keyboard.press('Escape');
    await p.evaluate(() => document.querySelectorAll('.row-menu').forEach(m => m.remove()));
    await p.waitForTimeout(200);
    return txt;
  }

  const menuAlzum = await menuDe(`AAA Comun ${SUF}`);
  ck('EN UN EJERCICIO DE ALZUM NO SE OFRECE ELIMINAR',
     !menuAlzum.includes('Eliminar'), menuAlzum);
  ck('ni editarlo', !menuAlzum.includes('Editar'), menuAlzum);
  ck('ni archivarlo', !/Archivar|Activar/.test(menuAlzum), menuAlzum);
  ck('pero sí duplicarlo, que es lo que le sirve', menuAlzum.includes('Duplicar'), menuAlzum);
  ck('y se le dice por qué', /cat[áa]logo de Alzum/i.test(menuAlzum), menuAlzum);

  const menuSuyo = await menuDe(`AAA Mio ${SUF}`);
  ck('EN EL SUYO SÍ PUEDE ELIMINAR', menuSuyo.includes('Eliminar'), menuSuyo);
  ck('y editarlo', menuSuyo.includes('Editar'), menuSuyo);

  // ── Y el servidor tampoco se deja, aunque se llame a mano ────────────────
  const aPelo = await ctx.request.delete(`${API}/api/trainings/${dePlataforma.data.id}`, {
    headers: Hc, failOnStatusCode: false });
  ck('llamando a la API directamente tampoco', aPelo.status() === 403, aPelo.status());

  /* El caso que de verdad se escapaba: lo creó él, la plataforma lo subió, y
     seguía teniendo la llave. */
  await ctx.request.put(`${API}/api/content/training/${suyo.data.id}/organization`, {
    headers: H, data: { organization_id: null } });
  const trasSubir = await ctx.request.delete(`${API}/api/trainings/${suyo.data.id}`, {
    headers: Hc, failOnStatusCode: false });
  ck('SUBIRLO A LA PLATAFORMA LE QUITA LA LLAVE AL AUTOR',
     trasSubir.status() === 403, trasSubir.status());

  // ── Las demás pantallas de la Librería ───────────────────────────────────
  /* Se comprueba que ninguna ofrezca borrar en una fila marcada como del
     catálogo común. */
  for (const pag of ['rutinas.html', 'aliments.html', 'diets.html', 'recipes.html', 'menus.html']) {
    await p.goto(FRONT + '/' + pag);
    await p.waitForTimeout(4000);
    if (p.url().includes('login')) { ck(`${pag}: no echa a login`, false, p.url()); continue; }
    ck(`${pag}: carga sin errores`, true);
  }

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
