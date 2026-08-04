const { chromium } = require('../_pw');
const fs = require('fs');
const path = require('path');

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 200))); if (!c) f++; };

  const modulo = fs.readFileSync(path.join(__dirname, '..', '..', 'frontend', 'js', 'chat-badge.js'), 'utf8');

  // Página mínima con el enlace de chat. Se acelera el reloj (setInterval con
  // un tope de 120 ms) para no esperar 20 s reales, y se cuenta cada petición.
  const html = `<!doctype html><html><body>
  <a href="chat.html">Chat</a>
  <script>
    // localStorage no está disponible en el origen opaco de setContent, así
    // que se dobla: lo que se prueba es el sondeo, no el almacenamiento.
    Object.defineProperty(window, 'localStorage', { value: { getItem: () => 't', setItem(){}, removeItem(){} } });
    window.__llamadas = 0;
    window.__oculto = false;
    Object.defineProperty(document, 'hidden', { get: () => window.__oculto });
    const _si = window.setInterval;
    window.setInterval = (fn, ms) => _si(fn, Math.min(ms, 120));
    window.fetch = () => { window.__llamadas++; return Promise.resolve({ json: () => Promise.resolve({ data: { total: 3 } }) }); };
  </script>
  <script>${modulo}</script>
  </body></html>`;

  await p.setContent(html);
  await p.waitForTimeout(400);

  ck('el globito se pinta con el número', (await p.textContent('[data-chat-unread]')) === '3');
  const visible = await p.evaluate(() => getComputedStyle(document.querySelector('[data-chat-unread]')).display);
  ck('y se muestra', visible !== 'none', visible);

  const conVista = await p.evaluate(() => window.__llamadas);
  ck('con la pestaña a la vista, sondea', conVista >= 2, conVista);

  // Ocultar la pestaña
  await p.evaluate(() => { window.__oculto = true; document.dispatchEvent(new Event('visibilitychange')); });
  const alOcultar = await p.evaluate(() => window.__llamadas);
  await p.waitForTimeout(600);
  const trasEsperar = await p.evaluate(() => window.__llamadas);
  ck('OCULTA: el sondeo se para del todo', trasEsperar === alOcultar, { alOcultar, trasEsperar });

  // Volver a mostrarla
  await p.evaluate(() => { window.__oculto = false; document.dispatchEvent(new Event('visibilitychange')); });
  await p.waitForTimeout(60);
  const alVolver = await p.evaluate(() => window.__llamadas);
  ck('al volver, pide dato fresco enseguida', alVolver > trasEsperar, { trasEsperar, alVolver });
  await p.waitForTimeout(400);
  ck('y reanuda el sondeo', (await p.evaluate(() => window.__llamadas)) > alVolver);

  // Mostrar dos veces seguidas no debe duplicar temporizadores
  await p.evaluate(() => { document.dispatchEvent(new Event('visibilitychange')); document.dispatchEvent(new Event('visibilitychange')); });
  const antes = await p.evaluate(() => window.__llamadas);
  await p.waitForTimeout(500);
  const despues = await p.evaluate(() => window.__llamadas);
  ck('no se duplican temporizadores', despues - antes <= 6, { antes, despues });

  ck('sigue expuesta window.refreshChatUnread', await p.evaluate(() => typeof window.refreshChatUnread) === 'function');

  // Sin sesión no debe pedir nada
  const p2 = await b.newPage();
  await p2.setContent(`<!doctype html><html><body><a href="chat.html">Chat</a>
    <script>Object.defineProperty(window,'localStorage',{value:{getItem:()=>null,setItem(){},removeItem(){}}});window.__llamadas=0;window.fetch=()=>{window.__llamadas++;return Promise.resolve({json:()=>Promise.resolve({})});};</script>
    <script>${modulo}</script></body></html>`);
  await p2.waitForTimeout(300);
  ck('sin sesión no pide nada', await p2.evaluate(() => window.__llamadas) === 0);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
