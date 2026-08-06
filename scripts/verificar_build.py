#!/usr/bin/env python3
"""Comprueba que el despliegue va a construirse como proyecto Python.

Existe por una caída real: al añadir un package.json en la raíz para fijar la
versión de Playwright, Nixpacks —que es quien construye en Railway, ver
railway.toml— dejó de ver un proyecto Python y pasó a verlo como Node.
Instaló dependencias de npm, nunca ejecutó `pip install -r requirements.txt`, y
el arranque falló con "alembic: command not found" y "uvicorn: not found".

Lo peligroso es que CI estaba en verde: los jobs instalan las dependencias a
mano, así que la detección de Nixpacks no se ejercita en ningún sitio. Este
script cierra ese punto ciego sin depender de tener Nixpacks instalado.

Uso:  python3 scripts/verificar_build.py
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ficheros de la raíz que hacen que Nixpacks elija otro lenguaje. La lista no
# pretende ser exhaustiva: son los que podrían aparecer en este repositorio.
INDICADORES_DE_OTRO_LENGUAJE = {
    "package.json": "Node",
    "package-lock.json": "Node",
    "yarn.lock": "Node",
    "pnpm-lock.yaml": "Node",
    "bun.lockb": "Bun",
    "deno.json": "Deno",
    "Gemfile": "Ruby",
    "go.mod": "Go",
    "composer.json": "PHP",
    "Cargo.toml": "Rust",
    "pom.xml": "Java",
    "build.gradle": "Java",
}

# Lo que Nixpacks necesita ver para elegir Python.
REQUERIDOS_PYTHON = ["requirements.txt"]


def main() -> int:
    problemas = []

    for fichero in REQUERIDOS_PYTHON:
        if not os.path.isfile(os.path.join(RAIZ, fichero)):
            problemas.append(
                f"Falta {fichero} en la raíz: sin él Nixpacks no detecta Python."
            )

    for fichero, lenguaje in INDICADORES_DE_OTRO_LENGUAJE.items():
        if os.path.exists(os.path.join(RAIZ, fichero)):
            problemas.append(
                f"{fichero} está en la RAÍZ y hace que Nixpacks construya como "
                f"{lenguaje} en vez de Python. El despliegue arrancará sin "
                f"alembic ni uvicorn. Si son dependencias de pruebas, van en "
                f"tests/ (ver tests/package.json)."
            )

    if problemas:
        print("El despliegue NO se construiría como Python:\n")
        for p in problemas:
            print(f"  - {p}")
        return 1

    print("La raíz indica Python: requirements.txt presente y ningún "
          "fichero de otro lenguaje.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
