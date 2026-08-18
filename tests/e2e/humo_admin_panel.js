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
  ck('las 11 secciones del documento', secs.length === 11, secs);
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

  await p.click('.s-item:has-text("Planes y suscripciones")');
  await p.waitForTimeout(200);
  ck('navegar entre secciones funciona', (await p.textContent('#titulo')).includes('Planes'), await p.textContent('#titulo'));
  ck('los nombres del menú son los del diseño del cliente',
     secs[1] === 'Coaches' && secs[3] === 'Facturación' && secs[9] === 'Equipo Alzum', secs);
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

  await p.click('.s-item:has-text("Contenido global")');
  await p.waitForTimeout(1500);
  ck('la sección Contenido global carga', (await p.textContent('#titulo')).trim() === 'Contenido global');

  /* ── Contenido global ES la Librería ────────────────────────────────────
     El cliente lo pidió literal: que el botón lleve a las páginas de verdad y
     que todo funcione igual que en el panel del coach, pero conservando el
     menú de la plataforma. Así que no se comprueba una pantalla rehecha aquí:
     se comprueba que se abre la página real y que trae el menú correcto. */
  const sub = await p.locator('.s-sub.abierto a').allTextContents();
  ck('el menú despliega las pantallas de la librería', sub.length === 13, sub);
  ck('con los grupos de la librería del coach',
     ['Rutinas', 'Ejercicios', 'Grupos musculares', 'Dietas', 'Alimentos', 'Formularios', 'Plantillas']
       .every(n => sub.includes(n)), sub);

  await p.click('.s-sub.abierto a:has-text("Rutinas")');
  await p.waitForLoadState('domcontentloaded');
  await p.locator('#sidePlataforma').waitFor({ state: 'visible', timeout: 25000 });
  ck('abre la página de verdad, no una copia', p.url().includes('/rutinas.html'), p.url());
  ck('con el menú de la plataforma', await p.locator('#sidePlataforma .s-item').count() >= 11);
  ck('y sin el menú del coach, para no tener dos',
     !(await p.locator('body > .layout > .sidebar, body > .sidebar').first().isVisible().catch(() => false)));
  ck('la pantalla marca dónde estás', await p.locator('.s-sub.abierto a.active:has-text("Rutinas")').count() === 1);

  await p.locator('table tbody tr').first().waitFor({ state: 'visible', timeout: 25000 }).catch(() => {});
  ck('con su buscador y sus filtros',
     await p.locator('input[placeholder*="Buscar rutinas"]').isVisible() &&
     await p.getByText('Nivel', { exact: true }).first().isVisible());
  ck('y sus acciones por fila (asignar, ver, editar, borrar)',
     (await p.locator('button:has-text("Asignar")').count()) >= 1);

  // Los enlaces de dentro arrastran el modo: si lo perdieran, a mitad de
  // navegación reaparecería el menú del coach.
  await p.click('a:has-text("Ejercicios")');
  await p.waitForLoadState('domcontentloaded');
  await p.locator('#sidePlataforma').waitFor({ state: 'visible', timeout: 25000 });
  ck('navegar por sus pestañas conserva el menú de plataforma',
     p.url().includes('panel=plataforma'), p.url());

  // Lo que de verdad importa de "entrar como plataforma": lo que se cree aquí
  // nace en el catálogo común, no dentro de una cuenta.
  ck('se trabaja sin contexto de cuenta, así que lo nuevo nace global',
     await p.evaluate(() => localStorage.getItem('org_context')) === null);

  await p.click('#sidePlataforma .ctx-card');
  await p.waitForLoadState('domcontentloaded');
  await p.waitForTimeout(1500);
  ck('«Plataforma Alzum» devuelve al panel', (await p.textContent('#titulo')).trim().length > 0);

  // La separación entre plataforma y cuentas se comprueba por API: es una
  // propiedad de los datos, no de la pantalla.
  const listaGlobal = await (await ctx.request.get(
    `${API}/api/admin/content?tipo=trainings&q=${SUF}`, { headers: H })).json();
  const nombresGlobal = (listaGlobal.data.items || []).map(i => i.nombre);
  ck('lo de plataforma está en el catálogo global', nombresGlobal.includes(`Sentadilla de fábrica ${SUF}`), nombresGlobal);
  ck('lo privado de una cuenta NO se cuela en la global',
     !nombresGlobal.includes(`Ejercicio privado ${SUF}`), nombresGlobal);

  // ── Contenido de organizaciones ─────────────────────────────────────────
  // Subir a la base común lo bueno de una cuenta. Era una pestaña dentro de
  // Contenido global; al pasar esa sección a ser la librería, es su propia
  // entrada.
  await p.click('.s-item:has-text("Contenido de organizaciones")');
  await p.waitForTimeout(1600);
  const to = await p.textContent('#contenido');
  ck('lo privado se lista aparte con su cuenta',
     to.includes(`Ejercicio privado ${SUF}`) && to.includes(`Centro Clientes ${SUF}`), to.slice(0, 220));
  ck('y las propuestas se marcan como pendientes, no como cero',
     to.includes('Todavía no existe el circuito de propuestas'));

  // Promover: el punto de la sección. Es reversible y ya existía por API.
  p.on('dialog', d => d.accept());
  await p.click(`tr:has-text("Ejercicio privado ${SUF}") button:has-text("Subir a plataforma")`);
  await p.waitForTimeout(1500);
  const trasPromover = await (await ctx.request.get(`${API}/api/admin/content?tipo=trainings&q=${SUF}`, { headers: H })).json();
  ck('subir a plataforma lo pasa al catálogo común',
     (trasPromover.data.items || []).some(i => i.nombre === `Ejercicio privado ${SUF}`),
     (trasPromover.data.items || []).map(i => i.nombre));

  // ── Analíticas ───────────────────────────────────────────────────────────
  // Lo que importa aquí es que las gráficas se dibujen con datos REALES y que
  // lo que no se puede calcular salga vacío en vez de inventado.
  await p.click('.s-item:has-text("Analíticas")');
  await p.locator('.graf svg').first().waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});
  ck('la sección Analíticas carga', (await p.textContent('#titulo')).trim() === 'Analíticas');
  ck('se dibujan las dos gráficas', await p.locator('.graf svg').count() === 2);
  ck('la de altas tiene una barra por mes', await p.locator('.graf svg rect').count() === 7);
  ck('la de acumulado tiene un punto por mes', await p.locator('.graf svg circle').count() === 7);

  const ana = await (await ctx.request.get(`${API}/api/admin/analytics`, { headers: H })).json();
  const acumulado = ana.data.acumulado.map(x => x.valor);
  ck('el acumulado nunca baja', JSON.stringify(acumulado) === JSON.stringify([...acumulado].sort((a, b) => a - b)), acumulado);
  ck('y su último valor es el total de cuentas',
     acumulado[acumulado.length - 1] === ana.data.kpis.cuentas, { acumulado, kpis: ana.data.kpis });

  const txtAna = await p.textContent('#contenido');
  ck('MRR y ARPA salen como pendientes, no con un número inventado',
     ana.data.kpis.mrr === null && ana.data.kpis.arpa === null &&
     (txtAna.match(/Requiere la pasarela de pago/g) || []).length === 2, txtAna.slice(0, 160));
  ck('«cuentas caídas» se explica como la foto de ahora, no como churn del mes',
     txtAna.includes('no el churn del mes'));
  ck('la retención se calcula por cohorte',
     /Mes 0/i.test(txtAna) && (await p.locator('.coh tbody tr').count()) >= 1);
  ck('el mes 0 de cada cohorte es 100%',
     (ana.data.cohortes || []).every(c => c.valores[0] === 100), ana.data.cohortes);

  // ── Equipo Alzum ─────────────────────────────────────────────────────────
  await p.click('.s-item:has-text("Equipo Alzum")');
  await p.locator('.rol-tarj').first().waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});
  ck('la sección Equipo Alzum carga', (await p.textContent('#titulo')).trim() === 'Equipo Alzum');
  ck('salen los tres roles internos', await p.locator('.rol-tarj').count() === 3);
  ck('la tarjeta "Tu rol" de la barra lateral sigue en su sitio',
     await p.evaluate(() => {
       const c = document.getElementById('rolCard');
       return !!c && c.closest('.side') !== null && getComputedStyle(c).display !== 'none';
     }));

  await p.click('button:has-text("+ Invitar miembro")');
  await p.waitForTimeout(500);
  await p.fill('#miemNombre', 'Lucía Prats');
  await p.fill('#miemEmail', `lucia.${SUF}@alzum.io`);
  await p.selectOption('#miemRol', '7');
  await p.fill('#miemClave', 'Equipo123!');
  await p.click('#miemBtn');
  await p.waitForTimeout(1800);
  const eq = await p.textContent('#contenido');
  ck('el miembro invitado aparece', eq.includes(`lucia.${SUF}@alzum.io`), eq.slice(0, 200));
  ck('y sale como invitado hasta que entre', eq.includes('Nunca ha entrado') && eq.includes('invitado'));

  // El rol no es una etiqueta: cambia lo que ve de verdad
  const lgL = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `lucia.${SUF}@alzum.io`, password: 'Equipo123!' } })).json();
  const suyas = await (await ctx.request.get(`${API}/api/admin/me`,
    { headers: { Authorization: 'Bearer ' + lgL.data.token } })).json();
  ck('el editor de contenido solo ve su sección',
     JSON.stringify((suyas.data.secciones || []).map(s => s.id)) === '["contenido"]', suyas.data.secciones);

  await p.click('.s-item:has-text("Equipo Alzum")');
  await p.locator('.rol-tarj').first().waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});
  ck('tras entrar pasa a activo', (await p.textContent('#contenido')).includes('Justo ahora'));

  // ── Invitar SIN saber su contraseña ──────────────────────────────────────
  // Quien invita no tiene por qué conocer la contraseña de otro, y menos la de
  // un super-admin. Dejando el campo vacío se le manda un correo para que la
  // ponga él.
  await p.click('button:has-text("+ Invitar miembro")');
  await p.waitForTimeout(500);
  ck('el formulario dice que se puede dejar vacía',
     (await p.getAttribute('#miemClave', 'placeholder')).includes('la pone él'));
  await p.fill('#miemNombre', 'Sin Clave');
  await p.fill('#miemEmail', `sinclave.${SUF}@alzum.io`);
  await p.selectOption('#miemRol', '1');
  await p.click('#miemBtn');
  await p.waitForTimeout(2000);
  // Invitar sin contraseña abre el modal del código: hay que cerrarlo o tapa
  // todo lo que viene después.
  ck('se le da un código para entrar por «Soy invitado»',
     await p.locator('#capaCodigo.on').count() === 1);
  ck('con el formato que se puede dictar sin confundirse',
     /^[A-Z0-9]{4}-[A-Z0-9]{4}$/.test((await p.textContent('#codValor')).trim()),
     await p.textContent('#codValor'));
  await p.click('#capaCodigo button:has-text("Entendido")');
  await p.locator('#capaCodigo.on').waitFor({ state: 'hidden', timeout: 10000 });
  ck('el super-admin invitado aparece',
     (await p.textContent('#contenido')).includes(`sinclave.${SUF}@alzum.io`),
     (await p.textContent('#contenido')).slice(0, 200));

  // LO IMPORTANTE: esa cuenta no se abre con nada adivinable
  for (const intento of ['', '123456', 'password', 'Alzum123!', `sinclave.${SUF}@alzum.io`]) {
    const r = await ctx.request.post(`${API}/api/auth/login`,
      { data: { email: `sinclave.${SUF}@alzum.io`, password: intento }, failOnStatusCode: false });
    ck(`no se entra con «${intento || '(vacío)'}»`, r.status() === 401, r.status());
  }

  // Lo que no puede pasar nunca: quedarse sin super-admin
  const yo = ((await (await ctx.request.get(`${API}/api/admin/team`, { headers: H })).json())
    .data.miembros || []).find(m => m.soy_yo);
  const degradar = await ctx.request.fetch(`${API}/api/admin/team/${yo.user_id}/role`,
    { method: 'PUT', data: { role_id: 8 }, headers: H });
  ck('NO SE PUEDE DEGRADAR AL ÚNICO SUPER-ADMIN', degradar.status() === 400, degradar.status());
  const sacarme = await ctx.request.fetch(`${API}/api/admin/team/${yo.user_id}`,
    { method: 'DELETE', headers: H });
  ck('ni sacarse uno mismo del equipo', sacarme.status() === 400, sacarme.status());
  ck('y la pantalla ni siquiera ofrece el botón',
     await p.evaluate(() => {
       const fila = [...document.querySelectorAll('#contenido tbody tr')]
         .find(t => t.textContent.includes('(tú)'));
       return !!fila && fila.querySelectorAll('.icono-btn').length === 0;
     }));

  // ── Planes ───────────────────────────────────────────────────────────────
  // "+ Nuevo plan" tiene que crear un plan de verdad con todos los campos del
  // formulario, y el "N cuentas" de la tarjeta tiene que contar de verdad.
  await p.click('.s-item:has-text("Planes")');
  await p.locator('button:has-text("+ Nuevo plan")').waitFor({ state: 'visible', timeout: 20000 });
  ck('la sección Planes carga', (await p.textContent('#titulo')).includes('Planes'));
  ck('avisa de que no es lo que el coach vende a sus clientes',
     (await p.textContent('#subtitulo')).includes('No confundir'));

  await p.click('button:has-text("+ Nuevo plan")');
  await p.waitForTimeout(500);
  await p.fill('#pNombre', `Pro ${SUF}`);
  await p.fill('#pMes', '49');
  await p.fill('#pAnual', '39');
  await p.fill('#pClientes', '50');
  await p.fill('#pCoaches', '1');
  await p.fill('#pExtra', '15');
  await p.fill('#pAlmacen', '50 GB');
  await p.fill('#pSoporte', 'Prioritario < 24 h');
  await p.fill('#pFeats', 'Todo lo de Starter\nAutomatizaciones y recordatorios');
  await p.check('#pDestacado');
  await p.click('#planBtn');
  await p.locator(`.plan:has-text("Pro ${SUF}")`).waitFor({ state: 'visible', timeout: 20000 });

  const tarjeta = await p.textContent(`.plan:has-text("Pro ${SUF}")`);
  ck('el plan se crea con su precio', tarjeta.includes('49 €'), tarjeta.slice(0, 120));
  ck('y con el descuento anual CALCULADO', tarjeta.includes('39 €/mes pagando anual') && tarjeta.includes('20%'), tarjeta);
  ck('con sus límites', tarjeta.includes('Hasta 50 clientes') && tarjeta.includes('+15 €/coach extra'));
  ck('y sus funcionalidades', tarjeta.includes('Automatizaciones y recordatorios'));
  ck('destacado se marca en la tarjeta',
     await p.locator(`.plan.destacado:has-text("Pro ${SUF}")`).count() === 1);
  ck('nace sin cuentas dentro', tarjeta.includes('0 cuentas'), tarjeta);

  // Pagar al año más caro que al mes no es un plan, es una errata
  await p.click('button:has-text("+ Nuevo plan")');
  await p.waitForTimeout(400);
  await p.fill('#pNombre', `Al revés ${SUF}`);
  await p.fill('#pMes', '19');
  await p.fill('#pAnual', '29');
  await p.click('#planBtn');
  await p.waitForTimeout(1200);
  ck('se rechaza que el anual salga más caro que el mensual',
     (await p.textContent('#planError')).includes('no puede ser mayor'), await p.textContent('#planError'));
  await p.click('#capaPlan .btn.ghost');
  await p.waitForTimeout(400);

  // Asignar el plan a una cuenta desde su ficha, y que el contador lo note
  const planId = ((await (await ctx.request.get(`${API}/api/admin/plans`, { headers: H })).json())
    .data.planes || []).find(x => x.name === `Pro ${SUF}`).id;
  const asignado = await ctx.request.fetch(`${API}/api/admin/organizations/${org.data.id}/plan`,
    { method: 'PUT', data: { plan_id: planId }, headers: H });
  ck('se puede asignar el plan a una cuenta', asignado.status() === 200, asignado.status());

  await p.click('.s-item:has-text("Planes")');
  await p.locator(`.plan:has-text("Pro ${SUF}")`).waitFor({ state: 'visible', timeout: 20000 });
  ck('EL CONTADOR DE CUENTAS ES REAL',
     (await p.textContent(`.plan:has-text("Pro ${SUF}")`)).includes('1 cuenta'),
     await p.textContent(`.plan:has-text("Pro ${SUF}")`));

  // Ocultar no es borrar: el plan sigue existiendo con sus cuentas dentro
  await p.click(`.plan:has-text("Pro ${SUF}") button:has-text("Ocultar")`);
  await p.waitForTimeout(1500);
  ck('ocultar lo marca pero no lo borra',
     (await p.textContent(`.plan:has-text("Pro ${SUF}")`)).includes('Oculto'));
  const noBorra = await ctx.request.fetch(`${API}/api/admin/plans/${planId}`, { method: 'DELETE', headers: H });
  ck('y con cuentas dentro no se deja borrar', noBorra.status() === 400, noBorra.status());

  // La columna Plan del listado de Coaches ya dice algo
  await p.click('.s-item:has-text("Coaches")');
  await p.waitForTimeout(1500);
  ck('el listado de Coaches enseña el plan de cada cuenta',
     (await p.textContent('#contenido')).includes(`Pro ${SUF}`), (await p.textContent('#contenido')).slice(0, 200));

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
