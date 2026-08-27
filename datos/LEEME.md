# Datos para cargas de una sola vez

## `alimentos-catalogo.csv`

El catálogo de alimentos que preparó el cliente: 803 filas, organizadas por
categoría, con las marcas separadas del nombre y los micronutrientes de los
que los tenían.

Está aquí y no en el ordenador de nadie para que la carga se pueda repetir y
comprobar: con el fichero suelto en Descargas, la ruta cambia según quién lo
lance y nadie sabe después qué se cargó exactamente.

No lleva datos personales: son alimentos y sus macros.

Se carga con:

    python scripts/limpiar_y_cargar_alimentos.py --csv datos/alimentos-catalogo.csv
    python scripts/limpiar_y_cargar_alimentos.py --csv datos/alimentos-catalogo.csv --ejecutar

El primero no toca nada: cuenta lo que haría y lo enseña.
