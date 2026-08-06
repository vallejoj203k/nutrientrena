const { chromium } = require('../_pw');
const fs = require('fs');
const path = require('path');

const MOD = fs.readFileSync(path.join(__dirname, '..', '..', 'frontend', 'js', 'org-context.js'), 'utf8');

/* Página mínima con el hueco del menú donde se engancha el selector.
   `almacen` precarga localStorage (que no funciona en el origen opaco de
   setContent) y `contextos` es lo que devolverá /organizations/switchable. */
function pagina(almacen, contextos) {
  return `<!doctype html><html><head><script>
    (function(){
      var store = ${JSON.stringify(almacen)};
      Object.defineProperty(window,'localStorage',{value:{
        getItem:k=>(k in store?store[k]:null),
        setItem:(k,v)=>{store[k]=String(v);},
        removeItem:k=>{delete store[k];}
      }});
      window.__store = store;
      window.__peticiones = [];
      window.fetch = function(u, o){
        var url = typeof u==='string'?u:(u&&u.url)||'';
        var h = new Headers((o&&o.headers)||{});
        window.__peticiones.push({url:url, org:h.get('X-Organization-Id')});
        if(url.indexOf('switchable')!==-1){
          return Promise.resolve({ok:true, json:()=>Promise.resolve({data:${JSON.stringify(contextos)}})});
        }
        return Promise.resolve({ok:true, json:()=>Promise.resolve({data:{}})});
      };
      // location.reload rompería la prueba: se anota y ya.
      window.__recargas = 0;
    })();
  </script>
  <script>${MOD}</script>
  </head><body>
  <div class="sidebar-user"><div class="user-name">Alguien</div></div>
  </body></html>`;
}

(async () => {
  const b = await chromium.launch();
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 220))); if (!c) f++; };

  const DOS = { puede_actuar_como_plataforma: true, organizaciones: [{ id: 'o1', name: 'NutriEntrena' }, { id: 'o2', name: 'Centro Alfa' }] };
  const UNA = { puede_actuar_como_plataforma: false, organizaciones: [{ id: 'o1', name: 'NutriEntrena' }] };

  // ── Super-admin: varias opciones
  let p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.setContent(pagina({ token: 't' }, DOS));
  await p.waitForTimeout(300);

  ck('el selector aparece', await p.locator('#orgCtxSel').count() === 1);
  const ops = await p.locator('#orgCtxSel option').allTextContents();
  ck('incluye plataforma y las organizaciones',
    JSON.stringify(ops) === JSON.stringify(['Plataforma (todo)', 'NutriEntrena', 'Centro Alfa']), ops);
  ck('va colocado dentro del menú', await p.locator('.org-ctx').count() === 1);

  const switchReq = await p.evaluate(() => window.__peticiones.find(r => r.url.indexOf('switchable') !== -1));
  ck('la propia consulta de contextos NO lleva cabecera', switchReq && switchReq.org === null, switchReq);

  // ── Con un contexto elegido, la cabecera entra en todas las llamadas
  p = await b.newPage();
  await p.setContent(pagina({ token: 't', org_context: 'o2' }, DOS));
  await p.waitForTimeout(300);
  const res = await p.evaluate(async () => {
    await fetch('https://nutrientrena-production.up.railway.app/api/diets/findAll', { headers: { Authorization: 'Bearer t' } });
    await fetch('/api/routines/findAll');
    await fetch('https://otro-servicio.com/api/cosas');   // tercero
    return window.__peticiones.slice(-3);
  });
  ck('cabecera en la llamada absoluta a nuestra API', res[0].org === 'o2', res[0]);
  ck('cabecera en la llamada relativa /api/', res[1].org === 'o2', res[1]);
  ck('NO se toca la petición a un tercero', res[2].org === null, res[2]);
  ck('el selector recuerda lo elegido', await p.inputValue('#orgCtxSel') === 'o2');

  // ── Sin contexto (plataforma): sin cabecera
  p = await b.newPage();
  await p.setContent(pagina({ token: 't' }, DOS));
  await p.waitForTimeout(300);
  const sin = await p.evaluate(async () => {
    await fetch('https://nutrientrena-production.up.railway.app/api/diets/findAll');
    return window.__peticiones.slice(-1)[0];
  });
  ck('actuando como plataforma no manda cabecera', sin.org === null, sin);

  // ── Un solo contexto: nada de selector
  p = await b.newPage();
  await p.setContent(pagina({ token: 't' }, UNA));
  await p.waitForTimeout(300);
  ck('con una sola opción NO se pinta el selector', await p.locator('#orgCtxSel').count() === 0);

  // ── Contexto guardado que ya no existe: se limpia
  p = await b.newPage();
  await p.setContent(pagina({ token: 't', org_context: 'borrada' }, DOS));
  await p.waitForTimeout(300);
  ck('un contexto que ya no existe se descarta',
    await p.evaluate(() => window.__store.org_context) === undefined,
    await p.evaluate(() => window.__store.org_context));
  const tras = await p.evaluate(async () => {
    await fetch('https://nutrientrena-production.up.railway.app/api/diets/findAll');
    return window.__peticiones.slice(-1)[0];
  });
  ck('y deja de mandarse esa cabecera', tras.org === null, tras);

  // ── Sin sesión: ni selector ni consulta
  p = await b.newPage();
  await p.setContent(pagina({}, DOS));
  await p.waitForTimeout(250);
  ck('sin sesión no consulta ni pinta',
    await p.locator('#orgCtxSel').count() === 0 && (await p.evaluate(() => window.__peticiones.length)) === 0);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
