/* La nutrición del cliente: lo que ve de su plan.

   Los macros del día salían con un guion —el servidor solo los mandaba si el
   coach los había escrito a mano al crear la dieta— y el día aparecía sin
   kcal, con las comidas enteras debajo. Aquí se comprueba lo que la pantalla
   hace con lo que le llega, incluido lo que pasa cuando de verdad no hay dato.

   Se carga la PÁGINA de verdad, con el servidor de mentira.
*/
const { chromium } = require('../_pw');

const dia = (i, extra) => Object.assign({
  day_index: i, label: ['L', 'M', 'X', 'J', 'V', 'S', 'D'][i],
  name: ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'][i],
  date: '2026-05-1' + (1 + i), is_today: i === 1, has_diet: true,
  kcal: null, protein: null, carbs: null, fats: null, meals: [],
}, extra || {});

const COMIDAS = [
  { name: 'Desayuno', time: '08:00', kcal: 232, subtitle: 'Yogur con fruta', foods: [
    { name: 'Yogur griego', quantity: 200, unit: 'g' },
    { name: 'Huevo grande', quantity: 2, unit: 'ud' },
    { name: 'Leche', quantity: 150, unit: 'ml' },
  ] },
  { name: 'Media mañana', time: '11:00', kcal: 932, foods: [
    { name: 'Anacardos', quantity: 30, unit: 'g' },
  ] },
];

const RESP = {
  '/auth/me': { data: { name: 'Juan', email: 'juan@x.com' } },
  '/client/nutrition': { data: {
    menu: { name: 'Plan semanal' }, week_start: '2026-05-11', plan_semanal: true,
    days: [
      dia(0),
      dia(1, { kcal: 1164, protein: 88.4, carbs: 120.2, fats: 41.6, meals: COMIDAS }),
      dia(2), dia(3), dia(4), dia(5),
      dia(6, { has_diet: false }),
    ],
  } },
};

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.setViewportSize({ width: 1280, height: 1000 });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));

  await p.addInitScript((resp) => {
    localStorage.setItem('token', 't'); localStorage.setItem('role_id', '6');
    window.fetch = async (url) => {
      const clave = Object.keys(resp).find(k => String(url).includes(k));
      return { status: 200, ok: true, json: async () => (clave ? resp[clave] : { data: {} }) };
    };
  }, RESP);

  await p.goto('file://' + __dirname + '/../../frontend/client-nutricion.html');

  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };
  let pintada = true;
  try {
    await p.waitForFunction(() => document.querySelectorAll('.meal-card').length > 0, { timeout: 8000 });
  } catch (e) { pintada = false; }
  ck('el plan se pinta', pintada, await p.textContent('#daybox'));

  const macros = () => p.$$eval('.macro', ns => ns.map(n => ({
    v: n.querySelector('.macro-v').textContent.trim(),
    l: n.querySelector('.macro-l').textContent.trim(),
  })));

  // ── Los macros del día ───────────────────────────────────────────────────
  const ms = await macros();
  ck('los tres macros del día', ms.map(m => m.l).join(',') === 'Proteína,Carbohidratos,Grasa', ms);
  ck('NO SALEN CON UN GUION cuando hay dato',
    !ms.some(m => m.v === '—'), ms.map(m => m.v));
  ck('con sus cifras', ms.map(m => m.v).join(' ').includes('88'), ms.map(m => m.v));
  ck('y el día lleva sus kcal',
    (await p.textContent('.day-kcal')).includes('1164'), await p.textContent('.day-kcal'));

  // ── Las comidas ──────────────────────────────────────────────────────────
  const comidas = await p.$$eval('.meal-card', ns => ns.map(n => ({
    nombre: n.querySelector('.meal-nm').textContent.trim(),
    sub: (n.querySelector('.meal-sub') || {}).textContent || '',
    que: (n.querySelector('.meal-que') || {}).textContent || '',
    abierta: n.classList.contains('open'),
    filas: Array.from(n.querySelectorAll('.mf-row')).map(r => r.textContent.replace(/\s+/g, ' ').trim()),
  })));
  ck('una tarjeta por comida', comidas.length === 2, comidas.length);
  ck('la primera viene abierta', comidas[0].abierta && !comidas[1].abierta,
    comidas.map(c => c.abierta));
  ck('con su hora y sus kcal', comidas[0].sub.includes('08:00') && comidas[0].sub.includes('232 kcal'),
    comidas[0].sub);
  ck('y lo que se come, si el coach lo escribió', comidas[0].que.includes('Yogur con fruta'), comidas[0].que);
  ck('los alimentos, con su cantidad',
    comidas[0].filas.length === 3 && comidas[0].filas[0].includes('Yogur griego'), comidas[0].filas);
  ck('CADA UNO EN SU UNIDAD, no todo en gramos',
    comidas[0].filas[0].includes('200g') && comidas[0].filas[1].includes('2 ud')
    && comidas[0].filas[2].includes('150ml'), comidas[0].filas);

  // Se puede desplegar la segunda.
  await p.locator('.meal-card').nth(1).locator('.meal-head').click();
  ck('la otra comida se abre al tocarla',
    await p.locator('.meal-card').nth(1).evaluate(n => n.classList.contains('open')));

  // ── Cambiar de día ───────────────────────────────────────────────────────
  const dias = await p.$$eval('.wday', ns => ns.map(n => n.textContent.replace(/\s+/g, ' ').trim()));
  ck('están los siete días', dias.length === 7, dias);
  // El 12 de mayo de 2026 es martes: la pastilla lleva la inicial y el día.
  ck('y el de hoy sale marcado',
    await p.locator('.wday.sel').textContent() === 'M12', await p.locator('.wday.sel').textContent());

  await p.locator('.wday').nth(6).click();
  ck('un día sin menú lo dice, no se queda en blanco',
    (await p.textContent('.day-note')).includes('No hay menú asignado'),
    await p.textContent('#daybox'));
  ck('y no enseña macros que no tiene', await p.locator('.macro').count() === 0);

  await p.locator('.wday').nth(0).click();
  const vacio = await macros();
  ck('un día con dieta pero sin datos sí enseña el guion',
    vacio.every(m => m.v === '—'), vacio.map(m => m.v));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
