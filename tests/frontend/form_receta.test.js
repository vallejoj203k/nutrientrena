/* El formulario de receta: etiquetas, notas y opciones clínicas.

   Lo que hay que dejar sujeto:

     · Que marcar y desmarcar deje la selección que se ve en pantalla, y que al
       abrir una receta guardada salga marcada tal cual se guardó.
     · Que las patologías se enseñen agrupadas y NO se pierda ninguna: una con
       un grupo que la pantalla no conoce tiene que salir igual.
     · Que las clínicas arranquen cerradas, pero abiertas si la receta trae
       algo dentro: un dato guardado que no se ve al abrir la receta es un dato
       perdido.
     · Y que el reparto de macros diga de dónde vienen las calorías, no cuántos
       gramos hay de cada cosa.
*/
const { chromium } = require('../_pw');

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.setViewportSize({ width: 1100, height: 900 });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/form-receta.html');
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };
  const sel = () => p.evaluate(() => __sel());
  const chip = (caja, texto) => p.locator('#' + caja + ' .rcp-chip', { hasText: new RegExp('^' + texto + '$') });

  await p.evaluate(() => __abre(null));

  // Lo clínico arranca cerrado; para mirarlo dentro hay que abrirlo.
  ck('las clínicas arrancan cerradas', await p.locator('#fClinBody').isHidden());
  await p.click('.rcp-clin-head');
  ck('y se abren al pulsar', await p.locator('#fClinBody').isVisible());
  ck('lo dice para quien no ve la flecha',
    await p.getAttribute('.rcp-clin-head', 'aria-expanded') === 'true');

  // ── Las listas ───────────────────────────────────────────────────────────
  ck('las etiquetas del diseño',
    await p.locator('#fTags .rcp-chip').count() === 12, await p.locator('#fTags .rcp-chip').count());
  ck('los alérgenos', await p.locator('#fAlerg .rcp-chip').count() === 13);
  ck('los estilos alimentarios', await p.locator('#fEstilos .rcp-chip').count() === 10);
  ck('y ninguno marcado en una receta nueva',
    await p.locator('.rcp-chip.on').count() === 0, await p.locator('.rcp-chip.on').count());

  // ── Marcar y desmarcar ───────────────────────────────────────────────────
  await chip('fTags', 'Alta proteína').click();
  await chip('fTags', 'Meal prep').click();
  await chip('fAlerg', 'Gluten').click();
  await chip('fEstilos', 'Mediterránea').click();
  let s = await sel();
  ck('lo marcado se guarda', s.tags.join(',') === 'Alta proteína,Meal prep', s.tags);
  ck('cada lista es la suya', s.alerg.join() === 'Gluten' && s.estilos.join() === 'Mediterránea', s);
  ck('y se ve marcado', await p.locator('.rcp-chip.on').count() === 4);

  await chip('fTags', 'Meal prep').click();
  s = await sel();
  ck('desmarcar lo quita', s.tags.join(',') === 'Alta proteína', s.tags);
  ck('y deja de verse marcado', await p.locator('.rcp-chip.on').count() === 3);

  // ── Patologías ───────────────────────────────────────────────────────────
  await p.waitForFunction(() => document.querySelectorAll('#fPatos .rcp-chip').length > 0);
  const grupos = await p.$$eval('#fPatos .rcp-grupo', ns => ns.map(n => n.textContent.trim()));
  ck('las patologías salen agrupadas',
    grupos.slice(0, 4).join(',') === 'Intolerancias,Digestivo,Metabólico,Cardiovascular', grupos);
  ck('UN GRUPO QUE LA PANTALLA NO CONOCE NO SE PIERDE',
    grupos[grupos.length - 1] === 'Grupo inventado', grupos);
  ck('están todas las del catálogo',
    await p.locator('#fPatos .rcp-chip').count() === 6, await p.locator('#fPatos .rcp-chip').count());

  await p.locator('#fPatos .rcp-chip', { hasText: 'Celiaquía' }).click();
  await p.locator('#fPatos .rcp-chip', { hasText: 'Hipertensión' }).click();
  s = await sel();
  ck('se guardan por id, como las dietas', s.patos.join(',') === '1,5', s.patos);

  // ── El desplegable ───────────────────────────────────────────────────────
  await p.click('.rcp-clin-head');
  ck('y se vuelven a cerrar', await p.locator('#fClinBody').isHidden());
  await p.click('.rcp-clin-head');

  // ── Abrir una receta ya escrita ──────────────────────────────────────────
  const GUARDADA = {
    id: 3, name: 'Arroz con pollo',
    tags: 'Alta proteína,Rápida', notes: 'Sustituir el arroz por quinoa',
    difficulty: 'media', allergen_free: 'Gluten,Lactosa', diet_styles: 'Mediterránea',
    glycemic_index: 'bajo', sodium_level: 'medio', fiber: 7.5,
    pathologies: [{ id: 4, name: 'Diabetes tipo 2', grupo: 'Metabólico' }],
  };
  await p.evaluate(r => __abre(r), GUARDADA);
  s = await sel();
  ck('sale marcado lo que se guardó',
    s.tags.join(',') === 'Alta proteína,Rápida' && s.alerg.join(',') === 'Gluten,Lactosa'
    && s.estilos.join(',') === 'Mediterránea' && s.patos.join(',') === '4', s);
  ck('los chips lo reflejan',
    await p.locator('.rcp-chip.on').count() === 6, await p.locator('.rcp-chip.on').count());
  ck('las notas', (await p.inputValue('#fNotes')) === 'Sustituir el arroz por quinoa');
  ck('la dificultad', (await p.inputValue('#fDifficulty')) === 'media');
  ck('el índice glucémico y el sodio',
    (await p.inputValue('#fGI')) === 'bajo' && (await p.inputValue('#fNa')) === 'medio');
  ck('la fibra', (await p.inputValue('#fFiber')) === '7.5');

  // ── Una receta sin nada clínico no arrastra lo de la anterior ────────────
  await p.evaluate(() => __abre({ id: 4, name: 'Otra' }));
  s = await sel();
  ck('abrir otra receta limpia lo de la anterior',
    !s.tags.length && !s.alerg.length && !s.estilos.length && !s.patos.length, s);
  ck('y sus campos', (await p.inputValue('#fNotes')) === '' && (await p.inputValue('#fFiber')) === '');

  // ── El reparto de macros ─────────────────────────────────────────────────
  // 42 g de proteína (168 kcal), 65 de carbo (260) y 12 de grasa (108): 536 en
  // total -> 31 / 49 / 20 %. En gramos saldría 35/54/10, que no es lo mismo.
  await p.evaluate(() => rcpReparto(42, 65, 12));
  const leg = await p.$$eval('#repLeg span', ns => ns.map(n => n.textContent.trim()));
  ck('el reparto va por calorías, no por gramos',
    leg.join(' ') === 'Prot 31% Carb 49% Gras 20%', leg);
  const anchos = await p.$$eval('#repBar > div', ns => ns.map(n => n.style.width));
  ck('y la barra dice lo mismo', anchos.join(',') === '31%,49%,20%', anchos);

  await p.evaluate(() => rcpReparto(0, 0, 0));
  ck('sin macros no se pinta una barra a cero',
    await p.locator('#repBar > div').count() === 0);
  ck('pero se dice que es cero',
    (await p.textContent('#repLeg')).includes('Prot 0%'));

  // ── Escapado ─────────────────────────────────────────────────────────────
  await p.evaluate(() => { __PATOS = [{ id: 1, name: '<img src=x>', grupo: '<b>g</b>' }];
    _rcpPatologias = []; return _rcpCargaPatologias(); });
  await p.waitForFunction(() => document.querySelectorAll('#fPatos .rcp-chip').length === 1);
  ck('escapa el HTML del catálogo',
    (await p.innerHTML('#fPatos')).includes('&lt;img') && (await p.innerHTML('#fPatos')).includes('&lt;b&gt;g'),
    await p.innerHTML('#fPatos'));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
