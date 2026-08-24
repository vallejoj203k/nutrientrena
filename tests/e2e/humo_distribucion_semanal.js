/* Asignar varias dietas y decir qué día come cada una.

   Lo pedido: después de «Asignar 3 dietas» aparece «Distribución semanal» para
   repartirlas por días.

   Y arregla de raíz lo que se había reportado antes desde el panel del cliente
   —«aparece repetido el mismo menú»—: tres dietas sueltas valen todas para los
   siete días, así que el cliente sólo ve una y cambiar de día no le cambia
   nada. Repartirlas es lo que hace que cada día traiga comida distinta.

   Por eso esto no se queda en «el modal se abre»: guarda el reparto y va a
   MIRAR lo que el cliente come cada día. Que salga la ventana no sirve de nada
   si al cliente le sigue llegando lo mismo. */
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

  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 260))); if (!c) f++; };
  const SUF = String(Date.now()).slice(-6);
  const errs = [];

  // ── Un centro, su coach, un cliente y tres dietas distinguibles ──────────
  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };
  await ctx.request.post(`${API}/api/admin/organizations`, { headers: H, data: {
    name: `Centro Dist ${SUF}`, owner_name: 'Coach Dist',
    owner_email: `coach.dist.${SUF}@nutrientrena-qa.com`, owner_password: 'Coach123!' } });
  const lgc = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `coach.dist.${SUF}@nutrientrena-qa.com`, password: 'Coach123!' } })).json();
  const Hc = { Authorization: 'Bearer ' + lgc.data.token, 'Content-Type': 'application/json' };
  const cli = await (await ctx.request.post(`${API}/api/users`, { headers: Hc, data: {
    name: 'Cliente Dist', email: `cli.dist.${SUF}@nutrientrena-qa.com`,
    password: 'Cliente123!', role_id: 6 } })).json();
  const lgcli = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `cli.dist.${SUF}@nutrientrena-qa.com`, password: 'Cliente123!' } })).json();

  /* El nombre de la COMIDA es lo que se compara luego. El nombre del día
     cambia siempre, así que comparar el texto entero de la tarjeta pasaría
     aunque no hubiera ni una comida — ya me pasó escribiendo la prueba de
     nutrición del cliente. */
  const dietas = [];
  for (const n of ['Ade', 'Bde', 'Cde']) {
    const al = await (await ctx.request.post(`${API}/api/aliments`, { headers: Hc, data: {
      name: `Alimento ${n} ${SUF}`, calories: 100, quantity_unit: 'g' } })).json();
    const d = await (await ctx.request.post(`${API}/api/diets`, { headers: Hc, data: {
      title: `Dieta ${n} ${SUF}`, calories: 2000,
      foods: [{ name: `Comida ${n} ${SUF}`, time: '08:00',
                detail: [{ aliment_id: al.data.id, quantity: 100 }] }] } })).json();
    dietas.push(d.data.id);
  }
  ck('tres dietas en la biblioteca del coach', dietas.length === 3 && dietas.every(Boolean), dietas);

  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(String(e)));
  await p.goto(FRONT + '/client-profile.html?id=' + cli.data.id);
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '5');
                          localStorage.removeItem('org_context'); }, lgc.data.token);
  await p.goto(FRONT + '/client-profile.html?id=' + cli.data.id);
  await p.waitForTimeout(5000);

  // ── Asignar las tres, como haría el coach ────────────────────────────────
  await p.evaluate(() => { showTab('nutricion'); renderNutricionTab(); });
  await p.waitForTimeout(2500);
  await p.evaluate(() => openAssignDietModal());
  await p.waitForTimeout(3000);
  for (const id of dietas) await p.evaluate(i => toggleAssignDiet(i), id);
  await p.waitForTimeout(500);
  ck('el botón dice cuántas se van a asignar',
     (await p.textContent('#assignDietBtnLbl')).trim() === 'Asignar 3 dietas',
     await p.textContent('#assignDietBtnLbl'));

  await p.click('#assignDietBtn');
  /* La asignación copia tres dietas y manda los PDF por correo: hay que darle
     tiempo antes de mirar si salió la ventana. */
  await p.waitForSelector('#weekDistOverlay.open', { timeout: 30000 }).catch(() => {});
  /* `isVisible()` NO vale aquí: estos modales se ocultan con `opacity:0` y
     `pointer-events:none`, y para Playwright eso sigue siendo visible —lo daba
     por abierto siempre—. Lo que de verdad los abre es la clase `open`. */
  const abierto = id => p.$eval(id, el => el.classList.contains('open'));
  ck('AL ASIGNAR SALE LA DISTRIBUCIÓN SEMANAL', await abierto('#weekDistOverlay'));
  ck('y el modal de asignar se ha cerrado', !(await abierto('#assignDietOverlay')));

  // ── Lo que trae la ventana ───────────────────────────────────────────────
  ck('enseña las tres dietas disponibles', (await p.locator('#wdistChips .wdist-chip').count()) === 3);
  ck('y una fila por cada día de la semana', (await p.locator('#wdistRows .wdist-row').count()) === 7);

  const porDefecto = await p.$$eval('#wdistRows select', ss => ss.map(s => s.value));
  ck('VIENE REPARTIDA EN CICLO, no en blanco',
     porDefecto.every(Boolean) &&
     porDefecto[3] === porDefecto[0] && porDefecto[4] === porDefecto[1] &&
     new Set(porDefecto.slice(0, 3)).size === 3, porDefecto);

  /* Cambiar un día tiene que quedarse cambiado: si «Reiniciar ciclo» o el
     repintado lo pisaran, el coach guardaría algo distinto de lo que ve. */
  const otra = porDefecto[1];
  await p.selectOption('#wdistRows .wdist-row:nth-child(1) select', otra);
  await p.waitForTimeout(300);
  ck('se puede cambiar un día suelto',
     (await p.$eval('#wdistRows .wdist-row:nth-child(1) select', s => s.value)) === otra);

  await p.click('.wdist-reset');
  await p.waitForTimeout(300);
  ck('y "Reiniciar ciclo" lo devuelve al reparto de partida',
     (await p.$eval('#wdistRows .wdist-row:nth-child(1) select', s => s.value)) === porDefecto[0]);

  // Un día sin dieta: el domingo se deja libre a propósito.
  await p.selectOption('#wdistRows .wdist-row:nth-child(7) select', '');
  await p.waitForTimeout(300);

  await p.click('#wdistSaveBtn');
  await p.waitForTimeout(6000);
  ck('la ventana se cierra al guardar', !(await abierto('#weekDistOverlay')));

  /* El carril de días ya no lista dietas sueltas: lista los siete días con lo
     que come en cada uno. */
  const carril = await p.$$eval('.nut-day-item .nut-day-meta', els => els.map(e => e.textContent.trim()));
  ck('el carril del coach pasa a enseñar los siete días', carril.length === 7, carril);
  ck('con dieta distinta en los tres primeros', new Set(carril.slice(0, 3)).size === 3, carril);
  ck('y el domingo, que se dejó libre, sin dieta', /sin dieta/i.test(carril[6] || ''), carril[6]);

  // ── Lo que de verdad importa: qué come el cliente ────────────────────────
  const pc = await ctx.newPage(); pc.on('pageerror', e => errs.push(String(e)));
  await pc.goto(FRONT + '/client-nutricion.html');
  await pc.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '6'); }, lgcli.data.token);
  await pc.goto(FRONT + '/client-nutricion.html');
  await pc.waitForTimeout(4000);

  const vistas = [];
  const n = await pc.locator('.wday').count();
  for (let i = 0; i < n; i++) {
    await pc.locator('.wday').nth(i).click();
    await pc.waitForTimeout(400);
    vistas.push((await pc.locator('#daybox .meal-nm').allTextContents()).join(' | ') || '(sin comidas)');
  }
  ck('EL CLIENTE YA COME COSAS DISTINTAS SEGÚN EL DÍA',
     new Set(vistas.slice(0, 3)).size === 3, vistas.slice(0, 3));
  ck('el domingo se le queda sin comidas, como se dejó', vistas[6] === '(sin comidas)', vistas[6]);
  ck('y ya no le sale el aviso de "el mismo plan todos los días"',
     !(await pc.locator('#planAviso').isVisible()));

  // ── Volver a abrirla desde la pestaña, sin asignar nada ──────────────────
  await p.evaluate(() => openWeekDistModal());
  await p.waitForTimeout(1500);
  ck('se puede volver a abrir desde Nutrición', await abierto('#weekDistOverlay'));
  const guardado = await p.$$eval('#wdistRows select', ss => ss.map(s => s.value));
  ck('Y LLEGA CON LO QUE SE GUARDÓ, no con el ciclo otra vez',
     guardado[6] === '' && guardado[0] === porDefecto[0], guardado);

  /* ── Y desde la BIBLIOTECA, que es el otro sitio donde se asignan dietas ──
     Aquí se asigna de una en una y no hay ventana de distribución. Arreglarlo
     sólo en la ficha dejaba este camino igual de roto: el cliente seguía
     viendo la misma dieta todos los días. Se reportó así. */
  const cli2 = await (await ctx.request.post(`${API}/api/users`, { headers: Hc, data: {
    name: 'Cliente Lib', email: `cli.lib.${SUF}@nutrientrena-qa.com`,
    password: 'Cliente123!', role_id: 6 } })).json();
  const lgcli2 = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `cli.lib.${SUF}@nutrientrena-qa.com`, password: 'Cliente123!' } })).json();

  const pl = await ctx.newPage(); pl.on('pageerror', e => errs.push(String(e)));
  await pl.goto(FRONT + '/diets.html');
  await pl.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '5');
                           localStorage.removeItem('org_context'); }, lgc.data.token);
  await pl.goto(FRONT + '/diets.html');
  await pl.waitForTimeout(5000);

  for (const id of [dietas[0], dietas[1]]) {
    await pl.evaluate(i => openAssign(i, 'x'), id);
    await pl.waitForTimeout(800);
    await pl.selectOption('#assignClientSel', cli2.data.id);
    await pl.evaluate(() => confirmAssign());
    await pl.waitForTimeout(2500);
  }
  ck('la biblioteca avisa de que ha repartido la semana',
     /repartida por d/i.test(await pl.textContent('body')),
     (await pl.textContent('body')).slice(0, 0));

  const pc2 = await ctx.newPage(); pc2.on('pageerror', e => errs.push(String(e)));
  await pc2.goto(FRONT + '/client-nutricion.html');
  await pc2.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '6'); }, lgcli2.data.token);
  await pc2.goto(FRONT + '/client-nutricion.html');
  await pc2.waitForTimeout(4000);
  const desdeLib = [];
  for (let i = 0; i < 2; i++) {
    await pc2.locator('.wday').nth(i).click();
    await pc2.waitForTimeout(400);
    desdeLib.push((await pc2.locator('#daybox .meal-nm').allTextContents()).join(' | ') || '(sin comidas)');
  }
  ck('ASIGNANDO DESDE LA BIBLIOTECA EL CLIENTE TAMBIÉN COME DISTINTO CADA DÍA',
     desdeLib[0] !== desdeLib[1] && desdeLib.every(x => x !== '(sin comidas)'), desdeLib);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
