/* El menú de "…" de una fila de tabla.

   Estaba copiado en cuatro pantallas —dietas, menús, recetas y alimentos— y
   las cuatro tenían el mismo fallo: el menú se abría, pero no se veía.

   La causa no está en el menú, está en la tabla. `.lib-table` lleva
   `overflow:hidden` para que las esquinas redondeadas recorten las filas, y
   `.lib-table-wrap` lleva `overflow-y:auto` para poder desplazarse. Un menú
   posicionado con `position:absolute` cuelga de la fila, y una caja con
   `overflow` recorta a sus hijos posicionados: el menú se dibujaba dentro de
   la tabla y lo que sobresalía desaparecía. En la última fila, o con una sola
   fila, no se veía absolutamente nada.

   La salida no es quitarle el `overflow` a la tabla —se perderían las esquinas
   y el desplazamiento—, sino sacar el menú de ahí: con `position:fixed` ya no
   cuelga de la fila sino de la ventana, y ninguna caja intermedia puede
   recortarlo. A cambio hay que colocarlo a mano, porque `fixed` no sabe dónde
   está su botón.

   Uso:  <button onclick="menuFila.abrir(event, this)">…</button>
         <div class="lib-menu-dd"> … </div>
*/
(function (global) {
  'use strict';

  var HUECO = 4;      // separación entre el botón y el menú
  var MARGEN = 8;     // aire mínimo contra el borde de la ventana
  var _abierto = null;
  var _suelto = null;

  function colocar(dd, btn) {
    var r = btn.getBoundingClientRect();
    dd.style.position = 'fixed';
    var alto = dd.offsetHeight, ancho = dd.offsetWidth;

    /* Si abajo no cabe, se abre hacia arriba. Sin esto, el menú de la última
       fila de una tabla larga se sale por debajo de la ventana, que es otra
       forma de no verlo. */
    var cabeAbajo = r.bottom + HUECO + alto <= global.innerHeight - MARGEN;
    var cabeArriba = r.top - HUECO - alto >= MARGEN;
    dd.style.top = ((cabeAbajo || !cabeArriba) ? r.bottom + HUECO : r.top - HUECO - alto) + 'px';

    // Alineado por la derecha con el botón, sin salirse por ningún lado.
    var izq = Math.min(r.right - ancho, global.innerWidth - ancho - MARGEN);
    dd.style.left = Math.max(MARGEN, izq) + 'px';
    dd.style.right = 'auto';
    dd.style.bottom = 'auto';
  }

  function cerrar() {
    var abiertos = document.querySelectorAll('.lib-menu-dd.open');
    Array.prototype.forEach.call(abiertos, function (d) { d.classList.remove('open'); });
    if (_suelto) {
      if (_suelto.parentNode) _suelto.parentNode.removeChild(_suelto);
      _suelto = null;
    }
    _abierto = null;
  }

  /* Un menú que la pantalla se ha fabricado y ha colgado del `body`, en vez
     del que ya está en la fila. Es el caso de Ejercicios, que arma el suyo
     según lo que el coach puede hacer con ese ejercicio. Se coloca igual
     —incluido abrirse hacia arriba cuando abajo no cabe, que era justo lo
     que le pasaba en la última fila— y se cierra por los mismos caminos. */
  function suelto(el, btn) {
    cerrar();
    colocar(el, btn);
    _suelto = el;
  }

  function abrir(e, btn) {
    if (e) e.stopPropagation();
    var dd = btn.nextElementSibling;
    if (!dd) return;
    var estaba = dd.classList.contains('open');
    cerrar();
    if (estaba) return;                       // segundo clic: se cierra
    dd.classList.add('open');
    colocar(dd, btn);
    _abierto = { dd: dd, btn: btn };
  }

  document.addEventListener('click', function () { cerrar(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') cerrar(); });

  /* Al desplazar, el menú se cierra. Está anclado a una fila que se está
     moviendo, y un menú flotando sobre otra fila señalaría a la dieta
     equivocada — el peor final posible para un menú que borra cosas. */
  document.addEventListener('scroll', function () { if (_abierto || _suelto) cerrar(); }, true);
  global.addEventListener('resize', function () { if (_abierto || _suelto) cerrar(); });

  global.menuFila = { abrir: abrir, cerrar: cerrar, colocar: colocar, suelto: suelto };

  /* Las pantallas llamaban a estas dos por su nombre de siempre. Se dejan
     apuntando aquí para no tener que tocar cada `onclick` de cada fila. */
  global.toggleRowMenu = abrir;
  global.closeRowMenus = cerrar;
})(window);
