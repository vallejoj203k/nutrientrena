/* El chat en el móvil, y el aviso sonoro.

   Lo que pasaba en un iPhone: la caja de escribir NO SE VEÍA. No estaba oculta
   ni desactivada — estaba fuera de la pantalla, debajo del borde, sin forma de
   llegar a ella.

   La causa es `100vh`. En iOS Safari, `100vh` es la altura de la ventana SIN
   contar la barra de direcciones ni la de abajo, así que la página mide más de
   lo que se ve; y como el body lleva `overflow:hidden`, tampoco se puede
   desplazar para alcanzarla. El chat quedaba de solo lectura en el móvil.
   `100dvh` sí descuenta el navegador.

   AVISO SOBRE ESTA PRUEBA, para que nadie se fíe de más: el navegador con el
   que corre —Chromium sin ventana— NO TIENE barra de direcciones, así que
   para él `100vh` y `100dvh` valen exactamente lo mismo. Lo comprobé
   deshaciendo el arreglo a propósito: la prueba seguía en verde.

   O sea que el síntoma de iOS no se puede reproducir aquí. Lo que sí se puede
   comprobar, y es lo que se hace abajo, es que el arreglo SIGA PUESTO en el
   CSS: si alguien quita el `100dvh`, se canta. Es una prueba de regresión, no
   de que el fallo esté curado; de eso responde haberlo mirado en un iPhone.

   Lo demás de este archivo —que se pueda escribir, enviar, y silenciar el
   aviso— sí se prueba de verdad. */
const { chromium, devices } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

const rutear = ctx => ctx.route(u => u.href.startsWith(PROD), async route => {
  const q = route.request();
  try {
    const res = await ctx.request.fetch(q.url().replace(PROD, API), { method: q.method(), headers: q.headers(), data: q.postData() || undefined, maxRedirects: 0, timeout: 30000 });
    const h = { ...res.headers() }; delete h['content-encoding']; delete h['content-length'];
    await route.fulfill({ status: res.status(), headers: h, body: await res.body() });
  } catch (e) { await route.abort(); }
});

(async () => {
  const b = await chromium.launch();
  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 240))); if (!c) f++; };
  const SUF = String(Date.now()).slice(-6);
  const errs = [];

  // ── Un coach y su cliente ────────────────────────────────────────────────
  const aux = await b.newContext(); await rutear(aux);
  const adm = await (await aux.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };
  await aux.request.post(`${API}/api/admin/organizations`, { headers: H, data: {
    name: `Centro Mov ${SUF}`, owner_name: 'Sergio Soto',
    owner_email: `coach.mov.${SUF}@nutrientrena-qa.com`, owner_password: 'Coach123!' } });
  const lgc = await (await aux.request.post(`${API}/api/auth/login`, {
    data: { email: `coach.mov.${SUF}@nutrientrena-qa.com`, password: 'Coach123!' } })).json();
  const Hc = { Authorization: 'Bearer ' + lgc.data.token, 'Content-Type': 'application/json' };
  await aux.request.post(`${API}/api/users`, { headers: Hc, data: {
    name: 'Cliente Movil', email: `cli.mov.${SUF}@nutrientrena-qa.com`,
    password: 'Cliente123!', role_id: 6 } });
  const lgcli = await (await aux.request.post(`${API}/api/auth/login`, {
    data: { email: `cli.mov.${SUF}@nutrientrena-qa.com`, password: 'Cliente123!' } })).json();

  /* Un iPhone de verdad, con su factor de escala y su user-agent: el fallo
     depende de la ventana pequeña, no de un viewport cualquiera. */
  const iPhone = devices['iPhone 12'] || { viewport: { width: 390, height: 664 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true };
  const ctxM = await b.newContext(iPhone); await rutear(ctxM);
  const m = await ctxM.newPage(); m.on('pageerror', e => errs.push(String(e)));
  await m.goto(FRONT + '/client-chat.html');
  await m.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '6'); }, lgcli.data.token);
  await m.goto(FRONT + '/client-chat.html');
  await m.waitForTimeout(5000);

  // ── Lo que no se veía ────────────────────────────────────────────────────
  ck('LA CAJA DE ESCRIBIR SE VE EN EL MÓVIL',
     await m.locator('#msgInput').isVisible());
  ck('y el botón de enviar también', await m.locator('#sendBtn').isVisible());

  /* isVisible() no basta: un elemento fuera de la pantalla sigue siendo
     "visible" para el navegador. Esto sí se comprueba, aunque en Chromium
     nunca falle: si algún día alguien mete un pie de página fijo, cazará que
     la caja se salió. */
  const sitio = await m.evaluate(() => {
    const i = document.getElementById('msgInput').getBoundingClientRect();
    return { abajo: Math.round(i.bottom), ventana: window.innerHeight,
             dentro: i.bottom <= window.innerHeight + 1 && i.top >= 0 };
  });
  ck('dentro de la pantalla, no debajo del borde', sitio.dentro, sitio);

  /* EL ARREGLO DE iOS, comprobado donde sí se puede: en el propio CSS. El
     navegador de esta prueba no distingue vh de dvh, así que se mira que la
     regla siga escrita. */
  const alturas = await m.evaluate(() => {
    /* Ojo: el navegador colapsa las declaraciones repetidas y en `cssText`
       solo queda la que gana. Escribimos `height:100vh;height:100dvh;` —el
       primero es el respaldo para navegadores viejos— y aquí solo se ve el
       dvh. Por eso se busca dvh, no la pareja. */
    const reglas = [];
    for (const hoja of document.styleSheets) {
      let lista; try { lista = hoja.cssRules; } catch (e) { continue; }
      for (const r of lista || []) {
        const t = r.cssText || '';
        if (/height:\s*100(d?)vh/.test(t)) reglas.push(t);
      }
    }
    return reglas;
  });
  ck('SIGUE PUESTO EL ARREGLO DE iOS (100dvh, no 100vh a secas)',
     alturas.length > 0 && alturas.every(t => /height:\s*100dvh/.test(t)),
     alturas.filter(t => !/height:\s*100dvh/.test(t)).map(t => t.slice(0, 90)));

  /* Y que se pueda pulsar de verdad: nada tapándola. */
  ck('se puede tocar, no la tapa nada', await m.evaluate(() => {
    const i = document.getElementById('msgInput');
    const r = i.getBoundingClientRect();
    const encima = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return !!encima && (encima === i || i.contains(encima));
  }));

  ck('no hay barra horizontal', await m.evaluate(() =>
     document.documentElement.scrollWidth <= window.innerWidth + 1));

  // ── Y se puede escribir de verdad ────────────────────────────────────────
  await m.fill('#msgInput', `Desde el móvil ${SUF}`);
  await m.click('#sendBtn');
  await m.waitForTimeout(3500);
  ck('SE PUEDE ENVIAR UN MENSAJE DESDE EL MÓVIL',
     (await m.textContent('#chatInner')).includes(`Desde el móvil ${SUF}`),
     (await m.textContent('#chatInner')).slice(-140));

  // ── El aviso sonoro ──────────────────────────────────────────────────────
  ck('está el botón para silenciarlo', await m.locator('#btnSonido').isVisible());
  ck('y arranca activado', await m.evaluate(() => !window.avisoChat.silenciado()));

  await m.click('#btnSonido');
  await m.waitForTimeout(400);
  ck('se puede silenciar', await m.evaluate(() => window.avisoChat.silenciado()));
  ck('y el icono lo dice', await m.evaluate(() =>
     document.getElementById('btnSonido').classList.contains('mudo')));
  /* Que se recuerde: un sonido que vuelve solo en cada recarga es lo mismo que
     no poderlo apagar. */
  await m.reload();
  await m.waitForTimeout(4000);
  ck('AL RECARGAR SIGUE EN SILENCIO', await m.evaluate(() => window.avisoChat.silenciado()));
  ck('y el botón se pinta callado', await m.evaluate(() =>
     document.getElementById('btnSonido').classList.contains('mudo')));

  await m.click('#btnSonido');
  await m.waitForTimeout(300);
  ck('y se puede volver a activar', await m.evaluate(() => !window.avisoChat.silenciado()));

  /* Callado no suena, ni por un mensaje que llega. Se comprueba contando las
     veces que sonar() devuelve true, que es lo único observable sin oírlo. */
  ck('callado no suena', await m.evaluate(() => {
    window.avisoChat.silenciar(true);
    const r = window.avisoChat.sonar();
    window.avisoChat.silenciar(false);
    return r === false;
  }));

  // ── En el ordenador sigue bien ───────────────────────────────────────────
  const ctxD = await b.newContext({ viewport: { width: 1400, height: 900 } }); await rutear(ctxD);
  const d = await ctxD.newPage(); d.on('pageerror', e => errs.push(String(e)));
  await d.goto(FRONT + '/chat.html');
  await d.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '5');
                          localStorage.removeItem('org_context'); }, lgc.data.token);
  await d.goto(FRONT + '/chat.html');
  await d.waitForTimeout(5000);
  await d.locator('.conv-item, .conv-row').first().click().catch(() => {});
  await d.waitForTimeout(2500);
  ck('el chat del coach sigue teniendo su barra de enviar',
     await d.locator('.send-bar').isVisible());
  ck('y su botón de silencio', await d.locator('#btnSonido').isVisible());
  ck('la barra de enviar cabe en la pantalla', await d.evaluate(() => {
    const s = document.querySelector('.send-bar');
    if (!s) return false;
    const r = s.getBoundingClientRect();
    return r.bottom <= window.innerHeight + 1;
  }));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
