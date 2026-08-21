/* Quién puede tocar qué contenido de la Librería.

   La regla es una sola frase: lo que está en el catálogo de la plataforma es de
   Alzum, y un coach lo VE y lo USA pero no lo edita ni lo borra. Lo suyo, sí.

   Estaba escrita cinco veces —rutinas, alimentos, dietas, recetas, menús— y
   como pasa siempre con lo copiado, había divergido: en ejercicios no estaba,
   así que el menú de cada fila ofrecía "Eliminar" también en el catálogo común.
   El servidor lo rechazaba con un 403, pero eso es lo de menos: una pantalla
   que ofrece algo que no se puede hacer ya está mintiendo.

   `organization_id` es lo que lo dice:
     · null  → catálogo de la plataforma. De Alzum.
     · valor → de esa cuenta.

   El editor de contenido global (rol 7) es el caso raro: mantener el catálogo
   común es literalmente su único trabajo, así que a él sí se le deja — pero
   solo con ejercicios y alimentos, que es lo que gestiona. */
(function () {
  'use strict';

  var SUPERADMIN = 1, ADMIN = 2, EDITOR_GLOBAL = 7;

  function miRol() {
    try { return parseInt(localStorage.getItem('role_id') || '0', 10); }
    catch (e) { return 0; }
  }

  function esDeLaPlataforma(obj) {
    return !obj || obj.organization_id == null;
  }

  /* `tipo` solo hace falta para el editor global: es lo que decide si esta
     familia entra en su encargo. */
  function puedeEditarContenido(obj, tipo) {
    if (!esDeLaPlataforma(obj)) return true;   // es de tu cuenta
    var rol = miRol();
    if (rol === SUPERADMIN || rol === ADMIN) return true;
    if (rol === EDITOR_GLOBAL && (tipo === 'ejercicio' || tipo === 'alimento')) return true;
    return false;
  }

  /* Por qué no se puede, para poder decirlo en vez de esconder el botón sin
     explicación. */
  function motivoNoEditar(tipo) {
    var nombres = {
      ejercicio: 'Este ejercicio es', rutina: 'Esta rutina es',
      alimento: 'Este alimento es', dieta: 'Esta dieta es',
      receta: 'Esta receta es', menu: 'Este menú es'
    };
    return (nombres[tipo] || 'Esto es') + ' del catálogo de Alzum: puedes usarlo, ' +
           'pero no editarlo ni eliminarlo. Duplícalo para tener tu propia versión.';
  }

  window.esDeLaPlataforma = esDeLaPlataforma;
  window.puedeEditarContenido = puedeEditarContenido;
  window.motivoNoEditar = motivoNoEditar;
})();
