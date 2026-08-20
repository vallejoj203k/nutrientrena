/* Grupos de chat, contra la aplicación de verdad.

   Dos maneras de montar un grupo, y no son lo mismo:

     · Por ROL ("mis clientes", "mis coaches"): la lista la resuelve el
       servidor cada vez, así que un cliente nuevo entra solo. Es de DIFUSIÓN:
       escribe quien lo creó y los demás responden en privado, porque un
       mensaje a todos los clientes no es una tertulia entre desconocidos.
     · A MEDIDA: eliges las personas y ahí habla todo el mundo, como WhatsApp.

   Lo que se comprueba aquí y no se puede comprobar por API: que el cliente
   NO tenga cuadro de escribir en un grupo de difusión, que se le ofrezca el
   camino privado, y que la lista de contactos para armar un grupo salga
   agrupada por rol. */
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

const rutear = ctx => ctx.route(u => u.href.startsWith(PROD), async route => {
  const q = route.request(); const url = q.url().replace(PROD, API);
  try {
    const res = await ctx.request.fetch(url, { method: q.method(), headers: q.headers(), data: q.postData() || undefined, maxRedirects: 0, timeout: 20000 });
    const h = { ...res.headers() }; delete h['content-encoding']; delete h['content-length'];
    await route.fulfill({ status: res.status(), headers: h, body: await res.body() });
  } catch (e) { await route.abort(); }
});

(async () => {
  const b = await chromium.launch();
  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 220))); if (!c) f++; };
  const SUF = String(Date.now()).slice(-6);

  // ── Un centro con su coach y dos clientes suyos ──────────────────────────
  let ctx = await b.newContext({ viewport: { width: 1400, height: 900 } }); await rutear(ctx);
  const errs = [];
  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };
  const org = await (await ctx.request.post(`${API}/api/admin/organizations`, { headers: H, data: {
    name: `Centro Chat ${SUF}`, owner_name: 'Coach Chat',
    owner_email: `coach.chat.${SUF}@nutrientrena-qa.com`, owner_password: 'Coach123!' } })).json();
  ck('centro de prueba creado', !!org.data?.id, org);
  const lgc = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `coach.chat.${SUF}@nutrientrena-qa.com`, password: 'Coach123!' } })).json();
  const Hc = { Authorization: 'Bearer ' + lgc.data.token, 'Content-Type': 'application/json' };
  for (const n of [1, 2]) {
    await ctx.request.post(`${API}/api/users`, { headers: Hc, data: {
      name: `Cliente ${n}`, email: `cli${n}.chat.${SUF}@nutrientrena-qa.com`,
      password: 'Cliente123!', role_id: 6 } });
  }

  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(String(e)));
  await p.goto(FRONT + '/chat.html');
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '2');
                          localStorage.removeItem('org_context'); }, lgc.data.token);
  await p.goto(FRONT + '/chat.html');
  await p.locator('#btnGrp').waitFor({ state: 'visible', timeout: 25000 });
  await p.waitForTimeout(1200);

  // ── El panel de grupo ────────────────────────────────────────────────────
  await p.click('#btnGrp');
  await p.locator('.grp-modo').first().waitFor({ state: 'visible', timeout: 15000 });
  await p.waitForTimeout(1200);
  ck('hay dos maneras de montar un grupo',
     JSON.stringify(await p.locator('.grp-modo').allTextContents()) === '["Por rol","A medida"]',
     await p.locator('.grp-modo').allTextContents());
  const ops = await p.locator('.target-opt').allTextContents();
  ck('se ofrece "Mis clientes" porque los tiene', ops.some(t => t.includes('Mis clientes')), ops);
  ck('y NO "Mis coaches", porque no tiene equipo todavía',
     !ops.some(t => t.includes('Mis coaches')), ops);

  // ── Grupo por rol: difusión ──────────────────────────────────────────────
  await p.click('.target-opt:has-text("Mis clientes")');
  await p.fill('#grpName', 'Avisos del centro');
  await p.click('.btn-start:has-text("Crear grupo")');
  await p.waitForTimeout(2500);
  ck('el grupo se crea con sus dos clientes y el coach',
     (await p.textContent('#msgHeaderSub')).includes('3 participantes'),
     await p.textContent('#msgHeaderSub'));

  // El globo de ayuda se sentaba encima del botón de enviar: al pulsar
  // "enviar" se abría la ayuda.
  ck('el globo de ayuda no tapa el botón de enviar', await p.evaluate(() => {
    const bt = document.querySelector('.send-btn');
    const r = bt.getBoundingClientRect();
    const encima = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return !!encima && encima.closest('.send-btn') !== null;
  }));

  await p.fill('#sendInput', 'Mañana cerramos a las 20h');
  await p.press('#sendInput', 'Enter');
  await p.waitForTimeout(2000);

  // ── Grupo a medida ───────────────────────────────────────────────────────
  await p.click('#btnGrp');
  await p.waitForTimeout(500);
  await p.click('#modoMano');
  await p.locator('.grp-contacto').first().waitFor({ state: 'visible', timeout: 15000 });
  ck('los contactos salen agrupados por rol',
     (await p.locator('.grp-grupo-rol').allTextContents()).includes('Tus clientes'),
     await p.locator('.grp-grupo-rol').allTextContents());
  await p.locator('.grp-contacto input').first().check();
  await p.fill('#grpName', 'Reto de verano');
  await p.click('.btn-start:has-text("Crear grupo")');
  await p.waitForTimeout(2500);
  ck('un grupo a medida se crea con quien elijas',
     (await p.textContent('#msgHeaderName')) === 'Reto de verano' &&
     (await p.textContent('#msgHeaderSub')).includes('2 participantes'),
     await p.textContent('#msgHeaderSub'));
  await ctx.close();

  // ── Lo que ve el CLIENTE ─────────────────────────────────────────────────
  ctx = await b.newContext({ viewport: { width: 1400, height: 900 } }); await rutear(ctx);
  const lgcli = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `cli1.chat.${SUF}@nutrientrena-qa.com`, password: 'Cliente123!' } })).json();
  const p2 = await ctx.newPage(); p2.on('pageerror', e => errs.push(String(e)));
  await p2.goto(FRONT + '/chat.html');
  await p2.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '6'); }, lgcli.data.token);
  await p2.goto(FRONT + '/chat.html');
  await p2.locator('.conv-item, .conv-row').first().waitFor({ state: 'visible', timeout: 25000 });
  await p2.locator('.conv-item, .conv-row').filter({ hasText: 'Avisos del centro' }).first().click();
  await p2.waitForTimeout(2000);

  ck('al cliente le llega el aviso', (await p2.textContent('#msgBody')).includes('Mañana cerramos'));
  ck('NO PUEDE ESCRIBIR en un grupo de difusión',
     !(await p2.locator('.send-bar').isVisible()));
  ck('y se le ofrece responder en privado',
     (await p2.locator('.aviso-difusion button').textContent()).includes('privado'));
  ck('no se le dice cuánta gente hay ni quién',
     (await p2.textContent('#msgHeaderSub')) === 'Mensaje de tu coach',
     await p2.textContent('#msgHeaderSub'));

  await p2.click('.aviso-difusion button');
  await p2.waitForTimeout(2500);
  ck('el botón le abre el chat privado con su coach',
     (await p2.textContent('#msgHeaderSub')) !== 'Mensaje de tu coach' &&
     await p2.locator('.send-bar').isVisible(),
     await p2.textContent('#msgHeaderSub'));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
