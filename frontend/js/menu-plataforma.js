/* El menú del panel de plataforma, dentro de las páginas de la Librería.

   El cliente lo pidió así: que "Contenido global" funcione como "Librería" en
   el panel del coach —que lleve a las páginas de verdad, con todas sus
   funciones— pero conservando el menú lateral de plataforma.

   Así que no se rehace ninguna pantalla ni se mete en un recuadro: se abre la
   página tal cual y se le cambia el menú. Un arreglo en la librería del coach
   lo hereda el panel sin tocar nada, y al revés.

   El modo se lleva en la URL (?panel=plataforma) y no en localStorage: si
   viviera guardado, salir al panel del coach dejaría el menú equivocado
   puesto, y sería un estado invisible que nadie sabe quitar. Los enlaces
   internos de la librería se reescriben para arrastrarlo. */
(function () {
  var PARAM = 'panel', VALOR = 'plataforma';

  /* El mapa de la Librería, en UN solo sitio. Lo usan el panel (/admin) para
     pintar su sub-menú y estas páginas para pintar el suyo: si estuviera en
     los dos, se separarían al añadir una pantalla. */
  var LIBRERIA = [
    { grupo: 'Entrenamiento', items: [
      { pagina: 'rutinas.html',            nombre: 'Rutinas' },
      { pagina: 'ejercicios.html',         nombre: 'Ejercicios' },
      { pagina: 'grupos-musculares.html',  nombre: 'Grupos musculares' },
    ]},
    { grupo: 'Nutrición', items: [
      { pagina: 'diets.html',                        nombre: 'Dietas' },
      { pagina: 'menus.html',                        nombre: 'Menús' },
      { pagina: 'recipes.html',                      nombre: 'Recetas' },
      { pagina: 'aliments.html',                     nombre: 'Alimentos' },
      { pagina: 'nutrition-catalog.html?tab=tipos',  nombre: 'Tipos de dieta' },
      { pagina: 'nutrition-catalog.html?tab=grupos', nombre: 'Grupos de alimentos' },
    ]},
    { grupo: 'Formularios', items: [
      { pagina: 'forms.html', nombre: 'Formularios' },
    ]},
    { grupo: 'Documentos', items: [
      { pagina: 'contratos.html',  nombre: 'Contratos' },
      { pagina: 'guias.html',      nombre: 'Guías' },
      { pagina: 'plantillas.html', nombre: 'Plantillas' },
    ]},
  ];

  var ICONOS = {
    chart:'<path d="M18 20V10M12 20V4M6 20v-6"/>',
    users:'<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/>',
    user:'<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    card:'<rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/>',
    box:'<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>',
    shield:'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    building:'<rect x="4" y="2" width="16" height="20" rx="2"/><line x1="10" y1="22" x2="14" y2="22"/>',
    life:'<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><line x1="4.93" y1="4.93" x2="9.17" y2="9.17"/><line x1="14.83" y1="14.83" x2="19.07" y2="19.07"/>',
    trend:'<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
    team:'<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>',
    gear:'<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9c.14.31.4.56.71.71H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
  };

  function modoPlataforma() {
    return new URLSearchParams(location.search).get(PARAM) === VALOR;
  }

  function conModo(href) {
    if (!href || /^(https?:)?\/\//.test(href) || href.charAt(0) === '#') return href;
    if (href.indexOf(PARAM + '=' + VALOR) !== -1) return href;
    return href + (href.indexOf('?') === -1 ? '?' : '&') + PARAM + '=' + VALOR;
  }

  function paginaActual() {
    var f = location.pathname.split('/').pop() || 'index.html';
    var tab = new URLSearchParams(location.search).get('tab');
    return tab ? f + '?tab=' + tab : f;
  }

  window.MenuPlataforma = { LIBRERIA: LIBRERIA, conModo: conModo, modoPlataforma: modoPlataforma };

  if (!modoPlataforma()) return;

  var esc = function (s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  };

  function arrancar() {
    var token;
    try { token = localStorage.getItem('token'); } catch (e) { return; }
    if (!token) return;

    // Se entra como la PLATAFORMA, así que se suelta el contexto de cuenta que
    // hubiera puesto el selector del panel: si quedara puesto, lo que se creara
    // aquí nacería dentro de esa cuenta en vez de en el catálogo común, y nada
    // en la pantalla lo diría.
    try {
      localStorage.removeItem('org_context');
      localStorage.removeItem('org_context_name');
    } catch (e) {}

    document.body.classList.add('panel-plataforma');
    esconderMenuDelCoach();
    marcarEnlaces();
    // La librería repinta sus tablas y sus pestañas al filtrar; sin observar
    // el DOM, los enlaces nuevos saldrían sin el modo y devolverían al panel
    // del coach a mitad de camino.
    new MutationObserver(marcarEnlaces).observe(document.documentElement, { childList: true, subtree: true });

    fetch('https://nutrientrena-production.up.railway.app/api/admin/me',
          { headers: { Authorization: 'Bearer ' + token } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        // Sin acceso al panel de plataforma no se pinta su menú: se devuelve
        // el del coach, que es el que le corresponde.
        if (!j || !j.data) { restaurarMenuDelCoach(); return; }
        pintar(j.data);
      })
      .catch(function () { restaurarMenuDelCoach(); });
  }

  function esconderMenuDelCoach() {
    if (document.getElementById('menuPlataformaCss')) return;
    var s = document.createElement('style');
    s.id = 'menuPlataformaCss';
    // Se esconde, no se borra: si la sesión no puede entrar al panel de
    // plataforma hay que devolvérselo tal cual estaba.
    s.textContent = 'body.panel-plataforma>.layout>.sidebar,' +
                    'body.panel-plataforma>.sidebar{display:none !important;}';
    document.head.appendChild(s);
  }

  function restaurarMenuDelCoach() {
    var s = document.getElementById('menuPlataformaCss');
    if (s) s.remove();
    document.body.classList.remove('panel-plataforma');
    var mio = document.getElementById('sidePlataforma');
    if (mio) mio.remove();
  }

  function pintar(d) {
    if (document.getElementById('sidePlataforma')) return;

    var actual = paginaActual();
    var side = document.createElement('aside');
    side.className = 'side';
    side.id = 'sidePlataforma';

    var secciones = (d.secciones || []).map(function (s) {
      if (s.id === 'contenido') return itemContenido(actual);
      return '<a class="s-item" href="admin/index.html#' + s.id + '">' +
             svg(s.icono) + '<span>' + esc(s.nombre) + '</span></a>';
    }).join('');

    side.innerHTML =
      '<div class="side-brand">' + svgEscudo() +
      '<div><b>ALZUM<span style="display:inline;color:#4F5BF2;">.io</span></b>' +
      '<span>Panel de plataforma</span></div></div>' +
      '<a class="ctx-card" href="admin/index.html" style="text-decoration:none;color:inherit;">' +
      '<div class="ctx-ico">' + svgEscudoPequeno() + '</div>' +
      '<div class="ctx-txt"><b>Plataforma Alzum</b><span>Volver al panel</span></div></a>' +
      '<nav class="side-nav">' + secciones + '</nav>' +
      '<div class="side-foot"><div class="avatar">' +
      esc((d.nombre || 'A').charAt(0).toUpperCase()) + '</div>' +
      '<div class="who"><b>' + esc(d.nombre || '') + '</b>' +
      '<span>' + (d.es_superadmin ? 'Super-admin' : 'Equipo de Alzum') + '</span></div>' +
      '<button class="salir" title="Cerrar sesión">' + svgSalir() + '</button></div>';

    document.body.insertBefore(side, document.body.firstChild);

    side.querySelector('.salir').addEventListener('click', function () {
      try { localStorage.removeItem('token'); localStorage.removeItem('role_id'); } catch (e) {}
      location.replace('login.html');
    });

    var cab = side.querySelector('#itemContenido');
    if (cab) cab.addEventListener('click', function () {
      cab.classList.toggle('abierto');
      document.getElementById('subContenido').classList.toggle('abierto');
    });
  }

  function itemContenido(actual) {
    var abierto = LIBRERIA.some(function (g) {
      return g.items.some(function (i) { return i.pagina === actual; });
    });
    var sub = LIBRERIA.map(function (g) {
      return '<div class="s-grupo">' + esc(g.grupo) + '</div>' +
        g.items.map(function (i) {
          return '<a href="' + conModo(i.pagina) + '"' +
                 (i.pagina === actual ? ' class="active"' : '') + '>' + esc(i.nombre) + '</a>';
        }).join('');
    }).join('');

    return '<button class="s-item' + (abierto ? ' active abierto' : '') + '" id="itemContenido" type="button">' +
           svg('shield') + '<span>Contenido global</span>' +
           '<svg class="chev" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"/></svg>' +
           '</button><div class="s-sub' + (abierto ? ' abierto' : '') + '" id="subContenido">' + sub + '</div>';
  }

  /* Los enlaces de la propia librería tienen que arrastrar el modo. Sin esto,
     pulsar "Nutrición" devolvería al menú del coach a mitad de navegación. */
  function marcarEnlaces() {
    var paginas = {};
    LIBRERIA.forEach(function (g) { g.items.forEach(function (i) { paginas[i.pagina.split('?')[0]] = 1; }); });

    var enlaces = document.querySelectorAll('a[href]:not([data-menu-plat])');
    for (var i = 0; i < enlaces.length; i++) {
      var a = enlaces[i];
      a.setAttribute('data-menu-plat', '1');
      if (a.closest('#sidePlataforma')) continue;      // el menú ya viene bien
      var href = a.getAttribute('href') || '';
      if (!paginas[href.split('?')[0]]) continue;      // solo páginas de la librería
      a.setAttribute('href', conModo(href));
    }
  }

  function svg(nombre) {
    return '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">' +
           (ICONOS[nombre] || '') + '</svg>';
  }
  function svgEscudo() {
    return '<svg width="22" height="22" fill="none" stroke="#4F5BF2" stroke-width="2" viewBox="0 0 24 24">' +
           ICONOS.shield + '</svg>';
  }
  function svgEscudoPequeno() {
    return '<svg width="15" height="15" fill="none" stroke="#fff" stroke-width="2" viewBox="0 0 24 24">' +
           ICONOS.shield + '</svg>';
  }
  function svgSalir() {
    return '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">' +
           '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/>' +
           '<line x1="21" y1="12" x2="9" y2="12"/></svg>';
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', arrancar);
  else arrancar();
})();
