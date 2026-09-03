/* ═══════════════════════════════════════════════════════════════════════════
   Los micronutrientes de un alimento, para el panel de "Buscar alimentos".

   El mismo modal está en diets.html, client-profile.html y recipes.html. Ya ha
   pasado tres veces que un arreglo se hace en una pantalla y las otras dos se
   quedan atrás, así que esto vive aquí: el panel entero lo pinta este módulo y
   cada pantalla solo dice dónde.

   Sobre el % VRN: es el Valor de Referencia de Nutrientes del Reglamento (UE)
   1169/2011, anexo XIII — lo que la ley manda poner en una etiqueta. Dice qué
   parte de un día cubre esa cantidad, que es lo que hace legible un número
   como "210 mg de fósforo".

   OJO con las unidades: la base guarda cada micro en un número pelado, sin
   decir en qué unidad está. Se asume lo de siempre —miligramos, salvo los que
   van en microgramos— porque es lo que ya hacía la ficha del alimento. Si un
   alimento tiene el dato en otra unidad, aquí se verá igual de mal que allí:
   el sitio de arreglarlo es el dato, no la pantalla.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';

  var NOMBRES = {
    vita: 'Vitamina A', vitb1: 'Vitamina B1', vitb2: 'Vitamina B2',
    vitb3: 'Vitamina B3', vitb5: 'Vitamina B5', vitb6: 'Vitamina B6',
    vitb9: 'Vitamina B9', vitb12: 'Vitamina B12', vitc: 'Vitamina C',
    vitd: 'Vitamina D', vite: 'Vitamina E', vitk: 'Vitamina K',
    calcium: 'Calcio', copper: 'Cobre', iron: 'Hierro', magnesium: 'Magnesio',
    manganese: 'Manganeso', phosphorus: 'Fósforo', potassium: 'Potasio',
    selenium: 'Selenio', sodium: 'Sodio', zinc: 'Zinc',
    calina: 'Colina', cholesterol: 'Colesterol', saturated_fats: 'Grasas saturadas',
    mono_saturated_fats: 'G. monoinsaturadas', poli_saturated_fats: 'G. poliinsaturadas',
    sugars: 'Azúcares', water: 'Agua', glycemic_index: 'Índice glucémico'
  };

  // Todo lo demás va en miligramos.
  var UNIDADES = {
    vita: 'mcg', vitb9: 'mcg', vitb12: 'mcg', vitd: 'mcg', vitk: 'mcg',
    selenium: 'mcg',
    saturated_fats: 'g', mono_saturated_fats: 'g', poli_saturated_fats: 'g',
    sugars: 'g', water: 'g',
    glycemic_index: ''
  };

  /* Reglamento (UE) 1169/2011, anexo XIII, en la misma unidad en que se
     enseña cada uno. El sodio no tiene VRN: se usa la ingesta de referencia
     de sal (6 g/día ≈ 2400 mg de sodio), y las grasas saturadas la suya. Lo
     que no aparece aquí no lleva porcentaje, que es mejor que inventarle uno:
     el colesterol o el agua no tienen valor de referencia. */
  var VRN = {
    vita: 800, vitb1: 1.1, vitb2: 1.4, vitb3: 16, vitb5: 6, vitb6: 1.4,
    vitb9: 200, vitb12: 2.5, vitc: 80, vitd: 5, vite: 12, vitk: 75,
    calcium: 800, copper: 1, iron: 14, magnesium: 375, manganese: 2,
    phosphorus: 700, potassium: 2000, selenium: 55, sodium: 2400, zinc: 10,
    saturated_fats: 20
  };

  var GRUPOS = [
    { titulo: 'Vitaminas', claves: ['vita', 'vitb1', 'vitb2', 'vitb3', 'vitb5',
      'vitb6', 'vitb9', 'vitb12', 'vitc', 'vitd', 'vite', 'vitk'] },
    { titulo: 'Minerales', claves: ['calcium', 'iron', 'magnesium', 'phosphorus',
      'potassium', 'sodium', 'zinc', 'selenium', 'copper', 'manganese'] },
    // La fibra no está: ya se enseña arriba, con el aporte de la ración.
    { titulo: 'Otros', claves: ['sugars', 'saturated_fats', 'mono_saturated_fats',
      'poli_saturated_fats', 'cholesterol', 'calina', 'water', 'glycemic_index'] }
  ];

  /* El valor puede venir en la ficha de micros o suelto en el alimento: los
     personales del cliente no tienen ficha aparte. */
  function valorDe(al, clave) {
    if (!al) return null;
    var ficha = al.description || {};
    var v = ficha[clave];
    if (v == null) v = al[clave];
    if (v == null || v === '') return null;
    v = parseFloat(v);
    return isFinite(v) ? v : null;
  }

  /* Tres cifras significativas: 13.7, 0.800, 210. Con más, una columna de
     números deja de leerse de un vistazo. */
  function cifra(v) {
    var n = Number(v);
    if (!isFinite(n)) return '—';
    if (n === 0) return '0';
    if (Math.abs(n) >= 1000) return String(Math.round(n));
    return n.toPrecision(3);
  }

  function porcentaje(clave, valor) {
    var ref = VRN[clave];
    if (!ref || valor == null) return null;
    return Math.round(valor / ref * 100);
  }

  /* Lo que tiene ese alimento, agrupado y en el orden del diseño. Los grupos
     sin ningún dato no salen: una cabecera "VITAMINAS" sin nada debajo ocupa
     sitio para decir que no hay nada. */
  function grupos(al) {
    var salida = [];
    GRUPOS.forEach(function (g) {
      var filas = [];
      g.claves.forEach(function (clave) {
        var v = valorDe(al, clave);
        if (v == null) return;
        filas.push({
          clave: clave,
          nombre: NOMBRES[clave] || clave,
          valor: v,
          texto: cifra(v),
          unidad: UNIDADES[clave] == null ? 'mg' : UNIDADES[clave],
          vrn: porcentaje(clave, v)
        });
      });
      if (filas.length) salida.push({ titulo: g.titulo, filas: filas });
    });
    return salida;
  }

  function cuantos(al) {
    return grupos(al).reduce(function (n, g) { return n + g.filas.length; }, 0);
  }

  /* A qué cantidad se refieren estos valores. No se escalan con la ración: son
     los del alimento, y la cabecera dice de qué porción habla. Escalarlos sin
     decirlo llevaría a leer "40% VRN de selenio" de una ración de 10 g. */
  function porcion(al) {
    var m = global.macrosAlimento;
    var cantidad = m ? m.porcionDe(al) : (parseFloat(al && al.quantity) || 100);
    var unidad = m ? m.unidadDe(al) : ((al && al.quantity_unit) || 'g');
    // Aquí no valen las tres cifras significativas de los valores: la porción
    // es "1 ud" o "100 g", no "1.00 ud".
    return (Math.round(cantidad * 100) / 100) + ' ' + unidad;
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  var LLAMA = '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>';
  var PROTE = '<path d="M15.4 15.63a7.875 6 135 1 1 6.23-6.23 4.5 3.43 135 0 0-6.23 6.23"/><path d="m8.29 12.71-2.6 2.6a2.5 2.5 0 1 0-1.65 4.65A2.5 2.5 0 1 0 8.7 18.3l2.59-2.59"/>';
  var TRIGO = '<path d="M2 22 16 8"/><path d="M3.47 12.53 5 11l1.53 1.53a3.5 3.5 0 0 1 0 4.94L5 19l-1.53-1.53a3.5 3.5 0 0 1 0-4.94Z"/><path d="M11.47 4.53 13 3l1.53 1.53a3.5 3.5 0 0 1 0 4.94L13 11l-1.53-1.53a3.5 3.5 0 0 1 0-4.94Z"/><path d="M20 2h2v2a4 4 0 0 1-4 4h-2V6a4 4 0 0 1 4-4Z"/>';
  var GOTA  = '<path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z"/>';
  var HOJA  = '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>';
  var ICONO = '<svg width="14" height="14" fill="none" stroke="#7C3AED" stroke-width="2" viewBox="0 0 24 24"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>';
  var CHEVRON = '<svg class="fsm-mic-chev" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"/></svg>';

  /* El panel entero. Devuelve '' si el alimento no tiene ni un dato: un
     desplegable que se abre y está vacío es una promesa incumplida. */
  function panelHTML(al, abierto) {
    var gs = grupos(al);
    if (!gs.length) return '';
    var n = gs.reduce(function (t, g) { return t + g.filas.length; }, 0);

    var cuerpo = gs.map(function (g) {
      return '<div class="fsm-mic-grupo">'
        + '<div class="fsm-mic-grupo-t">' + esc(g.titulo) + '</div>'
        + g.filas.map(function (f) {
            return '<div class="fsm-mic-fila">'
              + '<span class="fsm-mic-nom">' + esc(f.nombre) + '</span>'
              + '<span class="fsm-mic-val">' + esc(f.texto)
              +   (f.unidad ? ' <span class="fsm-mic-uni">' + esc(f.unidad) + '</span>' : '')
              + '</span>'
              + '<span class="fsm-mic-vrn">' + (f.vrn != null ? f.vrn + '% VRN' : '') + '</span>'
              + '</div>';
          }).join('')
        + '</div>';
    }).join('');

    return '<div class="fsm-mic' + (abierto ? ' abierto' : '') + '">'
      + '<button type="button" class="fsm-mic-head" onclick="microsAlimento.alternar(this)"'
      +   ' aria-expanded="' + (abierto ? 'true' : 'false') + '">'
      +   '<span class="fsm-mic-t">' + ICONO + ' Micronutrientes (' + esc(porcion(al)) + ')</span>'
      +   '<span class="fsm-mic-n">' + n + (n === 1 ? ' dato' : ' datos') + '</span>'
      +   CHEVRON
      + '</button>'
      + '<div class="fsm-mic-body"' + (abierto ? '' : ' hidden') + '>' + cuerpo + '</div>'
      + '</div>';
  }


  /* ── El resumen de un menú entero ─────────────────────────────────────────
     Lo mismo, pero sumado: cuánto aporta el día completo. Los valores los
     suma el servidor (`/aliments/resumen-nutricional`) porque los micros no
     viajan con la dieta; aquí solo se pintan. */
  function resumenHTML(d) {
    d = d || {};
    var micros = d.micros || {};
    var tarjeta = function (color, dibujo, valor, unidad, etiqueta) {
      return '<div class="rn-macro">'
        + '<div class="rn-macro-t"><svg width="14" height="14" fill="none" stroke="' + color
        +   '" stroke-width="2" viewBox="0 0 24 24">' + dibujo + '</svg>' + etiqueta + '</div>'
        + '<div class="rn-macro-v" style="color:' + color + '">' + cifra(valor || 0)
        +   '<small>' + unidad + '</small></div></div>';
    };

    var gs = grupos({ description: micros });
    var cuerpo = gs.length
      ? gs.map(function (g) {
          return '<div class="fsm-mic-grupo"><div class="fsm-mic-grupo-t">' + esc(g.titulo) + '</div>'
            + g.filas.map(function (f) {
                return '<div class="fsm-mic-fila">'
                  + '<span class="fsm-mic-nom">' + esc(f.nombre) + '</span>'
                  + '<span class="fsm-mic-val">' + esc(f.texto)
                  +   (f.unidad ? ' <span class="fsm-mic-uni">' + esc(f.unidad) + '</span>' : '')
                  + '</span>'
                  + '<span class="fsm-mic-vrn">' + (f.vrn != null ? f.vrn + '% VRN' : '') + '</span>'
                  + '</div>';
              }).join('')
            + '</div>';
        }).join('')
      : '<div class="rn-vacio">Los alimentos añadidos no tienen micronutrientes'
        + ' registrados todavía.</div>';

    /* Si parte de los alimentos no tiene ficha, la suma se queda corta. Se
       dice: un total incompleto que parece completo engaña más que no darlo. */
    var falta = d.sin_datos
      ? '<div class="rn-falta">' + d.sin_datos + (d.sin_datos === 1
          ? ' alimento del plan no tiene micronutrientes en su ficha, así que no cuenta en esta suma.'
          : ' alimentos del plan no tienen micronutrientes en su ficha, así que no cuentan en esta suma.')
        + '</div>'
      : '';

    return '<div class="rn-macros">'
      + tarjeta('#F97316', LLAMA, d.calories, ' kcal', 'Calorías')
      + tarjeta('#EF4444', PROTE, d.proteins, ' g', 'Proteínas')
      + tarjeta('#D97706', TRIGO, d.carbohydrates, ' g', 'Carbohidratos')
      + tarjeta('#3B82F6', GOTA, d.fats, ' g', 'Grasas')
      + tarjeta('#10B981', HOJA, micros.fiber, ' g', 'Fibra')
      + '</div>'
      + '<div class="rn-sec">' + ICONO + ' <b>Micronutrientes</b>'
      +   '<span>acumulados de todos los alimentos del plan</span></div>'
      + '<div class="rn-cuerpo">' + cuerpo + '</div>'
      + falta
      + '<div class="rn-pie">% VRN = porcentaje del valor de referencia diario para un'
      + ' adulto medio. Solo se muestran los nutrientes con datos registrados en la'
      + ' ficha del alimento.</div>';
  }

  function alternar(btn) {
    var caja = btn.parentElement;
    var cuerpo = caja.querySelector('.fsm-mic-body');
    var abierto = !caja.classList.contains('abierto');
    caja.classList.toggle('abierto', abierto);
    cuerpo.hidden = !abierto;
    btn.setAttribute('aria-expanded', abierto ? 'true' : 'false');
    // Que siga abierto al mirar el siguiente alimento: quien lo abre es
    // porque está comparando, y cerrarlo cada vez obliga a abrirlo otra vez.
    global.microsAlimento._abierto = abierto;
  }

  /* Lo que llama cada pantalla: pinta (o esconde) el panel en su hueco. */
  function pinta(al, id) {
    var caja = document.getElementById(id || 'fsmMicros');
    if (!caja) return;
    var html = panelHTML(al, !!global.microsAlimento._abierto);
    caja.innerHTML = html;
    caja.style.display = html ? '' : 'none';
  }

  global.microsAlimento = {
    grupos: grupos, cuantos: cuantos, panelHTML: panelHTML, pinta: pinta,
    resumenHTML: resumenHTML,
    alternar: alternar, cifra: cifra, porcion: porcion,
    NOMBRES: NOMBRES, UNIDADES: UNIDADES, VRN: VRN,
    _abierto: false
  };
})(window);
