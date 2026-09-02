/* El plan de entrenamiento en la ficha del cliente.

   Lo que de verdad cambia aquí no es el aspecto, es el REPARTO. El carril
   deducía el día de la semana del ORDEN: el primer día de la rutina era el
   lunes, el segundo el martes. Con eso no hay forma de decir "los miércoles
   descanso" — cuatro días de entreno salían lunes, martes, miércoles y
   jueves, aunque el coach los hubiera pensado para lunes, martes, jueves y
   viernes. Y el cliente entrena los días que le dijeron, no los que la
   pantalla supone.

   Ahora sale de `weekday`, que es un dato. Y cuando no está —todas las
   rutinas de antes— se cae al orden, que es lo que se hacía siempre: nadie
   pierde su reparto por desplegar esto.
*/
const { chromium } = require('../_pw');

const ej = (n, mg, s, reps, desc, inten, notas) => ({
  training_name: n, muscle_group_name: mg, series: s, repetitions: reps,
  break_time: desc, intensity_type: inten ? 'RPE' : null, intensity_value: inten || null,
  notes: notas || null,
});

const dia = (nombre, weekday, ejercicios) => ({
  day_name: nombre, weekday,
  blocks: [{ block_type: 'normal', exercises: ejercicios }],
});

// Como el diseño: cuatro días de entreno repartidos con el miércoles libre.
const RUTINA = {
  name: 'Empuje A', training: 'Gimnasio', days: 4, weeks: 6, time: 45,
  assigned_at: '2026-09-02T10:00:00',
  days_list: [
    dia('Empuje', 0, [
      ej('Press banca con barra', 'Pecho', 4, '8-10', 120, 8),
      ej('Press militar mancuernas', 'Hombro', 3, '10-12', 90),
      ej('Aperturas en polea alta', 'Pecho', 3, '12-15', 60),
      ej('Extensión tríceps en polea', 'Tríceps', 3, '12', 60)]),
    dia('Tirón', 1, [ej('Dominadas lastradas', 'Espalda', 4, '6-8', 120)]),
    dia('Pierna', 3, [ej('Sentadilla', 'Cuádriceps', 4, '8', 180)]),
    dia('Full body', 4, [ej('Peso muerto', 'Espalda', 3, '5', 180)]),
  ],
};

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.setViewportSize({ width: 1100, height: 1000 });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/entreno.html');
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };
  const reparto = () => p.$$eval('.nut-dist-row', ns => ns.map(n => ({
    abv: n.querySelector('.nut-dist-abv').textContent.trim(),
    lbl: n.querySelector('.nut-dist-lbl').textContent.trim(),
    vacio: n.classList.contains('vacio'), sel: n.classList.contains('sel'),
  })));

  await p.evaluate(r => __pinta(r), RUTINA);

  // ── La cabecera ──────────────────────────────────────────────────────────
  ck('la tarjeta se llama como el diseño',
    (await p.textContent('.eplan-t')).trim() === 'Plan de entrenamiento');
  ck('y dice cuándo se asignó',
    (await p.textContent('.eplan-s')).includes('Asignado el 2 sep'), await p.textContent('.eplan-s'));
  ck('la tira lleva el nombre del plan',
    (await p.textContent('.eplan-pill')).trim() === 'Empuje A');
  const meta = await p.textContent('.eplan-meta');
  ck('con sus datos', meta.includes('Gimnasio') && meta.includes('4 días/sem')
    && meta.includes('6 semanas') && meta.includes('45 min/sesión'), meta);
  ck('y el total de ejercicios', (await p.textContent('.eplan-der')).includes('7'),
    await p.textContent('.eplan-der'));

  // ── El reparto: lo que importa ───────────────────────────────────────────
  let rep = await reparto();
  ck('los siete días de la semana', rep.length === 7, rep.length);
  ck('de lunes a domingo',
    rep.map(x => x.abv).join(',') === 'Lun,Mar,Mié,Jue,Vie,Sáb,Dom', rep.map(x => x.abv));
  ck('el lunes es el Día 1', rep[0].lbl === 'Día 1 · Empuje', rep[0]);
  ck('EL MIÉRCOLES ES DESCANSO, no el tercer día de la rutina',
    rep[2].lbl === 'Descanso' && rep[2].vacio, rep[2]);
  ck('el jueves es el Día 3', rep[3].lbl === 'Día 3 · Pierna', rep[3]);
  ck('el viernes el Día 4', rep[4].lbl === 'Día 4 · Full body', rep[4]);
  ck('y el fin de semana, descanso',
    rep[5].lbl === 'Descanso' && rep[6].lbl === 'Descanso', rep.slice(5));

  // ── Los días de entreno ──────────────────────────────────────────────────
  const dias = await p.$$eval('.eday', ns => ns.map(n => ({
    abv: (n.querySelector('.eday-abv') || {}).textContent,
    nm: n.querySelector('.eday-nm').textContent.trim(),
    sel: n.classList.contains('sel'),
  })));
  ck('una tarjeta por día de la rutina', dias.length === 4, dias);
  ck('la abreviatura sale del REPARTO, no del orden',
    dias.map(d => (d.abv || '').trim()).join(',') === 'LUN,MAR,JUE,VIE', dias.map(d => d.abv));
  ck('con su nombre', dias.map(d => d.nm).join(',') === 'Empuje,Tirón,Pierna,Full body', dias);

  // ── La tabla del día ─────────────────────────────────────────────────────
  ck('el panel dice qué día se mira',
    (await p.textContent('.eday-h-t')).trim() === 'Lun · Empuje', await p.textContent('.eday-h-t'));
  ck('y cuántos ejercicios tiene',
    (await p.textContent('.eday-h-s')).includes('4 ejercicios'), await p.textContent('.eday-h-s'));
  const th = await p.$$eval('table.eex th', ns => ns.map(n => n.textContent.trim()));
  ck('las columnas del diseño',
    th.join(',') === 'Ejercicio,Series,Reps,Descanso,Nota', th);

  const filas = await p.$$eval('table.eex tbody tr', ns => ns.map(tr =>
    Array.from(tr.children).map(td => td.textContent.trim().replace(/\s+/g, ' '))));
  ck('cuatro ejercicios', filas.length === 4, filas.length);
  ck('con nombre y grupo muscular',
    filas[0][0] === 'Press banca con barra Pecho', filas[0]);
  ck('series y reps', filas[0][1] === '4' && filas[0][2] === '8-10', filas[0]);
  // 120 segundos son 2'; el minuto justo se queda en 60", como en el diseño.
  ck('el descanso largo se lee en minutos', filas[0][3] === "2'", filas[0]);
  ck('y el corto en segundos', filas[1][3] === '90"', filas[1]);
  ck('y el minuto justo tambien', filas[2][3] === '60"', filas[2]);
  ck('la intensidad va en la nota', filas[0][4] === 'RPE 8', filas[0]);
  ck('y sin intensidad no se inventa', filas[1][4] === '—', filas[1]);

  // ── Cambiar de día ───────────────────────────────────────────────────────
  await p.locator('.eday').nth(2).click();
  ck('tocar una tarjeta cambia el día',
    (await p.textContent('.eday-h-t')).trim() === 'Jue · Pierna', await p.textContent('.eday-h-t'));
  rep = await reparto();
  ck('y el reparto marca ese día', rep[3].sel && rep.filter(x => x.sel).length === 1, rep);
  await p.locator('.nut-dist-row').first().click();
  ck('y tocar el lunes en el reparto vuelve al Día 1',
    (await p.textContent('.eday-h-t')).trim() === 'Lun · Empuje');

  // ── Sin `weekday`: las rutinas de antes ──────────────────────────────────
  // Se cae al orden, que es lo que se hacía siempre. Nadie pierde su reparto.
  const vieja = JSON.parse(JSON.stringify(RUTINA));
  vieja.days_list.forEach(d => { delete d.weekday; });
  await p.evaluate(r => __pinta(r), vieja);
  rep = await reparto();
  ck('sin el dato, el orden manda como siempre',
    rep[0].lbl === 'Día 1 · Empuje' && rep[2].lbl === 'Día 3 · Pierna', rep.slice(0, 4));

  // ── Un día de descanso dentro de la rutina ───────────────────────────────
  const conDescanso = { ...RUTINA, days_list: [
    dia('Empuje', 0, [ej('Press banca', 'Pecho', 4, '8', 90)]),
    { day_name: 'Libre', weekday: 2, blocks: [] },
  ] };
  await p.evaluate(r => __pinta(r, 1), conDescanso);
  ck('un día sin ejercicios se llama Descanso',
    (await p.$$eval('.eday-nm', ns => ns[1].textContent.trim())) === 'Descanso');
  ck('y su panel lo dice en vez de una tabla vacía',
    (await p.textContent('.eplan-panel')).includes('descanso'), await p.textContent('.eplan-panel'));

  // ── Los botones ──────────────────────────────────────────────────────────
  await p.evaluate(r => __pinta(r), RUTINA);
  const btns = await p.$$eval('.eplan-acts .eplan-btn', ns => ns.map(n => n.textContent.trim()));
  ck('los cuatro botones del diseño',
    btns.length === 4 && btns[0] === 'Abrir editor' && btns[1] === 'PDF' && btns[2] === 'Cambiar plan', btns);
  for (let i = 0; i < 4; i++) await p.locator('.eplan-acts .eplan-btn').nth(i).click();
  ck('y hacen lo que dicen',
    (await p.evaluate(() => window.__acciones)).join() === 'editor:0,pdf,cambiar,borrar',
    await p.evaluate(() => window.__acciones));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
