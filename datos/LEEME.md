# Datos para cargas de una sola vez

## `alimentos-catalogo.csv`

El catálogo de alimentos que prepara el cliente: **1.441 filas** en 28
categorías, con las marcas separadas del nombre, el momento sugerido de cada
alimento y la marca de si entra o no en el generador de dietas.

Está aquí y no en el ordenador de nadie para que la carga se pueda repetir y
comprobar: con el fichero suelto en Descargas, la ruta cambia según quién lo
lance y nadie sabe después qué se cargó exactamente. Este fichero ES lo que
hay en producción.

No lleva datos personales: son alimentos, sus macros y sus fuentes.

### Cosas del fichero que conviene saber

  · **Una celda vacía es SIN DATO, no un cero.** La ficha del alimento pinta
    una rayita cuando no hay dato; un cero inventado diría "este alimento no
    tiene vitamina D", que es una afirmación que nadie ha hecho.
  · **Hay nombres repetidos, y está bien.** Son el genérico y sus versiones de
    marca: "Avena", "Avena · Brüggen" y "Avena · Max Protein" son tres
    alimentos distintos con macros distintos. El buscador enseña la marca al
    lado del nombre, así que se distinguen.
  · `momento_sugerido` viene con las etiquetas largas ("Media mañana /
    merienda") y el importador las traduce a las claves que comparan los chips
    del formulario. Vacío significa que vale para cualquier momento.
  · `usar_en_generador` en `False` deja al alimento fuera del generador de
    dietas. Son alimentos apartados a propósito, uno a uno.
  · Las columnas `tiene_micros` y `es_duplicado` son notas de trabajo del
    cliente: el importador no las usa.

### Cómo se carga

    python scripts/copia_seguridad.py             # primero esto. No se deshace.
    python scripts/limpiar_y_cargar_alimentos.py --inspeccionar
    python scripts/limpiar_y_cargar_alimentos.py  # ensayo: cuenta, no escribe
    python scripts/limpiar_y_cargar_alimentos.py --ejecutar
    python scripts/limpiar_y_cargar_alimentos.py --verificar

Sin `--csv` coge este fichero. Y ojo: la carga **sustituye el catálogo entero**
y se lleva por delante dietas, recetas, rutinas y menús, porque apuntaban a
alimentos que dejan de existir. El historial de entrenos de los clientes se
conserva.
