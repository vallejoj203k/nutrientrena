#!/usr/bin/env bash
#
# Copia de seguridad de la base de datos, antes de una operación que no se
# deshace (la carga del catálogo de alimentos, una migración grande…).
#
# Hace el volcado Y LO COMPRUEBA. Que el fichero exista no significa nada: un
# volcado cortado a la mitad pesa lo suyo y parece correcto hasta el día que
# hace falta restaurarlo, que es el peor día para descubrirlo.
#
#   ./scripts/copia_seguridad.sh "mysql://usuario:clave@host:puerto/base"
#
# La URL sale de Railway: pestaña de la base de datos -> Variables -> MYSQL_URL.
#
set -euo pipefail

URL="${1:-${DATABASE_URL:-}}"
if [ -z "$URL" ]; then
  echo "Falta la URL de la base de datos." >&2
  echo "Uso: $0 \"mysql://usuario:clave@host:puerto/base\"" >&2
  exit 1
fi

command -v mysqldump >/dev/null 2>&1 || {
  echo "No está mysqldump. En Debian/Ubuntu: sudo apt install mysql-client" >&2
  echo "En macOS: brew install mysql-client" >&2
  exit 1
}

# La URL puede venir como mysql:// o mysql+pymysql:// (la que usa la app).
LIMPIA="${URL/mysql+pymysql:\/\//mysql://}"
SIN_ESQUEMA="${LIMPIA#mysql://}"
CREDENCIALES="${SIN_ESQUEMA%%@*}"
RESTO="${SIN_ESQUEMA#*@}"
USUARIO="${CREDENCIALES%%:*}"
CLAVE="${CREDENCIALES#*:}"
HOSTPUERTO="${RESTO%%/*}"
BASE="${RESTO#*/}"
BASE="${BASE%%\?*}"
HOST="${HOSTPUERTO%%:*}"
PUERTO="${HOSTPUERTO#*:}"
[ "$PUERTO" = "$HOST" ] && PUERTO=3306

DESTINO="copia-${BASE}-$(date +%Y%m%d-%H%M%S).sql"

echo "Volcando ${BASE} de ${HOST}:${PUERTO} …"
# --single-transaction: la copia sale coherente sin bloquear la aplicación.
# --routines --triggers: si no, se pierden y la base restaurada no es la misma.
MYSQL_PWD="$CLAVE" mysqldump \
  --host="$HOST" --port="$PUERTO" --user="$USUARIO" \
  --single-transaction --routines --triggers --events \
  --default-character-set=utf8mb4 \
  "$BASE" > "$DESTINO"

# ── Comprobar que sirve ─────────────────────────────────────────────────────
TABLAS=$(grep -c '^CREATE TABLE' "$DESTINO" || true)
PESO=$(wc -c < "$DESTINO")

echo
echo "  fichero:  $DESTINO"
echo "  peso:     $(( PESO / 1024 )) KB"
echo "  tablas:   $TABLAS"

# mysqldump escribe esta línea AL FINAL. Si no está, el volcado se cortó: es la
# única señal fiable de que llegó hasta el final y no se quedó a medias.
if ! tail -5 "$DESTINO" | grep -q "Dump completed"; then
  echo
  echo "MAL: el volcado está incompleto, le falta la marca del final." >&2
  echo "NO sirve como copia de seguridad. No sigas con el borrado." >&2
  exit 1
fi

if [ "$TABLAS" -lt 20 ]; then
  echo
  echo "MAL: solo $TABLAS tablas. La base tiene bastantes más." >&2
  echo "Revisa que la URL apunte donde crees. No sigas con el borrado." >&2
  exit 1
fi

echo
echo "La copia está completa."
echo
echo "Para restaurarla, si hiciera falta:"
echo "  mysql --host=$HOST --port=$PUERTO --user=$USUARIO -p $BASE < $DESTINO"
echo
echo "Guárdala FUERA de Railway antes de seguir: una copia que vive en el mismo"
echo "sitio que el original no protege de perder ese sitio."
