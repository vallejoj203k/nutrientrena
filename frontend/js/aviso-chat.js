/* Un sonido corto cuando llega un mensaje.

   Se genera aquí mismo con WebAudio en vez de servir un fichero: son dos tonos
   de 90 ms, pesan cero, no hay nada que descargar ni que se pueda quedar a
   medias con mala cobertura, y no depende de que R2 esté en pie.

   Cuatro cosas que un aviso sonoro tiene que respetar, y que se saltan casi
   todos:

     · No sonar por lo TUYO. Solo por lo que llega de otra persona.
     · No sonar al abrir la pantalla. El historial no es "un mensaje nuevo":
       entrar en el chat y oír siete pitidos seguidos es lo peor que puede
       pasar aquí.
     · Poderse callar, y que se recuerde. Un sonido que no se puede apagar se
       arregla cerrando la pestaña, y entonces se pierde el chat entero.
     · No pelearse con el navegador. Sin un clic previo del usuario, el móvil
       NO deja sonar nada; se intenta y, si no sale, no pasa nada — la pantalla
       no puede romperse por un pitido.
*/
(function () {
  'use strict';

  var LLAVE_SILENCIO = 'chat_sin_sonido';
  var _audio = null;
  var _ultimoSonido = 0;

  function silenciado() {
    try { return localStorage.getItem(LLAVE_SILENCIO) === '1'; }
    catch (e) { return false; }
  }

  function silenciar(valor) {
    try {
      if (valor) localStorage.setItem(LLAVE_SILENCIO, '1');
      else localStorage.removeItem(LLAVE_SILENCIO);
    } catch (e) {}
  }

  function contexto() {
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;                    // navegador sin WebAudio
    if (!_audio) { try { _audio = new AC(); } catch (e) { return null; } }
    return _audio;
  }

  /* Dos notas cortas, la segunda un poco más aguda. Sin ataque brusco: una
     onda cuadrada o un corte seco suenan a error, y esto no es un error. */
  function sonar() {
    if (silenciado()) return false;
    // Dos mensajes seguidos no son dos pitidos encimados.
    var ahora = Date.now();
    if (ahora - _ultimoSonido < 900) return false;

    var ctx = contexto();
    if (!ctx) return false;
    // El navegador suspende el audio hasta que hay un gesto del usuario.
    if (ctx.state === 'suspended') { try { ctx.resume(); } catch (e) {} }
    if (ctx.state !== 'running') return false;

    _ultimoSonido = ahora;
    try {
      [[660, 0], [880, 0.09]].forEach(function (par) {
        var frec = par[0], retraso = par[1];
        var osc = ctx.createOscillator();
        var vol = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.value = frec;
        var t0 = ctx.currentTime + retraso;
        // Subida y bajada suaves: un corte seco chasquea.
        vol.gain.setValueAtTime(0.0001, t0);
        vol.gain.exponentialRampToValueAtTime(0.09, t0 + 0.012);
        vol.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.11);
        osc.connect(vol); vol.connect(ctx.destination);
        osc.start(t0); osc.stop(t0 + 0.13);
      });
      return true;
    } catch (e) { return false; }
  }

  /* El permiso del navegador se gana con un gesto. Se aprovecha el primero que
     haga el usuario en la página, sea el que sea, para dejar el audio listo;
     así el primer mensaje que llegue ya suena. */
  function despertarConElPrimerGesto() {
    var hecho = false;
    function despertar() {
      if (hecho) return;
      hecho = true;
      var ctx = contexto();
      if (ctx && ctx.state === 'suspended') { try { ctx.resume(); } catch (e) {} }
      ['pointerdown', 'keydown', 'touchstart'].forEach(function (ev) {
        document.removeEventListener(ev, despertar);
      });
    }
    ['pointerdown', 'keydown', 'touchstart'].forEach(function (ev) {
      document.addEventListener(ev, despertar, { passive: true });
    });
  }
  despertarConElPrimerGesto();

  window.avisoChat = {
    sonar: sonar,
    silenciado: silenciado,
    silenciar: silenciar,
    /* Devuelve el nuevo estado, para que el botón se pinte con la verdad y no
       con lo que cree que pasó. */
    alternar: function () { silenciar(!silenciado()); return silenciado(); }
  };
})();
