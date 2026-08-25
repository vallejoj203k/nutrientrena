/* La pantalla del chat del CLIENTE, puesta a la altura de la del coach.

   Tres cosas, y las tres nacen de mirar las dos pantallas juntas:

     · El cliente también manda fotos. Antes solo podía recibirlas: para
       mandarle a su coach la foto de la comida tenía que salirse a WhatsApp,
       que es justo de donde se quiere sacar esto.
     · La cabecera decía "● Activo" en verde SIEMPRE. Nadie comprobaba nada: el
       coach podía llevar tres días sin aparecer y el puntito seguía ahí. Ahora
       dice lo único que sabemos de verdad, que es si el chat está abierto.
     · Y si el coach se lo ha cerrado, se le quita el cuadro de escribir. Antes
       el interruptor no hacía nada de nada: el coach lo apagaba, veía "Chat
       desactivado" en su panel, y su cliente seguía escribiéndole.

   Lo del archivo se comprueba en las dos direcciones —del cliente al coach y
   del coach al cliente— porque son dos ficheros distintos que pintan lo mismo.
*/
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

(async () => {
  const b = await chromium.launch();

  /* Un contexto POR PERSONA. Las dos pantallas se sirven del mismo origen, así
     que comparten localStorage: abrir el panel del coach en el mismo contexto
     machacaba el token del cliente, y al recargar su pantalla el guardia de
     rol la mandaba al panel del coach. Pasa desapercibido porque el fallo sale
     como "no encuentro el elemento", que parece un fallo de la página. */
  async function nuevoContexto(ancho, alto) {
    const c = await b.newContext({ viewport: { width: ancho, height: alto } });
    await c.route(u => u.href.startsWith(PROD), async route => {
      const q = route.request();
      try {
        const res = await c.request.fetch(q.url().replace(PROD, API), { method: q.method(), headers: q.headers(), data: q.postData() || undefined, maxRedirects: 0, timeout: 30000 });
        const h = { ...res.headers() }; delete h['content-encoding']; delete h['content-length'];
        await route.fulfill({ status: res.status(), headers: h, body: await res.body() });
      } catch (e) { await route.abort(); }
    });
    return c;
  }
  const ctx = await nuevoContexto(430, 900);          // el móvil del cliente

  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 260))); if (!c) f++; };
  const SUF = String(Date.now()).slice(-6);
  const errs = [];

  // ── Un coach con un cliente suyo ────────────────────────────────────────
  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };
  await ctx.request.post(`${API}/api/admin/organizations`, { headers: H, data: {
    name: `Centro CliChat ${SUF}`, owner_name: 'Coach CliChat',
    owner_email: `coach.clichat.${SUF}@nutrientrena-qa.com`, owner_password: 'Coach123!' } });
  const lgc = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `coach.clichat.${SUF}@nutrientrena-qa.com`, password: 'Coach123!' } })).json();
  const Hc = { Authorization: 'Bearer ' + lgc.data.token, 'Content-Type': 'application/json' };
  const cli = await (await ctx.request.post(`${API}/api/users`, { headers: Hc, data: {
    name: 'Cliente CliChat', email: `cli.clichat.${SUF}@nutrientrena-qa.com`,
    password: 'Cliente123!', role_id: 6 } })).json();
  const lgcli = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `cli.clichat.${SUF}@nutrientrena-qa.com`, password: 'Cliente123!' } })).json();
  ck('montado el cliente con su coach', !!cli.data?.id && !!lgcli.data?.token);

  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(String(e)));
  await p.goto(FRONT + '/client-chat.html');
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '6'); }, lgcli.data.token);
  await p.goto(FRONT + '/client-chat.html');
  await p.waitForTimeout(5000);

  // ── La cabecera ya no miente ────────────────────────────────────────────
  ck('LA CABECERA DICE SI EL CHAT ESTÁ ABIERTO, no "Activo" a secas',
     /chat activo/i.test(await p.textContent('#coachStatus')),
     await p.textContent('#coachStatus'));

  // ── El cliente manda una foto ───────────────────────────────────────────
  /* La subida real va a R2, que aquí no está: se simula la respuesta del
     servidor para poder probar todo lo demás —que se queda esperando, que se
     manda con sus datos, y que se pinta—. */
  await p.route('**/chat/conversations/*/attachment', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ success: true, data: {
      attachment_url: 'https://cdn.example/chat/comida.png',
      attachment_name: `comida-${SUF}.png`,
      attachment_type: 'image/png', attachment_size: 153600 } }) }));

  ck('tiene botón para adjuntar', await p.locator('#btnClip').isVisible());
  await p.setInputFiles('#adjFile', {
    name: `comida-${SUF}.png`, mimeType: 'image/png', buffer: Buffer.from('\x89PNG\r\n\x1a\n0000') });
  await p.waitForTimeout(2000);
  ck('el archivo se queda esperando antes de mandarlo',
     await p.$eval('#adjPrevio', e => e.style.display !== 'none') &&
     (await p.textContent('#adjPrevioTxt')).includes(`comida-${SUF}.png`),
     await p.textContent('#adjPrevioTxt'));

  await p.fill('#msgInput', 'Esto es lo que he comido hoy');
  await p.click('#sendBtn');
  await p.waitForTimeout(3000);
  ck('EL CLIENTE PUEDE MANDARLE UNA FOTO A SU COACH',
     (await p.locator('#chatInner .adj-img').count()) > 0,
     await p.textContent('#chatInner'));
  ck('con su texto al lado', (await p.textContent('#chatInner')).includes('Esto es lo que he comido hoy'));
  ck('y el previo se limpia', await p.$eval('#adjPrevio', e => e.style.display === 'none'));

  // ── Y le llega al coach, que es otra pantalla ───────────────────────────
  const ctxCoach = await nuevoContexto(1500, 950);
  const pk = await ctxCoach.newPage(); pk.on('pageerror', e => errs.push(String(e)));
  await pk.goto(FRONT + '/chat.html');
  await pk.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '5');
                           localStorage.removeItem('org_context'); }, lgc.data.token);
  await pk.goto(FRONT + '/chat.html');
  await pk.waitForTimeout(5000);
  await pk.locator('.conv-item').first().click();
  await pk.waitForTimeout(2500);
  ck('AL COACH LE LLEGA LA FOTO DEL CLIENTE',
     (await pk.locator('#msgBody .adj-img').count()) > 0,
     await pk.textContent('#msgBody'));
  /* Y en la lista se ve que hay algo, no "Sin mensajes": un mensaje que es
     solo un archivo no tiene texto que enseñar. */
  ck('y la lista de la izquierda no dice "Sin mensajes"',
     !(await pk.locator('.conv-item .conv-last').first().textContent()).includes('Sin mensajes'),
     await pk.locator('.conv-item .conv-last').first().textContent());

  // ── El coach le desactiva el chat ───────────────────────────────────────
  const apagar = await ctx.request.put(
    `${API}/api/users/client/${cli.data.id}/chat-enabled`,
    { headers: Hc, data: { chat_enabled: false } });
  /* Se comprueba que la llamada FUNCIONA: un 404 silencioso dejaría la
     comprobación de abajo fallando por el motivo equivocado. Ya me pasó
     escribiendo la prueba del chat del coach. */
  ck('el coach puede desactivarle el chat', apagar.ok(), apagar.status());

  await p.reload();
  await p.waitForTimeout(5000);
  /* Que la recarga siga en la pantalla del cliente. Si el token se hubiera
     pisado, el guardia de rol la habría llevado a otra página y todo lo de
     abajo fallaría diciendo "no encuentro el elemento". */
  ck('la recarga sigue en la pantalla del cliente', p.url().includes('client-chat.html'), p.url());
  ck('AL CLIENTE SE LE QUITA EL CUADRO DE ESCRIBIR',
     await p.$eval('#composerInner', e => e.style.display === 'none'));
  ck('y se le dice por qué, en vez de dejarlo sin explicación',
     await p.$eval('#chatOff', e => e.style.display !== 'none') &&
     /desactivado el chat/i.test(await p.textContent('#chatOff')));
  ck('la cabecera también lo dice',
     /desactivado/i.test(await p.textContent('#coachStatus')),
     await p.textContent('#coachStatus'));
  /* Sigue viendo lo que le escribió su coach: apagar el chat es dejar de
     poder responder, no perder el historial. */
  ck('pero sigue viendo lo que ya había',
     (await p.textContent('#chatInner')).includes('Esto es lo que he comido hoy'));

  // Y el servidor no se fía de la pantalla: aunque se llame a mano, no cuela.
  const aPelo = await ctx.request.post(`${API}/api/chat/conversations/${
    (await (await ctx.request.get(`${API}/api/client/chat`, {
      headers: { Authorization: 'Bearer ' + lgcli.data.token } })).json()).data.conversation_id
    }/messages`, {
    headers: { Authorization: 'Bearer ' + lgcli.data.token, 'Content-Type': 'application/json' },
    data: { content: 'por detrás' } });
  ck('Y EL SERVIDOR TAMPOCO LO ADMITE saltándose la pantalla',
     aPelo.status() === 403, aPelo.status());

  // ── Volver a activarlo ──────────────────────────────────────────────────
  await ctx.request.put(`${API}/api/users/client/${cli.data.id}/chat-enabled`,
    { headers: Hc, data: { chat_enabled: true } });
  await p.reload();
  await p.waitForTimeout(5000);
  ck('al reactivarlo puede volver a escribir',
     await p.$eval('#composerInner', e => e.style.display !== 'none') &&
     await p.$eval('#chatOff', e => e.style.display === 'none'));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
