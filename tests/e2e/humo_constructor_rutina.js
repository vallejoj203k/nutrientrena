/* El constructor de rutinas, abierto desde los DOS sitios donde vive.

   Lo reportado, editando la rutina de un cliente desde su ficha:
     · las notas del día salían descolocadas abajo,
     · y las fotos de los ejercicios no se veían.

   Las dos cosas eran la misma historia de siempre: el constructor está
   compartido (`js/routine-builder.js` + `css/routine-builder.css`) pero cada
   página se había quedado con su propio trozo suelto, y uno de los dos trozos
   estaba incompleto.

     · El CSS de `.day-notes-card` vivía DENTRO de rutinas.html, así que la
       ficha del cliente —misma maqueta, mismo JS— no lo tenía: la etiqueta y
       el recuadro salían uno al lado del otro, con el textarea a su tamaño de
       fábrica.
     · El mapeo de ejercicios de la ficha copiaba campo a campo y se dejaba
       `image` fuera, así que el constructor pintaba el icono genérico de
       mancuerna en lugar de la foto. En rutinas.html sí estaba.

   Por eso esta prueba abre el constructor en las DOS páginas y compara: un
   fallo así no se ve mirando una sola. */
const { chromium } = require('../_pw');
const FRONT = 'http://127.0.0.1:8011', API = 'http://127.0.0.1:8010';
const PROD = 'https://nutrientrena-production.up.railway.app';

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1500, height: 950 } });
  await ctx.route(u => u.href.startsWith(PROD), async route => {
    const q = route.request();
    try {
      const res = await ctx.request.fetch(q.url().replace(PROD, API), { method: q.method(), headers: q.headers(), data: q.postData() || undefined, maxRedirects: 0, timeout: 30000 });
      const h = { ...res.headers() }; delete h['content-encoding']; delete h['content-length'];
      await route.fulfill({ status: res.status(), headers: h, body: await res.body() });
    } catch (e) { await route.abort(); }
  });

  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 240))); if (!c) f++; };
  const SUF = String(Date.now()).slice(-6);
  const errs = [];

  // ── Un centro, su coach, un cliente y un ejercicio CON FOTO ──────────────
  const adm = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: 'admin@nutrientrena.com', password: 'Admin123!' } })).json();
  const H = { Authorization: 'Bearer ' + adm.data.token, 'Content-Type': 'application/json' };
  await ctx.request.post(`${API}/api/admin/organizations`, { headers: H, data: {
    name: `Centro Cons ${SUF}`, owner_name: 'Coach Cons',
    owner_email: `coach.cons.${SUF}@nutrientrena-qa.com`, owner_password: 'Coach123!' } });
  const lgc = await (await ctx.request.post(`${API}/api/auth/login`, {
    data: { email: `coach.cons.${SUF}@nutrientrena-qa.com`, password: 'Coach123!' } })).json();
  const Hc = { Authorization: 'Bearer ' + lgc.data.token, 'Content-Type': 'application/json' };
  const cli = await (await ctx.request.post(`${API}/api/users`, { headers: Hc, data: {
    name: 'Cliente Cons', email: `cli.cons.${SUF}@nutrientrena-qa.com`,
    password: 'Cliente123!', role_id: 6 } })).json();

  /* Un PNG de 1x1 incrustado: no depende de que R2 esté en pie ni de la red,
     y basta para saber si la foto llega al constructor o no. */
  const FOTO = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==';
  const ej = await (await ctx.request.post(`${API}/api/trainings`, { headers: Hc, data: {
    name: `Press de banca ${SUF}`, image: FOTO } })).json();
  ck('ejercicio creado CON foto', !!ej.data?.id && !!ej.data?.image, ej.data);

  const rut = await (await ctx.request.post(`${API}/api/routines`, { headers: Hc, data: {
    name: `Rutina Cons ${SUF}`, days: 3,
    days_list: [{ day_name: 'Día 1 Lunes', blocks: [{ block_type: 'normal', order_index: 0,
      exercises: [{ training_id: ej.data.id, series: 3, repetitions: '8', break_time: 60, order_index: 0 }] }] }] } })).json();
  const asignada = await (await ctx.request.post(`${API}/api/routines/${rut.data.id}/clone-to-client`, {
    headers: Hc, data: { name: rut.data.name, client_id: cli.data.id } })).json();
  ck('y asignada al cliente', !!asignada.data?.id, asignada);

  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(String(e)));
  await p.goto(FRONT + '/rutinas.html');
  await p.evaluate(t => { localStorage.setItem('token', t); localStorage.setItem('role_id', '5');
                          localStorage.removeItem('org_context'); }, lgc.data.token);

  /* Lo que se mide en las dos páginas, para poder compararlas. */
  async function comoQuedaElConstructor() {
    const notas = await p.evaluate(() => {
      const card = document.getElementById('dayNotesCard');
      if (!card) return null;
      const lab = card.querySelector('label').getBoundingClientRect();
      const ta = card.querySelector('textarea').getBoundingClientRect();
      const cs = getComputedStyle(card);
      return {
        // Con el CSS puesto, el textarea va DEBAJO de la etiqueta y ocupa el
        // ancho de la tarjeta. Sin él, se quedan uno al lado del otro.
        textareaDebajo: ta.top >= lab.bottom - 1,
        anchoCompleto: ta.width > card.getBoundingClientRect().width * 0.8,
        altoDecente: ta.height >= 80,
        tarjetaConFondo: cs.backgroundColor !== 'rgba(0, 0, 0, 0)',
      };
    });
    const foto = await p.evaluate(() => {
      const ico = document.querySelector('.ex-ico2');
      if (!ico) return null;
      const img = ico.querySelector('img');
      return { hayImg: !!img,
               cargada: !!img && img.complete && img.naturalWidth > 0,
               // Si no hay <img> es que se pintó el icono genérico.
               iconoGenerico: !img && !!ico.querySelector('svg') };
    });
    return { notas, foto };
  }

  // ── 1) Desde la Librería (rutinas.html) ─────────────────────────────────
  await p.goto(FRONT + '/rutinas.html');
  await p.waitForTimeout(4000);
  /* En la Librería el constructor son dos pasos: `openForm` carga la rutina y
     abre el panel de datos, y `wizardNext` pasa a la pantalla de bloques —que
     es la que tiene las notas del día—. */
  await p.evaluate(id => openForm(id), rut.data.id);
  await p.waitForTimeout(2500);
  await p.evaluate(() => wizardNext());
  await p.waitForTimeout(2500);
  /* Medir con el constructor CERRADO no vale: la tarjeta existe en el DOM
     pero sin dimensiones, y todo saldría en cero. Me pasó escribiéndola: la
     librería daba "ancho incompleto" cuando en realidad no estaba abierta. */
  ck('LIBRERÍA: el constructor está abierto de verdad',
     await p.locator('#dayNotesCard').isVisible());
  const enLibreria = await comoQuedaElConstructor();

  // ── 2) Desde la ficha del cliente ───────────────────────────────────────
  await p.goto(FRONT + '/client-profile.html?id=' + cli.data.id);
  await p.waitForTimeout(5000);
  await p.evaluate(() => { if (window.loadEntrenamiento) return window.loadEntrenamiento(); });
  await p.waitForTimeout(3000);
  await p.evaluate(() => openEntBuilder(0));
  await p.waitForTimeout(3000);
  ck('FICHA: el constructor está abierto de verdad',
     await p.locator('#dayNotesCard').isVisible());
  const enFicha = await comoQuedaElConstructor();

  // ── Lo reportado ────────────────────────────────────────────────────────
  if (enFicha.notas) {
    ck('LAS NOTAS DEL DÍA NO SALEN DESCOLOCADAS EN LA FICHA',
       enFicha.notas.textareaDebajo && enFicha.notas.anchoCompleto &&
       enFicha.notas.altoDecente && enFicha.notas.tarjetaConFondo, enFicha.notas);
  }
  if (enFicha.foto) {
    ck('Y LA FOTO DEL EJERCICIO SE VE EN LA FICHA',
       enFicha.foto.hayImg && enFicha.foto.cargada, enFicha.foto);
  }

  /* Lo que de verdad protege esto: que las dos páginas se comporten IGUAL. Un
     fallo así solo se ve comparándolas. */
  if (enLibreria.notas && enFicha.notas) {
    ck('LAS DOS PÁGINAS PINTAN LAS NOTAS IGUAL',
       JSON.stringify(enLibreria.notas) === JSON.stringify(enFicha.notas),
       { libreria: enLibreria.notas, ficha: enFicha.notas });
  }
  if (enLibreria.foto && enFicha.foto) {
    ck('y las dos enseñan la foto del ejercicio',
       enLibreria.foto.hayImg === enFicha.foto.hayImg,
       { libreria: enLibreria.foto, ficha: enFicha.foto });
  }

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
