/* "Gestionar grupo": la ventana del grupo ya creado.

   Antes esto era un panel desplegable en la cabecera: una lista de nombres a
   secas y un desplegable para añadir. No se veía quién era quién —equipo o
   cliente— ni había forma de cambiarle el nombre a un grupo, así que "Reto
   enero" seguía llamándose así en marzo y la única salida era rehacerlo y
   perder la conversación entera.

   Lo que se comprueba, y por qué:

     · Quién manda: solo quien creó el grupo renombra, saca gente y lo borra.
       A quien no, se le ofrece salirse — estar en un grupo no es una condena.
     · La gente sale separada por lo que es. En un seguimiento hay equipo y
       cliente en el mismo grupo, y no es lo mismo sacar a la nutricionista que
       sacar al cliente al que se le hace el seguimiento.
     · Al creador no se le puede sacar: el grupo se quedaría sin administrador.
     · Y borrar el grupo se lleva la conversación por delante, así que pide
       escribir el nombre. Un "¿seguro?" se pulsa sin leerlo. */
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

(async () => {
  const b = await chromium.launch();

  /* Un contexto por persona: las pantallas comparten origen y por tanto
     localStorage, así que abrir la del otro machacaría la sesión de la
     primera. Me pasó escribiendo la prueba del chat del cliente. */
  async function nuevoContexto() {
    const c = await b.newContext({ viewport: { width: 1500, height: 950 } });
    await c.route(u => u.href.startsWith(PROD), async route => {
      const q = route.request();
      try {
        const res = await c.request.fetch(q.url().replace(PROD, API), { method: q.method(), headers: q.headers(), data: q.postData() || undefined, maxRedirects: 0, timeout: 30000 });
        const h = { ...res.headers() }; delete h['content-encoding']; delete h['content-length'];
        await route.fulfill({ status: res.status(), headers: h, body: await res.body() });
      } catch (e) { await route.abort(); }
    });
    return c;
  }
  const ctx = await nuevoContexto();

  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 260))); if (!c) f++; };
  const SUF = String(Date.now()).slice(-6);
  const errs = [];

  // ── Un centro, su coach, dos del equipo y un cliente ────────────────────
  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };
  await ctx.request.post(`${API}/api/admin/organizations`, { headers: H, data: {
    name: `Centro GG ${SUF}`, owner_name: 'Coach GG',
    owner_email: `coach.gg.${SUF}@nutrientrena-qa.com`, owner_password: 'Coach123!' } });
  const lgc = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `coach.gg.${SUF}@nutrientrena-qa.com`, password: 'Coach123!' } })).json();
  const Hc = { Authorization: 'Bearer ' + lgc.data.token, 'Content-Type': 'application/json' };

  const equipo = [];
  for (const [nom, oficio] of [['Laura Minguez', 'Nutricionista'], ['Sergio Garcia', 'Entrenador']]) {
    const slug = nom.split(' ')[0].toLowerCase();
    const u = await (await ctx.request.post(`${API}/api/users`, { headers: H, data: {
      name: nom, email: `${slug}.gg.${SUF}@nutrientrena-qa.com`,
      password: 'Equipo123!', role_id: 5 } })).json();
    await ctx.request.post(`${API}/api/team`, { headers: Hc, data: {
      user_detail_id: u.data.id, member_name: nom,
      member_email: `${slug}.gg.${SUF}@nutrientrena-qa.com`, role_label: oficio } });
    const lg = await (await ctx.request.post(`${API}/api/auth/login`, {
      data: { email: `${slug}.gg.${SUF}@nutrientrena-qa.com`, password: 'Equipo123!' } })).json();
    equipo.push({ nom, oficio, uid: lg.data.user.id, token: lg.data.token });
  }
  const cliU = await (await ctx.request.post(`${API}/api/users`, { headers: Hc, data: {
    name: 'Ana Cliente', email: `ana.gg.${SUF}@nutrientrena-qa.com`,
    password: 'Cliente123!', role_id: 6 } })).json();
  const lgcli = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `ana.gg.${SUF}@nutrientrena-qa.com`, password: 'Cliente123!' } })).json();
  ck('montados el equipo y el cliente',
     equipo.length === 2 && equipo.every(e => e.uid) && !!cliU.data?.id);

  // Un seguimiento: equipo Y cliente en el mismo grupo.
  const grupo = await (await ctx.request.post(`${API}/api/chat/conversations`, { headers: Hc, data: {
    type: 'group', name: `Seguimiento Ana ${SUF}`, tipo: 'seguimiento',
    participant_user_ids: [equipo[0].uid, lgcli.data.user.id] } })).json();
  ck('y el grupo de seguimiento creado', !!grupo.data?.id, grupo);

  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(String(e)));
  await p.goto(FRONT + '/chat.html');
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '5');
                          localStorage.removeItem('org_context'); }, lgc.data.token);
  await p.goto(FRONT + '/chat.html');
  await p.waitForTimeout(5000);
  await p.click('#tabGrupos');
  await p.waitForTimeout(800);
  await p.locator('.conv-item', { hasText: `Seguimiento Ana ${SUF}` }).first().click();
  await p.waitForTimeout(2500);

  const abierto = () => p.$eval('#ggOverlay', e => e.classList.contains('open'));

  // ── El botón y la ventana ───────────────────────────────────────────────
  ck('la cabecera del grupo ofrece "Gestionar grupo"',
     await p.locator('#btnParts').isVisible() &&
     /Gestionar grupo/.test(await p.textContent('#btnPartsTxt')),
     await p.textContent('#btnPartsTxt'));
  await p.click('#btnParts');
  await p.waitForTimeout(1500);
  ck('se abre la ventana del grupo', await abierto());
  ck('con el nombre del grupo',
     (await p.textContent('#ggNombre')).includes(`Seguimiento Ana ${SUF}`),
     await p.textContent('#ggNombre'));
  ck('y cuántos hay dentro', /3 miembros/.test(await p.textContent('#ggSub')),
     await p.textContent('#ggSub'));

  // ── Quién es quién ──────────────────────────────────────────────────────
  ck('el que lo creó sale como administrador del grupo',
     /Administrador del grupo/.test(await p.textContent('.gg-yo')),
     await p.textContent('.gg-yo'));
  const secciones = await p.$$eval('.gg-sec', els => els.map(e => e.textContent.trim()));
  ck('LA GENTE SALE SEPARADA POR LO QUE ES, equipo y clientes',
     secciones.includes('Equipo') && secciones.includes('Clientes'), secciones);
  ck('y cada uno con su oficio, no solo el nombre',
     (await p.textContent('#ggBody')).includes('Nutricionista'),
     await p.textContent('#ggBody'));
  /* La ficha de uno mismo no lleva cruz. Contar las cruces NO valía: aquí el
     creador es quien mira, y su ficha va aparte arriba, así que la cuenta
     salía bien igual aunque la regla no existiera. Lo comprobé quitándola. */
  ck('la ficha de uno mismo no lleva cruz para sacarse',
     (await p.locator('.gg-yo .gg-quitar').count()) === 0);
  /* Y lo que de verdad protege al grupo está en el servidor: el creador no
     puede salirse y dejarlo sin dueño. Para eso está borrarlo. */
  const salirse = await ctx.request.delete(
    `${API}/api/chat/conversations/${grupo.data.id}/participants/${lgc.data.user.id}`,
    { headers: Hc });
  ck('EL CREADOR NO PUEDE SALIRSE Y DEJAR EL GRUPO SIN DUEÑO',
     salirse.status() === 400, salirse.status());

  // ── Renombrar ───────────────────────────────────────────────────────────
  p.once('dialog', d => d.accept(`Seguimiento Ana marzo ${SUF}`));
  await p.click('#ggLapiz');
  await p.waitForTimeout(3500);
  ck('SE LE PUEDE CAMBIAR EL NOMBRE AL GRUPO',
     (await p.textContent('#ggNombre')).includes(`Seguimiento Ana marzo ${SUF}`),
     await p.textContent('#ggNombre'));
  ck('y el nombre nuevo se ve también en la cabecera del chat',
     (await p.textContent('#msgHeaderName')).includes('marzo'),
     await p.textContent('#msgHeaderName'));

  // ── Añadir gente ────────────────────────────────────────────────────────
  await p.click('.gg-anadir');
  await p.waitForTimeout(2500);
  const aAnadir = await p.$$eval('#ggBody .ng-miembro .nm b', els => els.map(e => e.textContent.trim()));
  ck('para añadir salen los que NO están ya dentro',
     aAnadir.includes('Sergio Garcia') && !aAnadir.includes('Laura Minguez'), aAnadir);
  await p.locator('#ggBody .ng-miembro', { hasText: 'Sergio Garcia' }).locator('input').check();
  await p.click('#ggConfirmar');
  await p.waitForTimeout(3500);
  ck('AÑADIR A ALGUIEN LO METE DE VERDAD',
     /4 miembros/.test(await p.textContent('#ggSub')), await p.textContent('#ggSub'));

  // ── Sacar a alguien ─────────────────────────────────────────────────────
  p.once('dialog', d => d.accept());
  await p.locator('.gg-fila', { hasText: 'Sergio Garcia' }).locator('.gg-quitar').click();
  await p.waitForTimeout(3500);
  ck('y sacarlo lo saca',
     /3 miembros/.test(await p.textContent('#ggSub')) &&
     !(await p.textContent('#ggBody')).includes('Sergio Garcia'),
     await p.textContent('#ggSub'));

  // ── Quien no lo creó no manda, pero puede salirse ───────────────────────
  const ctx2 = await nuevoContexto();
  const p2 = await ctx2.newPage(); p2.on('pageerror', e => errs.push(String(e)));
  await p2.goto(FRONT + '/chat.html');
  await p2.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '5');
                           localStorage.removeItem('org_context'); }, equipo[0].token);
  await p2.goto(FRONT + '/chat.html');
  await p2.waitForTimeout(5000);
  await p2.click('#tabGrupos');
  await p2.waitForTimeout(800);
  await p2.locator('.conv-item').first().click();
  await p2.waitForTimeout(2500);
  await p2.click('#btnParts');
  await p2.waitForTimeout(2000);
  ck('a quien NO lo creó no se le ofrece renombrar',
     await p2.$eval('#ggLapiz', e => e.style.display === 'none'));
  ck('ni sacar a nadie', (await p2.locator('.gg-quitar').count()) === 0);
  ck('ni borrar el grupo', (await p2.locator('.gg-borrar').count()) === 0);
  ck('PERO SÍ SALIRSE, que estar en un grupo no es una condena',
     (await p2.locator('.gg-salir').count()) === 1);

  // ── Borrar el grupo ─────────────────────────────────────────────────────
  /* Con el nombre mal escrito NO se borra: es lo que separa un borrado de un
     accidente. Salen DOS ventanas —la que pide el nombre y el aviso de que no
     coincide—, así que el manejador tiene que durar las dos: con dos `once`
     encadenados, ambos intentan responder a la primera y revienta. */
  const manejador = d => d.accept(d.type() === 'prompt' ? 'otra cosa' : '');
  p.on('dialog', manejador);
  await p.click('.gg-borrar');
  await p.waitForTimeout(2500);
  ck('CON EL NOMBRE MAL ESCRITO NO SE BORRA', await abierto());

  p.off('dialog', manejador);
  const nombreFinal = (await p.textContent('#ggNombre')).trim();
  p.once('dialog', d => d.accept(nombreFinal));
  await p.click('.gg-borrar');
  await p.waitForTimeout(4000);
  ck('y escribiéndolo bien, sí', !(await abierto()));
  ck('el grupo desaparece de la lista',
     !(await p.$$eval('.conv-item .conv-name', els => els.map(e => e.textContent)))
       .some(n => n.includes(SUF)),
     await p.$$eval('.conv-item .conv-name', els => els.map(e => e.textContent)));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
