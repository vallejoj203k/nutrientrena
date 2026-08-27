/* La lista de la compra del cliente.

   El botón "Lista" del plan nutricional no hacía nada: mostraba un aviso de
   "disponible próximamente". Ahora abre la compra del día o de la semana,
   agrupada por categoría del catálogo y con las cantidades sumadas.

   El banco de `tests/frontend/` mide las cuentas con datos inventados. Lo que
   solo se ve aquí es si el camino entero se sostiene: que la API mande la
   categoría, que la página cargue el módulo —un `<script src>` olvidado ya ha
   roto CI una vez— y que lo que se pinta sea lo que se calculó. */
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

  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 320))); if (!c) f++; };
  const errs = [];

  const SUF = String(Date.now()).slice(-6);
  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  if (!adm.data) { console.log('FALLO no se pudo entrar como admin', adm); process.exit(1); }
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };

  // Un centro, su coach y un cliente suyo.
  await ctx.request.post(`${API}/api/admin/organizations`, { headers: H, data: {
    name: `Centro Lista ${SUF}`, owner_name: 'Coach Lista',
    owner_email: `coach.lista.${SUF}@nutrientrena-qa.com`, owner_password: 'Coach123!' } });
  const lgc = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `coach.lista.${SUF}@nutrientrena-qa.com`, password: 'Coach123!' } })).json();
  const Hc = { Authorization: 'Bearer ' + lgc.data.token, 'Content-Type': 'application/json' };
  const cli = await (await ctx.request.post(`${API}/api/users`, { headers: Hc, data: {
    name: 'Cliente Lista', email: `cli.lista.${SUF}@nutrientrena-qa.com`,
    password: 'Cliente123!', role_id: 6 } })).json();

  // Dos alimentos del catálogo, cada uno con su categoría.
  const cat = async nombre => (await (await ctx.request.post(`${API}/api/groupFood`, {
    headers: Hc, data: { name: nombre } })).json());
  const gAves = await cat(`Aves ${SUF}`);
  const gFrutas = await cat(`Frutas ${SUF}`);
  const idAves = (gAves.data && gAves.data.id) || null;
  const idFrutas = (gFrutas.data && gFrutas.data.id) || null;
  // Sin categorías no hay nada que agrupar: mejor parar aquí que ver "Otros" y
  // creer que el fallo está en la lista.
  ck('las categorías se han creado', !!idAves && !!idFrutas, { idAves, idFrutas });

  const alim = async (nombre, gid, unidad) => (await (await ctx.request.post(`${API}/api/aliments`, {
    headers: Hc, data: { name: nombre, group_food_id: gid, calories: 100,
                         quantity: 100, quantity_unit: unidad } })).json()).data.id;
  const pollo = await alim(`Pechuga de pollo ${SUF}`, idAves, 'g');
  const manzana = await alim(`Manzana ${SUF}`, idFrutas, 'ud');

  // Una dieta con el pollo en DOS comidas: la lista tiene que juntarlo.
  const dieta = await (await ctx.request.post(`${API}/api/diets`, {
    headers: Hc, data: { title: `Plan ${SUF}` } })).json();
  const did = dieta.data.id;
  const upd = await ctx.request.put(`${API}/api/diets/${did}/update`, { headers: Hc, data: {
    id: did, title: `Plan ${SUF}`, foods: [
      { name: 'Desayuno', time: '08:00', detail: [
        { aliment_id: pollo, quantity_calc: 120, order: 0 },
        { aliment_id: manzana, quantity_calc: 1, order: 1 }] },
      { name: 'Cena', time: '21:00', detail: [
        { aliment_id: pollo, quantity_calc: 80, order: 0 }] },
    ] } });
  ck('la dieta se ha podido montar', upd.ok(), upd.status());
  await ctx.request.post(`${API}/api/diets/${did}/assign`, {
    headers: Hc, data: { client_id: cli.data.id } });

  // ── Como el cliente ──────────────────────────────────────────────────────
  const lgcli = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `cli.lista.${SUF}@nutrientrena-qa.com`, password: 'Cliente123!' } })).json();
  if (!lgcli.data) { console.log('FALLO no se pudo entrar como el cliente', lgcli); process.exit(1); }

  const p = await ctx.newPage();
  p.on('pageerror', e => errs.push(String(e)));
  await p.goto(`${FRONT}/client-nutricion.html`);
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '6'); }, lgcli.data.token);
  await p.goto(`${FRONT}/client-nutricion.html`);
  await p.waitForTimeout(2500);

  ck('la página carga el módulo de la lista',
    await p.evaluate(() => typeof (window.listaCompra || {}).listaDeCompra) === 'function');

  // El botón ya no es un "próximamente".
  ck('el botón "Lista" abre la lista, no un aviso',
    !(await p.getAttribute('#btnLista', 'onclick') || '').includes('soon()'),
    await p.getAttribute('#btnLista', 'onclick'));

  await p.click('#btnLista');
  await p.waitForTimeout(600);
  ck('la ventana se abre', await p.locator('#lcBack.open').count() === 1);

  const renglones = async () => p.$$eval('#lcBody .lc-item', ns => ns.map(n => ({
    nombre: n.querySelector('.lc-nm').textContent.trim(),
    cant: n.querySelector('.lc-qty').textContent.trim(),
  })));
  const cats = async () => p.$$eval('#lcBody .lc-cat', ns => ns.map(n => n.textContent.trim()));

  const dia = await renglones();
  ck('EL POLLO DE LAS DOS COMIDAS SALE EN UN SOLO RENGLÓN, SUMADO',
    dia.filter(r => r.nombre.startsWith('Pechuga')).length === 1
    && dia.find(r => r.nombre.startsWith('Pechuga')).cant === '200 g', dia);
  ck('la manzana sale en unidades', dia.find(r => r.nombre.startsWith('Manzana')).cant === '1 ud', dia);
  // Las mayúsculas del diseño las pone el CSS (`text-transform`), así que el
  // texto del nodo viene tal cual está en el catálogo.
  ck('agrupado por la categoría del catálogo',
    (await cats()).join() === `Aves ${SUF},Frutas ${SUF}`, await cats());

  // ── Marcar ───────────────────────────────────────────────────────────────
  ck('el contador empieza a cero',
    (await p.textContent('#lcSub')).includes('0/2 marcados'), await p.textContent('#lcSub'));
  await p.locator('#lcBody .lc-item').first().click();
  await p.waitForTimeout(300);
  ck('marcar cuenta', (await p.textContent('#lcSub')).includes('1/2 marcados'),
    await p.textContent('#lcSub'));
  await p.reload();
  await p.waitForTimeout(2500);
  await p.click('#btnLista');
  await p.waitForTimeout(600);
  ck('lo marcado se recuerda al recargar',
    (await p.textContent('#lcSub')).includes('1/2 marcados'), await p.textContent('#lcSub'));

  // ── La semana ────────────────────────────────────────────────────────────
  await p.click('#lcTabSemana');
  await p.waitForTimeout(400);
  const semana = await renglones();
  // La dieta suelta vale los siete días: 200 g × 7 = 1400 g = 1,4 kg.
  ck('LA SEMANA SUMA LOS SIETE DÍAS Y SE LEE EN KILOS',
    semana.find(r => r.nombre.startsWith('Pechuga')).cant === '1,4 kg', semana);
  ck('7 manzanas', semana.find(r => r.nombre.startsWith('Manzana')).cant === '7 ud', semana);
  ck('lo marcado del día no se arrastra a la semana',
    (await p.textContent('#lcSub')).includes('0/2 marcados'), await p.textContent('#lcSub'));

  // ── Descargar en los dos formatos ────────────────────────────────────────
  // Las pestañas ya eligen día o semana; estos botones eligen el FORMATO. El
  // PDF pasa por el servidor, así que aquí se ve algo que el banco de pruebas
  // no puede ver: que el endpoint exista, responda y devuelva un PDF.
  const bajar = async sel => {
    const [d] = await Promise.all([
      p.waitForEvent('download', { timeout: 20000 }),
      p.click(sel),
    ]);
    return d;
  };

  const png = await bajar('.lc-foot .lc-dl:not(.pri)');
  ck('la imagen se descarga como PNG de la semana',
    png.suggestedFilename() === 'lista-compra-semana.png', png.suggestedFilename());
  const rutaPng = await png.path();
  const bytesPng = require('fs').readFileSync(rutaPng);
  // Los ocho primeros bytes de todo PNG. Que el fichero exista no dice nada.
  ck('y es un PNG de verdad',
    bytesPng.slice(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])),
    bytesPng.slice(0, 8));
  ck('con contenido, no un lienzo en blanco de 100 bytes', bytesPng.length > 3000, bytesPng.length);

  const pdf = await bajar('#lcPdf');
  ck('el PDF se descarga', pdf.suggestedFilename() === 'lista-compra-semana.pdf',
    pdf.suggestedFilename());
  const bytesPdf = require('fs').readFileSync(await pdf.path());
  ck('y es un PDF de verdad', bytesPdf.slice(0, 4).toString() === '%PDF',
    bytesPdf.slice(0, 8).toString());
  ck('con la lista dentro, no una página en blanco', bytesPdf.length > 1500, bytesPdf.length);

  // Y el del día se llama distinto: si los dos salieran igual, uno pisaría al
  // otro en la carpeta de descargas.
  await p.click('#lcTabDia');
  await p.waitForTimeout(400);
  const pdfDia = await bajar('#lcPdf');
  ck('el del día se llama distinto que el de la semana',
    pdfDia.suggestedFilename() === 'lista-compra-dia.pdf', pdfDia.suggestedFilename());

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
