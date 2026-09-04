/* El lado del coach de la sección Soporte del panel de plataforma.

   Se construye a la vez que la bandeja de Alzum a propósito: una bandeja de
   entrada sin forma de que entre nada es una pantalla que siempre está vacía y
   que parece rota, y un comunicado que no se ve en ninguna parte no es un
   comunicado.

   Dos piezas, las dos discretas:

   - Los comunicados publicados salen en una barra arriba. Se puede cerrar, y
     se recuerda cuál se cerró: un aviso que reaparece en cada pantalla deja de
     leerse a la tercera y entonces ya no sirve para avisar de nada.
   - Un botón de ayuda abre un panel para escribir una incidencia y ver las que
     ya se mandaron, con la respuesta de Alzum dentro. Sin la respuesta escrita
     habría que contestar por WhatsApp y no quedaría constancia de nada.

   Va aquí y no copiado en cada página por lo de siempre: 38 copias divergen. */
(function () {
  var API = API_BASE;
  var token;
  try { token = localStorage.getItem('token'); } catch (e) { return; }
  if (!token) return;

  var CERRADOS = 'comunicados_cerrados';
  // Nombre y correo de soporte configurables desde el panel de plataforma. Si
  // la petición falla se usan estos, para no dejar el panel de ayuda sin
  // título ni a quién escribir.
  var plataforma = { platform_name: 'Alzum', support_email: null, maintenance_mode: false };
  var esc = function (s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  };
  var cab = function () { return { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token }; };

  function leidos() {
    try { return JSON.parse(localStorage.getItem(CERRADOS) || '[]'); } catch (e) { return []; }
  }
  function marcarLeido(id) {
    try {
      var l = leidos();
      if (l.indexOf(id) === -1) { l.push(id); localStorage.setItem(CERRADOS, JSON.stringify(l.slice(-50))); }
    } catch (e) {}
  }

  function estilos() {
    if (document.getElementById('sopCss')) return;
    var s = document.createElement('style');
    s.id = 'sopCss';
    s.textContent =
      /* Fijo arriba y no dentro del flujo: media aplicación tiene el <body> en
         flex de dos columnas —barra lateral y contenido—, así que meterle un
         hijo más lo convertía en una TERCERA columna y descuadraba la pantalla
         entera. En el chat dejaba el panel de mensajes fuera de la ventana. */
      '.sop-aviso{position:fixed;top:0;left:0;right:0;z-index:40;display:flex;gap:11px;' +
      'align-items:flex-start;box-shadow:0 1px 4px rgba(0,0,0,.08);' +
      'background:#EEF2FF;border-bottom:1px solid #DDE2FE;color:#3730A3;font-size:13px;padding:11px 16px;}' +
      '.sop-aviso b{font-weight:800;}' +
      '.sop-aviso .x{margin-left:auto;border:none;background:none;color:inherit;font-size:17px;line-height:1;' +
      'cursor:pointer;padding:0 3px;opacity:.6;}' +
      '.sop-aviso .x:hover{opacity:1;}' +
      '.sop-btn{position:fixed;right:20px;bottom:20px;z-index:60;border:none;border-radius:24px;' +
      'background:#4F46E5;color:#fff;font:inherit;font-size:13px;font-weight:600;padding:10px 17px;' +
      'cursor:pointer;box-shadow:0 4px 14px rgba(79,70,229,.35);display:flex;align-items:center;gap:7px;}' +
      '.sop-capa{position:fixed;inset:0;background:rgba(16,20,30,.5);z-index:70;display:none;' +
      'align-items:center;justify-content:center;padding:20px;}' +
      '.sop-capa.on{display:flex;}' +
      '.sop-modal{background:#fff;border-radius:14px;width:540px;max-width:100%;max-height:88vh;overflow-y:auto;' +
      'font-size:13px;color:#111827;}' +
      '.sop-modal h3{font-size:15px;padding:17px 20px;border-bottom:1px solid #E2E4EA;margin:0;}' +
      '.sop-modal .cu{padding:18px 20px;display:flex;flex-direction:column;gap:13px;}' +
      '.sop-modal label{display:block;font-size:11.5px;font-weight:600;color:#6B7280;margin-bottom:5px;}' +
      '.sop-modal input,.sop-modal select,.sop-modal textarea{width:100%;padding:9px 11px;border:1px solid #E2E4EA;' +
      'border-radius:9px;font:inherit;font-size:13px;outline:none;box-sizing:border-box;}' +
      '.sop-modal textarea{min-height:84px;resize:vertical;}' +
      '.sop-modal input:focus,.sop-modal textarea:focus,.sop-modal select:focus{border-color:#4F46E5;}' +
      '.sop-pie{padding:13px 20px;border-top:1px solid #E2E4EA;display:flex;justify-content:flex-end;gap:9px;align-items:center;}' +
      '.sop-b{padding:9px 15px;border:none;border-radius:9px;background:#4F46E5;color:#fff;font:inherit;' +
      'font-size:13px;font-weight:600;cursor:pointer;}' +
      '.sop-b.g{background:#fff;border:1px solid #E2E4EA;color:#374151;}' +
      '.sop-tk{border-top:1px solid #F1F2F6;padding:12px 0;}' +
      '.sop-tk:first-child{border-top:none;}' +
      '.sop-tk .t{font-weight:700;}' +
      '.sop-tk .m{font-size:11.5px;color:#9CA3AF;margin-top:3px;}' +
      '.sop-tk .r{background:#EEF2FF;border-radius:9px;padding:9px 11px;margin-top:8px;line-height:1.5;}' +
      '.sop-tk .r .q{font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:#6366F1;margin-bottom:3px;}' +
      '.sop-err{font-size:12.5px;color:#DC2626;flex:1;}' +
      '.sop-mant{position:relative;z-index:41;display:flex;gap:11px;align-items:center;' +
      'background:#B45309;color:#fff;font-size:13px;font-weight:600;padding:11px 16px;}' +
      '.sop-mant .p{width:8px;height:8px;border-radius:50%;background:#FDE68A;flex:none;}' +
      '.sop-correo{font-size:11.5px;color:#6B7280;}' +
      '.sop-correo a{color:#4F46E5;font-weight:600;}';
    document.head.appendChild(s);
  }

  // ── Comunicados ─────────────────────────────────────────────────────────
  function pintarAvisos(lista) {
    var ya = leidos();
    var pendientes = lista.filter(function (a) { return ya.indexOf(a.id) === -1; });
    if (!pendientes.length) return;
    var a = pendientes[0];   // de uno en uno: dos barras apiladas no las lee nadie
    var barra = document.createElement('div');
    barra.className = 'sop-aviso';
    barra.setAttribute('data-comunicado', a.id);
    barra.innerHTML = '<span><b></b> <span class="cuerpo"></span></span>' +
                      '<button class="x" type="button" aria-label="Cerrar">&times;</button>';
    barra.querySelector('b').textContent = a.title;
    barra.querySelector('.cuerpo').textContent = a.body || '';
    barra.querySelector('.x').addEventListener('click', function () {
      marcarLeido(a.id);
      if (barra.parentNode) barra.parentNode.removeChild(barra);
      ajustarHueco();
    });
    document.body.insertBefore(barra, document.body.firstChild);
    ajustarHueco();
  }

  /* La barra va fija arriba, así que hay que hacerle sitio empujando la página.
     Es lo mismo que hace el aviso de "estás dentro de otra cuenta"; sin esto
     taparía la cabecera de la pantalla que haya debajo. */
  function ajustarHueco() {
    var alto = 0;
    var barras = document.querySelectorAll('.sop-aviso');
    for (var i = 0; i < barras.length; i++) alto += barras[i].offsetHeight;
    document.body.style.paddingTop = alto ? alto + 'px' : '';
    for (var j = 0; j < barras.length; j++) {
      barras[j].style.top = (j === 0 ? 0 : barras[j - 1].offsetHeight) + 'px';
    }
  }

  // ── Ayuda ───────────────────────────────────────────────────────────────
  function montarAyuda() {
    if (document.getElementById('sopBtn')) return;
    var btn = document.createElement('button');
    btn.id = 'sopBtn';
    btn.className = 'sop-btn';
    btn.type = 'button';
    btn.innerHTML = '<svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">' +
      '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>Ayuda';
    document.body.appendChild(btn);

    var capa = document.createElement('div');
    capa.className = 'sop-capa';
    capa.id = 'sopCapa';
    capa.innerHTML =
      '<div class="sop-modal">' +
      '<h3>Soporte de Alzum</h3>' +
      '<div class="cu">' +
      '<div><label>¿Qué ha pasado?</label><input id="sopAsunto" placeholder="Ej: no me deja asignar una rutina"></div>' +
      '<div><label>Cuéntanoslo con detalle</label><textarea id="sopCuerpo" placeholder="Qué estabas haciendo y qué esperabas que pasara."></textarea></div>' +
      '<div><label>Urgencia</label><select id="sopPrio">' +
      '<option value="baja">Baja — puede esperar</option>' +
      '<option value="media" selected>Media — me está estorbando</option>' +
      '<option value="alta">Alta — no puedo trabajar</option>' +
      '</select></div>' +
      '<div id="sopMios"></div>' +
      '</div>' +
      '<div class="sop-pie"><span class="sop-err" id="sopErr"></span>' +
      '<button class="sop-b g" type="button" id="sopCerrar">Cerrar</button>' +
      '<button class="sop-b" type="button" id="sopEnviar">Enviar</button></div>' +
      '</div>';
    document.body.appendChild(capa);

    btn.addEventListener('click', function () { capa.classList.add('on'); cargarMios(); });
    capa.addEventListener('click', function (e) { if (e.target === capa) capa.classList.remove('on'); });
    capa.querySelector('#sopCerrar').addEventListener('click', function () { capa.classList.remove('on'); });
    capa.querySelector('#sopEnviar').addEventListener('click', enviar);
  }

  function cargarMios() {
    var caja = document.getElementById('sopMios');
    fetch(API + '/support/tickets', { headers: cab() })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        var l = (j && j.data) || [];
        if (!l.length) { caja.innerHTML = ''; return; }
        caja.innerHTML = '<label>Lo que ya nos has mandado</label>' + l.slice(0, 5).map(function (t) {
          return '<div class="sop-tk"><div class="t">' + esc(t.subject) + '</div>' +
                 '<div class="m">' + esc((t.created_at || '').slice(0, 10)) + ' · ' +
                 ({ abierto: 'Abierto', en_curso: 'En curso', resuelto: 'Resuelto' }[t.state] || t.state) +
                 (t.respuestas ? ' · ' + t.respuestas + ' respuesta' + (t.respuestas > 1 ? 's' : '') : '') +
                 '</div><div data-hilo="' + esc(t.id) + '"></div></div>';
        }).join('');
        // La respuesta de Alzum se trae y se enseña: es lo único que el coach
        // viene a buscar cuando vuelve a abrir esto.
        l.slice(0, 5).filter(function (t) { return t.respuestas; }).forEach(function (t) {
          fetch(API + '/support/tickets/' + t.id, { headers: cab() })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (j2) {
              var hueco = caja.querySelector('[data-hilo="' + t.id + '"]');
              if (!hueco || !j2) return;
              hueco.innerHTML = ((j2.data || {}).mensajes || []).map(function (m) {
                return '<div class="r"><div class="q">' + (m.de_plataforma ? 'Alzum' : 'Tú') + '</div>' + esc(m.body) + '</div>';
              }).join('');
            }).catch(function () {});
        });
      }).catch(function () {});
  }

  function enviar() {
    var err = document.getElementById('sopErr');
    var asunto = document.getElementById('sopAsunto');
    if (!asunto.value.trim()) { err.textContent = 'Dinos al menos qué ha pasado.'; asunto.focus(); return; }
    var boton = document.getElementById('sopEnviar');
    boton.disabled = true;
    fetch(API + '/support/tickets', {
      method: 'POST', headers: cab(),
      body: JSON.stringify({
        subject: asunto.value.trim(),
        body: document.getElementById('sopCuerpo').value.trim(),
        priority: document.getElementById('sopPrio').value,
      }),
    }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) { err.textContent = (res.j && res.j.message) || 'No se pudo enviar.'; return; }
        err.textContent = '';
        asunto.value = '';
        document.getElementById('sopCuerpo').value = '';
        cargarMios();
      }).catch(function () { err.textContent = 'No se pudo enviar.'; })
      .finally(function () { boton.disabled = false; });
  }

  /* Mantenimiento: el aviso NO es un adorno. Mientras está puesto, la API
     responde 503 a todo lo que escribe, así que sin este cartel el coach
     vería fallar cada guardado sin entender por qué. */
  function pintarMantenimiento() {
    if (document.getElementById('sopMant')) return;
    var barra = document.createElement('div');
    barra.id = 'sopMant';
    barra.className = 'sop-mant';
    barra.innerHTML = '<span class="p"></span><span></span>';
    barra.lastChild.textContent =
      plataforma.platform_name + ' está en mantenimiento. Puedes consultar tus datos, ' +
      'pero los cambios no se guardarán hasta que termine.';
    document.body.insertBefore(barra, document.body.firstChild);
  }

  function arrancar() {
    estilos();
    montarAyuda();

    fetch(API + '/platform/settings', { headers: cab() })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        if (!j || !j.data) return;
        plataforma = j.data;
        var t = document.querySelector('#sopCapa h3');
        if (t) t.textContent = 'Soporte de ' + plataforma.platform_name;
        pintarCorreo();
        if (plataforma.maintenance_mode) pintarMantenimiento();
      })
      .catch(function () {});

    fetch(API + '/support/announcements', { headers: cab() })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) { if (j) pintarAvisos(j.data || []); })
      .catch(function () {});
  }

  /* El correo de soporte, donde sirve: dentro del panel de ayuda. Un ajuste
     que solo se ve en la pantalla donde se escribe no le sirve a nadie. */
  function pintarCorreo() {
    if (!plataforma.support_email || document.getElementById('sopCorreo')) return;
    var pie = document.querySelector('#sopCapa .sop-pie');
    if (!pie) return;
    var p = document.createElement('span');
    p.id = 'sopCorreo';
    p.className = 'sop-correo';
    p.style.cssText = 'flex:1;';
    p.innerHTML = 'O escríbenos a <a href="mailto:' + esc(plataforma.support_email) + '">' +
                  esc(plataforma.support_email) + '</a>';
    pie.insertBefore(p, pie.firstChild);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', arrancar);
  else arrancar();
})();
