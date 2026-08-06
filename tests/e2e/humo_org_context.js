/* El selector de contexto contra la app real: que la cabecera llegue al
   backend y de verdad cambie lo que se ve. */
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

(async () => {
  const b = await chromium.launch(); const ctx = await b.newContext();
  await ctx.route(u => u.href.startsWith(PROD), async route => {
    const req = route.request(); const url = req.url().replace(PROD, API);
    try {
      const res = await ctx.request.fetch(url, { method: req.method(), headers: req.headers(), data: req.postData() || undefined, maxRedirects: 0, timeout: 20000 });
      const h = { ...res.headers() }; delete h['content-encoding']; delete h['content-length'];
      await route.fulfill({ status: res.status(), headers: h, body: await res.body() });
    } catch (e) { await route.abort(); }
  });
  const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(String(e)));
  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 220))); if (!c) f++; };

  const SUF = String(Date.now()).slice(-6);
  const lg = await (await ctx.request.post(`${API}/api/auth/login`, { data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const token = lg.data.token, roleId = String(lg.data.user.role_id);
  const H = { Authorization: 'Bearer ' + token };
  const post = async (path, data) => (await ctx.request.post(`${API}/api${path}`, { data, headers: H })).json();

  // Dos organizaciones, cada una con su dieta privada
  const mk = async (sufijo) => {
    const u = await post('/users', { name: 'Dueño ' + sufijo, email: `duenio.${sufijo}.${SUF}@nutrientrena-qa.com`, password: 'Duenio123!', role_id: 2 });
    return u;
  };
  await mk('a'); await mk('b');
  const orgs = [];
  for (const s of ['a', 'b']) {
    const o = await post('/organizations', { name: `Organización ${s.toUpperCase()} ${SUF}` });
    orgs.push(o.data);
  }
  ck('dos organizaciones creadas', orgs.length === 2 && orgs.every(o => o && o.id), orgs);

  await p.goto(FRONT + '/diets.html');
  await p.evaluate(([t, r]) => { localStorage.setItem('token', t); localStorage.setItem('role_id', r); }, [token, roleId]);
  await p.goto(FRONT + '/diets.html');
  await p.waitForTimeout(2500);

  ck('el selector aparece en la app real', await p.locator('#orgCtxSel').count() === 1);
  const ops = await p.locator('#orgCtxSel option').allTextContents();
  ck('lista plataforma + las organizaciones', ops[0] === 'Plataforma (todo)' && ops.length >= 3, ops);

  // Como plataforma, crear una dieta -> queda global
  const d1 = await post('/diets', { title: `Dieta plataforma ${SUF}` });
  ck('dieta creada como plataforma es global', d1.data.organization_id === null, d1.data.organization_id);

  // Cambiar de sombrero desde el selector y crear otra
  await p.selectOption('#orgCtxSel', orgs[0].id);
  await p.waitForTimeout(2500);   // recarga
  ck('tras cambiar, el selector conserva la organización', await p.inputValue('#orgCtxSel') === orgs[0].id);

  const creada = await p.evaluate(async (t) => {
    const r = await fetch('https://nutrientrena-production.up.railway.app/api/diets',
      { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + t }, body: JSON.stringify({ title: 'Dieta con sombrero puesto' }) });
    return (await r.json()).data;
  }, token);
  ck('LA CABECERA LLEGA: lo creado queda en la organización elegida',
     creada && creada.organization_id === orgs[0].id, { esperado: orgs[0].id, obtenido: creada && creada.organization_id });

  // Y la facturación cambia de alcance
  const fact = await p.evaluate(async (t) => {
    const r = await fetch('https://nutrientrena-production.up.railway.app/api/billing/summary', { headers: { Authorization: 'Bearer ' + t } });
    return (await r.json()).data;
  }, token);
  ck('la facturación pasa a ser de esa organización',
     fact && fact.alcance === 'organizacion' && fact.organization_id === orgs[0].id, fact);

  // Volver a plataforma
  await p.selectOption('#orgCtxSel', '');
  await p.waitForTimeout(2500);
  const fact2 = await p.evaluate(async (t) => {
    const r = await fetch('https://nutrientrena-production.up.railway.app/api/billing/summary', { headers: { Authorization: 'Bearer ' + t } });
    return (await r.json()).data;
  }, token);
  ck('al volver a plataforma, alcance global otra vez', fact2 && fact2.alcance === 'plataforma', fact2);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
