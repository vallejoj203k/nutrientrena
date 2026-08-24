/* La nutrición del cliente: qué come cada día.

   Lo reportado: «no aparecen todas las comidas si voy cambiando de días,
   aparece repetido el mismo menú».

   Y es cierto, pero por una razón que la pantalla no contaba. Hay dos formas
   de darle comida a un cliente:

     · Una DIETA suelta asignada al cliente → vale para los siete días. Es lo
       que pasaba. Y si el coach le asignó varias, el cliente solo ve la última.
     · Un MENÚ SEMANAL → una dieta por día. Es la única forma de comer distinto
       el lunes y el martes.

   El problema no era que repitiera —eso es lo que el coach había configurado—
   sino que la tira de días de arriba invitaba a esperar algo distinto en cada
   uno y cambiar de día no cambiaba nada, sin explicación. Ahora se dice.

   Aquí se montan los DOS casos con un cliente de verdad y se comparan. */
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 430, height: 900 } });
  await ctx.route(u => u.href.startsWith(PROD), async route => {
    const q = route.request();
    try {
      const res = await ctx.request.fetch(q.url().replace(PROD, API), { method: q.method(), headers: q.headers(), data: q.postData() || undefined, maxRedirects: 0, timeout: 30000 });
      const h = { ...res.headers() }; delete h['content-encoding']; delete h['content-length'];
      await route.fulfill({ status: res.status(), headers: h, body: await res.body() });
    } catch (e) { await route.abort(); }
  });

  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 240))); if (!c) f++; };
  const SUF = String(Date.now()).slice(-6);
  const errs = [];

  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };
  await ctx.request.post(`${API}/api/admin/organizations`, { headers: H, data: {
    name: `Centro Nut ${SUF}`, owner_name: 'Coach Nut',
    owner_email: `coach.nut.${SUF}@nutrientrena-qa.com`, owner_password: 'Coach123!' } });
  const lgc = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `coach.nut.${SUF}@nutrientrena-qa.com`, password: 'Coach123!' } })).json();
  const Hc = { Authorization: 'Bearer ' + lgc.data.token, 'Content-Type': 'application/json' };
  const cli = await (await ctx.request.post(`${API}/api/users`, { headers: Hc, data: {
    name: 'Cliente Nut', email: `cli.nut.${SUF}@nutrientrena-qa.com`,
    password: 'Cliente123!', role_id: 6 } })).json();
  const lgcli = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `cli.nut.${SUF}@nutrientrena-qa.com`, password: 'Cliente123!' } })).json();
  ck('montado el cliente de prueba', !!cli.data?.id && !!lgcli.data?.token, { cli });

  /* Tres dietas, cada una con una comida de nombre distinto. El nombre de la
     comida es lo que se compara después: el nombre del DÍA cambia siempre
     (Lunes, Martes…), así que comparar el texto entero de la tarjeta pasaría
     aunque no hubiera ni una comida. */
  const dietas = [];
  for (const nombre of ['Lunes', 'Martes', 'Miercoles']) {
    const al = await (await ctx.request.post(`${API}/api/aliments`, { headers: Hc, data: {
      name: `Alimento ${nombre} ${SUF}`, calories: 100, quantity_unit: 'g' } })).json();
    const d = await (await ctx.request.post(`${API}/api/diets`, { headers: Hc, data: {
      title: `${nombre} ${SUF}`, calories: 2000,
      foods: [{ name: `Comida de ${nombre} ${SUF}`, time: '08:00',
                detail: [{ aliment_id: al.data.id, quantity: 100 }] }] } })).json();
    dietas.push(d.data.id);
  }
  ck('y tres dietas, cada una con su comida', dietas.length === 3 && dietas.every(Boolean), dietas);

  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(String(e)));

  async function comidasQueSeVen() {
    /* Se recorren los siete días PULSANDO en la tira, como haría el cliente, y
       se anota SOLO el nombre de las comidas. Comparar el texto entero de la
       tarjeta no vale: el nombre del día cambia siempre, así que la
       comprobación pasaría aunque no hubiera ni una comida. Me pasó
       escribiéndola. */
    const vistas = [];
    const n = await p.locator('.wday').count();
    for (let i = 0; i < n; i++) {
      await p.locator('.wday').nth(i).click();
      await p.waitForTimeout(400);
      const nombres = await p.locator('#daybox .meal-nm').allTextContents();
      vistas.push(nombres.join(' | ') || '(sin comidas)');
    }
    return vistas;
  }

  // ── Caso A: una dieta suelta asignada al cliente ─────────────────────────
  const suelta = await (await ctx.request.post(`${API}/api/diets/${dietas[0]}/assign`, {
    headers: Hc, data: { client_id: cli.data.id } })).json();
  ck('el coach le asigna una dieta suelta', !!suelta.data, suelta);

  await p.goto(FRONT + '/client-nutricion.html');
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '6'); }, lgcli.data.token);
  await p.goto(FRONT + '/client-nutricion.html');
  await p.waitForTimeout(4000);

  ck('la tira enseña los siete días', (await p.locator('.wday').count()) === 7);
  const sinMenu = await comidasQueSeVen();
  ck('SIN MENÚ SEMANAL, TODOS LOS DÍAS TRAEN LA MISMA COMIDA',
     new Set(sinMenu).size === 1 && sinMenu[0] !== '(sin comidas)', sinMenu);
  ck('PERO AHORA LA PANTALLA LO DICE, en vez de dejarte cambiando de día sin ver nada',
     await p.locator('#planAviso').isVisible());
  ck('y lo dice con palabras', (await p.textContent('#planAviso')).includes('mismo plan'),
     await p.textContent('#planAviso'));

  // ── Caso B: un menú semanal con una dieta por día ────────────────────────
  const menu = await (await ctx.request.post(`${API}/api/weekly-menus`, { headers: Hc, data: {
    name: `Semana ${SUF}`,
    days: [
      { day_index: 0, name: 'Lunes', diet_id: dietas[0] },
      { day_index: 1, name: 'Martes', diet_id: dietas[1] },
      { day_index: 2, name: 'Miércoles', diet_id: dietas[2] },
      { day_index: 3, name: 'Jueves', diet_id: dietas[0] },
      { day_index: 4, name: 'Viernes', diet_id: dietas[1] },
      { day_index: 5, name: 'Sábado', diet_id: null },
      { day_index: 6, name: 'Domingo', diet_id: null },
    ] } })).json();
  const asig = await (await ctx.request.post(`${API}/api/weekly-menus/${menu.data.id}/assign`, {
    headers: Hc, data: { client_id: cli.data.id } })).json();
  ck('el coach le asigna un menú semanal', !!asig.data, asig);

  await p.reload();
  await p.waitForTimeout(4000);

  const conMenu = await comidasQueSeVen();
  ck('CON MENÚ SEMANAL, LOS DÍAS TRAEN COSAS DISTINTAS',
     new Set(conMenu.slice(0, 3)).size === 3, conMenu.slice(0, 3));
  ck('el sábado, sin dieta, se queda sin comidas', conMenu[5] === '(sin comidas)', conMenu[5]);
  /* Y lo dice con palabras, no lo deja en blanco: un día vacío sin explicación
     parece que la aplicación no ha cargado. */
  await p.locator('.wday').nth(5).click();
  await p.waitForTimeout(400);
  ck('y lo dice con palabras',
     (await p.textContent('#daybox')).includes('No hay menú asignado'),
     (await p.textContent('#daybox')).replace(/\s+/g, ' ').slice(0, 120));
  ck('sin el aviso de "mismo plan todos los días", porque no lo es',
     !(await p.locator('#planAviso').isVisible()));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
