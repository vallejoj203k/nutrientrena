# Nutrientrena — Backend API + Frontend

Plataforma de gestión de clientes, planes de entrenamiento y nutrición para coaches y nutricionistas.

---

## Acceso rápido

| Recurso | URL |
|---------|-----|
| **Aplicación web** | https://nutrientrena-production.up.railway.app/app/login.html |
| **Dashboard** | https://nutrientrena-production.up.railway.app/app/dashboard.html |
| **Swagger (API docs)** | https://nutrientrena-production.up.railway.app/api/docs |
| **Health check** | https://nutrientrena-production.up.railway.app/api/health |

---

## Stack tecnológico

| Tecnología | Uso |
|------------|-----|
| **FastAPI** | Framework principal de la API |
| **SQLAlchemy 2** | ORM para base de datos |
| **Alembic** | Migraciones de base de datos |
| **MySQL** (Railway) | Base de datos en producción |
| **JWT** (python-jose) | Autenticación segura |
| **Resend SDK** | Envío de emails transaccionales |
| **Cloudflare R2** | Almacenamiento de imágenes (S3-compatible) |
| **WeasyPrint** | Generación de PDFs de dietas y rutinas |
| **Pydantic v2** | Validación de datos |
| **GitHub Actions** | CI/CD automático |
| **HTML/CSS/JS** | Frontend puro sin frameworks externos |

---

## Cómo autenticarse

Todos los endpoints (excepto `/api/auth/login`, recuperar contraseña y `/api/public/*`) requieren un token JWT.

**Paso 1 — Obtener token:**
```
POST /api/auth/login
{ "email": "vallejoj203k@gmail.com", "password": "Admin123!" }
```
La respuesta incluye `data.token`.

**Paso 2 — Usar el token:**
```
Authorization: Bearer <token>
```

**En Swagger:** clic en **Authorize** (candado arriba a la derecha), pegar el token y confirmar.

> El token expira en 60 minutos. Usar `PUT /api/auth/refresh-token` para renovarlo.

---

## Frontend — Páginas disponibles

| Página | URL | Descripción |
|--------|-----|-------------|
| Login | `/app/login.html` | Autenticación con JWT |
| Reset password | `/app/reset-password.html` | Recuperar contraseña |
| Dashboard | `/app/dashboard.html` | Estadísticas generales y preview kanban |
| Kanban | `/app/kanban.html` | Pipeline de clientes con drag & drop |
| Clientes | `/app/clients.html` | Lista, búsqueda, filtros, exportar CSV |
| Perfil cliente | `/app/client-profile.html?id={uuid}` | Tabs: Resumen · Formulario · Entregas · Comercial · Progreso |
| Check-ins | `/app/checkins.html` | Historial semanal con mediciones corporales |
| Formularios | `/app/forms.html` | Plantillas de intake y gestión de asignaciones |
| **Eventos** | `/app/events.html` | Calendario mensual + CRUD tipos de eventos |
| **Notas** | `/app/notes.html` | Plantillas reutilizables + notas por cliente |
| **Progreso** | `/app/progress.html` | Medidas, fotos (x3), gráfica de peso |
| Dietas | `/app/diets.html` | Creación de dietas, macros, alimentos, PDF, clonar |
| Alimentos | `/app/aliments.html` | Biblioteca de alimentos + importación CSV |
| Recetas | `/app/recipes.html` | CRUD de recetas con ingredientes y macros |
| Rutinas | `/app/routines.html` | Creación de rutinas por días, PDF, clonar |
| Ajustes | `/app/settings.html` | Configuración del negocio (nombre, moneda, zona horaria…) |
| Analytics | `/app/analytics.html` | Métricas, gráficos SVG, rendimiento por coach |
| Catálogos nutrición | `/app/nutrition-catalog.html` | Tipos y grupos de alimentos |
| Formulario público | `/app/public/form.html?id={uuid}` | Formulario para clientes sin login |

---

## Guía de pruebas — Fase 3 y Fase 4

Sigue estos pasos en orden desde el navegador. Cada sección cubre un módulo completo.

---

### Requisitos previos

1. Abrir https://nutrientrena-production.up.railway.app/app/login.html
2. Iniciar sesión con las credenciales de administrador
3. Tener al menos **un cliente creado** (rol Cliente) para asociar datos

---

### FASE 3 — Nutrición completa

#### 3.1 Catálogos de nutrición (`/app/nutrition-catalog.html`)

1. Ir a **Catálogos** en el menú lateral
2. En la pestaña **Tipos de alimento**: crear un tipo nuevo (ej. "Proteína animal") → debe aparecer en la lista
3. Editar el tipo recién creado → cambiar nombre → guardar → verificar que cambia
4. Cambiar a la pestaña **Grupos de alimento**: crear un grupo (ej. "Carnes") → debe aparecer
5. Intentar eliminar un tipo/grupo → confirmar que el diálogo de confirmación aparece y borra correctamente

#### 3.2 Alimentos (`/app/aliments.html`)

1. Ir a **Alimentos** en el menú lateral
2. Hacer clic en **Nuevo alimento** → rellenar nombre, proteínas, carbos, grasas, calorías → guardar
3. Buscar el alimento por nombre en el buscador → debe filtrarse en tiempo real
4. Editar el alimento → modificar un macro → guardar → verificar el cambio
5. *(Opcional)* Probar importación CSV: descargar la plantilla y subir un CSV con 2–3 alimentos

#### 3.3 Recetas (`/app/recipes.html`)

1. Ir a **Recetas** en el menú lateral
2. Hacer clic en **Nueva receta** → añadir nombre y descripción
3. En la sección de ingredientes: buscar alimentos por nombre → añadir cantidad en gramos
4. Verificar que los macros totales se calculan automáticamente al añadir ingredientes
5. Guardar → la receta aparece en la lista con sus macros
6. Editar la receta → añadir o quitar un ingrediente → guardar
7. Eliminar la receta → confirmar que desaparece de la lista

#### 3.4 Dietas (`/app/diets.html`)

1. Ir a **Dietas** en el menú lateral
2. Crear una dieta nueva → añadir nombre y seleccionar cliente
3. Añadir comidas (desayuno, comida, cena) con alimentos de la biblioteca
4. Verificar que los macros del día se suman correctamente
5. Descargar el PDF → el PDF debe mostrar las comidas y macros
6. Usar el botón **Clonar** → la copia aparece en la lista con el sufijo "(copia)"
7. Asignar la dieta a un cliente → ir al perfil del cliente → pestaña **Entregas** → verificar que aparece

#### 3.5 Ajustes del negocio (`/app/settings.html`)

1. Ir a **Ajustes** en el menú lateral
2. Rellenar: nombre del negocio, email, teléfono, país, moneda, zona horaria, días de alerta de renovación
3. Guardar → recargar la página → verificar que los datos persisten

#### 3.6 Perfil de cliente — pestaña Comercial

1. Ir a **Clientes** → abrir el perfil de cualquier cliente
2. Ir a la pestaña **Comercial**
3. Hacer clic en editar → introducir la **Fecha de renovación** → guardar
4. Verificar que el badge de renovación aparece con color correcto:
   - 🔴 Rojo → renovación vencida
   - 🟡 Amarillo → ≤ 7 días
   - 🟣 Morado → ≤ 30 días

---

### FASE 4 — Eventos, Notas y Progreso

#### 4.1 Tipos de evento (`/app/events.html` — panel derecho)

1. Ir a **Eventos** en el menú lateral
2. En el panel derecho **Tipos de evento**, hacer clic en **+ Tipo**
3. Escribir un nombre (ej. "Sesión de coaching") y seleccionar un color → guardar
4. El tipo aparece en la lista con el color elegido
5. Crear al menos **2 tipos distintos** con colores diferentes (se usarán en el paso siguiente)
6. Editar un tipo → cambiar el color → guardar → verificar el cambio
7. Eliminar un tipo que no tenga eventos → confirmar que desaparece

#### 4.2 Calendario de eventos (`/app/events.html` — calendario)

1. Hacer clic en cualquier día del mes en el calendario → se abre el modal de creación con esa fecha prefijada
2. Rellenar: título (ej. "Llamada de seguimiento"), seleccionar tipo, hora de inicio y fin
3. Guardar → el evento aparece como chip en el día correspondiente con el color del tipo
4. Hacer clic en el chip del evento → se abre el **popover** con el título, tipo, horario y botones de editar/eliminar
5. Editar el evento → cambiar el título → guardar → verificar que el chip se actualiza
6. **Evento recurrente**: crear un nuevo evento → en el campo Repetición elegir "Semanal" → poner fecha de fin 1 mes después → guardar
7. Verificar que se crean múltiples chips en todos los lunes (o el día elegido) hasta la fecha de fin
8. En el popover de un evento recurrente: aparecen dos opciones al eliminar → "Solo este evento" y "Toda la serie" → probar ambas
9. Navegar entre meses con las flechas ← → y el botón **Hoy**

#### 4.3 Plantillas de notas (`/app/notes.html` — pestaña Plantillas)

1. Ir a **Notas** en el menú lateral
2. En la pestaña **Plantillas**, hacer clic en **Nueva plantilla**
3. Escribir título (ej. "Revisión semanal") y contenido detallado → guardar
4. La plantilla aparece como tarjeta con las primeras líneas del contenido
5. Crear una segunda plantilla
6. Buscar por nombre en el buscador → debe filtrar en tiempo real
7. Editar una plantilla → modificar el contenido → guardar → verificar cambio
8. Eliminar una plantilla → confirmar que desaparece

#### 4.4 Notas de clientes (`/app/notes.html` — pestaña Notas de clientes)

1. Cambiar a la pestaña **Notas de clientes**
2. Hacer clic en **Nueva nota**
3. En el campo **Cliente**: escribir el nombre o email → seleccionar de la lista desplegable
4. En el campo **Plantilla (opcional)**: elegir una de las plantillas creadas → el título y contenido se rellenan automáticamente
5. Ajustar el contenido → guardar → la nota aparece en la lista con el nombre del cliente
6. Filtrar por cliente usando el desplegable → solo deben aparecer notas de ese cliente
7. Buscar por título en el buscador → debe filtrar correctamente
8. Editar la nota → modificar el contenido → guardar
9. Eliminar la nota → confirmar que desaparece

#### 4.5 Progreso del cliente (`/app/progress.html`)

1. Ir a **Progreso** en el menú lateral
2. Buscar un cliente en el campo de búsqueda de la barra superior → seleccionarlo
3. El nombre del cliente aparece como etiqueta y el período de los últimos 90 días se carga automáticamente
4. Hacer clic en **Nuevo registro**
5. Rellenar: fecha de hoy, peso (ej. 75.5), % grasa, masa muscular, cintura, cadera
6. Subir **1 foto**: hacer clic en el slot "Foto 1" → seleccionar una imagen del dispositivo → esperar la subida → la miniatura aparece
7. Guardar → el registro aparece como tarjeta con los valores y la foto
8. Crear un **segundo registro** con fecha de hace 7 días y peso diferente → la **gráfica de evolución del peso** debe actualizarse
9. Verificar las **4 tarjetas de estadísticas**: peso actual, % grasa, masa muscular, total de registros
10. La delta de peso (ej. "-1.2 kg") aparece en verde si bajó o en rojo si subió
11. Hacer clic en la foto → se abre el **lightbox** a pantalla completa → clic para cerrar
12. **Filtrar por fechas**: cambiar el rango "Desde / Hasta" → los registros y la gráfica se actualizan
13. Editar un registro → añadir la foto 2 y la foto 3 → guardar → verificar las 3 fotos
14. Eliminar un registro → confirmar que desaparece y la gráfica se recalcula
15. Hacer clic en **×** junto al nombre del cliente → se limpia la selección para elegir otro cliente

#### 4.6 Progreso en perfil de cliente (`/app/client-profile.html`)

1. Ir a **Clientes** → abrir el perfil de un cliente que tenga registros de progreso
2. Navegar a la pestaña **Progreso**
3. Verificar que aparecen las tarjetas de peso, grasa y músculo, la gráfica de peso y la tabla de registros

---

### Verificaciones finales

| Comprobación | Cómo verificar |
|---|---|
| Menú lateral consistente | Cada página debe mostrar los mismos links en el sidebar |
| Notas y Progreso en sidebar | Visible en todas las páginas (dashboard, clientes, dietas, etc.) |
| Toast de confirmación | Cada acción guardar/eliminar muestra notificación verde o roja |
| Sesión expirada | Abrir en incógnito sin token → redirige a login.html |
| Datos persistentes | Recargar la página tras guardar → los datos siguen ahí |

---

## Módulos de la API

### Autenticación (`/api/auth`)

| Endpoint | Método | Auth | Descripción |
|----------|--------|------|-------------|
| `/api/auth/login` | POST | ❌ | Iniciar sesión, devuelve token JWT |
| `/api/auth/me` | GET | ✅ | Perfil del usuario autenticado |
| `/api/auth/refresh-token` | PUT | ✅ | Renovar token |
| `/api/auth/logout` | POST | ✅ | Cerrar sesión |
| `/api/auth/recover-password` | POST | ❌ | Email de recuperación |
| `/api/auth/menus` | GET | ✅ | Menús disponibles según rol |

---

### Usuarios y Clientes (`/api/users`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/users` | POST | Crear usuario/cliente |
| `/api/users/{slug}/findAll` | GET | Listar usuarios de un rol |
| `/api/users/{slug}/search` | GET | Buscar con paginación y filtros |
| `/api/users/{id}/edit` | GET | Ver perfil completo |
| `/api/users/{id}/update` | PUT | Actualizar datos + campos CRM |
| `/api/users/{id}/change` | PUT | Cambiar estado del cliente |
| `/api/users/kanban` | GET | Clientes agrupados por estado |
| `/api/users/assign` | POST | Asignar cliente a coach |

**Roles disponibles:**

| ID | Slug | Nombre |
|----|------|--------|
| 1 | superadmin | Superadministrador |
| 2 | admin | Administrador |
| 3 | setter | Setter |
| 4 | closer | Closer |
| 5 | coach | Coach |
| 6 | client | Cliente |

---

### Check-ins Semanales (`/api/checkins`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/checkins` | POST | Registrar check-in con mediciones corporales |
| `/api/checkins/client/{id}` | GET | Historial + delta de peso semana a semana |
| `/api/checkins/summary/{id}` | GET | Cambio total de peso desde el inicio |
| `/api/checkins/{id}/coach-notes` | PUT | Notas del coach + actualizar mediciones |
| `/api/checkins/{id}` | DELETE | Eliminar check-in |

---

### Entrega de Planes (`/api/plans`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/plans/deliver` | POST | Entregar dieta + rutina al cliente por email |
| `/api/plans/history/{client_id}` | GET | Historial de entregas con nombres de dieta/rutina |
| `/api/plans/resend/{delivery_id}` | POST | Reenviar email de una entrega anterior |

---

### Formularios de Intake (`/api/form-templates`, `/api/form-assignments`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/form-templates` | GET | Listar plantillas |
| `/api/form-templates` | POST | Crear plantilla con campos |
| `/api/form-templates/{id}` | PUT | Editar plantilla |
| `/api/form-templates/{id}` | DELETE | Eliminar plantilla |
| `/api/form-assignments` | POST | Asignar formulario a cliente |
| `/api/form-assignments/pending` | GET | Formularios pendientes de respuesta |
| `/api/form-assignments/client/{id}` | GET | Formulario de un cliente |
| `/api/form-assignments/{id}/submit` | POST | Cliente envía respuestas |

### Formulario público — sin autenticación (`/api/public`)

| Endpoint | Método | Auth | Descripción |
|----------|--------|------|-------------|
| `/api/public/form/{assignment_id}` | GET | ❌ | Obtener template + estado del formulario |
| `/api/public/form/{assignment_id}/submit` | POST | ❌ | Cliente envía respuestas desde el email |

---

### Analytics (`/api/analytics`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/analytics/overview` | GET | Total clientes, activos, nuevos este mes, coaches, check-ins |
| `/api/analytics/states` | GET | Distribución de clientes por estado (%) |
| `/api/analytics/checkins` | GET | Adherencia, cambio de peso promedio, tendencia 8 semanas |
| `/api/analytics/coaches` | GET | Clientes y check-ins por coach |

---

### Archivos e Imágenes (`/api/files`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/files/upload` | POST | Subir imagen → devuelve URL pública (Cloudflare R2) |
| `/api/files/delete` | DELETE | Eliminar archivo por key |
| `/api/files/list` | GET | Listar archivos de una carpeta |

Límite: **10 MB** · Formatos: JPG, PNG, WEBP, GIF  
Carpetas: `profiles`, `checkins`, `aliments`, `uploads`, `progress`

---

### Nutrición

#### Dietas (`/api/diets`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/diets/findAll` | GET | Todas las dietas del coach |
| `/api/diets` | POST | Crear dieta con macros y alimentos |
| `/api/diets/{id}` | PUT | Actualizar dieta |
| `/api/diets/{id}` | DELETE | Eliminar dieta |
| `/api/diets/{id}/pdf` | GET | Descargar PDF de la dieta |
| `/api/diets/clone` | POST | Clonar dieta existente |

#### Alimentos y Recetas

| Módulo | Prefijo | Descripción |
|--------|---------|-------------|
| Alimentos | `/api/aliments` | CRUD + importación masiva CSV |
| Recetas | `/api/recipes` | CRUD con ingredientes y macros calculados |

#### Catálogos (`/api/typeFood`, `/api/groupFood`)

| Endpoint | Descripción |
|----------|-------------|
| `GET /api/typeFood/findAll` | Todos los tipos activos |
| `POST /api/typeFood` | Crear tipo |
| `GET /api/groupFood/findAll` | Todos los grupos activos |
| `POST /api/groupFood` | Crear grupo |

---

### Entrenamiento

| Módulo | Prefijo | Descripción |
|--------|---------|-------------|
| Rutinas | `/api/routines` | CRUD + días + PDF + clonar |
| Grupos musculares | `/api/muscle-groups` | Catálogo |
| Ejercicios | `/api/trainings` | Biblioteca de ejercicios |

---

### Seguimiento — Fase 4

#### Eventos (`/api/events`, `/api/type-events`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/events` | POST | Crear evento (único o recurrente) |
| `/api/events/search` | GET | Eventos por usuario y rango de fechas |
| `/api/events/update/{id}` | POST | Actualizar evento |
| `/api/events/delete/{id}` | DELETE | Eliminar un evento |
| `/api/events/delete-group/{group_id}` | DELETE | Eliminar serie recurrente completa |
| `/api/type-events` | POST | Crear tipo de evento |
| `/api/type-events/find-all` | GET | Todos los tipos activos |
| `/api/type-events/update/{id}` | POST | Editar tipo |
| `/api/type-events/delete/{id}` | DELETE | Eliminar tipo |

**Recurrencia disponible:** `none` · `daily` · `weekly` · `monthly`

#### Notas (`/api/template-notes`, `/api/note-users`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/template-notes` | POST | Crear plantilla de nota |
| `/api/template-notes/find-all` | GET | Plantillas del coach autenticado |
| `/api/template-notes/update/{id}` | POST | Editar plantilla |
| `/api/template-notes/delete/{id}` | DELETE | Eliminar plantilla |
| `/api/note-users` | POST | Crear nota para un cliente |
| `/api/note-users/find-all` | GET | Notas del coach autenticado |
| `/api/note-users/search` | GET | Filtrar notas por cliente o título |
| `/api/note-users/update/{id}` | POST | Editar nota |
| `/api/note-users/delete/{id}` | DELETE | Eliminar nota |

#### Progreso diario (`/api/progress-day-users`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/progress-day-users/upsert` | POST | Crear o actualizar registro por usuario + fecha |
| `/api/progress-day-users/search` | GET | Registros en rango de fechas (`?from=&to=&user_id=`) |
| `/api/progress-day-users/{id}` | GET | Registro individual |
| `/api/progress-day-users/{id}` | PUT | Actualizar registro |
| `/api/progress-day-users/delete/{id}` | DELETE | Eliminar registro |

**Campos de medición:** `weight`, `body_fat`, `muscle_mass`, `waist`, `hip`, `chest`, `arm`, `thigh`, `notes`, `photo`, `photo2`, `photo3`

#### Metas del cliente (`/api/client-targets`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/client-targets/search` | GET | Metas actuales del cliente |
| `/api/client-targets` | PUT | Crear o actualizar metas |

#### Ajustes del negocio (`/api/settings`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/settings` | GET | Obtener configuración actual |
| `/api/settings` | PUT | Actualizar configuración |

---

## Base de datos

Migraciones con Alembic. Ejecutar en orden:

```bash
alembic upgrade head
python -m app.seeds.run_seeds
```

| Revisión | Descripción |
|----------|-------------|
| `bb298e505f5b` | Schema inicial — todas las tablas base |
| `a1b2c3d4e5f6` | Módulo de formularios de intake |
| `b2c3d4e5f6a7` | Tabla weekly_checkins |
| `c3d4e5f6a7b8` | Campos CRM en user_details |
| `d4e5f6a7b8c9` | Tabla plan_deliveries |
| `e5f6a7b8c9d0` | Mediciones corporales en weekly_checkins |
| `h7i8j9k0l1m2` | Módulo nutrición (alimentos, recetas, dietas) |
| `i8j9k0l1m2n3` | Tabla app_settings + fecha_renovacion en user_details |
| `j9k0l1m2n3o4` | Fotos x3 en progress_day_users + recurrencia en event_users |

---

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `MYSQL_URL` | URL de conexión a MySQL |
| `SECRET_KEY` | Clave secreta para JWT |
| `RESEND_API_KEY` | API key de Resend (emails) |
| `MAIL_FROM` | Dirección de envío de emails |
| `ADMIN_EMAIL` | Email del administrador inicial |
| `FRONTEND_URL` | URL pública del frontend (para links en emails) |
| `AWS_ACCESS_KEY_ID` | Access key de Cloudflare R2 |
| `AWS_SECRET_ACCESS_KEY` | Secret key de Cloudflare R2 |
| `AWS_BUCKET` | Nombre del bucket R2 |
| `R2_PUBLIC_URL` | URL pública del bucket |

---

## Instalación local

```bash
git clone https://github.com/vallejoj203k/nutrientrena.git
cd nutrientrena

python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

pip install -r requirements.txt

cp .env.example .env
# Editar .env con credenciales

alembic upgrade head
python -m app.seeds.run_seeds

uvicorn app.main:app --reload
```

Servidor en `http://localhost:8000` — Swagger en `http://localhost:8000/api/docs`.

---

## Estructura del proyecto

```
app/
├── main.py               # Entry point, routers, archivos estáticos
├── config.py             # Variables de entorno
├── database.py           # Conexión SQLAlchemy
├── core/
│   ├── security.py       # JWT y hash de contraseñas
│   ├── dependencies.py   # require_role_ids, verify_client_access
│   ├── email.py          # Emails transaccionales (Resend)
│   └── responses.py      # send_response / send_error
├── models/               # Modelos SQLAlchemy
├── schemas/              # Schemas Pydantic v2
├── routers/
│   ├── auth.py, users.py, checkins.py, plans.py
│   ├── forms.py, analytics.py, files.py, public.py
│   ├── events.py, notes.py, progress.py, settings.py
│   └── nutrition/
│       ├── diets.py, aliments.py, recipes.py
│       └── type_food.py, group_food.py
├── pdf/                  # Generación de PDFs (WeasyPrint)
└── seeds/                # Datos iniciales idempotentes
alembic/
└── versions/             # 9 migraciones aplicadas
frontend/
├── login.html, dashboard.html, kanban.html
├── clients.html, client-profile.html
├── checkins.html, forms.html, analytics.html
├── events.html, notes.html, progress.html
├── diets.html, aliments.html, recipes.html
├── routines.html, settings.html
├── nutrition-catalog.html
└── public/
    └── form.html         # Formulario sin login para clientes
```

---

## CI/CD

Cada push a `main` ejecuta en GitHub Actions:

1. **Lint** con `ruff` (`E`, `F`, `W` — ignora `E501`, `F401`)
2. **Validación de modelos** — tablas registradas en SQLAlchemy
3. **Validación de rutas** — endpoints registrados en FastAPI
4. **Validación de migraciones** — archivos de migración presentes

---

## Estado del proyecto

| Fase | Descripción | Estado |
|------|-------------|--------|
| **Fase 0** | Infraestructura, auth, roles, seeds, CI/CD, deploy en Railway | ✅ Completa |
| **Fase 1** | Clientes, kanban, check-ins, planes, formularios, frontend base | ✅ Completa |
| **Fase 2** | Analytics, imágenes R2, PDFs, frontend avanzado, roles, emails, CRM | ✅ Completa |
| **Fase 3** | Nutrición completa, ajustes, perfil extendido, recetas | ✅ Completa |
| **Fase 4** | Eventos recurrentes, notas, progreso con fotos | ✅ Completa |

### Fase 3 — Detalle

| Ítem | Estado |
|------|--------|
| Catálogos de nutrición (Tipos + Grupos de alimentos) | ✅ |
| Alimentos: CRUD + importación masiva CSV | ✅ |
| Recetas: CRUD con ingredientes y macros calculados | ✅ |
| Dietas: creación, PDF, clonar, asignar a cliente | ✅ |
| Ajustes del negocio (nombre, moneda, zona horaria, alertas) | ✅ |
| Perfil cliente: pestaña Progreso + fecha de renovación con countdown | ✅ |
| Dashboard: métricas reales (nuevos este mes, adherencia check-ins) | ✅ |

### Fase 4 — Detalle

| Ítem | Estado |
|------|--------|
| Backend: progreso con 3 fotos + upsert por fecha + rango fechas | ✅ |
| Backend: eventos recurrentes (diario / semanal / mensual) | ✅ |
| `events.html`: calendario mensual con chips por tipo + navegación | ✅ |
| `events.html`: CRUD tipos de evento con selector de color | ✅ |
| `events.html`: popover editar/eliminar (uno solo o toda la serie) | ✅ |
| `notes.html`: plantillas reutilizables CRUD | ✅ |
| `notes.html`: notas por cliente con aplicación de plantilla | ✅ |
| `progress.html`: medidas corporales + gráfica SVG de peso | ✅ |
| `progress.html`: subida de hasta 3 fotos a R2 + lightbox | ✅ |
| Sidebar unificado en las 16 páginas | ✅ |

---

*Nutrientrena v2.0 — Junio 2026*
