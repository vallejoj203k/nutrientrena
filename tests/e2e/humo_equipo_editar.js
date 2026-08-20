/* Editar a alguien del equipo de Alzum, contra la aplicación de verdad.

   La pantalla dejaba cambiar el rol y sacar a la persona, pero no arreglar una
   errata en un apellido ni un correo mal escrito al invitar. Lo que hay que
   ver aquí y no se ve por API: que el lápiz esté en la fila, que el formulario
   llegue RELLENO con lo que ya tenía —si sale vacío, guardar borraría datos— y
   que la contraseña que se escribe ahí sirva de verdad para entrar. */
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1500, height: 950 } });
  await ctx.route(u => u.href.startsWith(PROD), async route => {
    const q = route.request(); const url = q.url().replace(PROD, API);
    try {
      const res = await ctx.request.fetch(url, { method: q.method(), headers: q.headers(), data: q.postData() || undefined, maxRedirects: 0, timeout: 20000 });
      const h = { ...res.headers() }; delete h['content-encoding']; delete h['content-length'];
      await route.fulfill({ status: res.status(), headers: h, body: await res.body() });
    } catch (e) { await route.abort(); }
  });

  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 240))); if (!c) f++; };
  const SUF = String(Date.now()).slice(-6);

  const lg = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const H = { Authorization: 'Bearer ' + lg.data.token, 'Content-Type': 'application/json' };

  // Alguien del equipo con datos a medio poner, que es el caso real.
  const alta = await (await ctx.request.post(`${API}/api/admin/team`, { headers: H, data: {
    name: 'Lucia', email: `lucia.mal.${SUF}@nutrentrena-qa.com`,   // correo con errata
    role_id: 7, password: 'Editor123!' } })).json();
  ck('miembro de prueba creado', !!alta.data?.user_id, alta);
  const uid = alta.data.user_id;

  const errs = [];
  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(String(e)));
  await p.goto(FRONT + '/admin/index.html');
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '1'); }, lg.data.token);
  await p.goto(FRONT + '/admin/index.html#equipo');
  await p.locator('.rol-tarj').first().waitFor({ state: 'visible', timeout: 25000 });
  await p.waitForTimeout(1500);

  const fila = p.locator('tr', { hasText: `lucia.mal.${SUF}@nutrentrena-qa.com` }).first();
  await fila.waitFor({ state: 'visible', timeout: 15000 });
  ck('la fila ofrece editar', await fila.locator('button[title="Editar datos"]').isVisible());

  await fila.locator('button[title="Editar datos"]').click();
  await p.locator('#capaEditMiem.on').waitFor({ state: 'visible', timeout: 10000 });
  await p.waitForTimeout(400);

  /* Si el formulario sale vacío, darle a guardar BORRA lo que había: es el
     fallo más caro que puede tener un formulario de edición. */
  ck('el formulario llega relleno con lo que ya tenía', await p.evaluate(() => ({
    n: document.getElementById('edMiemNombre').value,
    e: document.getElementById('edMiemEmail').value,
  })).then(v => v.n === 'Lucia' && v.e.startsWith('lucia.mal.')),
     await p.inputValue('#edMiemNombre'));
  ck('y la contraseña llega VACÍA, no con la de la persona',
     (await p.inputValue('#edMiemClave')) === '');

  // Corregir todo, contraseña incluida.
  await p.fill('#edMiemNombre', 'Lucía');
  await p.fill('#edMiemApellidos', 'Prats Gómez');
  await p.fill('#edMiemEmail', `lucia.${SUF}@alzum.io`);
  await p.fill('#edMiemTel', '600112233');
  await p.fill('#edMiemClave', 'ClaveNueva9!');
  await p.click('#edMiemBtn');
  await p.waitForTimeout(2500);

  ck('la ventana se cierra al guardar', !(await p.locator('#capaEditMiem.on').count()));
  const filaNueva = p.locator('tr', { hasText: `lucia.${SUF}@alzum.io` }).first();
  ck('la tabla ya enseña los datos corregidos',
     (await filaNueva.count()) === 1 &&
     (await filaNueva.textContent()).includes('Lucía Prats Gómez'),
     await filaNueva.textContent().catch(() => 'sin fila'));

  // Lo que de verdad importa de una contraseña: que sirva para entrar.
  const conNueva = await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `lucia.${SUF}@alzum.io`, password: 'ClaveNueva9!' }, failOnStatusCode: false });
  ck('LA CONTRASEÑA NUEVA SIRVE PARA ENTRAR', conNueva.status() === 200, conNueva.status());
  const conVieja = await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `lucia.${SUF}@alzum.io`, password: 'Editor123!' }, failOnStatusCode: false });
  ck('y la vieja ya no', conVieja.status() !== 200, conVieja.status());

  /* Guardar sin tocar la contraseña no puede cambiarla: es la trampa de todo
     formulario de edición que lleva un campo de contraseña. */
  await filaNueva.locator('button[title="Editar datos"]').click();
  await p.locator('#capaEditMiem.on').waitFor({ state: 'visible', timeout: 10000 });
  await p.fill('#edMiemApellidos', 'Prats');
  await p.click('#edMiemBtn');
  await p.waitForTimeout(2500);
  const sigueValiendo = await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `lucia.${SUF}@alzum.io`, password: 'ClaveNueva9!' }, failOnStatusCode: false });
  ck('GUARDAR SIN TOCAR LA CONTRASEÑA NO LA CAMBIA', sigueValiendo.status() === 200, sigueValiendo.status());

  // Un correo que ya es de otro se rechaza con un motivo, no en silencio.
  await ctx.request.post(`${API}/api/admin/team`, { headers: H, data: {
    name: 'Otro', email: `otro.${SUF}@alzum.io`, role_id: 8, password: 'Otro12345!' } });
  await p.reload(); await p.waitForTimeout(2500);
  await p.locator('tr', { hasText: `lucia.${SUF}@alzum.io` }).first()
       .locator('button[title="Editar datos"]').click();
  await p.locator('#capaEditMiem.on').waitFor({ state: 'visible', timeout: 10000 });
  await p.fill('#edMiemEmail', `otro.${SUF}@alzum.io`);
  await p.click('#edMiemBtn');
  await p.waitForTimeout(2000);
  ck('un correo ya usado se rechaza diciendo por qué',
     (await p.textContent('#edMiemError')).toLowerCase().includes('email'),
     await p.textContent('#edMiemError'));
  ck('y la ventana sigue abierta para poder corregirlo',
     await p.locator('#capaEditMiem.on').isVisible());

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
