/* El chat con el cliente, dentro de su ficha.

   La idea es entrar a la conversación que YA existe con esa persona, no
   empezar otra. Por eso el panel pide `/chat/con/{id}` en vez de buscarla
   entre las conversaciones cargadas: dos conversaciones con el mismo cliente
   dejan los mensajes repartidos, y cada uno creyendo que el otro no contesta.

   Y lo otro que se comprueba aquí es lo que se pierde cuando algo falla: un
   mensaje escrito y no enviado no puede desaparecer de la caja.
*/
const { chromium } = require('../_pw');

const msg = (id, de, texto, cuando) => ({
  id, sender_user_id: de, content: texto, created_at: cuando,
});

// 77 es el cliente (lo dice `clientData.user_id`); 9 soy yo.
const HILO = [
  msg(1, 77, 'Hola, listo para arrancar la semana', '2026-09-03T09:12:00'),
  msg(2, 9, '¡Genial! Recuerda subir el check-in del viernes.', '2026-09-03T09:14:00'),
  msg(3, 77, 'Hecho. Te subo también las fotos.', '2026-09-03T09:16:00'),
];

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.setViewportSize({ width: 900, height: 800 });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + __dirname + '/chatficha.html');
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };
  const llamadas = () => p.evaluate(() => window.__llamadas);
  const burbujas = () => p.$$eval('.cp-msg', ns => ns.map(n => ({
    txt: (n.childNodes[0].textContent || '').trim(),
    mio: n.classList.contains('mio'),
    hora: (n.querySelector('.cp-msg-h') || {}).textContent,
  })));

  // ── Abre la conversación que ya existe ───────────────────────────────────
  await p.evaluate(m => { __reset(m); return cpChatAbrir(); }, HILO);
  const l = await llamadas();
  ck('PIDE LA CONVERSACION CON ESE CLIENTE, no crea otra',
    l[0].url.endsWith('/chat/con/77') && l[0].metodo === 'GET', l[0]);
  // Crear una conversación es un POST a `/chat/conversations` a secas; el
  // `read` y el envío cuelgan de una que ya existe.
  ck('y no llama a crear conversaciones',
    !l.some(x => x.metodo === 'POST' && /\/chat\/conversations$/.test(x.url)), l);
  ck('luego pide sus mensajes',
    l.some(x => x.url.includes('/conversations/conv-1/messages') && x.metodo === 'GET'), l);
  // Abrir el chat es haberlo leído: dejar el aviso encendido con la
  // conversación delante es contar mensajes que ya se han visto.
  ck('y los marca como leidos',
    l.some(x => x.url.endsWith('/conversations/conv-1/read')), l);

  // ── Los mensajes ─────────────────────────────────────────────────────────
  const bs = await burbujas();
  ck('salen los tres mensajes', bs.length === 3, bs);
  ck('el del cliente a la izquierda', bs[0].txt.startsWith('Hola') && !bs[0].mio, bs[0]);
  ck('y el mio a la derecha', bs[1].mio, bs[1]);
  ck('el tercero es suyo otra vez', !bs[2].mio, bs[2]);
  ck('cada uno con su hora', /\d{2}:\d{2}/.test(bs[0].hora || ''), bs[0]);
  ck('y el dia se separa una sola vez',
    await p.locator('.cp-chat-dia').count() === 1, await p.locator('.cp-chat-dia').count());

  ck('la cabecera dice con quien se habla',
    (await p.textContent('#cpChatTitulo')).includes('Carlos'), await p.textContent('#cpChatTitulo'));

  // ── Enviar ───────────────────────────────────────────────────────────────
  await p.fill('#cpChatIn', 'Nos vemos el lunes');
  await p.click('#cpChatSend');
  await p.waitForFunction(() => window.__llamadas.some(
    x => x.metodo === 'POST' && x.url.includes('/messages')));
  const env = (await llamadas()).find(x => x.metodo === 'POST' && x.url.includes('/messages'));
  ck('el mensaje va a ESA conversacion', env.url.includes('/conversations/conv-1/'), env);
  ck('con lo que se escribio', JSON.parse(env.cuerpo).content === 'Nos vemos el lunes', env.cuerpo);
  ck('y la caja se vacia', (await p.inputValue('#cpChatIn')) === '');
  ck('se recargan los mensajes despues de enviar',
    (await llamadas()).filter(x => x.metodo === 'GET' && x.url.includes('/messages')).length === 2,
    await llamadas());

  // Enter envía; con Shift no.
  await p.evaluate(m => { __reset(m); return cpChatAbrir(); }, HILO);
  await p.fill('#cpChatIn', 'Con Enter');
  await p.press('#cpChatIn', 'Enter');
  await p.waitForFunction(() => window.__llamadas.some(
    x => x.metodo === 'POST' && x.url.includes('/messages')));
  ck('Enter envia', true);

  // ── Si el envío falla, el texto NO se pierde ─────────────────────────────
  await p.evaluate(m => { __reset(m); return cpChatAbrir(); }, HILO);
  await p.evaluate(() => { window.__falla = '/messages'; });
  await p.fill('#cpChatIn', 'Esto no se puede perder');
  await p.click('#cpChatSend');
  await p.waitForFunction(() => window.__toast);
  ck('un fallo al enviar se avisa',
    (await p.evaluate(() => window.__toastTipo)) === 'error', await p.evaluate(() => window.__toast));
  ck('Y EL MENSAJE SIGUE EN LA CAJA',
    (await p.inputValue('#cpChatIn')) === 'Esto no se puede perder', await p.inputValue('#cpChatIn'));
  ck('el boton vuelve a poder pulsarse',
    !(await p.evaluate(() => document.getElementById('cpChatSend').disabled)));
  await p.evaluate(() => { window.__falla = null; });

  // Un mensaje vacío no se manda.
  await p.evaluate(m => { __reset(m); return cpChatAbrir(); }, HILO);
  await p.fill('#cpChatIn', '   ');
  await p.click('#cpChatSend');
  ck('un mensaje en blanco no se envia',
    !(await llamadas()).some(x => x.metodo === 'POST' && x.url.includes('/messages')),
    await llamadas());

  // ── Sin mensajes ─────────────────────────────────────────────────────────
  await p.evaluate(() => { __reset([]); return cpChatAbrir(); });
  ck('sin mensajes se dice, no se deja en blanco',
    (await p.textContent('.cp-chat-vacio')).includes('Todavía no hay mensajes'),
    await p.textContent('.cp-chat-vacio'));

  // ── Si no se puede abrir ─────────────────────────────────────────────────
  await p.evaluate(() => { __reset([]); window.__falla = '/chat/con/'; return cpChatAbrir(); });
  ck('un fallo al abrir se dice y se puede reintentar',
    (await p.textContent('#cpChatMsgs')).includes('No se ha podido abrir'),
    await p.textContent('#cpChatMsgs'));
  await p.evaluate(() => { window.__falla = null; });

  // ── El interruptor ───────────────────────────────────────────────────────
  await p.evaluate(m => { __reset(m); return cpChatAbrir(); }, HILO);
  ck('el interruptor arranca encendido',
    await p.evaluate(() => document.getElementById('cpChatSw').checked));
  ck('y lo dice', (await p.textContent('#cpChatEstado')).includes('puede escribirte'),
    await p.textContent('#cpChatEstado'));

  await p.evaluate(() => { __reset([], false); return cpChatAbrir(); });
  ck('con el chat apagado, el interruptor lo refleja',
    !(await p.evaluate(() => document.getElementById('cpChatSw').checked)));
  ck('y el texto tambien',
    (await p.textContent('#cpChatEstado')).includes('no puede escribirte'),
    await p.textContent('#cpChatEstado'));
  // Apagarlo le corta el canal al CLIENTE; el coach sigue pudiendo escribirle
  // para avisarle de que lo ha hecho.
  ck('pero el coach sigue pudiendo escribir',
    !(await p.evaluate(() => document.getElementById('cpChatIn').disabled)));

  // ── Escapado ─────────────────────────────────────────────────────────────
  await p.evaluate(() => { __reset([{ id: 1, sender_user_id: 77,
    content: '<img src=x onerror=alert(1)>', created_at: '2026-09-03T09:00:00' }]);
    return cpChatAbrir(); });
  ck('escapa el HTML de los mensajes',
    (await p.innerHTML('#cpChatMsgs')).includes('&lt;img'), await p.textContent('.cp-msg'));

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
