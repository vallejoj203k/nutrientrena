/* Otros nombres (sinónimos) de un ejercicio, por el camino real.

   El mismo ejercicio se llama de varias formas: "Press de banca", "bench
   press", "press banca plano". El catálogo solo guardaba uno, así que quien
   buscaba por cualquiera de los otros no encontraba nada — y lo que se hace
   entonces es crearlo otra vez. Así es como un catálogo común acaba con el
   mismo ejercicio tres veces.

   Las pruebas de `tests/` cubren el servidor y las de `tests/frontend/` el
   filtro del selector. Lo que ninguna de las dos ve es si la caja de texto de
   la pantalla llega hasta la base de datos: un `id` mal escrito en el HTML
   pasa las dos y deja el campo sin guardar nada. Eso es lo que se conduce
   aquí, con un navegador de verdad:

     1. Se escriben los sinónimos en el formulario y se pulsa Crear.
     2. Se recarga la página y se busca por uno de ellos.
     3. Se abre a editar y siguen ahí. */
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1400, height: 950 } });
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

  const SUF = String(Date.now()).slice(-6);
  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  if (!adm.data) { console.log('FALLO no se pudo entrar como admin', adm); process.exit(1); }

  const p = await ctx.newPage();
  p.on('pageerror', e => errs.push(String(e)));
  await p.goto(`${FRONT}/ejercicios.html`);
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '1'); }, adm.data.token);
  await p.goto(`${FRONT}/ejercicios.html`);
  await p.waitForTimeout(1200);

  // ── 1. El campo existe y se rellena ───────────────────────────────────────
  await p.evaluate(() => openExerciseModal());
  await p.waitForTimeout(800);
  ck('el formulario tiene la caja de otros nombres', await p.locator('#ex_aliases').count() === 1);
  ck('lleva la ayuda que explica para qué sirve',
    (await p.locator('#ex_aliases').locator('xpath=following-sibling::div[1]').textContent() || '').includes('buscador'));

  const NOMBRE = `Press de banca ${SUF}`;
  await p.fill('#ex_name', NOMBRE);
  await p.fill('#ex_aliases', 'Bench press, Press banca plano');
  // El grupo muscular principal está marcado como obligatorio en la pantalla.
  await p.evaluate(() => { const s = document.getElementById('ex_mg'); if (s.options.length > 1) s.value = s.options[1].value; });
  await p.click('#xfSaveBtn');
  await p.waitForTimeout(1500);

  // ── 2. Se ha guardado de verdad, no solo pintado ──────────────────────────
  const H = { Authorization: 'Bearer ' + adm.data.token };
  const porSinonimo = await (await ctx.request.get(
    `${API}/api/trainings/search?search=Bench%20press&per_page=100`, { headers: H })).json();
  const hallados = (porSinonimo.data.data || []).filter(t => t.name === NOMBRE);
  ck('se encuentra por el sinónimo', hallados.length === 1, (porSinonimo.data.data || []).map(t => t.name));
  ck('se llama como se llamaba: el sinónimo no le cambia el nombre',
    hallados[0] && hallados[0].name === NOMBRE, hallados[0]);
  ck('los sinónimos han llegado a la base de datos',
    hallados[0] && hallados[0].aliases === 'Bench press, Press banca plano', hallados[0] && hallados[0].aliases);

  // ── 3. Vuelven al formulario al editar ────────────────────────────────────
  const id = hallados[0] && hallados[0].id;
  if (id) {
    await p.evaluate(i => openExerciseModal(i), id);
    await p.waitForTimeout(1200);
    ck('al editar, los sinónimos están escritos',
      (await p.inputValue('#ex_aliases')) === 'Bench press, Press banca plano',
      await p.inputValue('#ex_aliases'));

    // Y se pueden quitar: un campo que se escribe pero no se vacía está a medias.
    await p.fill('#ex_aliases', '');
    await p.click('#xfSaveBtn');
    await p.waitForTimeout(1500);
    const tras = await (await ctx.request.get(
      `${API}/api/trainings/search?search=Bench%20press&per_page=100`, { headers: H })).json();
    ck('se pueden quitar', !(tras.data.data || []).some(t => t.name === NOMBRE),
      (tras.data.data || []).map(t => t.name));
  }

  // ── 4. Y el formulario en blanco no arrastra lo del anterior ──────────────
  await p.evaluate(() => closeExerciseModal());
  await p.evaluate(() => openExerciseModal());
  await p.waitForTimeout(800);
  ck('un ejercicio nuevo abre con la caja vacía', (await p.inputValue('#ex_aliases')) === '',
    await p.inputValue('#ex_aliases'));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
