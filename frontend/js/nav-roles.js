/* Menú lateral según el rol.

   Antes esto era una función adaptSidebar() copiada en 21 de las 38 páginas,
   con siete variantes que solo diferían en espacios y comillas —el mismo
   comportamiento escrito siete veces— y otras 17 páginas sin nada. Ahora vive
   aquí y se aplica igual en todas.

   Dos roles se restringen:

   - COACH (5): no ve Equipo, Ajustes ni Analíticas. Es lo que ya hacía
     adaptSidebar; se conserva tal cual.

   - EDITOR DE CONTENIDO GLOBAL (7): el documento de jerarquía lo describe como
     "el ayudante que llena la base de datos" — alimentos y ejercicios de la
     base maestra y nada más. El backend ya se lo impide todo (403 en clientes,
     equipo, organizaciones y facturación), pero seguía viendo el menú entero y
     chocándose contra puertas cerradas.

   Para el rol 7 se usa una lista de lo PERMITIDO, no de lo prohibido: si mañana
   alguien añade una sección al menú, quedará oculta para él por defecto en vez
   de aparecer sin querer. */
(function () {
  var COACH = 5, EDITOR = 7;

  // Lo único que el editor de contenido global puede usar.
  var PERMITIDO_EDITOR = ['aliments.html', 'ejercicios.html', 'grupos-musculares.html'];

  // Lo que el coach no ve. Se mantiene el comportamiento que ya había.
  var OCULTO_COACH = ['coaches.html', 'settings.html', 'analytics.html'];

  function rol() {
    try { return parseInt(localStorage.getItem('role_id') || '0', 10); } catch (e) { return 0; }
  }

  function ocultar(el) { if (el) el.style.display = 'none'; }

  function aplicar() {
    var rid = rol();

    if (rid === COACH) {
      OCULTO_COACH.forEach(function (href) {
        ocultar(document.querySelector('.nav-item[href="' + href + '"]'));
      });
      return;
    }

    if (rid !== EDITOR) return;

    // Enlaces de primer nivel: se oculta todo lo que no esté permitido.
    document.querySelectorAll('.nav-item[href]').forEach(function (el) {
      var href = (el.getAttribute('href') || '').split('?')[0];
      if (PERMITIDO_EDITOR.indexOf(href) === -1) ocultar(el);
    });
    // Y dentro de Librería, lo mismo.
    document.querySelectorAll('.nav-sub-item[href]').forEach(function (el) {
      var href = (el.getAttribute('href') || '').split('?')[0];
      if (PERMITIDO_EDITOR.indexOf(href) === -1) ocultar(el);
    });

    // Los separadores de sección que se quedan sin ningún enlace visible
    // dejarían un título suelto ("Negocio" sin nada debajo).
    document.querySelectorAll('.nav-section').forEach(function (sec) {
      var n = sec.nextElementSibling, hayAlguno = false;
      while (n && !n.classList.contains('nav-section')) {
        if (n.style.display !== 'none' && (n.classList.contains('nav-item') || n.classList.contains('nav-dropdown'))) {
          hayAlguno = true; break;
        }
        n = n.nextElementSibling;
      }
      if (!hayAlguno) ocultar(sec);
    });

    // El desplegable de Librería no tiene href propio: se deja visible solo si
    // le queda algún hijo, y abierto, que es lo único a lo que puede ir.
    var lib = document.getElementById('navLibrary');
    if (lib) {
      var vivos = 0;
      document.querySelectorAll('.nav-sub-item[href]').forEach(function (el) {
        if (el.style.display !== 'none') vivos++;
      });
      if (!vivos) ocultar(lib);
      else if (!lib.classList.contains('open') && typeof toggleLibrary === 'function') toggleLibrary(lib);
    }

    // Aterriza en dashboard.html al entrar, que es justo lo que no puede ver.
    var aqui = (location.pathname.split('/').pop() || 'dashboard.html');
    if (PERMITIDO_EDITOR.indexOf(aqui) === -1 && aqui !== 'login.html') {
      location.replace(PERMITIDO_EDITOR[0]);
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', aplicar);
  else aplicar();
})();
