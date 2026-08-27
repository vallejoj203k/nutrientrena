/* La ejecución de un ejercicio, en la página de verdad.

   El banco de pruebas de `tests/frontend/` incrusta el módulo dentro del
   harness, así que pasa aunque la página real no lo cargue. Esa diferencia ya
   ha roto CI una vez: el harness en verde y la página con un "is undefined".

   Aquí se abre `ejercicios.html` de verdad, con su `<script src>`, y se mira
   lo que ve el coach al pulsar un ejercicio. */
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

const DESC = [
  '1. Siéntate con la espalda apoyada y las almohadillas en la cara interna de los muslos.',
  '2. Cierra las piernas juntando los muslos contra la resistencia.',
  '3. Aprieta al final del recorrido.',
  '4. Abre controlado sin dejar caer el peso. Repite.',
  '',
  '⚠ Errores comunes',
  '',
  '- Abrir demasiado al inicio y forzar la ingle.',
  '- Usar impulso.',
].join('\n');

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

  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 300))); if (!c) f++; };
  const errs = [];

  const SUF = String(Date.now()).slice(-6);
  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  if (!adm.data) { console.log('FALLO no se pudo entrar como admin', adm); process.exit(1); }
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };

  const creado = await (await ctx.request.post(`${API}/api/trainings`, { headers: H, data: {
    name: `Aducción de cadera ${SUF}`, description: DESC } })).json();
  const id = creado.data.id;

  const p = await ctx.newPage();
  p.on('pageerror', e => errs.push(String(e)));
  await p.goto(`${FRONT}/ejercicios.html`);
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '1'); }, adm.data.token);
  await p.goto(`${FRONT}/ejercicios.html`);
  await p.waitForTimeout(1200);

  // Lo que rompió CI la otra vez: el módulo no cargado en la página real.
  ck('la página carga el módulo de pasos',
    await p.evaluate(() => typeof pasosDeEjecucion) === 'function',
    await p.evaluate(() => typeof pasosDeEjecucion));

  await p.evaluate(i => openExerciseView(i), id);
  await p.waitForTimeout(1200);

  const pasos = await p.$$eval('#xvBody .xv-step', ns => ns.map(n => n.textContent.trim()));
  const nums = await p.$$eval('#xvBody .xv-step-num', ns => ns.map(n => n.textContent.trim()));
  const vin = await p.$$eval('#xvBody .xv-bullet', ns => ns.map(n => n.textContent.trim()));
  const tit = await p.$$eval('#xvBody .xv-step-title', ns => ns.map(n => n.textContent.trim()));

  ck('4 pasos, no 7', pasos.length === 4, pasos);
  ck('numerados 1 2 3 4', JSON.stringify(nums) === '["1.","2.","3.","4."]', nums);
  ck('NO SALE EL NUMERO DOS VECES', !pasos.some(s => /^\d+\.\s*\d+\./.test(s)), pasos);
  ck('"Errores comunes" sale como título', tit.length === 1 && tit[0].includes('Errores comunes'), tit);
  ck('las viñetas salen como viñetas', vin.length === 2, vin);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
