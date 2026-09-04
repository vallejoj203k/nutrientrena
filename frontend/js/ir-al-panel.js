/* Un atajo al panel de plataforma desde la barra del coach.

   La misma persona es super-admin de Alzum Y dueña de su propio centro, así que
   cambia de sombrero varias veces al día. Para volver al panel de plataforma
   había que escribir la dirección a mano: desde el panel se puede entrar en una
   cuenta, pero no había camino de vuelta.

   Solo lo ve el SUPER-ADMIN. Un coach no tiene nada que hacer en ese panel, y
   un botón que lleva a una puerta cerrada es peor que no tener botón.

   Se pregunta al servidor quién eres, no se decide en el navegador: el rol
   guardado en localStorage vale para no preguntar cuando es que no —y ahorrar
   una petición en cada página a todo el mundo—, pero no para decir que sí. */
(function () {
  var API = API_BASE;
  var SUPERADMIN = '1';

  function arrancar() {
    var token, rol;
    try {
      token = localStorage.getItem('token');
      rol = localStorage.getItem('role_id');
    } catch (e) { return; }
    if (!token) return;

    // Ya se está en el panel de plataforma (la Librería abierta desde él): allí
    // el menú del coach está escondido y ya hay un "Volver al panel".
    try {
      if (new URLSearchParams(location.search).get('panel') === 'plataforma') return;
    } catch (e) {}

    // Si el rol guardado dice que NO es super-admin, se cree y no se pregunta:
    // así un coach no paga una petición de más en cada pantalla. Si no hay rol
    // guardado se pregunta, que es el caso dudoso.
    if (rol && rol !== SUPERADMIN) return;

    var caja = document.querySelector('.sidebar-user');
    if (!caja || document.getElementById('irAlPanel')) return;

    fetch(API + '/admin/me', { headers: { Authorization: 'Bearer ' + token } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        // `es_superadmin`, no "tiene acceso al panel": el editor de contenido y
        // soporte también entran, y este atajo es solo para el super-admin.
        if (!j || !j.data || j.data.es_superadmin !== true) return;
        pintar(caja);
      })
      .catch(function () {});
  }

  function pintar(caja) {
    if (document.getElementById('irAlPanel')) return;
    estilos();

    var a = document.createElement('a');
    a.id = 'irAlPanel';
    a.className = 'ir-panel';
    a.href = 'admin/index.html';
    a.innerHTML =
      '<span class="ip-ico">' +
        '<svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">' +
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>' +
      '</span>' +
      // Sin flecha a la derecha: en 240px de barra se comía el ancho justo que
      // le faltaba al nombre, y "Panel de platafo…" no dice adónde lleva.
      '<span class="ip-txt"><b>Panel de plataforma</b><span>Administrar Alzum</span></span>';

    caja.parentNode.insertBefore(a, caja);
  }

  function estilos() {
    if (document.getElementById('irAlPanelCss')) return;
    var s = document.createElement('style');
    s.id = 'irAlPanelCss';
    // La tinta oscura es la del panel de plataforma: se reconoce de un vistazo
    // adónde lleva, igual que la barra de allí se distingue de la de aquí.
    s.textContent =
      '.ir-panel{display:flex;align-items:center;gap:10px;margin:10px 14px;padding:9px 11px;' +
      'border-radius:10px;background:#10141E;color:#fff;text-decoration:none;' +
      'border:1px solid rgba(255,255,255,.08);transition:background .15s,transform .15s;}' +
      '.ir-panel:hover{background:#1B2130;}' +
      '.ir-panel .ip-ico{width:24px;height:24px;border-radius:7px;background:#4F5BF2;flex:none;' +
      'display:flex;align-items:center;justify-content:center;}' +
      '.ir-panel .ip-txt{min-width:0;flex:1;line-height:1.25;}' +
      '.ir-panel .ip-txt b{display:block;font-size:12.5px;font-weight:600;' +
      'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}' +
      '.ir-panel .ip-txt span{font-size:10.5px;color:rgba(255,255,255,.5);}';
    document.head.appendChild(s);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', arrancar);
  else arrancar();
})();
