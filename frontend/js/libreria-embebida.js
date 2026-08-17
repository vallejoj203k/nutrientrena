/* Las páginas de la Librería, servidas DENTRO del panel de plataforma.

   El cliente quiere que Contenido global se vea y funcione exactamente como la
   librería del coach. Hay dos formas de conseguirlo:

   1. Rehacer cada pantalla dentro del panel. Son miles de líneas por página, y
      a partir del día siguiente hay dos versiones de lo mismo que se van
      separando. Ya pasó en este proyecto con el constructor de rutinas (dos
      copias), con el menú lateral (21 copias, 7 variantes) y con el globito de
      chat (38 copias idénticas). Siempre acaba igual.
   2. Servir la MISMA página dentro del panel, sin su menú lateral.

   Esto es lo segundo. La página es la misma, con sus filtros, sus acciones y
   sus formularios; lo único que cambia es que se ve dentro del panel. Un
   arreglo en la librería del coach lo hereda el panel sin tocar nada, y al
   revés.

   Se activa con ?embed=1, o cuando la página se detecta dentro de un marco.
   Va aquí y no copiado en cada página por lo de siempre. */
(function () {
  var dentroDeMarco = false;
  try { dentroDeMarco = window.self !== window.top; } catch (e) { dentroDeMarco = true; }
  var pedido = new URLSearchParams(location.search).get('embed') === '1';
  if (!pedido && !dentroDeMarco) return;

  function aplicar() {
    document.body.classList.add('embebida');

    if (!document.getElementById('embebidaCss')) {
      var s = document.createElement('style');
      s.id = 'embebidaCss';
      s.textContent =
        // El menú lateral lo pone el panel: dos menús a la vez es un laberinto.
        'body.embebida .sidebar{display:none !important;}' +
        // La página está pensada para ocupar la ventana entera; dentro del
        // panel tiene que ocupar su hueco y dejar que el marco crezca.
        'body.embebida .main{height:auto !important;min-height:0 !important;overflow:visible !important;}' +
        'body.embebida{height:auto !important;min-height:0 !important;overflow:hidden !important;}' +
        // Los contenedores internos de la página tienen su propio scroll para
        // caber en una ventana. Dentro del panel estorban: el que scrollea es
        // el panel, y una barra dentro de otra es incómoda de usar de verdad.
        'body.embebida .main>div{height:auto !important;max-height:none !important;overflow:visible !important;}' +
        'body.embebida .main>div>div{max-height:none !important;}' +
        // El botón de ayuda flotante es del panel del coach; aquí sobra.
        'body.embebida #sopBtn,body.embebida #sopCapa,' +
        'body.embebida .sop-aviso,body.embebida .sop-mant{display:none !important;}';
      document.head.appendChild(s);
    }

    // Las pestañas de la librería son enlaces a otras páginas. Sin esto,
    // pulsar "Ejercicios" cargaría la página CON su menú lateral dentro del
    // marco, y el usuario vería dos menús.
    marcarEnlaces();
    new MutationObserver(marcarEnlaces).observe(document.body, { childList: true, subtree: true });

    // El panel necesita saber cuánto mide para no dejar un marco corto con
    // barra de scroll propia, que es incómodo de usar.
    avisarAltura();
    new ResizeObserver(avisarAltura).observe(document.body);
    setInterval(avisarAltura, 1000);
  }

  function marcarEnlaces() {
    var enlaces = document.querySelectorAll('a[href$=".html"]:not([data-embebida])');
    for (var i = 0; i < enlaces.length; i++) {
      var a = enlaces[i];
      a.setAttribute('data-embebida', '1');
      var href = a.getAttribute('href') || '';
      // Solo rutas relativas de la propia aplicación.
      if (/^(https?:)?\/\//.test(href) || href.charAt(0) === '#') continue;
      a.setAttribute('href', href + (href.indexOf('?') === -1 ? '?' : '&') + 'embed=1');
    }
  }

  var ultima = 0;
  function avisarAltura() {
    var alto = Math.max(
      document.body.scrollHeight, document.documentElement.scrollHeight,
      document.body.offsetHeight, document.documentElement.offsetHeight);
    if (Math.abs(alto - ultima) < 8) return;   // el ruido de un píxel no cuenta
    ultima = alto;
    try { parent.postMessage({ tipo: 'libreria-alto', alto: alto }, '*'); } catch (e) {}
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', aplicar);
  else aplicar();
})();
