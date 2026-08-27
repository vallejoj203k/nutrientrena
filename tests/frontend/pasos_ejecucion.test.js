/* La ejecución de un ejercicio, leída como la escribió el autor.

   La pantalla numeraba TODAS las líneas, una por una. Eso vale mientras se
   escriban pasos sueltos, que es como está el catálogo de siempre. En cuanto
   alguien da estructura a lo que escribe se rompe de tres formas a la vez, y
   las tres salían juntas en la misma captura:

     · numeró a mano y salió "1. 1. Siéntate…";
     · puso el título "⚠ Errores comunes" y salió como el paso 5;
     · puso viñetas y salieron como los pasos 6, 7, 8 y 9.

   Lo que NO puede pasar al arreglarlo: que los ejercicios ya escritos —líneas
   sueltas, sin números ni viñetas— dejen de numerarse. Son la mayoría del
   catálogo y hoy se ven bien. */
const { chromium } = require('../_pw');

// El texto exacto de la captura, tal cual lo escribió el cliente.
const REAL = [
  '1. Siéntate con la espalda apoyada y las almohadillas en la cara interna de los muslos.',
  '2. Cierra las piernas juntando los muslos contra la resistencia.',
  '3. Aprieta al final del recorrido.',
  '4. Abre controlado sin dejar caer el peso. Repite.',
  '',
  '⚠ Errores comunes',
  '',
  '- Abrir demasiado al inicio y forzar la ingle.',
  '- Usar impulso.',
  '- Recorrido corto.',
  '- Cerrar de golpe.',
].join('\n');

(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/pasos.html');
  let f = 0; const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };

  const pinta = async t => { await p.evaluate(v => __pinta(v), t); };
  const pasos = () => p.$$eval('.xv-step', ns => ns.map(n => n.textContent.trim()));
  const nums = () => p.$$eval('.xv-step-num', ns => ns.map(n => n.textContent.trim()));
  const vinetas = () => p.$$eval('.xv-bullet', ns => ns.map(n => n.textContent.replace('·', '').trim()));
  const titulos = () => p.$$eval('.xv-step-title', ns => ns.map(n => n.textContent.trim()));

  // ── El caso de la captura ────────────────────────────────────────────────
  await pinta(REAL);

  ck('4 pasos, no 9', (await pasos()).length === 4, await pasos());
  ck('numerados 1 2 3 4', JSON.stringify(await nums()) === '["1.","2.","3.","4."]', await nums());
  ck('NO SALE EL NUMERO DOS VECES',
    !(await pasos()).some(s => /^\d+\.\s*\d+\./.test(s)), await pasos());
  // `textContent` pega el número y el texto sin espacio: "1." + "Siéntate…".
  ck('el primer paso es el texto sin su número',
    (await pasos())[0] === '1.Siéntate con la espalda apoyada y las almohadillas en la cara interna de los muslos.',
    (await pasos())[0]);
  ck('"Errores comunes" es un título, no el paso 5',
    JSON.stringify(await titulos()) === '["⚠ Errores comunes"]', await titulos());
  ck('las 4 viñetas son viñetas', (await vinetas()).length === 4, await vinetas());
  ck('ninguna viñeta lleva número',
    !(await pasos()).some(s => s.includes('Usar impulso')), await pasos());

  // ── Lo que ya estaba escrito, que no se puede tocar ──────────────────────
  await pinta('Siéntate en el banco.\nEmpuja la barra.\nBaja controlado.');
  ck('SIN NUMEROS NI VIÑETAS SE SIGUE NUMERANDO TODO',
    JSON.stringify(await nums()) === '["1.","2.","3."]', await nums());
  ck('y no aparecen títulos donde antes había pasos', (await titulos()).length === 0, await titulos());

  // ── Bordes ──────────────────────────────────────────────────────────────
  await pinta('');
  ck('una descripción vacía no pinta nada', (await pasos()).length === 0 && (await titulos()).length === 0);

  await pinta('1) Coge la barra.\n2- Levanta.');
  ck('también con "1)" y "2-"', JSON.stringify(await nums()) === '["1.","2."]', await nums());

  await pinta('- Solo una viñeta.');
  ck('una viñeta suelta no se numera', (await pasos()).length === 0 && (await vinetas()).length === 1,
    { pasos: await pasos(), vinetas: await vinetas() });

  await pinta('3. Empieza por el tres.\n7. Y sigue por el siete.');
  ck('se renumera seguido aunque el autor se salte números',
    JSON.stringify(await nums()) === '["1.","2."]', await nums());

  await pinta('Levanta 10 kg. Baja 5 kg.');
  ck('un número dentro del texto no se confunde con una numeración',
    JSON.stringify(await pasos()) === '["1.Levanta 10 kg. Baja 5 kg."]', await pasos());

  await pinta('<b>Ojo</b> con esto\n- <script>x</script>');
  const html = await p.innerHTML('#out');
  ck('el texto del autor no se interpreta como HTML',
    !html.includes('<b>Ojo') && !html.includes('<script>x'), html.slice(0, 200));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close(); process.exit(f ? 1 : 0);
})();
