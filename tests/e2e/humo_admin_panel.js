/* El panel de plataforma contra la app real. */
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
  const token = lg.data.token, H = { Authorization: 'Bearer ' + token };
  const post = async (path, data) => (await ctx.request.post(`${API}/api${path}`, { data, headers: H })).json();

  await post('/users', { name: 'Dueño panel', email: `duenio.panel.${SUF}@nutrientrena-qa.com`, password: 'Duenio123!', role_id: 2 });
  const org = await post('/organizations', { name: `Centro Panel ${SUF}` });
  ck('organización de prueba creada', !!org.data?.id, org);

  // ── Super-admin
  await p.goto(FRONT + '/admin/index.html');
  await p.evaluate(t => localStorage.setItem('token', t), token);
  await p.goto(FRONT + '/admin/index.html');
  await p.waitForTimeout(1500);

  ck('el panel carga', await p.locator('#layout').isVisible());
  const secs = await p.locator('.s-item span').allTextContents();
  ck('las 10 secciones del documento', secs.length === 10, secs);
  ck('empieza en Visión general', (await p.textContent('#titulo')).trim() === 'Visión general');
  ck('la barra lateral usa la tinta oscura del documento',
     (await p.evaluate(() => getComputedStyle(document.querySelector('.side')).backgroundColor)) === 'rgb(16, 20, 30)');

  /* El selector va en la barra LATERAL, como el diseño que aprobó el cliente.
     El documento lo situaba en la barra superior; manda la captura. */
  ck('el selector de contexto está en la barra lateral', await p.evaluate(() => {
    const c = document.querySelector('.ctx-card');
    return !!c && c.closest('.side') !== null;
  }));
  const ops = await p.locator('#ctxSel option').allTextContents();
  ck('ofrece Plataforma Alzum y las organizaciones', ops[0] === 'Plataforma Alzum' && ops.length >= 2, ops);

  await p.click('.s-item:nth-child(6)');
  await p.waitForTimeout(200);
  ck('navegar entre secciones funciona', (await p.textContent('#titulo')).includes('Contenido'), await p.textContent('#titulo'));
  ck('los nombres del menú son los del diseño del cliente',
     secs[1] === 'Coaches' && secs[3] === 'Facturación' && secs[8] === 'Equipo Alzum', secs);
  ck('la sección queda marcada como activa', await p.locator('.s-item.active').count() === 1);

  // ── Clientes finales ─────────────────────────────────────────────────────
  // Una cuenta con su propio dueño y un cliente colgando de él: es lo que hace
  // que la atribución a la cuenta se pueda comprobar de verdad.
  const cuenta = await post('/admin/organizations', {
    name: `Centro Clientes ${SUF}`, state: 'activa',
    owner_name: 'Marta Coach', owner_email: `marta.cli.${SUF}@nutrientrena-qa.com`,
    owner_password: 'Centro123!' });
  ck('cuenta con dueño propio creada', !!cuenta.data?.id, cuenta);
  const cli = await post('/users', { name: 'Laura Gómez', email: `laura.cli.${SUF}@nutrientrena-qa.com`,
    password: 'Cliente123!', role_id: 6, instructor: cuenta.data.owner_user_detail_id });
  ck('cliente asignado a ese coach', !!cli.data, cli);

  await p.click('.s-item:nth-child(3)');
  await p.waitForTimeout(1800);
  ck('la sección Clientes finales carga', (await p.textContent('#titulo')).trim() === 'Clientes finales');
  const tc = await p.textContent('#contenido');
  ck('el cliente sale con su cuenta y su coach',
     tc.includes('Laura Gómez') && tc.includes(`Centro Clientes ${SUF}`) && tc.includes('Marta Coach'),
     tc.slice(0, 200));
  ck('se dice que es solo lectura', tc.includes('no se muestran medidas, fotos ni historial médico'));
  ck('sin actividad se dice, no se inventa una fecha', tc.includes('Sin actividad'));

  // Lo que NO puede salir: el panel de plataforma no enseña lo íntimo.
  const bruto = await p.evaluate(async () => {
    const r = await fetch('https://nutrientrena-production.up.railway.app/api/admin/clients',
      { headers: { Authorization: 'Bearer ' + localStorage.getItem('token') } });
    return JSON.stringify((await r.json()).data.clientes[0] || {});
  });
  ck('la API no manda peso, medidas ni fotos',
     !/weight|height|body_fat|photo|allergies|patholog/i.test(bruto), bruto.slice(0, 200));

  // Filtro por cuenta: lo que hace que el desplegable signifique algo
  await p.selectOption('#cuentaCli', cuenta.data.id);
  await p.waitForTimeout(400);
  const filas = await p.locator('#contenido tbody tr').count();
  ck('filtrar por cuenta deja solo sus clientes',
     filas >= 1 && (await p.textContent('#contenido')).includes('Laura Gómez'), { filas });
  await p.fill('#qc', 'zzz-no-existe');
  await p.waitForTimeout(400);
  ck('buscar algo que no está lo dice', (await p.textContent('#contenido')).includes('Ningún cliente con ese filtro'));
  await p.fill('#qc', '');
  await p.waitForTimeout(400);

  // ── Contenido global ─────────────────────────────────────────────────────
  // Contenido de fábrica (plataforma) y contenido privado de una cuenta: la
  // sección entera se apoya en que no se mezclen.
  const glob = await post('/trainings', { name: `Sentadilla de fábrica ${SUF}` });
  ck('ejercicio de plataforma creado', glob.data?.organization_id === null, glob.data);
  const lgd = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `marta.cli.${SUF}@nutrientrena-qa.com`, password: 'Centro123!' } })).json();
  const priv = await (await ctx.request.post(`${API}/api/trainings`, {
    data: { name: `Ejercicio privado ${SUF}` },
    headers: { Authorization: 'Bearer ' + lgd.data.token } })).json();
  ck('ejercicio privado de una cuenta creado', !!priv.data?.organization_id, priv.data);

  await p.click('.s-item:nth-child(6)');
  await p.waitForTimeout(1800);
  ck('la sección Contenido global carga', (await p.textContent('#titulo')).trim() === 'Contenido global');
  await p.click('.tipo:has-text("Ejercicios")');
  await p.waitForTimeout(900);
  const tg = await p.textContent('#contenido');
  ck('lo de plataforma sale en la lista global', tg.includes(`Sentadilla de fábrica ${SUF}`));
  ck('lo privado de una cuenta NO se cuela en la global', !tg.includes(`Ejercicio privado ${SUF}`), tg.slice(0, 200));

  await p.click('.fam:has-text("Contenido de organizaciones")');
  await p.waitForTimeout(1400);
  const to = await p.textContent('#contenido');
  ck('lo privado se lista aparte con su cuenta',
     to.includes(`Ejercicio privado ${SUF}`) && to.includes(`Centro Clientes ${SUF}`), to.slice(0, 220));

  // Promover: el punto de la sección. Es reversible y ya existía por API.
  p.on('dialog', d => d.accept());
  await p.click(`tr:has-text("Ejercicio privado ${SUF}") button:has-text("Subir a plataforma")`);
  await p.waitForTimeout(1500);
  const trasPromover = await (await ctx.request.get(`${API}/api/admin/content?tipo=trainings&q=${SUF}`, { headers: H })).json();
  ck('subir a plataforma lo pasa al catálogo común',
     (trasPromover.data.items || []).some(i => i.nombre === `Ejercicio privado ${SUF}`),
     (trasPromover.data.items || []).map(i => i.nombre));

  // Catálogos sin dueño: se crean y se renombran aquí, y en ningún otro sitio
  await p.click('.fam:has-text("Entrenamiento")');
  await p.waitForTimeout(1200);
  await p.click('.tipo:has-text("Grupos musculares")');
  await p.waitForTimeout(900);
  await p.click('button:has-text("+ Nuevo")');
  await p.waitForTimeout(400);
  ck('el alta de catálogo se abre', await p.locator('#capaCat.on').count() === 1);
  await p.fill('#catNombre', `Isquiotibiales ${SUF}`);
  await p.click('#catBtn');
  await p.waitForTimeout(1400);
  ck('la entrada de catálogo se crea', (await p.textContent('#contenido')).includes(`Isquiotibiales ${SUF}`));

  // Y no se borra si algo lo usa: rompería la librería de todas las cuentas
  const grupos = await (await ctx.request.get(`${API}/api/admin/content?tipo=muscle_groups&q=${SUF}`, { headers: H })).json();
  const gid = grupos.data.items[0].id;
  await post('/trainings', { name: `Ejercicio que usa el grupo ${SUF}`, muscle_group_id: Number(gid) });
  const negado = await ctx.request.fetch(`${API}/api/admin/content/muscle_groups/${gid}`, { method: 'DELETE', headers: H });
  ck('no se borra un catálogo en uso', negado.status() === 400, negado.status());

  // Lo que aún no tiene ámbito global se dice, no se finge
  await p.click('.fam:has-text("Formularios")');
  await p.waitForTimeout(600);
  ck('formularios avisa de que le falta el ámbito de organización',
     (await p.textContent('#contenido')).includes('todavía no tiene ámbito global'));
  ck('y las propuestas se marcan como pendientes, no como cero',
     (await p.textContent('#contenido')).includes('Todavía no existe el circuito de propuestas'));

  // Cambiar de contexto lleva al panel de coach
  await p.click('.s-item:nth-child(2)');
  await p.waitForTimeout(1200);
  const orgId = org.data.id;
  await p.selectOption('#ctxSel', orgId);
  await p.waitForTimeout(1500);
  ck('elegir una organización lleva al panel de coach', p.url().includes('dashboard.html'), p.url());
  ck('y deja puesto ese contexto', await p.evaluate(() => localStorage.getItem('org_context')) === orgId);

  // ── Un coach no entra
  const c = await post('/users', { name: 'Coach fuera', email: `coach.fuera.${SUF}@nutrientrena-qa.com`, password: 'Coach123!', role_id: 5 });
  const lg2 = await (await ctx.request.post(`${API}/api/auth/login`, { data: { email: `coach.fuera.${SUF}@nutrientrena-qa.com`, password: 'Coach123!' } })).json();
  const p2 = await ctx.newPage();
  await p2.goto(FRONT + '/admin/index.html');
  await p2.evaluate(t => localStorage.setItem('token', t), lg2.data.token);
  await p2.goto(FRONT + '/admin/index.html');
  await p2.waitForTimeout(1200);
  ck('un coach ve el aviso de sin acceso', await p2.locator('#sinAcceso').isVisible());
  ck('y no ve el panel', !(await p2.locator('#layout').isVisible()));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
