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

  /* Las familias de la Librería y sus pantallas salen de js/libreria-menu.js,
     que es EL MISMO fichero que usa el menú del coach. Antes había aquí una
     lista propia, y por tanto dos: la del coach ya tenía Programas y Catálogos
     y esta no. El cliente pidió que "Contenido global" funcione exactamente
     igual que "Librería"; la única manera de que siga siendo verdad dentro de
     un mes es que sea la misma lista, no una copia parecida. */
  function familias() {
    var m = window.LIBRERIA_MENU || window._flyoutMenus || {};
    return Object.keys(m).map(function (k) { return { clave: k, menu: m[k] }; });
  }

  /* El icono de cada familia en el desplegable, igual que en el menú del
     coach. Las pantallas traen el suyo dentro del mapa compartido. */
  var ICONOS_FAM = {
    entrenamiento: '<path d="M6 4v16M18 4v16M6 12h12"/>',
    nutricion:     '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    formulario:    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>',
    documento:     '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>',
  };

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

  /* Qué pantalla se está viendo, para marcarla. Se compara con el `cat` porque
     las tres entradas de Formulario son la misma página con distinto filtro:
     sin eso, estando en Encuestas se marcaría Check-ins. */
  function paginaActual() {
    var f = location.pathname.split('/').pop() || 'index.html';
    var cat = new URLSearchParams(location.search).get('cat');
    return cat ? f + '?cat=' + cat : f;
  }

  function esLaActual(href) {
    return href.split('&')[0] === paginaActual();
  }

  /* La vista previa del panel ("ver el panel como otro rol") vale también aquí.

     Contenido global abre las páginas de la Librería, que son otras páginas: si
     la vista previa se quedara en el panel, al entrar en Rutinas reaparecería
     el menú entero del super-admin y uno creería que se le ha caído la
     previsualización. Solo cambia lo que se PINTA, igual que en el panel: los
     permisos siguen siendo los de quien mira. */
  function vistaPrevia() {
    try { return JSON.parse(sessionStorage.getItem('panel_vista_previa') || 'null'); }
    catch (e) { return null; }
  }

  function avisarVistaPrevia(prev) {
    if (document.getElementById('platPreview')) return;
    var d = document.createElement('div');
    d.id = 'platPreview';
    d.className = 'aviso-preview plat-preview';
    d.innerHTML = '<span>Estás viendo el panel como <b>' + esc(prev.nombre) +
                  '</b>. Solo cambia lo que se muestra, no tus permisos.</span>' +
                  '<button type="button">Volver a mi vista</button>';
    d.querySelector('button').addEventListener('click', function () {
      try { sessionStorage.removeItem('panel_vista_previa'); } catch (e) {}
      location.reload();
    });
    document.body.insertBefore(d, document.body.firstChild);
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  window.MenuPlataforma = {
    familias: familias, conModo: conModo, modoPlataforma: modoPlataforma,
    esLaActual: esLaActual,
    // Lo que usa el panel (/admin) para pintar el MISMO desplegable.
    htmlItemContenido: function (prefijo, enlace) { return htmlItemContenido(prefijo, enlace); },
    conectarFlyout: conectarFlyout,
    cerrarFlyout: cerrarFlyout,
  };

  if (!modoPlataforma()) return;

  /* El menú del coach se esconde AQUÍ, según se lee el fichero, y no al estar
     listo el documento: este script se carga en la cabecera justamente para
     que el panel del coach no llegue a dibujarse ni un instante. Cargado al
     final del documento se veía primero el panel del coach y luego el de
     plataforma, que es lo que hacía pensar que se había cambiado de panel. */
  esconderMenuDelCoach();


  function arrancar() {
    var token;
    try { token = localStorage.getItem('token'); } catch (e) { return; }
    if (!token) { restaurarMenuDelCoach(); return; }

    /* Del ámbito se encarga org-context.js, que ve el mismo ?panel=plataforma
       y manda la cabecera X-Organization-Id: plataforma en TODAS las llamadas.
       Aquí no se toca localStorage: borrar el contexto de cuenta que hubiera
       elegido el usuario le cambiaría, sin decírselo, lo que ve al volver al
       panel del coach. El modo vive en la URL y solo mientras dura. */

    document.body.classList.add('panel-plataforma');
    marcarEnlaces();
    // La librería repinta sus tablas y sus pestañas al filtrar; sin observar
    // el DOM, los enlaces nuevos saldrían sin el modo y devolverían al panel
    // del coach a mitad de camino.
    new MutationObserver(marcarEnlaces).observe(document.documentElement, { childList: true, subtree: true });

    // Se pinta ya con lo que hay en este fichero —la marca, la vuelta al panel
    // y las pantallas de la Librería— y luego se rellena con las secciones que
    // conteste el servidor. Esperar a la respuesta dejaba la página sin ningún
    // menú mientras tanto, que es justo cuando uno cree que algo se ha roto.
    pintar({ secciones: [], nombre: '', es_superadmin: false });
    pedirAcceso(token, 0);
  }

  /* Quién eres se pregunta al servidor, y el servidor puede tardar o fallar.
     Hay que distinguir las dos respuestas, porque piden cosas contrarias:

     - "no eres del equipo de Alzum" (403): se le devuelve su panel de coach y
       se limpia el ?panel=plataforma de la barra de direcciones, para que lo
       que ve y lo que dice la URL sean lo mismo.
     - "no he podido preguntarlo" (red caída, 502, arranque frío): NO se le
       devuelve el panel del coach. Cambiar de panel por un fallo de red hace
       creer que se ha cambiado de sitio, y encima calladamente. Se dice lo que
       pasa y se ofrece reintentar. */
  function pedirAcceso(token, intento) {
    fetch(API_BASE + '/admin/me',
          { headers: { Authorization: 'Bearer ' + token } })
      .then(function (r) {
        if (r.status === 401 || r.status === 403) { salirDelModo(); return null; }
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (j) {
        if (!j) return;
        if (!j.data) { salirDelModo(); return; }
        quitarAvisoDeFallo();
        pintar(j.data);
        var prev = vistaPrevia();
        if (prev && j.data.es_superadmin) avisarVistaPrevia(prev);
      })
      .catch(function () {
        // Dos reintentos cortos: un arranque frío del servidor tarda unos
        // segundos y no es un error que haya que enseñarle a nadie.
        if (intento < 2) {
          setTimeout(function () { pedirAcceso(token, intento + 1); }, 1200 * (intento + 1));
          return;
        }
        // El menú se pinta igual con lo que se sabe sin preguntar: la marca,
        // la vuelta al panel y las pantallas de la Librería, que están en este
        // mismo fichero. Faltará la lista de secciones, y eso es lo que dice
        // el aviso. Dejarle sin ningún menú sería un callejón sin salida.
        pintar({ secciones: [], nombre: '', es_superadmin: false });
        avisarDeFallo(token);
      });
  }

  function esconderMenuDelCoach() {
    if (document.getElementById('menuPlataformaCss')) return;
    var s = document.createElement('style');
    s.id = 'menuPlataformaCss';
    // Se esconde, no se borra: si la sesión no puede entrar al panel de
    // plataforma hay que devolvérselo tal cual estaba.
    //
    // Sin la clase en el <body> —que se pone al estar listo el documento— el
    // selector no casa, así que se esconde también por el atributo del <html>,
    // que sí existe desde el primer instante.
    s.textContent = 'body.panel-plataforma>.layout>.sidebar,' +
                    'body.panel-plataforma>.sidebar,' +
                    'html[data-panel-plataforma] body>.layout>.sidebar,' +
                    'html[data-panel-plataforma] body>.sidebar{display:none !important;}';
    (document.head || document.documentElement).appendChild(s);
    document.documentElement.setAttribute('data-panel-plataforma', '1');
  }

  /* Salir del modo de verdad: además de devolver el menú del coach, se quita
     el ?panel=plataforma. Si se quedara, recargar volvería a intentarlo y la
     dirección seguiría diciendo que estás en el panel de plataforma cuando no
     lo estás. */
  function salirDelModo() {
    restaurarMenuDelCoach();
    try {
      var u = new URL(location.href);
      u.searchParams.delete(PARAM);
      history.replaceState(null, '', u.pathname + (u.search || '') + u.hash);
    } catch (e) {}
  }

  function avisarDeFallo(token) {
    if (document.getElementById('menuPlatFallo')) return;
    var d = document.createElement('div');
    d.id = 'menuPlatFallo';
    d.className = 'plat-fallo';
    d.innerHTML = '<span>No se ha podido comprobar tu acceso al panel de plataforma. ' +
                  'Sigues en <b>Contenido global</b>: lo que veas puede estar incompleto.</span>' +
                  '<button type="button">Reintentar</button>';
    d.querySelector('button').addEventListener('click', function () {
      quitarAvisoDeFallo();
      pedirAcceso(token, 0);
    });
    document.body.appendChild(d);
  }

  function quitarAvisoDeFallo() {
    var d = document.getElementById('menuPlatFallo');
    if (d) d.remove();
  }

  function restaurarMenuDelCoach() {
    var s = document.getElementById('menuPlataformaCss');
    if (s) s.remove();
    document.documentElement.removeAttribute('data-panel-plataforma');
    if (document.body) document.body.classList.remove('panel-plataforma');
    var mio = document.getElementById('sidePlataforma');
    if (mio) mio.remove();
    quitarAvisoDeFallo();
  }

  function pintar(d) {
    var previo = document.getElementById('sidePlataforma');

    var side = document.createElement('aside');
    side.className = 'side';
    side.id = 'sidePlataforma';

    var lista = d.secciones || [];
    var prev = vistaPrevia();
    if (prev && prev.secciones) {
      lista = lista.filter(function (s) { return prev.secciones.indexOf(s.id) !== -1; });
    }

    var secciones = lista.map(function (s) {
      if (s.id === 'contenido') return itemContenido();
      return '<a class="s-item" href="admin/index.html#' + s.id + '">' +
             svg(s.icono) + '<span>' + esc(s.nombre) + '</span></a>';
    }).join('');

    // Sin lista de secciones —el servidor no contestó— se pinta al menos
    // Contenido global: es la pantalla en la que se está, y es lo que permite
    // seguir moviéndose por la Librería. Con lista, manda la lista: si el rol
    // que se previsualiza no la tiene, no debe salir.
    if (!lista.length && !/id="itemContenido"/.test(secciones)) {
      secciones = itemContenido() + secciones;
    }

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

    // Repintar en vez de salir si ya había uno: el reintento tras un fallo
    // trae la lista de secciones que faltaba.
    if (previo) previo.replaceWith(side);
    else document.body.insertBefore(side, document.body.firstChild);

    side.querySelector('.salir').addEventListener('click', function () {
      try { localStorage.removeItem('token'); localStorage.removeItem('role_id'); } catch (e) {}
      location.replace('login.html');
    });

    conectarFlyout(side, '', conModo);
  }

  /* "Contenido global" se despliega igual que "Librería" en el panel del coach:
     primero las cuatro familias, y cada una abre a un lado el panel con sus
     pantallas. Es el mismo mapa y la misma forma de navegar; lo único distinto
     es que estas pantallas se abren en modo plataforma. */
  function itemContenido() {
    return htmlItemContenido('', conModo);
  }

  /* Los enlaces de la propia librería tienen que arrastrar el modo. Sin esto,
     pulsar "Nutrición" devolvería al menú del coach a mitad de navegación. */
  function marcarEnlaces() {
    var paginas = {};
    familias().forEach(function (f) {
      f.menu.items.forEach(function (i) { paginas[i.href.split('?')[0]] = 1; });
    });

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

  /* ── El desplegable de dos niveles, compartido ──────────────────────────
     Lo pintan los DOS sitios: el panel (/admin) y estas páginas. Vive aquí
     porque tenerlo en los dos era exactamente lo que acaba de pasarle al menú
     del coach: 31 copias y una ya distinta de las demás.

     `prefijo` es lo que hay que anteponer a las direcciones ('../' desde
     /admin, nada desde la raíz) y `enlace` decide cómo se compone cada una. */
  function htmlItemContenido(prefijo, enlace, activa) {
    var fams = familias();
    var abierta = activa || familiaDeLaPagina();

    var sub = fams.map(function (f) {
      return '<button type="button" class="s-fam' + (f.clave === abierta ? ' on' : '') +
             '" data-fam="' + f.clave + '">' +
             '<svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">' +
             (ICONOS_FAM[f.clave] || '') + '</svg>' +
             '<span>' + esc(f.menu.title) + '</span>' +
             '<svg class="flecha" width="10" height="10" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6"/></svg>' +
             '</button>';
    }).join('');

    return '<button class="s-item' + (abierta ? ' active abierto' : '') + '" id="itemContenido" type="button">' +
           svg('shield') + '<span>Contenido global</span>' +
           '<svg class="chev" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"/></svg>' +
           '</button><div class="s-sub' + (abierta ? ' abierto' : '') + '" id="subContenido">' + sub + '</div>';
  }

  // Qué familia contiene la pantalla que se está viendo. Sirve para dejar el
  // desplegable abierto por donde estás, sin tener que buscarte tú.
  function familiaDeLaPagina() {
    var act = paginaActual(), encontrada = '';
    familias().forEach(function (f) {
      f.menu.items.forEach(function (i) {
        if (i.href === act || i.href.split('?')[0] === act) encontrada = encontrada || f.clave;
      });
    });
    return encontrada;
  }

  /* El panel lateral que se abre a la derecha con las pantallas de la familia.
     Se crea aquí y no se toma el de la página: el de la página cuelga del menú
     del coach, que en modo plataforma está escondido. */
  function conectarFlyout(raiz, prefijo, enlace) {
    var item = raiz.querySelector('#itemContenido');
    var sub = raiz.querySelector('#subContenido');
    if (item && sub) item.addEventListener('click', function () {
      item.classList.toggle('abierto');
      sub.classList.toggle('abierto');
      if (!sub.classList.contains('abierto')) cerrarFlyout();
    });

    Array.prototype.forEach.call(raiz.querySelectorAll('.s-fam'), function (b) {
      b.addEventListener('click', function (e) {
        e.stopPropagation();
        abrirFlyout(b, b.getAttribute('data-fam'), prefijo, enlace);
      });
    });
  }

  function cajaFlyout() {
    var caja = document.getElementById('platFlyout');
    if (caja) return caja;
    var fondo = document.createElement('div');
    fondo.id = 'platFlyoutFondo';
    fondo.className = 'plat-fly-fondo';
    fondo.addEventListener('click', cerrarFlyout);
    caja = document.createElement('div');
    caja.id = 'platFlyout';
    caja.className = 'plat-fly';
    caja.innerHTML = '<div class="plat-fly-cab"><span class="punto"></span><b></b></div><div class="plat-fly-items"></div>';
    document.body.appendChild(fondo);
    document.body.appendChild(caja);
    // Cerrar con Escape: es un panel flotante, y quedarse sin salida con el
    // teclado es lo que convierte un menú en una trampa.
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') cerrarFlyout(); });
    return caja;
  }

  function abrirFlyout(boton, clave, prefijo, enlace) {
    var m = (window.LIBRERIA_MENU || window._flyoutMenus || {})[clave];
    if (!m) return;
    var caja = cajaFlyout(), fondo = document.getElementById('platFlyoutFondo');

    caja.querySelector('.punto').style.background = m.color;
    caja.querySelector('b').textContent = m.title;
    caja.querySelector('.plat-fly-items').innerHTML = m.items.map(function (i) {
      var href = prefijo + enlace(i.href);
      return '<a class="plat-fly-item' + (esLaActual(enlace(i.href)) ? ' on' : '') + '" href="' + href + '">' +
             '<svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">' +
             i.icon + '</svg>' + esc(i.label) + '</a>';
    }).join('');

    var r = boton.getBoundingClientRect();
    caja.style.left = Math.round(r.right + 8) + 'px';
    caja.style.top = Math.max(8, Math.min(r.top, window.innerHeight - (m.items.length * 40 + 76))) + 'px';
    caja.classList.add('on');
    fondo.classList.add('on');

    Array.prototype.forEach.call(document.querySelectorAll('.s-fam'), function (b) {
      b.classList.toggle('on', b === boton);
    });
  }

  function cerrarFlyout() {
    var caja = document.getElementById('platFlyout');
    var fondo = document.getElementById('platFlyoutFondo');
    if (caja) caja.classList.remove('on');
    if (fondo) fondo.classList.remove('on');
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
