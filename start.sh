#!/bin/bash

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

echo ">>> Alembic heads actuales (en archivos):"
alembic heads 2>&1 || true

echo ">>> Corriendo migraciones..."
alembic upgrade heads 2>&1
MIGRATION_EXIT=$?
if [ $MIGRATION_EXIT -eq 0 ]; then
    echo ">>> Migraciones OK"
    echo ">>> Cargando seeds iniciales..."
    python -m app.seeds.run_seeds && echo ">>> Seeds OK" || echo ">>> Seeds fallaron (continuando)"
else
    echo ">>> MIGRACIONES FALLARON (exit=$MIGRATION_EXIT) — intentando upgrade head como fallback..."
    alembic upgrade head 2>&1 || echo ">>> Fallback tambien fallo — iniciando servidor de todos modos"
fi

echo ">>> Iniciando servidor en puerto ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
