/* El selector de modo de programación, en la ficha del cliente.

   Hay dos: uno en Nutrición y otro en Entrenamiento. Son la misma tarjeta y
   por eso está escrita una sola vez — dos copias con los mismos radios y los
   mismos textos acaban diciendo cosas distintas en cuanto una se toca.

   Pero son DECISIONES distintas: un coach puede tener la comida cerrada en un
   plan semanal y los entrenos día a día. Compartir el código no puede
   significar compartir el interruptor, y eso es lo que se comprueba aquí:
   que tocar uno no mueve el otro, y que cada uno llama a su propia ruta.

   Y el aviso: nada se cambia hasta confirmar. Un radio que guarda al primer
   clic pone en pausa el plan de un cliente por un roce.
*/
const { chromium } = require('../_pw');

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.setViewportSize({ width: 1100, height: 900 });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/modos.html');
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };
  const modos = () => p.evaluate(() => __modos());
  const puestas = () => p.evaluate(() => window.__puestas.filter(x => x.metodo === 'PUT'));
  const abierto = () => p.evaluate(() => document.getElementById('cmodoBack').classList.contains('open'));
  // El radio marcado de una sección: 0 = semanal, 1 = calendario.
  const activo = (sec) => p.evaluate(s => {
    const ns = Array.from(document.querySelectorAll('#' + s + 'Content .nmodo'));
    return ns.findIndex(n => n.classList.contains('on'));
  }, sec);

  await p.evaluate(() => __pinta('semanal', 'semanal'));

  // ── Las dos secciones tienen su selector ─────────────────────────────────
  ck('Nutricion tiene su selector',
    (await p.textContent('#nutricionContent')).includes('Modo de programación · Nutrición'));
  ck('y Entrenamiento el suyo',
    (await p.textContent('#entrenamientoContent')).includes('Modo de programación · Entrenamiento'));
  ck('los dos arrancan en plan semanal',
    (await activo('nutricion')) === 0 && (await activo('entrenamiento')) === 0);
  const ent = await p.textContent('#entrenamientoContent');
  ck('con las dos opciones y sus etiquetas',
    ent.includes('Plan semanal recurrente') && ent.includes('Calendario completo')
    && ent.includes('Activo') && ent.includes('En pausa'), ent);

  // ── No se cambia nada sin confirmar ──────────────────────────────────────
  await p.click('#entrenamientoContent .nmodo:nth-child(2)');
  ck('pide confirmacion', await abierto());
  ck('y AUN NO ha guardado nada', (await puestas()).length === 0, await puestas());
  const aviso = await p.textContent('#cmodoTexto');
  ck('el aviso dice que el otro modo queda en pausa y no se borra',
    aviso.includes('en pausa') && aviso.includes('no se borra'), aviso);

  await p.click('.cmodo-foot .btn-ghost');            // Cancelar
  ck('cancelar cierra', !(await abierto()));
  ck('y no ha guardado nada', (await puestas()).length === 0, await puestas());
  ck('el entrenamiento sigue en semanal', (await modos()).ent === 'semanal');

  // ── Confirmar: cada uno por su ruta ──────────────────────────────────────
  await p.click('#entrenamientoContent .nmodo:nth-child(2)');
  await p.click('#cmodoOk');
  await p.waitForFunction(() => window.__puestas.some(x => x.metodo === 'PUT'));
  let ps = await puestas();
  ck('guarda una sola vez', ps.length === 1, ps);
  ck('LLAMA A LA RUTA DEL ENTRENAMIENTO', ps[0].url.endsWith('/training-mode'), ps[0]);
  ck('con el campo que espera el servidor',
    JSON.parse(ps[0].cuerpo).training_mode === 'calendario', ps[0].cuerpo);

  // ── Lo que de verdad importa: son independientes ─────────────────────────
  let m = await modos();
  ck('el entrenamiento pasa a calendario', m.ent === 'calendario', m);
  ck('Y LA NUTRICION NO SE HA MOVIDO', m.nut === 'semanal', m);
  ck('la tarjeta de nutricion sigue marcando semanal', (await activo('nutricion')) === 0);
  ck('y la de entrenamiento, calendario', (await activo('entrenamiento')) === 1);
  ck('lleva al calendario', await p.evaluate(() => window.__pestana) === 'calendario');

  // Y al revés: mover la nutrición no arrastra el entrenamiento.
  await p.evaluate(() => { window.__puestas = []; });
  await p.click('#nutricionContent .nmodo:nth-child(2)');
  await p.click('#cmodoOk');
  await p.waitForFunction(() => window.__puestas.some(x => x.metodo === 'PUT'));
  ps = await puestas();
  ck('la nutricion llama a SU ruta', ps[0].url.endsWith('/nutrition-mode'), ps[0]);
  ck('con SU campo', JSON.parse(ps[0].cuerpo).nutrition_mode === 'calendario', ps[0].cuerpo);
  m = await modos();
  ck('ahora las dos estan en calendario', m.nut === 'calendario' && m.ent === 'calendario', m);

  // Volver una sola no puede arrastrar a la otra.
  await p.evaluate(() => { window.__puestas = []; });
  await p.click('#nutricionContent .nmodo:nth-child(1)');
  await p.click('#cmodoOk');
  await p.waitForFunction(() => window.__puestas.some(x => x.metodo === 'PUT'));
  m = await modos();
  ck('VOLVER LA NUTRICION NO TOCA EL ENTRENAMIENTO',
    m.nut === 'semanal' && m.ent === 'calendario', m);

  // ── Pulsar el modo que ya está puesto no hace nada ───────────────────────
  await p.evaluate(() => { window.__puestas = []; });
  await p.click('#entrenamientoContent .nmodo:nth-child(2)');   // ya es calendario
  ck('el modo que ya esta puesto no pregunta', !(await abierto()));
  ck('ni guarda', (await puestas()).length === 0, await puestas());

  // ── Si el servidor falla, no se finge que se ha cambiado ─────────────────
  await p.evaluate(() => { window.__falla = true; window.__puestas = []; });
  await p.click('#entrenamientoContent .nmodo:nth-child(1)');
  await p.click('#cmodoOk');
  await p.waitForFunction(() => window.__toast);
  ck('un fallo se avisa', (await p.evaluate(() => window.__toastTipo)) === 'error');
  ck('y el modo NO cambia en pantalla', (await modos()).ent === 'calendario', await modos());
  await p.evaluate(() => { window.__falla = false; });

  // ── El enfoque del calendario ────────────────────────────────────────────
  // Fija el tipo de tarea al llegar desde el modo calendario, para no acabar
  // creando otra cosa sin querer.
  const enfoque = () => p.evaluate(() => _enfoqueCalendario());
  await p.evaluate(() => __pinta('calendario', 'semanal'));
  ck('solo la nutricion en calendario -> se fijan dietas', await enfoque() === 'nutricion');
  await p.evaluate(() => __pinta('semanal', 'calendario'));
  ck('solo el entrenamiento -> se fijan rutinas', await enfoque() === 'rutina');
  await p.evaluate(() => __pinta('semanal', 'semanal'));
  ck('ninguno en calendario -> sin enfoque', await enfoque() === null);
  // Con las dos en calendario no se elige por el coach: fijar una haría la
  // otra incomoda justo cuando mas se usa.
  await p.evaluate(() => __pinta('calendario', 'calendario'));
  ck('las dos en calendario -> tampoco se fija ninguna', await enfoque() === null);
  // Y el enlace "crear otro tipo de tarea" suelta el enfoque.
  await p.evaluate(() => __pinta('semanal', 'calendario'));
  await p.evaluate(() => { _calSalirEnfoque = true; });
  ck('salir del enfoque lo suelta', await enfoque() === null);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
