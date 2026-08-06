/* Selector de "segundo sombrero": actuar dentro de una organización concreta.

   El backend ya lo soportaba desde hace tiempo — la cabecera
   X-Organization-Id y GET /organizations/switchable— pero ninguna pantalla la
   enviaba, así que solo era usable por API. Esto lo conecta.

   Por qué se envuelve fetch en vez de tocar cada página: las 38 páginas hacen
   sus peticiones con helpers distintos (authHeaders(), h(), objetos sueltos).
   Añadir la cabecera en cada sitio serían decenas de puntos donde olvidarse, y
   uno olvidado significa una pantalla que enseña datos de otro contexto sin
   avisar. Envolviendo fetch una vez, entra en TODAS las llamadas a la API.

   Este fichero debe cargarse ANTES que el script de la página, para que la
   envoltura esté puesta antes de la primera petición. */
(function () {
  var API_HOST = 'nutrientrena-production.up.railway.app';
  var CLAVE = 'org_context';       // '' = plataforma
  var CLAVE_NOMBRE = 'org_context_name';

  function contextoActual() {
    try { return localStorage.getItem(CLAVE) || ''; } catch (e) { return ''; }
  }

  function esNuestraApi(url) {
    if (!url) return false;
    if (url.indexOf(API_HOST) !== -1) return true;          // absoluta a nuestra API
    if (url.charAt(0) === '/') return url.indexOf('/api/') === 0;  // relativa
    return false;
  }

  // ── 1. La cabecera, en todas las peticiones a la API ────────────────────
  var _fetch = window.fetch.bind(window);
  window.fetch = function (entrada, opciones) {
    var org = contextoActual();
    if (org) {
      var url = typeof entrada === 'string' ? entrada : (entrada && entrada.url) || '';
      // Solo a nuestra API. Un "contiene /api/" a secas colaría la cabecera
      // en peticiones a terceros que casualmente tengan /api/ en la ruta.
      if (esNuestraApi(url)) {
        opciones = opciones || {};
        var h = new Headers((opciones && opciones.headers) || (entrada && entrada.headers) || {});
        h.set('X-Organization-Id', org);
        opciones = Object.assign({}, opciones, { headers: h });
      }
    }
    return _fetch(entrada, opciones);
  };

  // ── 2. El selector, solo si hay más de un contexto ──────────────────────
  function pintar(contextos, puedePlataforma) {
    var caja = document.querySelector('.sidebar-user');
    if (!caja || document.getElementById('orgCtxSel')) return;

    var actual = contextoActual();
    var envoltorio = document.createElement('div');
    envoltorio.className = 'org-ctx';
    envoltorio.innerHTML =
      '<label for="orgCtxSel">Actuando como</label>' +
      '<select id="orgCtxSel">' +
      (puedePlataforma ? '<option value="">Plataforma (todo)</option>' : '') +
      contextos.map(function (o) {
        return '<option value="' + o.id + '"' + (o.id === actual ? ' selected' : '') + '>' + o.name + '</option>';
      }).join('') +
      '</select>';
    caja.parentNode.insertBefore(envoltorio, caja);

    var sel = envoltorio.querySelector('select');
    sel.value = actual;
    sel.addEventListener('change', function () {
      try {
        localStorage.setItem(CLAVE, sel.value);
        localStorage.setItem(CLAVE_NOMBRE, sel.options[sel.selectedIndex].textContent);
      } catch (e) {}
      // Recarga completa a propósito: cambiar de contexto cambia TODO lo que
      // se está viendo. Refrescar por partes dejaría media pantalla con datos
      // del contexto anterior, que es peor que esperar un segundo.
      location.reload();
    });
  }

  function estilos() {
    if (document.getElementById('orgCtxCss')) return;
    var s = document.createElement('style');
    s.id = 'orgCtxCss';
    s.textContent =
      '.org-ctx{padding:9px 14px;border-top:1px solid rgba(148,163,184,.18);display:flex;flex-direction:column;gap:4px;}' +
      '.org-ctx label{font-size:9.5px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;color:#94A3B8;}' +
      '.org-ctx select{width:100%;padding:6px 8px;border:1px solid rgba(148,163,184,.3);border-radius:7px;' +
      'background:rgba(148,163,184,.10);color:inherit;font-size:12px;font-weight:600;cursor:pointer;outline:none;}' +
      '.org-ctx select:focus{border-color:#4F46E5;}';
    document.head.appendChild(s);
  }

  function arrancar() {
    var token;
    try { token = localStorage.getItem('token'); } catch (e) { return; }
    if (!token) return;

    // Se usa _fetch: esta llamada no debe llevar la cabecera, porque justamente
    // sirve para saber a qué contextos se puede cambiar.
    _fetch('https://' + API_HOST + '/api/organizations/switchable',
           { headers: { Authorization: 'Bearer ' + token } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        if (!j) return;
        var d = j.data || {};
        var orgs = d.organizaciones || [];
        var plataforma = !!d.puede_actuar_como_plataforma;
        var opciones = orgs.length + (plataforma ? 1 : 0);

        // Con una sola opción el selector no decide nada: solo ocuparía sitio
        // y sugeriría que hay algo que elegir.
        if (opciones < 2) {
          if (contextoActual()) { try { localStorage.removeItem(CLAVE); } catch (e) {} }
          return;
        }
        // Si el contexto guardado ya no está disponible, se vuelve a
        // plataforma en vez de seguir mandando una cabecera que dará 403.
        var actual = contextoActual();
        if (actual && !orgs.some(function (o) { return o.id === actual; })) {
          try { localStorage.removeItem(CLAVE); } catch (e) {}
        }
        estilos();
        pintar(orgs, plataforma);
      })
      .catch(function () {});
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', arrancar);
  else arrancar();
})();
