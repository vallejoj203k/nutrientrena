/* El vídeo de ejecución se abre DENTRO de la app, nunca en una pestaña nueva.

   Lo que pasaba: al pulsar la miniatura de un ejercicio mientras se está
   entrenando, se abría una pestaña nueva del navegador con el vídeo. En un
   móvil eso saca al cliente de la aplicación a mitad de una serie.

   El botón vivía en dos sitios y cada uno se comportaba distinto:
     · El plan del día (antes de empezar): ya reproducía "inline", pero dentro
       de su propia tarjeta de 360px.
     · La sesión en curso (la de la captura): usaba un <a target="_blank">
       liso — pestaña nueva siempre, incluso para un vídeo de YouTube que se
       podía incrustar perfectamente.

   Ahora los dos abren el mismo modal por encima de la pantalla, así que ver la
   ejecución no interrumpe el entrenamiento. */
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
  const errs = [];
  const pestañasAbiertas = [];
  /* El propio reproductor incrustado de YouTube abre por su cuenta una
     pestaña "about:blank" — verificado: nuestro código nunca llama a
     window.open() en este camino, así que solo puede venir de su script. Un
     navegador normal, con el bloqueo de popups activado por defecto, ni la
     deja aparecer. Lo que de verdad importaría —salir de la app— sería que se
     abriera una pestaña con un DESTINO, así que se cuentan solo esas. */
  ctx.on('page', pg => pestañasAbiertas.push(pg));
  function pestañasConDestino(){
    return ctx.pages().filter(pg => pg.url() && pg.url() !== 'about:blank').length - 1; // -1: la propia app
  }

  /* Se monta todo por API: un centro, su coach, un cliente, un ejercicio con
     vídeo y una rutina asignada cuyo día de HOY lo lleva. Antes esto venía de
     un script suelto y una variable de entorno, así que la prueba no se podía
     lanzar sola — y una prueba que no se puede lanzar no protege nada. */
  const SUF = String(Date.now()).slice(-6);
  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };
  await ctx.request.post(`${API}/api/admin/organizations`, { headers: H, data: {
    name: `Centro Vid ${SUF}`, owner_name: 'Coach Vid',
    owner_email: `coach.vid.${SUF}@nutrientrena-qa.com`, owner_password: 'Coach123!' } });
  const lgc = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `coach.vid.${SUF}@nutrientrena-qa.com`, password: 'Coach123!' } })).json();
  const Hc = { Authorization: 'Bearer ' + lgc.data.token, 'Content-Type': 'application/json' };
  const cli = await (await ctx.request.post(`${API}/api/users`, { headers: Hc, data: {
    name: 'Cliente Vid', email: `cli.vid.${SUF}@nutrientrena-qa.com`,
    password: 'Cliente123!', role_id: 6 } })).json();
  /* Varios ejercicios, no uno: el plan del día tiene que ser más alto que la
     pantalla para poder comprobar que el fondo NO se desplaza con el vídeo
     abierto. Con uno solo no hay nada que desplazar y la comprobación de
     control no probaría nada. */
  const ejercicios = [];
  for (let i = 0; i < 5; i++) {
    const t = await (await ctx.request.post(`${API}/api/trainings`, { headers: Hc, data: {
      name: `Ejercicio ${i + 1} ${SUF}`,
      video_url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' } })).json();
    ejercicios.push(t.data);
  }
  const ej = { data: ejercicios[0] };
  ck('montado: cliente y ejercicios con vídeo',
     !!cli.data?.id && ejercicios.length === 5 && ejercicios.every(x => !!x?.id),
     { cli, ejercicios: ejercicios.length });

  /* La pantalla del cliente busca el día de la rutina por índice de día de la
     semana (lunes = 0), así que hacen falta tantos días como haga falta para
     que HOY caiga en el último, que es el que lleva el ejercicio. */
  const hoyIdx = (new Date().getDay() + 6) % 7;
  const dias = [];
  for (let i = 0; i <= hoyIdx; i++) {
    dias.push({ day_name: `Día ${i + 1}`,
      blocks: i === hoyIdx ? [{ block_type: 'normal', order_index: 0,
        exercises: ejercicios.map((t, n) => (
          { training_id: t.id, series: 3, repetitions: '8', break_time: 60, order_index: n })) }] : [] });
  }
  const rut = await (await ctx.request.post(`${API}/api/routines`, { headers: Hc, data: {
    name: `Rutina Vid ${SUF}`, days: 7, days_list: dias } })).json();
  const asignada = await (await ctx.request.post(`${API}/api/routines/${rut.data.id}/clone-to-client`, {
    headers: Hc, data: { name: rut.data.name, client_id: cli.data.id } })).json();
  ck('y la rutina asignada al cliente, con el ejercicio en el día de hoy',
     !!asignada.data?.id, asignada);

  const lgcli = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `cli.vid.${SUF}@nutrientrena-qa.com`, password: 'Cliente123!' } })).json();
  if (!lgcli.data) { console.log('FALLO no se pudo entrar como el cliente de prueba', lgcli); process.exit(1); }

  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(String(e)));
  await p.goto(FRONT + '/client-entrena.html');
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '6'); }, lgcli.data.token);
  await p.goto(FRONT + '/client-entrena.html');
  await p.waitForTimeout(4000);

  // ── Desde el plan del día, antes de empezar ──────────────────────────────
  const media = p.locator('.ex-media').first();
  await media.waitFor({ state: 'visible', timeout: 20000 });
  await media.click();
  await p.waitForTimeout(2000);
  await p.waitForTimeout(600);
  ck('DESDE EL PLAN DEL DÍA: se abre el modal, no una pestaña con destino',
     await p.locator('#vidModal.open').isVisible() && pestañasConDestino() === 0,
     { modalAbierto: await p.locator('#vidModal.open').count(), pestañasConDestino: pestañasConDestino() });
  ck('con un reproductor dentro', (await p.locator('#vidFrame iframe').count()) === 1);
  await p.click('.vid-close');
  await p.waitForTimeout(500);
  ck('y se cierra', !(await p.locator('#vidModal.open').count()));
  ck('vaciando el reproductor, para que no siga sonando de fondo',
     (await p.locator('#vidFrame iframe').count()) === 0);

  // ── Empezar el entrenamiento: la pantalla de la captura ──────────────────
  await p.click('.start-btn');
  await p.locator('#wsOverlay.open').waitFor({ state: 'visible', timeout: 15000 });
  await p.waitForTimeout(1500);

  const thumb = p.locator('.ws-thumb').first();
  await thumb.waitFor({ state: 'visible', timeout: 20000 });
  ck('LA MINIATURA DE LA SESIÓN EN CURSO YA NO ES UN ENLACE',
     (await thumb.evaluate(el => el.tagName)) === 'DIV',
     await thumb.evaluate(el => el.outerHTML.slice(0, 90)));

  await thumb.click();
  await p.waitForTimeout(2000);
  await p.waitForTimeout(600);
  ck('SE ABRE EL MISMO MODAL DESDE LA SESIÓN EN CURSO, SIN SALIR DE LA APP',
     await p.locator('#vidModal.open').isVisible() && pestañasConDestino() === 0,
     { modalAbierto: await p.locator('#vidModal.open').count(), pestañasConDestino: pestañasConDestino() });
  ck('y la sesión sigue detrás, sin perderse',
     await p.locator('#wsOverlay.open').isVisible());

  // Se puede cerrar con Escape, no solo con el botón.
  await p.keyboard.press('Escape');
  await p.waitForTimeout(500);
  ck('Escape también cierra el vídeo', !(await p.locator('#vidModal.open').count()));

  // Y tocar fuera del recuadro también cierra.
  await thumb.click();
  await p.waitForTimeout(1000);
  await p.mouse.click(20, 20);
  await p.waitForTimeout(500);
  ck('tocar fuera del vídeo también lo cierra', !(await p.locator('#vidModal.open').count()));

  /* ── Con el teclado ────────────────────────────────────────────────────
     La miniatura de la sesión era un <a>, que traía esto de fábrica; al
     convertirla en <div role=button> para abrir el modal se perdió sin
     querer y dejó de ser alcanzable con el tabulador. */
  ck('la miniatura de la sesión se alcanza con el tabulador',
     await p.evaluate(() => document.querySelector('.ws-thumb[role=button]').tabIndex >= 0));
  await p.evaluate(() => document.querySelector('.ws-thumb[role=button]').focus());
  await p.keyboard.press('Enter');
  await p.waitForTimeout(1800);
  ck('Y SE ABRE CON ENTER', await p.locator('#vidModal.open').isVisible());
  await p.keyboard.press('Escape');
  await p.waitForTimeout(400);

  /* ── Sobre el bloqueo del fondo, y por qué NO se comprueba aquí ────────
     El modal lleva un bloqueo de scroll del fondo. No hay comprobación de
     ello en esta prueba, y conviene decir por qué en vez de dejar un verde
     que no significa nada:

     el modal es hermano de `.main`, no descendiente de `.content`, así que
     una rueda sobre el fondo oscuro nunca llega a `.content` — con bloqueo o
     sin él. Lo comprobé quitando el bloqueo a propósito: la prueba seguía en
     verde, o sea que no distinguía nada.

     El bloqueo se deja puesto porque en iOS Safari el gesto SÍ puede arrastrar
     la página de detrás de una capa fija (el mismo tipo de diferencia que hizo
     falta para el `100dvh` del chat), y eso no se puede reproducir en este
     navegador. Es una precaución para iOS, no algo verificado aquí.
  */

  ck('AL FINAL NO QUEDA NINGUNA PESTAÑA CON UN DESTINO', pestañasConDestino() === 0, pestañasConDestino());
  ck('(informativo) pestañas about:blank que el propio YouTube abrió y no cuentan',
     true, ctx.pages().length - 1);
  /* ── El botón de cerrar, en apaisado corto ──────────────────────────────
     Estaba colocado 42px POR ENCIMA del vídeo. Con el móvil en horizontal el
     vídeo queda casi pegado al borde de arriba y el botón se salía de la
     pantalla: medido, en un 667x320 acababa en -28px. El cliente se quedaba
     sin forma visible de cerrarlo. */
  const apaisado = await b.newContext({ viewport: { width: 667, height: 320 }, isMobile: true, hasTouch: true });
  await apaisado.route(u => u.href.startsWith(PROD), async route => {
    const q = route.request();
    try {
      const res = await apaisado.request.fetch(q.url().replace(PROD, API), { method: q.method(), headers: q.headers(), data: q.postData() || undefined, maxRedirects: 0, timeout: 30000 });
      const h = { ...res.headers() }; delete h['content-encoding']; delete h['content-length'];
      await route.fulfill({ status: res.status(), headers: h, body: await res.body() });
    } catch (e) { await route.abort(); }
  });
  const pa = await apaisado.newPage(); pa.on('pageerror', e => errs.push(String(e)));
  await pa.goto(FRONT + '/client-entrena.html');
  await pa.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '6'); }, lgcli.data.token);
  await pa.goto(FRONT + '/client-entrena.html');
  await pa.waitForTimeout(3500);
  await pa.locator('.ex-media').first().click();
  await pa.waitForTimeout(1800);
  const sitioCierre = await pa.evaluate(() => {
    const r = document.querySelector('.vid-close').getBoundingClientRect();
    const encima = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return { top: Math.round(r.top),
             dentro: r.top >= 0 && r.bottom <= window.innerHeight,
             pulsable: !!encima && !!encima.closest('.vid-close') };
  });
  ck('EN APAISADO CORTO EL BOTÓN DE CERRAR SIGUE EN PANTALLA Y SE PUEDE PULSAR',
     sitioCierre.dentro && sitioCierre.pulsable, sitioCierre);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
