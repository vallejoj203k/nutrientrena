#!/bin/bash
set -e

echo ">>> Corriendo migraciones..."
alembic upgrade head

echo ">>> Cargando seeds iniciales..."
python -m app.seeds.run_seeds

echo ">>> Iniciando servidor en puerto ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
