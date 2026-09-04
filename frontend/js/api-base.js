/* ═══════════════════════════════════════════════════════════════════════════
   Dónde vive la API.

   La sirve el MISMO servidor que esta página: la aplicación se monta bajo
   `/app` de la propia API, así que basta con mirar de dónde se ha cargado.
   Eso es lo que permite ponerla en cualquier dominio —hoy la de Railway,
   mañana app.alzum.io— sin tocar una línea: el navegador pide a su propio
   origen y no hay ni CORS de por medio.

   Antes el dominio estaba escrito a mano en cuarenta y ocho ficheros. Con eso,
   servir la web en un dominio nuevo dejaba a todas las páginas llamando al
   viejo: funciona mientras la lista de orígenes permitidos lo consienta, y se
   cae entera el día que ese dominio cambie.

   El respaldo es para cuando la página NO la sirve la API: abierta desde el
   disco (`file://`), que es como corren las pruebas de navegador, o servida
   desde otro sitio.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (w) {
  'use strict';

  var RESPALDO = 'https://nutrientrena-production.up.railway.app';
  var loc = w.location || {};
  var mismo = /^https?:$/.test(loc.protocol || '') && !!loc.host;

  var origen = mismo ? (loc.origin || (loc.protocol + '//' + loc.host)) : RESPALDO;

  w.API_ORIGIN = origen;                                   // https://app.alzum.io
  w.API_BASE = origen + '/api';                            // …/api
  w.WS_BASE = origen.replace(/^http/, 'ws') + '/ws/chat';  // wss://…/ws/chat
  w.API_HOST = origen.replace(/^https?:\/\//, '');         // app.alzum.io
})(window);
