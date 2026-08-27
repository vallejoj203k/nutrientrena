/* Leer la descripción de un ejercicio como una lista de pasos.
 *
 * El campo es una caja de texto libre y la pantalla numeraba TODAS las líneas,
 * una por una. Eso funciona mientras el autor escriba solo pasos sueltos, que
 * es como está escrito el catálogo de siempre. En cuanto alguien da estructura
 * a lo que escribe, se rompe de tres formas a la vez:
 *
 *   · Numera a mano ("1. Siéntate…") y sale "1. 1. Siéntate…".
 *   · Pone un título ("⚠ Errores comunes") y sale como si fuera el paso 5.
 *   · Pone viñetas ("- Usar impulso.") y salen como pasos 6, 7, 8 y 9.
 *
 * La regla es: hacer caso a lo que el autor escribió.
 *
 *   · Una línea con viñeta (-, –, •, *) es una viñeta. Nunca un paso numerado.
 *   · Una línea numerada a mano es un paso, y se le quita el número escrito
 *     para poner el nuestro: si no, salen los dos.
 *   · Las demás líneas dependen del texto entero. Si en alguna parte hay
 *     números a mano o viñetas, el autor está montando su propia estructura y
 *     una línea suelta es un título, no un paso. Si no hay nada de eso —el
 *     catálogo entero de hoy—, cada línea es un paso, como hasta ahora.
 *
 * Esa última condición es la que evita que arreglar esto renumere de golpe
 * todos los ejercicios que ya están escritos.
 */
(function (raiz) {
  var VINETA = /^[-–—•*]\s+/;
  var NUMERO = /^\d+\s*[.)-]\s+/;

  function pasosDeEjecucion(texto) {
    var lineas = String(texto == null ? '' : texto)
      .split(/\r?\n/)
      .map(function (s) { return s.trim(); })
      .filter(Boolean);
    if (!lineas.length) return [];

    var hayEstructura = lineas.some(function (l) {
      return VINETA.test(l) || NUMERO.test(l);
    });

    var n = 0;
    return lineas.map(function (l) {
      if (VINETA.test(l)) {
        return { tipo: 'vineta', texto: l.replace(VINETA, '') };
      }
      if (NUMERO.test(l)) {
        n += 1;
        return { tipo: 'paso', numero: n, texto: l.replace(NUMERO, '') };
      }
      if (hayEstructura) {
        return { tipo: 'titulo', texto: l };
      }
      n += 1;
      return { tipo: 'paso', numero: n, texto: l };
    });
  }

  raiz.pasosDeEjecucion = pasosDeEjecucion;
  if (typeof module !== 'undefined' && module.exports) module.exports = { pasosDeEjecucion: pasosDeEjecucion };
})(typeof window !== 'undefined' ? window : globalThis);
