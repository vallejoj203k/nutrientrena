/* El Inicio del coach: los próximos cinco días y los clientes sin plan.

   La agenda se pedía a `/events`, una ruta que no existe —devolvía 405— así
   que el panel enseñaba cinco "Sin eventos" dijera lo que dijera el
   calendario. Es el mismo fallo que ya tuvo la cartera de clientes, en la
   llamada de al lado.

   Se carga la PÁGINA de verdad, con el servidor de mentira: lo que se
   comprueba es qué pide y qué pinta con lo que le contestan.

   Lo que hay que dejar sujeto:

     · Que pida la agenda a la ruta que existe, y por la ventana de los cinco
       días que enseña.
     · Que cada evento caiga en SU día, y que un día sin nada lo diga en vez
       de desaparecer: un hueco en la agenda es sitio para una sesión.
     · Y que las cuentas de arriba salgan de los datos, no de un número fijo.
*/
const { chromium } = require('../_pw');

const HOY = '2026-05-15T09:00:00';   // viernes

const RESP = {
  '/api/auth/me': { data: { name: 'Oswal Sergio', roles: [{ name: 'Superadmin' }] } },
  '/api/analytics/overview': { data: { active_clients: 5, new_this_month: 0, total_clients: 5 } },
  '/api/checkins/bandeja': { data: { recibidos: [{ id: 1 }, { id: 2 }], esperando: [] } },
  '/api/users/clients/portfolio': { data: { stats: { activos: 5 }, clients: [
    { id: 'c1', name: 'María', last_name: 'García', sin_plan: true, lifecycle_status: 'activo',
      alta: '2026-05-11T10:00:00', objective: { name: 'Pérdida de grasa' }, precio: 250 },
    { id: 'c2', name: 'Javier', last_name: 'López', sin_plan: true, lifecycle_status: 'activo',
      alta: '2026-05-14T10:00:00', objective: { name: 'Ganancia muscular' }, precio: 250 },
    { id: 'c3', name: 'Ana', last_name: 'Martínez', sin_plan: true, lifecycle_status: 'activo',
      alta: '2026-05-15T08:00:00', objective: null, precio: 250 },
    // Con plan: no debe salir en la lista de "sin plan".
    { id: 'c4', name: 'Luis', last_name: 'Pérez', sin_plan: false, lifecycle_status: 'activo',
      alta: '2026-01-02T10:00:00', precio: 300 },
  ] } },
  '/api/events/search': { data: [
    { id: 1, title: 'Revisar check-in', start_date: '2026-05-15T00:00:00', all_day: 1,
      description: 'Elena', type_event: { id: 2, name: 'Check-in', color: '#F59E0B' } },
    { id: 2, title: 'Sesión online', start_date: '2026-05-18T10:00:00', all_day: 0,
      description: 'Laura', type_event: { id: 1, name: 'Cita', color: '#3B82F6' } },
  ] },
  '/api/form-assignments': { data: { total: 0 } },
};

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.setViewportSize({ width: 1440, height: 1000 });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));

  await p.addInitScript(([hoy, resp]) => {
    localStorage.setItem('token', 't'); localStorage.setItem('role_id', '1');
    const R = new Date(hoy).getTime();
    const _D = Date;
    window.Date = class extends _D {
      constructor(...a) { super(...(a.length ? a : [R])); }
      static now() { return R; }
    };
    window.__llamadas = [];
    window.fetch = async (url) => {
      window.__llamadas.push(String(url));
      const clave = Object.keys(resp).find(k => String(url).includes(k));
      return { status: 200, ok: true, json: async () => (clave ? resp[clave] : { data: {} }) };
    };
  }, [HOY, RESP]);

  await p.goto('file://' + __dirname + '/../../frontend/dashboard.html');

  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };

  // Que la página termine de pintarse es la primera comprobación: si no lo
  // hace, se dice y se sigue, en vez de esperar treinta segundos a nada.
  let pintada = true;
  try {
    await p.waitForFunction(
      () => document.querySelectorAll('#upcomingList .event-row').length === 5,
      { timeout: 8000 });
  } catch (e) { pintada = false; }
  ck('la agenda se pinta', pintada, await p.textContent('#upcomingList'));

  const llamadas = await p.evaluate(() => window.__llamadas);

  // ── A qué se le pide la agenda ───────────────────────────────────────────
  const agenda = llamadas.find(u => u.includes('/api/events'));
  ck('PIDE LA AGENDA A LA RUTA QUE EXISTE',
    !!agenda && agenda.includes('/api/events/search?'), agenda);
  ck('y no a `/events` a secas',
    !llamadas.some(u => /\/api\/events\?/.test(u)), llamadas);
  const q = new URLSearchParams(String(agenda).split('?')[1] || '');
  ck('con la ventana que empieza hoy',
    (q.get('start') || '').startsWith('2026-05-15'), q.get('start'));
  ck('y que llega a los cinco días que se enseñan',
    (q.get('end') || '').startsWith('2026-05-20'), q.get('end'));

  // ── Los cinco días ───────────────────────────────────────────────────────
  const dias = await p.$$eval('#upcomingList .event-row', ns => ns.map(n => ({
    fecha: (n.querySelector('.fecha-num') || n.querySelector('div'))?.textContent.trim(),
    txt: n.textContent.replace(/\s+/g, ' ').trim(),
    vacio: n.classList.contains('vacio'),
    color: (n.querySelector('.event-punto') || {}).style?.backgroundColor || '',
  })));
  ck('salen los cinco días', dias.length === 5, dias.map(d => d.txt));
  ck('el de hoy lleva el check-in',
    dias[0].txt.includes('Revisar check-in') && dias[0].txt.includes('con Elena'), dias[0]);
  ck('CON EL COLOR DE SU TIPO, no gris',
    dias[0].color === 'rgb(245, 158, 11)', dias[0].color);
  ck('un evento de todo el día no inventa una hora',
    !/\d{2}:\d{2}/.test(dias[0].txt), dias[0].txt);
  ck('la sesión del lunes va en su día',
    dias[3].txt.includes('Sesión online') && dias[3].txt.includes('10:00'), dias[3]);
  ck('y con su color', dias[3].color === 'rgb(59, 130, 246)', dias[3].color);
  ck('LOS DÍAS SIN NADA LO DICEN, no desaparecen',
    dias[1].vacio && dias[2].vacio && dias[4].vacio, dias.map(d => d.vacio));

  // ── Los clientes sin plan ────────────────────────────────────────────────
  const filas = await p.$$eval('#noPlanList .client-row', ns => ns.map(n =>
    n.textContent.replace(/\s+/g, ' ').trim()));
  ck('sale un cliente sin plan por fila', filas.length === 3, filas);
  ck('el que lleva más esperando, primero',
    filas[0].includes('María García'), filas[0]);
  ck('el que ya tiene plan NO sale',
    !filas.some(t => t.includes('Luis Pérez')), filas);
  ck('quien lleva días esperando se marca urgente',
    filas[0].includes('Urgente'), filas[0]);
  ck('y quien no ha rellenado el formulario, también se dice',
    filas[2].includes('Sin formulario'), filas[2]);
  ck('con su objetivo y su precio',
    filas[0].includes('Pérdida de grasa') && filas[0].includes('250€/mes'), filas[0]);

  // ── Las cuentas de arriba ────────────────────────────────────────────────
  const kpi = id => p.evaluate(i => document.getElementById(i).textContent.trim(), id);
  ck('clientes activos', await kpi('valActive') === '5', await kpi('valActive'));
  ck('check-ins por revisar', await kpi('valCheckins') === '2', await kpi('valCheckins'));
  ck('planes pendientes', await kpi('valPlanes') === '3', await kpi('valPlanes'));
  ck('y lo que hay que hacer hoy sale de sumarlos',
    (await p.textContent('#todayDate')).includes('5 acciones pendientes hoy'),
    await p.textContent('#todayDate'));
  ck('con la fecha de hoy',
    (await p.textContent('#todayDate')).includes('Viernes, 15 de mayo de 2026'),
    await p.textContent('#todayDate'));

  // ── Las dos columnas, a la misma altura ──────────────────────────────────
  const alturas = await p.$$eval('.two-col > .card', ns => ns.map(n => Math.round(n.getBoundingClientRect().height)));
  ck('las dos tarjetas miden lo mismo',
    Math.abs(alturas[0] - alturas[1]) <= 1, alturas);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
