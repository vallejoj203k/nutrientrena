/* El cliente rellena su check-in. Una pantalla, en blanco, de una sentada.

   Lo que pasaba: «Hacer check-in» llevaba a PROGRESO, que es el historial. El
   formulario estaba partido en tres trozos sueltos entre los datos viejos
   —peso arriba, medidas dentro de una tarjeta que ya enseñaba las de la última
   vez, sensaciones más abajo— y cada trozo se guardaba por su cuenta. Volver a
   rellenarlo era ir buscando formularios entre lo ya registrado.

   Y una trampa fina: las sensaciones eran deslizadores puestos en 5. Un 5 de
   salida es una respuesta que el cliente NO ha dado, y al coach le llega como
   si la hubiera dado. Aquí no hay nada elegido hasta que se pulsa.
*/
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

  // ── Un coach, su cliente, y un check-in ya enviado hoy ───────────────────
  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };
  await ctx.request.post(`${API}/api/admin/organizations`, { headers: H, data: {
    name: `Centro Ck ${SUF}`, owner_name: 'Coach Ck',
    owner_email: `coach.ck.${SUF}@nutrientrena-qa.com`, owner_password: 'Coach123!' } });
  const lgc = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `coach.ck.${SUF}@nutrientrena-qa.com`, password: 'Coach123!' } })).json();
  const Hc = { Authorization: 'Bearer ' + lgc.data.token, 'Content-Type': 'application/json' };
  await ctx.request.post(`${API}/api/users`, { headers: Hc, data: {
    name: 'Cliente Ck', email: `cli.ck.${SUF}@nutrientrena-qa.com`,
    password: 'Cliente123!', role_id: 6 } });
  const lgcli = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `cli.ck.${SUF}@nutrientrena-qa.com`, password: 'Cliente123!' } })).json();
  const Hcli = { Authorization: 'Bearer ' + lgcli.data.token, 'Content-Type': 'application/json' };

  const previo = await ctx.request.post(`${API}/api/client/checkin`, { headers: Hcli, data: {
    weight: 80, body_fat: 19, waist: 88, chest: 100, energy: 8, effort: 7, notes: 'lo de la semana pasada' } });
  ck('el cliente ya tenía un check-in enviado hoy', previo.ok(), previo.status());

  // ── Desde Inicio ─────────────────────────────────────────────────────────
  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(String(e)));
  await p.goto(FRONT + '/client-home.html');
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '6'); }, lgcli.data.token);
  await p.goto(FRONT + '/client-home.html');
  await p.waitForTimeout(4000);

  /* Con el check-in de hoy ya enviado, la tarjeta pasa a "Hecho". Antes ahí
     solo quedaba "Ver progreso": corregir el peso o añadir las fotos que se te
     olvidaron no tenía puerta de entrada desde Inicio, que es justo lo que se
     quería arreglar. */
  const boton = p.locator('a.ci-btn[href="client-checkin.html"]').first();
  await boton.waitFor({ state: 'visible', timeout: 20000 });
  ck('CON EL CHECK-IN YA HECHO, SIGUE HABIENDO PUERTA PARA VOLVER',
     await boton.isVisible(), await p.locator('.ci-foot').first().textContent());
  ck('y no lleva al historial',
     (await boton.getAttribute('href')) === 'client-checkin.html',
     await boton.getAttribute('href'));

  await boton.click();
  await p.waitForURL(/client-checkin/, { timeout: 20000 });
  await p.waitForTimeout(3500);

  // ── Arranca en blanco ────────────────────────────────────────────────────
  ck('EL PESO ARRANCA VACÍO', (await p.inputValue('#ckPeso')) === '');
  ck('LAS MEDIDAS ARRANCAN VACÍAS', await p.evaluate(() =>
     ['waist','chest','hips','arms','legs']
       .every(k => document.getElementById('ck_' + k).value === '')));
  /* Un cliente no tiene báscula de bioimpedancia ni plicómetros. Pedirle esos
     dos lleva a una de dos cosas, las dos malas: o los deja vacíos siempre, o
     se inventa un número que al coach le llega como una medición. */
  ck('NO SE LE PIDE % DE GRASA NI MASA MUSCULAR', await p.evaluate(() =>
     !document.getElementById('ck_body_fat') && !document.getElementById('ck_muscle_mass')));
  ck('el comentario arranca vacío', (await p.inputValue('#ckNota')) === '');
  /* La trampa: un 5 puesto de salida es una respuesta que nadie ha dado. */
  ck('NINGUNA PUNTUACIÓN VIENE ELEGIDA', (await p.locator('.ck-num.on').count()) === 0);
  ck('pero se avisa de que ya mandó uno hoy', await p.locator('#ckYa').isVisible());
  ck('están las cuatro escalas', (await p.locator('.ck-esc').count()) === 4);

  // ── Rellenarlo entero ────────────────────────────────────────────────────
  await p.fill('#ckPeso', '79.4');
  await p.click('.ck-num[data-k="energy"][data-n="9"]');
  await p.click('.ck-num[data-k="effort"][data-n="6"]');
  await p.click('.ck-num[data-k="hunger"][data-n="3"]');
  await p.click('.ck-num[data-k="sleep"][data-n="7"]');
  ck('lo pulsado se marca', (await p.locator('.ck-num.on').count()) === 4);

  /* Poder deshacer: sin esto, una equivocación se manda igual. */
  await p.click('.ck-num[data-k="hunger"][data-n="3"]');
  ck('y volver a pulsarlo lo quita', (await p.locator('.ck-num.on').count()) === 3);
  await p.click('.ck-num[data-k="hunger"][data-n="4"]');

  await p.fill('#ck_waist', '86');
  await p.fill('#ck_hips', '95.5');
  await p.fill('#ckNota', `Semana dura pero bien ${SUF}`);

  await p.click('#ckBtn');
  await p.waitForURL(/client-home/, { timeout: 25000 }).catch(() => {});
  ck('al enviarlo vuelve al inicio', /client-home/.test(p.url()), p.url());

  // ── Y le llega al coach, con lo que se escribió ──────────────────────────
  const band = await (await ctx.request.get(`${API}/api/checkins/bandeja`, {
    headers: { Authorization: 'Bearer ' + lgc.data.token } })).json();
  const fila = (band.data.recibidos || []).find(x => x.weight === 79.4);
  ck('LE LLEGA AL COACH A SU BANDEJA', !!fila, band.data.recibidos);
  if (fila) {
    ck('con las puntuaciones que eligió',
       [fila.energy, fila.effort, fila.hunger, fila.sleep].join(',') === '9,6,4,7',
       [fila.energy, fila.effort, fila.hunger, fila.sleep]);
    ck('y con su comentario', fila.tiene_comentario === true, fila);
  }

  /* Se envía SOLO lo que el cliente rellenó: lo que dejó vacío no puede
     borrarle al coach lo que ya había. */
  const detalle = await (await ctx.request.get(`${API}/api/checkins/client/${fila.client_user_detail_id}`, {
    headers: { Authorization: 'Bearer ' + lgc.data.token } })).json();
  const bruto = detalle.data;
  const lista = Array.isArray(bruto) ? bruto : (bruto.checkins || []);
  const hoy = lista.find(x => x.id === fila.id) || {};
  ck('lo que se dejó en blanco no pisó lo anterior', hoy.chest === 100, hoy.chest);
  ck('y lo que se cambió, se cambió', hoy.waist === 86 && hoy.hips === 95.5,
     { waist: hoy.waist, hips: hoy.hips });
  /* Y lo que el coach había anotado con su aparato sigue ahí: quitarle al
     cliente esos campos no puede borrar lo que ya estaba medido. */
  ck('el % de grasa que anotó el coach sigue intacto', hoy.body_fat === 19, hoy.body_fat);

  /* Progreso pasa a ser solo historial: se le quitan los tres mini-formularios
     que hacían lo mismo repartido. Lo que NO puede pasar es que quede sin
     salida — quien entra ahí a apuntar su peso tiene que saber a dónde ir. */
  await p.goto(FRONT + '/client-progreso.html');
  await p.waitForTimeout(4000);
  ck('Progreso ya no tiene formularios sueltos', await p.evaluate(() =>
     !document.getElementById('wInput') && !document.getElementById('measForm')
     && !document.getElementById('feelForm')));
  ck('pero sí una salida clara al check-in',
     await p.locator('a.pg-ir-ck[href="client-checkin.html"]').isVisible());
  ck('y sigue enseñando el historial',
     (await p.locator('.card').count()) > 0);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
