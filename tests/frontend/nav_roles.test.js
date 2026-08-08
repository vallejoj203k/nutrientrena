const { chromium } = require('../_pw');
const fs = require('fs');
const path = require('path');

const MOD = fs.readFileSync(path.join(__dirname, '..', '..', 'frontend', 'js', 'nav-roles.js'), 'utf8');

/* Menú equivalente al real: secciones, enlaces y el desplegable de Librería. */
function pagina(rol) {
  return `<!doctype html><html><head><script>
    Object.defineProperty(window,'localStorage',{value:{getItem:()=> '${rol}',setItem(){},removeItem(){}}});
    window.__redirigido=null;
    // location.replace no se puede espiar; se sustituye la función del módulo
    // observando el efecto: se anota en vez de navegar.
  </script></head><body>
  <nav>
    <div class="nav-section">Principal</div>
    <a class="nav-item" href="dashboard.html">Inicio</a>
    <a class="nav-item" href="events.html">Mi Calendario</a>
    <a class="nav-item" href="clients.html">Clientes</a>
    <a class="nav-item" href="checkins.html">Check-ins</a>
    <div class="nav-section">Contenido</div>
    <div class="nav-item nav-dropdown" id="navLibrary">Librería</div>
    <div id="librarySub">
      <a class="nav-sub-item" href="rutinas.html">Rutinas</a>
      <a class="nav-sub-item" href="ejercicios.html">Ejercicios</a>
      <a class="nav-sub-item" href="aliments.html">Alimentos</a>
      <a class="nav-sub-item" href="diets.html">Dietas</a>
      <a class="nav-sub-item" href="grupos-musculares.html">Grupos musculares</a>
    </div>
    <div class="nav-section">Negocio</div>
    <a class="nav-item" href="analytics.html">Analíticas</a>
    <a class="nav-item" href="coaches.html">Equipo</a>
    <a class="nav-item" href="mi-organizacion.html">Mi Organización</a>
    <div class="nav-section">Cuenta</div>
    <a class="nav-item" href="settings.html">Ajustes</a>
  </nav>
  <div class="sidebar-user">yo</div>
  <script>function toggleLibrary(el){el.classList.add('open');}</script>
  <script>${MOD}</script>
  </body></html>`;
}

(async () => {
  const b = await chromium.launch();
  let f = 0;

  /* Se sirve el harness en una ruta REAL (no setContent) porque el módulo mira
     location.pathname para decidir si redirige: con about:blank redirigiría
     siempre y no se podría comprobar nada. */
  async function abrir(rol, fichero) {
    const ctx = await b.newContext();
    await ctx.route('http://nav.test/**', route => route.fulfill({
      status: 200, contentType: 'text/html; charset=utf-8', body: pagina(rol),
    }));
    const p = await ctx.newPage();
    await p.goto('http://nav.test/' + fichero);
    await p.waitForTimeout(250);
    return p;
  }
  const ck = (n, c, x) => { console.log((c ? 'OK   ' : 'FALLO ') + n + (c ? '' : ' -> ' + String(JSON.stringify(x)).slice(0, 220))); if (!c) f++; };

  const visibles = p => p.evaluate(() =>
    [...document.querySelectorAll('.nav-item[href],.nav-sub-item[href]')]
      .filter(e => e.style.display !== 'none').map(e => e.getAttribute('href')));

  // ── Editor de contenido global: solo su parcela
  const errs = [];
  let p = await abrir(7, 'aliments.html');
  p.on('pageerror', e => errs.push(String(e)));
  await p.waitForTimeout(150);
  const v7 = (await visibles(p)).sort();
  ck('[editor] solo ve alimentos y ejercicios',
     JSON.stringify(v7) === JSON.stringify(['aliments.html', 'ejercicios.html']), v7);
  ck('[editor] NO ve grupos musculares: los lee, pero no los administra',
     !v7.includes('grupos-musculares.html'), v7);
  ck('[editor] NO ve clientes ni check-ins', !v7.includes('clients.html') && !v7.includes('checkins.html'));
  ck('[editor] NO ve equipo, organización ni analíticas',
     !v7.includes('coaches.html') && !v7.includes('mi-organizacion.html') && !v7.includes('analytics.html'));
  ck('[editor] NO ve rutinas ni dietas', !v7.includes('rutinas.html') && !v7.includes('diets.html'));

  const secciones = await p.evaluate(() =>
    [...document.querySelectorAll('.nav-section')].filter(e => e.style.display !== 'none').map(e => e.textContent));
  ck('[editor] las secciones que quedan vacías se ocultan',
     JSON.stringify(secciones) === JSON.stringify(['Contenido']), secciones);
  ck('[editor] Librería queda visible y abierta',
     await p.evaluate(() => { const l = document.getElementById('navLibrary'); return l.style.display !== 'none' && l.classList.contains('open'); }));

  // ── El editor que aterriza donde no debe, acaba en su sitio
  const pRedir = await abrir(7, 'dashboard.html');
  await pRedir.waitForTimeout(400);
  ck('[editor] entrar en dashboard lo lleva a alimentos',
     pRedir.url().endsWith('/aliments.html'), pRedir.url());

  // ── Coach: se conserva el comportamiento que ya había
  p = await abrir(5, 'dashboard.html');
  await p.waitForTimeout(150);
  const v5 = await visibles(p);
  ck('[coach] NO ve equipo, ajustes ni analíticas',
     !v5.includes('coaches.html') && !v5.includes('settings.html') && !v5.includes('analytics.html'), v5);
  ck('[coach] SÍ sigue viendo clientes y su biblioteca completa',
     v5.includes('clients.html') && v5.includes('rutinas.html') && v5.includes('diets.html'), v5);

  // ── Super-admin y admin: menú intacto
  for (const rol of [1, 2]) {
    p = await abrir(rol, 'dashboard.html');
    // Sin número mágico: nada oculto y ninguna sección escondida.
    const ocultos = await p.evaluate(() =>
      [...document.querySelectorAll('.nav-item,.nav-sub-item,.nav-section')]
        .filter(e => e.style.display === 'none').length);
    ck(`[rol ${rol}] no se le oculta nada`, ocultos === 0, { ocultos });
  }

  ck('sin errores de JS', errs.length === 0, errs);
  await b.close();
  process.exit(f ? 1 : 0);
})();
