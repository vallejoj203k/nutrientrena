# Humo end-to-end

Estas pruebas NO son unitarias: levantan la app de verdad contra MySQL y
conducen el frontend con un navegador real. Sirven para lo que los bancos de
prueba de `tests/frontend/` no pueden cubrir — que las piezas encajen entre sí.

Cubren los arreglos de UI de esta tanda:

- `humo_dietas.js` — borrar un alimento y que **persista sin pulsar Guardar**
  (autoguardado), y que un segundo autoguardado **no duplique** las comidas.
- `humo_rutinas_cliente.js` — arrastrar días en el constructor, duración en
  semanas, selector de país, y asignar una rutina viendo la pantalla de carga.

## Cómo se ejecutan

Hace falta un MySQL, la API y el frontend servidos:

```bash
# 1. MySQL (en este contenedor se instaló mariadb-server)
mariadbd --user=root --datadir=/var/lib/mysql --socket=/tmp/mysql.sock \
         --port=3399 --bind-address=127.0.0.1 --pid-file=/run/mysqld/mysqld.pid &
mariadb --socket=/tmp/mysql.sock -uroot -e "CREATE DATABASE nutri_fresh CHARACTER SET utf8mb4;"

# 2. Migraciones y seeds, igual que start.sh
export DATABASE_URL="mysql+pymysql://nutri:nutri@127.0.0.1:3399/nutri_fresh"
export SECRET_KEY=smoke AWS_ACCESS_KEY_ID=t AWS_SECRET_ACCESS_KEY=t AWS_BUCKET=t RESEND_API_KEY=t
alembic upgrade heads
python -m app.seeds.run_seeds

# 3. API y frontend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 &
(cd frontend && python3 -m http.server 8011 --bind 127.0.0.1 &)

# 4. Humo
node tests/e2e/humo_dietas.js
node tests/e2e/humo_rutinas_cliente.js
```

El frontend apunta por código a la URL de producción; los scripts la
reescriben a la API local interceptando las peticiones con Playwright, así que
no hay que tocar ningún fichero.

## Nota medida

Asignar una rutina deja la pantalla de carga a la vista **26 ms** en local.
Es el dato que descartó poner un vídeo de carga: no daría tiempo ni a
descargarlo. En producción será más por la latencia de red, pero del mismo
orden.
