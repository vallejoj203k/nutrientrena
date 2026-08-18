const { chromium } = require('../_pw');
const fs = require('fs');
const path = require('path');

/* IMPORTANTE: este banco usa el menú REAL extraído de una página, no uno
   inventado. La primera versión se escribió a mano suponiendo que los enlaces
   de Librería estaban en el HTML como .nav-sub-item[href]. No lo están: son
   categorías que abren un panel lateral cuyo contenido sale de _flyoutMenus.
   Aquella prueba pasaba en verde mientras el editor se quedaba sin menú en la
   aplicación real. */
const RAIZ = path.join(__dirname, '..', '..');
const MOD = fs.readFileSync(path.join(RAIZ, 'frontend', 'js', 'nav-roles.js'), 'utf8');
const PAGINA = fs.readFileSync(path.join(RAIZ, 'frontend', 'aliments.html'), 'utf8');
// El menú de la Librería ya no está copiado dentro de cada página: vive en su
// propio fichero, que es el que cargan las páginas. Se lee de ahí, que además
// es más honesto que sacarlo del HTML a base de contar llaves.
const FLYOUT = fs.readFileSync(path.join(RAIZ, 'frontend', 'js', 'libreria-menu.js'), 'utf8');

function trozo(marca, cierre) {
  const i = PAGINA.indexOf(marca);
  if (cierre === 'nav') return PAGINA.slice(i, PAGINA.indexOf('</nav>') + 6);
  let prof = 0, k = i;
  while (k < PAGINA.length) {
    if (PAGINA[k] === '{') prof++;
    else if (PAGINA[k] === '}') { prof--; if (!prof) { k++; break; } }
    k++;
  }
  return PAGINA.slice(i, k) + ';';
}
const NAV = trozo('<nav', 'nav');
// Pestañas de categoría y sub-pestañas: otra vía de navegación que también
// llevaba a páginas bloqueadas.
const TABS = (PAGINA.match(/<a class="lib-cat[^>]*>.*?<\/a>/gs) || []).join('\n')
           + (PAGINA.match(/<a class="lib-subtab[^>]*>.*?<\/a>/gs) || []).join('\n')
           + (PAGINA.match(/<button class="source-tab[^>]*>.*?<\/button>/gs) || []).join('\n');

for (const [nombre, txt] of [['NAV', NAV], ['TABS', TABS], ['FLYOUT', FLYOUT]]) {
  if (!txt || txt.length < 40) {
    console.error(`FALLO el banco no pudo extraer ${nombre} de la página real. ` +
                  'Si el código se ha movido de sitio, hay que actualizar el extractor: ' +
                  'seguir con un trozo vacío haría pasar la prueba sin probar nada.');
    process.exit(1);
  }
}

function pagina(rol) {
  return `<!doctype html><html><head><script>
    Object.defineProperty(window,'localStorage',{value:{getItem:()=> '${rol}',setItem(){},removeItem(){}}});
  </script></head><body>
  ${NAV}
  <div class="lib-tabs">${TABS}</div>
  <div class="sidebar-user">yo</div>
  <script>
    ${FLYOUT}
    function toggleLibrary(el){ el.classList.add('open'); }
    function openFlyout(){}
  </script>
  <script>${MOD}</script>
  </body></html>`;
}

(async () => {
  const b = await chromium.launch();
  let f = 0;
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 240))); if (!c) f++; };

  async function abrir(rol, fichero) {
    const ctx = await b.newContext();
    await ctx.route('http://nav.test/**', r => r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: pagina(rol) }));
    const p = await ctx.newPage();
    await p.goto('http://nav.test/' + fichero);
    await p.waitForTimeout(250);
    return p;
  }
  const visibles = p => p.evaluate(() =>
    [...document.querySelectorAll('.nav-item[href]')].filter(e => e.style.display !== 'none').map(e => e.getAttribute('href')));
  // Lo que el usuario ve realmente al desplegar Librería
  const alcanzables = p => p.evaluate(() => {
    const cats = [...document.querySelectorAll('#librarySub .nav-sub-item')]
      .filter(e => e.style.display !== 'none')
      .map(e => (e.getAttribute('onclick') || '').match(/openFlyout\s*\([^,]*,\s*['"]([^'"]+)['"]/))
      .filter(Boolean).map(m => m[1]);
    const out = [];
    cats.forEach(c => (_flyoutMenus[c]?.items || []).forEach(i => out.push(i.href)));
    return out.sort();
  });

  const errs = [];
  let p = await abrir(7, 'aliments.html');
  p.on('pageerror', e => errs.push(String(e)));
  await p.waitForTimeout(150);

  ck('[editor] no le queda ningún enlace suelto de primer nivel', (await visibles(p)).length === 0, await visibles(p));
  ck('[editor] Librería sigue visible y abierta',
     await p.evaluate(() => { const l = document.getElementById('navLibrary'); return l && l.style.display !== 'none' && l.classList.contains('open'); }));

  const alc = await alcanzables(p);
  ck('[editor] PUEDE LLEGAR a alimentos y ejercicios',
     JSON.stringify(alc) === JSON.stringify(['aliments.html', 'ejercicios.html']), alc);
  ck('[editor] no llega a rutinas, dietas ni grupos musculares',
     !alc.includes('rutinas.html') && !alc.includes('diets.html') && !alc.includes('grupos-musculares.html'), alc);

  const cats = await p.evaluate(() => [...document.querySelectorAll('#librarySub .nav-sub-item')]
    .filter(e => e.style.display !== 'none').map(e => e.textContent.trim().replace(/\s+/g, ' ')));
  ck('[editor] solo quedan las categorías con algo dentro', cats.length === 2, cats);

  const secs = await p.evaluate(() => [...document.querySelectorAll('.nav-section')].filter(e => e.style.display !== 'none').map(e => e.textContent.trim()));
  ck('[editor] las secciones vacías se ocultan', secs.length === 1, secs);

  // Las pestañas de categoría: reapuntadas o escondidas, nunca a un sitio vetado
  const tabs = await p.evaluate(() => [...document.querySelectorAll('.lib-cat')]
    .filter(e => e.style.display !== 'none')
    .map(e => [e.textContent.trim(), e.getAttribute('href')]));
  ck('[editor] "Entrenamiento" lleva a Ejercicios, no a Rutinas',
     tabs.some(t => /Entrenamiento/.test(t[0]) && t[1] === 'ejercicios.html'), tabs);
  ck('[editor] "Nutrición" lleva a Alimentos, no a Dietas',
     tabs.some(t => /Nutrici/.test(t[0]) && t[1] === 'aliments.html'), tabs);
  ck('[editor] las pestañas sin nada permitido se ocultan', tabs.length === 2, tabs);
  ck('[editor] ninguna pestaña apunta a una página vetada',
     tabs.every(t => ['aliments.html', 'ejercicios.html'].includes(t[1])), tabs);

  const subs = await p.evaluate(() => [...document.querySelectorAll('.lib-subtab')]
    .filter(e => e.style.display !== 'none').map(e => e.getAttribute('href')));
  ck('[editor] las sub-pestañas solo dejan lo permitido',
     subs.every(h => ['aliments.html', 'ejercicios.html'].includes((h || '').split('?')[0])), subs);

  // Al coach no se le toca ninguna pestaña
  const pCoach = await abrir(5, 'aliments.html');
  const tabsCoach = await pCoach.evaluate(() => [...document.querySelectorAll('.lib-cat')]
    .filter(e => e.style.display !== 'none').map(e => e.getAttribute('href')));
  const fuentesCoach = await pCoach.evaluate(() => [...document.querySelectorAll('.source-tab')]
    .filter(e => e.style.display !== 'none').length);
  ck('[coach] conserva el filtro Personal', fuentesCoach === 2, fuentesCoach);
  ck('[coach] conserva las 4 pestañas intactas',
     tabsCoach.length === 4 && tabsCoach.includes('rutinas.html') && tabsCoach.includes('diets.html'), tabsCoach);

  const fuentes = await p.evaluate(() => [...document.querySelectorAll('.source-tab')]
    .filter(e => e.style.display !== 'none').map(e => e.textContent.trim()));
  ck('[editor] el filtro "Personal" se oculta: no gestiona clientes',
     fuentes.length === 1 && /Plataforma/.test(fuentes[0]), fuentes);

  const pRedir = await abrir(7, 'dashboard.html');
  await pRedir.waitForTimeout(400);
  ck('[editor] entrar en dashboard lo lleva a alimentos', pRedir.url().endsWith('/aliments.html'), pRedir.url());

  p = await abrir(5, 'dashboard.html');
  const v5 = await visibles(p);
  ck('[coach] NO ve equipo, ajustes ni analíticas',
     !v5.includes('coaches.html') && !v5.includes('settings.html') && !v5.includes('analytics.html'), v5);
  ck('[coach] SÍ ve clientes', v5.includes('clients.html'), v5);
  const alc5 = await alcanzables(p);
  ck('[coach] conserva la biblioteca entera', alc5.includes('rutinas.html') && alc5.includes('diets.html'), alc5);

  for (const rol of [1, 2]) {
    p = await abrir(rol, 'dashboard.html');
    const ocultos = await p.evaluate(() =>
      [...document.querySelectorAll('.nav-item,.nav-sub-item,.nav-section')].filter(e => e.style.display === 'none').length);
    ck(`[rol ${rol}] no se le oculta nada`, ocultos === 0, { ocultos });
  }

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
