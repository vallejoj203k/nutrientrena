#!/bin/bash
set -e

echo "=========================================="
echo "  DB DIAGNOSTICO (sin passwords)"
echo "=========================================="
echo "  DATABASE_URL  = ${DATABASE_URL:-(no seteado)}"
echo "  MYSQL_URL     = ${MYSQL_URL:-(no seteado)}"
echo "  MYSQLHOST     = ${MYSQLHOST:-(no seteado)}"
echo "  MYSQLPORT     = ${MYSQLPORT:-(no seteado)}"
echo "  MYSQLUSER     = ${MYSQLUSER:-(no seteado)}"
echo "  MYSQLDATABASE = ${MYSQLDATABASE:-(no seteado)}"
echo "  DB_HOST       = ${DB_HOST:-(no seteado)}"
echo "=========================================="

echo ">>> Corriendo migraciones..."
alembic upgrade head

echo ">>> Cargando seeds iniciales..."
python -m app.seeds.run_seeds

echo ">>> Iniciando servidor en puerto ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
