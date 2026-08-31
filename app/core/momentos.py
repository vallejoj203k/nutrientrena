"""Los momentos del día en que se puede tomar un alimento.

Hay dos vocabularios y hasta ahora nadie los traducía:

  · La pantalla guarda CLAVES cortas — `desayuno`, `snack`, `principal` — que
    son las que comparan los tres chips del formulario.
  · Los ficheros que prepara el cliente traen las ETIQUETAS que se leen en
    pantalla: "Desayuno", "Media mañana / merienda", "Comida / cena".

Importando las etiquetas tal cual, el dato entra en la base pero los chips no
se marcan: el alimento tiene su momento y el formulario lo enseña vacío. Se
guardan siempre las claves, que es lo que ya entendía la pantalla.

Vacío significa que el alimento vale para los tres momentos. Se guarda vacío y
no se rellena con los tres: son cosas distintas —"sin restricción" y "los tres
marcados a mano"— y el día que alguien quiera distinguirlas, el dato estará.
"""

# Clave interna -> cómo se lee en pantalla.
ETIQUETAS = {
    "desayuno": "Desayuno",
    "snack": "Media mañana / merienda",
    "principal": "Comida / cena",
}

# Todo lo que puede llegar en un fichero, ya normalizado, -> clave interna.
# Se aceptan las etiquetas completas y las claves, porque por la pantalla de
# importar puede entrar un CSV exportado antes por la propia plataforma.
_ALIAS = {
    "desayuno": "desayuno",
    "media manana / merienda": "snack",
    "media manana/merienda": "snack",
    "media manana": "snack",
    "merienda": "snack",
    "snack": "snack",
    "comida / cena": "principal",
    "comida/cena": "principal",
    "comida": "principal",
    "cena": "principal",
    "principal": "principal",
}


def _plano(s):
    """Sin tildes, sin mayúsculas y sin espacios de más, para comparar."""
    import unicodedata
    t = unicodedata.normalize("NFKD", (s or "").strip().lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.split())


def momentos_a_claves(valor):
    """El texto del fichero, convertido a las claves que usa la pantalla.

    Devuelve None cuando no hay ninguno: vacío = vale para los tres.

        "Desayuno, Comida / cena"  ->  "desayuno,principal"
        ""                         ->  None
    """
    claves = []
    for trozo in str(valor or "").split(","):
        c = _ALIAS.get(_plano(trozo))
        if c and c not in claves:
            claves.append(c)
    if not claves:
        return None
    # Siempre en el mismo orden, el del día: si no, el mismo alimento se guarda
    # de dos formas distintas según cómo viniera escrito en el fichero.
    orden = list(ETIQUETAS)
    return ",".join(sorted(claves, key=orden.index))


def texto_de_momentos(guardado):
    """Cómo se lee lo guardado. "" cuando vale para los tres."""
    claves = [c.strip() for c in str(guardado or "").split(",") if c.strip()]
    return ", ".join(ETIQUETAS[c] for c in claves if c in ETIQUETAS)


# Lo que un fichero puede traer en una columna de sí/no. Se lista en vez de
# usar `bool(texto)`, que daría True para la cadena "False".
_SI = {"true", "1", "si", "sí", "yes", "x", "verdadero"}
_NO = {"false", "0", "no", "none", "null", "falso"}


def booleano(valor, por_defecto=False):
    """Un sí/no de un fichero. `bool("False")` es True, que es el fallo obvio.

    Solo un NO escrito cuenta como no. Una celda vacía, o una columna que el
    fichero ni siquiera trae, no son una respuesta: valen lo que diga
    `por_defecto`. Tomarlas por un no dejaría fuera del generador alimentos
    sobre los que nadie se ha pronunciado, y eso no se nota — el generador
    simplemente no los propone nunca.
    """
    t = _plano(valor)
    if t in _SI:
        return True
    if t in _NO:
        return False
    return por_defecto          # incluye vacío y columna ausente
