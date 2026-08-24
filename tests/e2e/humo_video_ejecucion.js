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

  // Datos de prueba: seed_video.py deja un coach, un cliente y una rutina de
  // hoy con un ejercicio que lleva vídeo de YouTube.
  const datos = JSON.parse(process.env.DATOS_VIDEO || '{}');
  if (!datos.cli_email) { console.log('FALLO falta DATOS_VIDEO en el entorno'); process.exit(1); }

  const lgcli = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: datos.cli_email, password: 'Cliente123!' } })).json();
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

  ck('AL FINAL NO QUEDA NINGUNA PESTAÑA CON UN DESTINO', pestañasConDestino() === 0, pestañasConDestino());
  ck('(informativo) pestañas about:blank que el propio YouTube abrió y no cuentan',
     true, ctx.pages().length - 1);
  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
