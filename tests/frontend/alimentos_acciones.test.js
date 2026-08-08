const { chromium } = require('../_pw');
const fs = require('fs');
const path = require('path');

/* Qué acciones OFRECE la lista de alimentos según el rol.

   Ninguna prueba cubría esto y se coló un fallo evidente al usarlo: el editor
   de contenido global veía "Solo lectura" en todas las filas del catálogo de
   plataforma, que es justamente lo único que puede editar. El backend le
   dejaba; la pantalla no se lo ofrecía. */
const PAGINA = fs.readFileSync(path.join(__dirname, '..', '..', 'frontend', 'aliments.html'), 'utf8');

/* Se extraen las DOS líneas reales que deciden, no una copia a mano. Si
   alguien las cambia en la página, esta prueba cambia con ellas. */
const L_ADMIN = PAGINA.match(/const _isAdmin = [^;]+;/)[0];
const L_CANEDIT = PAGINA.match(/const canEdit = [^;]+;/)[0];

(async () => {
  const b = await chromium.launch();
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 200))); if (!c) f++; };

  const p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.setContent('<!doctype html><html><body><script>window.__rol="0";</script></body></html>');

  // Se reproduce el cálculo tal cual está en la página, con el rol variable.
  const puedeEditar = (rol, alimento) => p.evaluate(([r, a, lAdmin, lCan]) => {
    var _rid = r;
    var isPlatformAdmin = a._source !== 'personal' && a.organization_id == null;
    var _isAdmin, canEdit;
    eval(lAdmin.replace('const ', ''));
    eval(lCan.replace('const ', ''));
    return canEdit;
  }, [rol, alimento, L_ADMIN, L_CANEDIT]);

  const PLATAFORMA = { _source: 'plataforma', organization_id: null };
  const DE_ORG     = { _source: 'plataforma', organization_id: 'o1' };
  const PERSONAL   = { _source: 'personal', organization_id: null };

  ck('[editor] PUEDE editar el catálogo de plataforma', await puedeEditar(7, PLATAFORMA) === true);
  ck('[superadmin] puede', await puedeEditar(1, PLATAFORMA) === true);
  ck('[admin] puede', await puedeEditar(2, PLATAFORMA) === true);
  ck('[coach] NO puede tocar el catálogo de plataforma', await puedeEditar(5, PLATAFORMA) === false);
  ck('[coach] sí puede con lo de su organización', await puedeEditar(5, DE_ORG) === true);
  ck('[coach] sí puede con sus alimentos personales', await puedeEditar(5, PERSONAL) === true);

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
