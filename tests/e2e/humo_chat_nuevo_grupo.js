/* "Nuevo grupo", desde la pestaña de Grupos.

   Lo pedido: un botón dentro de Grupos que abre una ventana donde primero se
   elige QUÉ CLASE de grupo es, y la lista de gente se filtra según eso.

   No es adorno. La clase decide quién puede estar dentro:

     · Equipo      — solo el equipo. Un cliente ahí dentro lee cómo se habla de
                     los clientes.
     · Comunidad   — el coach con sus clientes: un reto. Aquí los clientes SÍ
                     se ven entre ellos.
     · Seguimiento — un cliente con quien lo lleva: hacen falta los dos.

   Por eso esto no se queda en "el modal se abre": comprueba que la lista
   cambia con la clase, que el botón no deja crear un grupo que no encaja, y
   que el grupo creado sale luego en su pestaña. */
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

  // ── Un centro con coach, alguien del equipo y dos clientes ──────────────
  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };
  const org = await (await ctx.request.post(`${API}/api/admin/organizations`, { headers: H, data: {
    name: `Centro NG ${SUF}`, owner_name: 'Coach NG',
    owner_email: `coach.ng.${SUF}@nutrientrena-qa.com`, owner_password: 'Coach123!' } })).json();
  const lgc = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `coach.ng.${SUF}@nutrientrena-qa.com`, password: 'Coach123!' } })).json();
  const Hc = { Authorization: 'Bearer ' + lgc.data.token, 'Content-Type': 'application/json' };

  /* Alguien del equipo, con cuenta propia y con su oficio: es por lo que se le
     elige al montar un seguimiento. Se crea la cuenta y DESPUÉS se mete en el
     equipo, que es como se hace desde la pantalla de Equipo. */
  // La cuenta la crea el admin: un coach solo da de alta clientes.
  const proU = await (await ctx.request.post(`${API}/api/users`, { headers: H, data: {
    name: 'Laura Minguez', email: `laura.ng.${SUF}@nutrientrena-qa.com`,
    password: 'Laura123!', role_id: 5 } })).json();
  const pro = await (await ctx.request.post(`${API}/api/team`, { headers: Hc, data: {
    user_detail_id: proU.data.id, member_name: 'Laura Minguez',
    member_email: `laura.ng.${SUF}@nutrientrena-qa.com`,
    role_label: 'Nutricionista' } })).json();
  ck('metido alguien en el equipo, con su oficio',
     !!proU.data?.id && !!pro.data, { proU, pro });

  const clientes = [];
  for (const n of ['Ana', 'Bruno']) {
    const c = await (await ctx.request.post(`${API}/api/users`, { headers: Hc, data: {
      name: `${n} NG`, email: `cli.${n.toLowerCase()}.ng.${SUF}@nutrientrena-qa.com`,
      password: 'Cliente123!', role_id: 6 } })).json();
    clientes.push(c.data.id);
  }
  ck('y dos clientes', clientes.length === 2 && clientes.every(Boolean), clientes);

  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(String(e)));
  await p.goto(FRONT + '/chat.html');
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '5');
                          localStorage.removeItem('org_context'); }, lgc.data.token);
  await p.goto(FRONT + '/chat.html');
  await p.waitForTimeout(5000);

  // ── El botón está donde se busca ────────────────────────────────────────
  ck('en Directos NO se ofrece crear grupo', !(await p.locator('#btnNuevoGrupo').isVisible()));
  await p.click('#tabGrupos');
  await p.waitForTimeout(700);
  /* Y la pestaña de Grupos existe aunque no haya ninguno todavía: si se
     escondiera cuando está vacía, no habría por dónde crear el primero. */
  ck('LA PESTAÑA DE GRUPOS ESTÁ AUNQUE NO HAYA NINGUNO',
     await p.locator('#tabGrupos').isVisible());
  ck('y ahí sí aparece "+ Nuevo grupo"', await p.locator('#btnNuevoGrupo').isVisible());

  await p.click('#btnNuevoGrupo');
  await p.waitForTimeout(2500);
  const abierto = () => p.$eval('#ngOverlay', e => e.classList.contains('open'));
  ck('se abre la ventana de nuevo grupo', await abierto());
  ck('ofrece las tres clases del diseño, y el aviso que ya existía',
     (await p.locator('.ng-tipo').count()) === 4);

  // ── La lista cambia con la clase, que es de lo que va todo esto ─────────
  const nombres = () => p.$$eval('#ngMiembros .nm b', els => els.map(e => e.textContent.trim()));

  ck('arranca en Equipo', await p.$eval('.ng-tipo', e => e.classList.contains('sel')));
  const enEquipo = await nombres();
  ck('EN "EQUIPO" SOLO SALE EL EQUIPO, ningún cliente',
     enEquipo.length > 0 && !enEquipo.some(n => /Ana NG|Bruno NG/.test(n)), enEquipo);
  ck('y con su oficio al lado, que es por lo que se le elige',
     (await p.textContent('#ngMiembros')).includes('Nutricionista'),
     await p.textContent('#ngMiembros'));

  await p.locator('.ng-tipo').nth(1).click();
  await p.waitForTimeout(700);
  const enComunidad = await nombres();
  ck('EN "COMUNIDAD" SOLO SALEN LOS CLIENTES',
     enComunidad.length === 2 && enComunidad.every(n => /Ana NG|Bruno NG/.test(n)), enComunidad);
  /* Y se avisa de lo que no se ve mirando la pantalla: en un reto los clientes
     se leen entre ellos, al revés que en el aviso a todos. */
  ck('y se avisa de que ahí los clientes se ven entre ellos',
     /se leen entre ellos/i.test(await p.textContent('#ngNota')),
     await p.textContent('#ngNota'));

  await p.locator('.ng-tipo').nth(2).click();
  await p.waitForTimeout(700);
  const enSeguimiento = await nombres();
  ck('en "Seguimiento" salen los dos, equipo y clientes',
     enSeguimiento.length === 3, enSeguimiento);

  /* Cambiar de clase no puede arrastrar lo ya marcado: lo elegido para un
     grupo del equipo no vale para una comunidad, y colarlo metería a gente
     que no toca sin que se vea. */
  await p.locator('#ngMiembros input').first().check();
  await p.waitForTimeout(400);
  await p.locator('.ng-tipo').nth(1).click();
  await p.waitForTimeout(700);
  ck('CAMBIAR DE CLASE NO ARRASTRA A LOS YA MARCADOS',
     (await p.$$eval('#ngMiembros input', els => els.filter(e => e.checked).length)) === 0);

  // ── El botón cuenta, y no deja crear lo que no encaja ───────────────────
  ck('sin nadie marcado no deja crear', await p.$eval('#ngCrear', e => e.disabled));
  await p.locator('#ngMiembros input').first().check();
  await p.waitForTimeout(400);
  ck('y dice cuántos van', /1 miembro\b/.test(await p.textContent('#ngCrear')),
     await p.textContent('#ngCrear'));

  await p.locator('.ng-tipo').nth(2).click();   // Seguimiento
  await p.waitForTimeout(700);
  const rotulos = await p.$$eval('#ngMiembros .nm', els => els.map(e => e.textContent));
  const iCli = rotulos.findIndex(t => /Ana NG/.test(t));
  const iPro = rotulos.findIndex(t => /Nutricionista/.test(t));
  ck('en la lista de seguimiento están el cliente y quien lo lleva',
     iCli >= 0 && iPro >= 0, rotulos);
  const fila = i => p.locator('#ngMiembros .ng-miembro').nth(i).locator('input');
  await fila(iCli).check();
  await p.waitForTimeout(400);
  ck('UN SEGUIMIENTO CON SOLO EL CLIENTE NO DEJA CREAR',
     await p.$eval('#ngCrear', e => e.disabled));
  await fila(iPro).check();
  await p.waitForTimeout(400);
  ck('y con el cliente y quien lo lleva, sí',
     !(await p.$eval('#ngCrear', e => e.disabled)));

  // ── Crear de verdad ────────────────────────────────────────────────────
  await p.fill('#ngNombre', `Seguimiento Ana ${SUF}`);
  await p.click('#ngCrear');
  await p.waitForTimeout(4000);
  ck('la ventana se cierra al crearlo', !(await abierto()));
  ck('EL GRUPO CREADO SALE EN LA PESTAÑA DE GRUPOS',
     (await p.$$eval('.conv-item .conv-name', els => els.map(e => e.textContent)))
       .some(n => n.includes(`Seguimiento Ana ${SUF}`)),
     await p.$$eval('.conv-item .conv-name', els => els.map(e => e.textContent)));
  ck('y queda abierto, listo para escribir',
     (await p.textContent('#msgHeaderName')).includes(`Seguimiento Ana ${SUF}`),
     await p.textContent('#msgHeaderName'));
  /* Un grupo de estos NO es difusión: es una conversación. Si naciera de
     difusión, solo escribiría el coach y no habría seguimiento ninguno. */
  ck('se puede escribir en él', await p.locator('.send-bar').isVisible());

  // ── Y el servidor no se fía de la pantalla ─────────────────────────────
  const aPelo = await ctx.request.post(`${API}/api/chat/conversations`, { headers: Hc, data: {
    type: 'group', name: `Colado ${SUF}`, tipo: 'equipo',
    participant_user_ids: [] } });
  const colado = await ctx.request.post(`${API}/api/chat/conversations`, { headers: Hc, data: {
    type: 'group', name: `Colado2 ${SUF}`, tipo: 'equipo',
    participant_user_ids: [999999] } });
  ck('EL SERVIDOR TAMPOCO ADMITE UN GRUPO QUE NO ENCAJA saltándose la pantalla',
     aPelo.status() >= 400 && colado.status() >= 400, [aPelo.status(), colado.status()]);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
