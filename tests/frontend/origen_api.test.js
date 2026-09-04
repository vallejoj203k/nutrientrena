/* A qué servidor le habla la aplicación.

   El dominio estaba escrito a mano en cuarenta y ocho ficheros. Con eso,
   servir la web en un dominio nuevo —app.alzum.io— dejaba a todas las páginas
   llamando al viejo: funciona mientras la lista de orígenes permitidos lo
   consienta, y se cae entera el día que ese dominio cambie.

   Ahora la API es la que sirve la página, y eso se comprueba de verdad:
   sirviendo el frontend por HTTP y mirando qué dice cada pantalla.

   Lo que hay que dejar sujeto:

     · Que la API salga del origen desde el que se sirve la página.
     · Que TODAS las páginas carguen el módulo que lo decide, incluidas las que
       hoy no llaman a la API: cargan piezas compartidas que sí.
     · Y que no vuelva a aparecer el dominio escrito a mano.
*/
const { chromium } = require('../_pw');
const http = require('http');
const fs = require('fs');
const path = require('path');

const RAIZ = path.join(__dirname, '..', '..', 'frontend');
const TIPOS = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css' };

// Un puñado representativo: coach, cliente, pública y la de administración.
const PAGINAS = ['dashboard.html', 'login.html', 'diets.html', 'chat.html',
                 'client-nutricion.html', 'events.html',
                 'admin/index.html', 'public/form.html'];

(async () => {
  const servidor = http.createServer((req, res) => {
    const f = path.join(RAIZ, decodeURIComponent(req.url.split('?')[0]));
    fs.readFile(f, (e, d) => {
      if (e) { res.writeHead(404); res.end(); return; }
      res.writeHead(200, { 'Content-Type': TIPOS[path.extname(f)] || 'text/plain' });
      res.end(d);
    });
  });
  await new Promise(r => servidor.listen(0, '127.0.0.1', r));
  const origen = 'http://127.0.0.1:' + servidor.address().port;

  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + JSON.stringify(x))); if (!c) f++; };

  const b = await chromium.launch();
  for (const pagina of PAGINAS) {
    const p = await b.newPage();
    const errs = [];
    p.on('pageerror', e => errs.push(String(e)));
    await p.addInitScript(() => {
      localStorage.setItem('token', 't'); localStorage.setItem('role_id', '1');
      window.fetch = async () => ({ status: 200, ok: true, json: async () => ({ data: {} }) });
    });
    await p.goto(origen + '/' + pagina, { waitUntil: 'domcontentloaded' });
    await p.waitForTimeout(250);

    const base = await p.evaluate(() => window.API_BASE || null);
    ck(pagina + ': la API es quien sirve la página', base === origen + '/api', base);
    const rotos = errs.filter(e => /is not defined|before initialization/.test(e));
    ck(pagina + ': sin variables sin definir', rotos.length === 0, rotos);
    await p.close();
  }

  // El websocket del chat cuelga del mismo sitio, en su esquema.
  const p = await b.newPage();
  await p.goto(origen + '/chat.html', { waitUntil: 'domcontentloaded' });
  ck('el websocket también va al mismo servidor',
    await p.evaluate(() => window.WS_BASE) === origen.replace('http', 'ws') + '/ws/chat',
    await p.evaluate(() => window.WS_BASE));
  await p.close();
  await b.close();
  servidor.close();

  // ── Y que no quede el dominio a mano ─────────────────────────────────────
  const conDominio = [];
  const mirar = (dir) => fs.readdirSync(dir, { withFileTypes: true }).forEach(e => {
    const completo = path.join(dir, e.name);
    if (e.isDirectory()) { if (e.name !== 'node_modules') mirar(completo); return; }
    if (!/\.(html|js)$/.test(e.name)) return;
    if (completo.endsWith(path.join('js', 'api-base.js'))) return;   // ahí vive el respaldo
    if (fs.readFileSync(completo, 'utf8').includes('nutrientrena-production')) {
      conDominio.push(path.relative(RAIZ, completo));
    }
  });
  mirar(RAIZ);
  ck('NINGUNA página lleva el dominio escrito a mano', conDominio.length === 0, conDominio);

  // Todas las páginas cargan el módulo: las que hoy no llaman a la API cargan
  // piezas compartidas que sí, y el fallo no se ve hasta que revienta.
  const sinModulo = [];
  const paginas = (dir, pre) => fs.readdirSync(dir, { withFileTypes: true }).forEach(e => {
    if (e.isDirectory()) { if (['admin', 'public'].includes(e.name)) paginas(path.join(dir, e.name), e.name + '/'); return; }
    if (!e.name.endsWith('.html')) return;
    const s = fs.readFileSync(path.join(dir, e.name), 'utf8');
    if (s.includes('<script') && !s.includes('js/api-base.js')) sinModulo.push(pre + e.name);
  });
  paginas(RAIZ, '');
  ck('y todas cargan js/api-base.js', sinModulo.length === 0, sinModulo);

  process.exit(f ? 1 : 0);
})();
