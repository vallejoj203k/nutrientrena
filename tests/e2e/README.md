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

## humo_restablecer_clave.js

Necesita dos variables porque el token del correo se firma con la clave del
backend y no se puede fabricar desde el navegador:

```bash
export DATABASE_URL=... SECRET_KEY=smoke   # los mismos que la API
CORREO="reset.$(date +%s)@alzum.io"
TOK=$(python - "$CORREO" <<'PY'
import sys, uuid, secrets
from app.database import SessionLocal
from app.models.user import User, RoleUser, UserDetail
from app.core.security import hash_password, create_access_token
correo = sys.argv[1]
db = SessionLocal()
u = User(name="Reset QA", email=correo, password=hash_password(secrets.token_urlsafe(32)))
db.add(u); db.flush()
db.add(RoleUser(role_id=1, user_id=u.id))
db.add(UserDetail(id=str(uuid.uuid4()), user_id=u.id, name="Reset QA"))
db.commit()
print(create_access_token({"sub": str(u.id), "purpose": "reset"}))
PY
)
TOKEN_RESET="$TOK" CORREO_RESET="$CORREO" node tests/e2e/humo_restablecer_clave.js
```

Comprueba lo que falló en producción: que la página del enlace EXISTE donde el
correo la busca (/app/reset-password.html, no la raíz) y que poner la
contraseña allí sirve para entrar.
