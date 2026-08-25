/* La pantalla del chat del coach, rehecha según el prototipo del cliente.

   Lo que se comprueba aquí:

     · Las pestañas Directos / Grupos filtran de verdad. Mezclados en una sola
       lista, con veinte clientes los grupos del equipo quedaban enterrados.
     · La cabecera dice si el chat de ese cliente está activo y lleva a su
       ficha. Si el coach le desactivó el chat, el cliente no puede
       contestarle: sin decirlo, el coach escribe y no entiende el silencio.
     · Se puede mandar un archivo, y le LLEGA al cliente. El coach quería
       mandar el PDF de la dieta sin salirse a WhatsApp.

   Lo del archivo se mira desde las dos pantallas —la del coach y la del
   cliente— porque son dos ficheros distintos que pintan lo mismo, y ya nos ha
   pasado arreglar una copia y dejar la otra rota. */
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

  // ── Un centro, su coach y dos clientes ──────────────────────────────────
  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };
  await ctx.request.post(`${API}/api/admin/organizations`, { headers: H, data: {
    name: `Centro Chat ${SUF}`, owner_name: 'Coach Chat',
    owner_email: `coach.chat.${SUF}@nutrientrena-qa.com`, owner_password: 'Coach123!' } });
  const lgc = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `coach.chat.${SUF}@nutrientrena-qa.com`, password: 'Coach123!' } })).json();
  const Hc = { Authorization: 'Bearer ' + lgc.data.token, 'Content-Type': 'application/json' };

  const clientes = [];
  for (const n of ['Ana', 'Bruno']) {
    const c = await (await ctx.request.post(`${API}/api/users`, { headers: Hc, data: {
      name: `${n} Chat`, email: `cli.${n.toLowerCase()}.${SUF}@nutrientrena-qa.com`,
      password: 'Cliente123!', role_id: 6 } })).json();
    const lg = await (await ctx.request.post(`${API}/api/auth/login`, {
      data: { email: `cli.${n.toLowerCase()}.${SUF}@nutrientrena-qa.com`, password: 'Cliente123!' } })).json();
    clientes.push({ det: c.data.id, uid: lg.data.user.id, token: lg.data.token, nombre: n });
  }
  ck('montados el coach y dos clientes', clientes.length === 2 && clientes.every(c => c.det && c.token));

  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(String(e)));
  await p.goto(FRONT + '/chat.html');
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '5');
                          localStorage.removeItem('org_context'); }, lgc.data.token);
  await p.goto(FRONT + '/chat.html');
  await p.waitForTimeout(5000);

  // ── La cabecera de la página ────────────────────────────────────────────
  ck('la página se presenta como en el prototipo',
     (await p.textContent('.chat-page-head h1')).trim() === 'Chat' &&
     /Conversaciones directas/.test(await p.textContent('.chat-page-head p')));

  // ── Conversación con Ana, y un grupo ────────────────────────────────────
  async function convCon(cli) {
    const r = await (await ctx.request.post(`${API}/api/chat/conversations`, { headers: Hc,
      data: { type: 'individual', participant_user_ids: [cli.uid] } })).json();
    if (!r.data) { console.log('FALLO no se pudo crear la conversación -> ' + JSON.stringify(r)); f++; return null; }
    return r.data.id;
  }
  const convAna = await convCon(clientes[0]);
  await convCon(clientes[1]);
  const grupo = await (await ctx.request.post(`${API}/api/chat/conversations`, { headers: Hc,
    data: { type: 'group', name: `Equipo ${SUF}`, audience: 'mis_clientes' } })).json();
  ck('y creados dos directos y un grupo', !!convAna && !!grupo.data?.id, grupo);

  await p.reload();
  await p.waitForTimeout(4000);

  // ── Las pestañas ────────────────────────────────────────────────────────
  ck('arranca en Directos', await p.$eval('#tabDirectos', e => e.classList.contains('sel')));
  const enDirectos = await p.$$eval('.conv-item .conv-name', els => els.map(e => e.textContent.trim()));
  ck('DIRECTOS ENSEÑA LOS CLIENTES Y NO EL GRUPO',
     enDirectos.length === 2 && !enDirectos.some(n => n.includes('Equipo')), enDirectos);

  await p.click('#tabGrupos');
  await p.waitForTimeout(600);
  const enGrupos = await p.$$eval('.conv-item .conv-name', els => els.map(e => e.textContent.trim()));
  ck('Y GRUPOS ENSEÑA EL GRUPO Y NO LOS CLIENTES',
     enGrupos.length === 1 && enGrupos[0].includes('Equipo'), enGrupos);

  /* El filtro tiene que aplicarse aunque repinte otro: abrir una conversación
     repinta la lista, y si el repintado se olvidara de la pestaña, saldrían de
     golpe los directos que la pestaña estaba escondiendo. */
  await p.click('.conv-item');
  await p.waitForTimeout(1500);
  const trasAbrir = await p.$$eval('.conv-item .conv-name', els => els.map(e => e.textContent.trim()));
  ck('y abrir una conversación NO deshace el filtro',
     trasAbrir.length === 1 && trasAbrir[0].includes('Equipo'), trasAbrir);

  await p.click('#tabDirectos');
  await p.waitForTimeout(600);
  await p.fill('#convSearch', 'Ana');
  await p.waitForTimeout(600);
  ck('la búsqueda sigue funcionando dentro de la pestaña',
     (await p.$$eval('.conv-item .conv-name', els => els.map(e => e.textContent))).length === 1);
  await p.fill('#convSearch', '');
  await p.waitForTimeout(600);

  // ── La cabecera de la conversación ──────────────────────────────────────
  /* Se abre la de Ana POR NOMBRE. Pinchar "la primera" no vale: la lista va
     por la última actividad, así que la primera fila cambia sola y la prueba
     acabaría mirando la cabecera de un cliente y el chat de otro — que es
     justo lo que me pasó escribiéndola. */
  async function abrir(nombre) {
    await p.locator('.conv-item', { hasText: nombre }).first().click();
    await p.waitForTimeout(2000);
    return (await p.textContent('#msgHeaderName')).trim();
  }
  ck('se abre la conversación de Ana, y es la de Ana',
     (await abrir('Ana')).includes('Ana'), await p.textContent('#msgHeaderName'));
  ck('el chat del cliente sale como ACTIVADO',
     (await p.textContent('#chipChat')).trim() === 'Activado' &&
     await p.$eval('#chipChat', e => e.classList.contains('on')));
  ck('y la cabecera lo dice también con palabras',
     (await p.textContent('#msgHeaderSub')).includes('activo'),
     await p.textContent('#msgHeaderSub'));
  const ficha = await p.getAttribute('#btnFicha', 'href');
  ck('"Ver ficha" lleva a la ficha DE ESE cliente',
     !!ficha && ficha.includes(clientes[0].det), ficha);

  /* Y si el coach le desactiva el chat, se dice. Sin esto el coach escribe y
     no entiende por qué el otro no contesta nunca. */
  const apagar = await ctx.request.put(
    `${API}/api/users/client/${clientes[0].det}/chat-enabled`,
    { headers: Hc, data: { chat_enabled: false } });
  /* Se comprueba que la llamada FUNCIONA. La primera versión de esto pegaba a
     una ruta que no existía: el 404 pasaba sin ruido y la comprobación de
     abajo habría dicho "no se ve desactivado" por el motivo equivocado. */
  ck('el coach puede desactivarle el chat', apagar.ok(), apagar.status());
  await p.reload();
  await p.waitForTimeout(4000);
  await abrir('Ana');
  ck('DESACTIVARLE EL CHAT AL CLIENTE SE VE EN LA CABECERA',
     (await p.textContent('#chipChat')).trim() === 'Desactivado' &&
     await p.$eval('#chipChat', e => e.classList.contains('off')));
  await ctx.request.put(`${API}/api/users/client/${clientes[0].det}/chat-enabled`,
    { headers: Hc, data: { chat_enabled: true } });
  await p.reload();
  await p.waitForTimeout(4000);
  await abrir('Ana');

  // ── Mandar un archivo ───────────────────────────────────────────────────
  /* La subida de verdad va a R2, que aquí no está: se simula la respuesta del
     servidor para poder probar TODO lo demás —que el mensaje se manda con los
     datos del archivo, que se pinta, y que le llega al cliente—. */
  await p.route('**/chat/conversations/*/attachment', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ success: true, data: {
      attachment_url: 'https://cdn.example/chat/dieta.pdf',
      attachment_name: `dieta-${SUF}.pdf`,
      attachment_type: 'application/pdf', attachment_size: 204800 } }) }));

  await p.setInputFiles('#adjFile', {
    name: `dieta-${SUF}.pdf`, mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4 x') });
  await p.waitForTimeout(2000);
  ck('el archivo se queda esperando antes de mandarlo',
     await p.$eval('#adjPrevio', e => e.style.display !== 'none') &&
     (await p.textContent('#adjPrevioTxt')).includes(`dieta-${SUF}.pdf`),
     await p.textContent('#adjPrevioTxt'));

  await p.fill('#sendInput', 'Aquí tienes la dieta');
  await p.click('.send-btn');
  await p.waitForTimeout(3000);
  ck('EL COACH VE EL ARCHIVO EN LA CONVERSACIÓN',
     (await p.locator('.adj-file .nm').last().textContent()).includes(`dieta-${SUF}.pdf`),
     await p.locator('.adj-file .nm').last().textContent().catch(() => null));
  ck('con su tamaño, no solo el nombre',
     /KB|MB/.test(await p.locator('.adj-file .sz').last().textContent()));
  ck('y el pie de foto va aparte, no dentro del archivo',
     (await p.textContent('#msgBody')).includes('Aquí tienes la dieta'));
  ck('el previo se limpia al mandarlo',
     await p.$eval('#adjPrevio', e => e.style.display === 'none'));

  // ── Y lo que ve el cliente, que es otra pantalla distinta ───────────────
  const pc = await ctx.newPage(); pc.on('pageerror', e => errs.push(String(e)));
  await pc.goto(FRONT + '/client-chat.html');
  await pc.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '6'); }, clientes[0].token);
  await pc.goto(FRONT + '/client-chat.html');
  await pc.waitForTimeout(5000);
  ck('AL CLIENTE LE LLEGA EL ARCHIVO, no una burbuja vacía',
     (await pc.locator('.adj-file .nm').count()) > 0 &&
     (await pc.locator('.adj-file .nm').last().textContent()).includes(`dieta-${SUF}.pdf`),
     await pc.textContent('#chatInner').catch(() => null));
  ck('y con el texto que lo acompañaba',
     (await pc.textContent('#chatInner')).includes('Aquí tienes la dieta'));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
