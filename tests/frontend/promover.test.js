const { chromium } = require('../_pw');
const fs = require('fs');
const path = require('path');

/* _puedePromover decide si se ofrece la acción. El backend responde 403 a quien
   no puede, pero enseñar un botón que siempre falla es prometer lo que no se
   puede cumplir — el mismo fallo que ya se corrigió en el botón Editar. */
function extraer(fichero, marca, fin) {
  const s = fs.readFileSync(path.join(__dirname, '..', '..', 'frontend', fichero), 'utf8');
  const i = s.indexOf(marca);
  return s.slice(i, s.indexOf(fin, i));
}

(async () => {
  const b = await chromium.launch();
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 200))); if (!c) f++; };

  for (const [fichero, marca, fin, etiqueta] of [
    ['diets.html', 'function _puedePromover(d)', 'async function promover', 'dietas'],
    ['rutinas.html', 'function _puedePromover(r)', 'async function promover', 'rutinas'],
  ]) {
    const fn = extraer(fichero, marca, fin);
    const p = await b.newPage();
    const errs = []; p.on('pageerror', e => errs.push(String(e)));
    await p.setContent(`<!doctype html><html><body><script>
      var __rol='1';
      Object.defineProperty(window,'localStorage',{value:{getItem:k=>k==='role_id'?__rol:null,setItem(){},removeItem(){}}});
      ${fn}
      window.__setRol=function(v){__rol=v;};
    </script></body></html>`);

    const puede = async (obj, rol) => {
      await p.evaluate(r => window.__setRol(r), rol);
      return p.evaluate(o => _puedePromover(o), obj);
    };

    ck(`[${etiqueta}] superadmin puede promover contenido de una organización`, await puede({ organization_id: 'o1' }, '1'));
    ck(`[${etiqueta}] admin también`, await puede({ organization_id: 'o1' }, '2'));
    ck(`[${etiqueta}] un coach NO`, (await puede({ organization_id: 'o1' }, '5')) === false);
    ck(`[${etiqueta}] lo que ya es de plataforma no se promueve`, (await puede({ organization_id: null }, '1')) === false);
    ck(`[${etiqueta}] sin objeto no revienta`, (await puede(null, '1')) === false);
    ck(`[${etiqueta}] sin errores de JS`, errs.length === 0, errs);
  }

  await b.close();
  process.exit(f ? 1 : 0);
})();
