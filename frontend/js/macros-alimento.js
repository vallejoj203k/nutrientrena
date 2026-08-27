/* Cuánto aporta una cantidad de un alimento.

   La fórmula estaba copiada en unos cuarenta sitios entre el backend y las
   pantallas, y todas dividían entre 100 a ciegas. Pero no todos los alimentos
   vienen por 100 g: un huevo grande son 74 kcal por UNIDAD, un cacito de
   proteína 117 kcal por 29 g, un yogur griego 176 kcal por el envase de 125 g.

   Con el divisor fijo, el coach que ponía dos huevos en una dieta veía 1,5 kcal
   en vez de 148, y el yogur contaba 220 en vez de 176. Fallaba en las dos
   direcciones y el total de la dieta descuadraba sin que nadie supiera por qué.

   El dato que hace falta ya estaba guardado —`quantity` dice a qué cantidad se
   refieren esos macros—; lo único que pasaba es que nadie lo miraba.

   Va en un fichero aparte, y no copiado en cada pantalla, porque de eso venía
   el problema: cuarenta copias de la misma cuenta y ninguna forma de
   arreglarlas todas a la vez. Es el mismo criterio que `app/core/macros.py`,
   que hace exactamente esto en el servidor. */
(function (global) {
  'use strict';

  /* La cantidad a la que se refieren los macros del alimento. Sin dato, 100:
     es lo que la aplicación ha hecho siempre y lo que vale para la enorme
     mayoría del catálogo. Un cero se trata igual que un vacío, que si no la
     división deja la pantalla llena de "Infinity". */
  function porcionDe(al) {
    var q = al && (al.quantity != null ? al.quantity : al.cantidad);
    q = parseFloat(q);
    return (isFinite(q) && q > 0) ? q : 100;
  }

  /* Lo que aportan `cantidad` unidades de este alimento. `valor` es el macro
     tal como está guardado (kcal, proteínas…), referido a su porción. */
  function escalar(valor, al, cantidad) {
    var v = parseFloat(valor), c = parseFloat(cantidad);
    if (!isFinite(v) || !isFinite(c)) return 0;
    return v / porcionDe(al) * c;
  }

  global.macrosAlimento = { porcionDe: porcionDe, escalar: escalar };
})(window);
