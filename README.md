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
| **Guía de despliegue** | [DEPLOY.md](./DEPLOY.md) |

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

## Guía de pruebas — Fases 3, 4 y 5

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
   - ● Rojo → renovación vencida
   - ● Amarillo → ≤ 7 días
   - ● Morado → ≤ 30 días

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

#### 4.7 Correcciones aplicadas tras la entrega

**Campo "Repetir hasta" en eventos recurrentes**

1. Ir a **Eventos** → hacer clic en cualquier día del calendario para crear un evento
2. En el campo **Repetición**, seleccionar "Semanal" (o diaria/mensual)
3. Debe aparecer inmediatamente el campo **"Repetir hasta"** para indicar la fecha de fin de la serie
4. Rellenar la fecha → debe aparecer un texto indicando cuántos eventos se van a crear (ej. "Se crearán 5 eventos")

**Editar una serie de eventos recurrentes**

1. Hacer clic sobre cualquier chip de evento que pertenezca a una serie recurrente
2. En el popover, hacer clic en **Editar**
3. Modificar el título u horario → guardar
4. El sistema debe eliminar la serie antigua y recrear todos los eventos con los nuevos datos → verificar en el calendario que los chips actualizados aparecen en los días correctos

**Subida de imágenes en ejercicios**

1. Ir a **Rutinas** → pestaña **Ejercicios**
2. Hacer clic en editar sobre cualquier ejercicio → se abre el modal de edición
3. En el campo **Imagen**, hacer clic en la zona de subida → seleccionar una imagen del dispositivo
4. Esperar a que suba → debe aparecer la miniatura de la imagen dentro del modal
5. Guardar → volver a abrir el ejercicio → la imagen debe seguir guardada

---

### FASE 5 — Seguridad, rendimiento y documentación

#### 5.1 Bloqueo por intentos de login fallidos

1. Ir a la pantalla de **Login** (`/app/login.html`)
2. Dejar el campo de contraseña con un valor incorrecto y hacer clic en **Login** repetidamente — **10 veces seguidas** en menos de 1 minuto
3. En el intento 11 debe aparecer un mensaje de error indicando que se han hecho demasiados intentos y que el acceso está bloqueado temporalmente
4. Esperar 1 minuto y volver a intentar con las credenciales correctas → el login debe funcionar con normalidad

#### 5.2 Redirección automática sin sesión

1. Abrir una ventana en **modo incógnito** (Ctrl+Shift+N en Chrome / ⌘+Shift+N en Mac)
2. Escribir directamente en la barra de direcciones: `https://nutrientrena-production.up.railway.app/app/dashboard.html`
3. El panel debe redirigirte automáticamente a la pantalla de login sin mostrar ningún dato del panel
4. Iniciar sesión → navegar normalmente → cerrar sesión usando el botón de salida del menú lateral
5. Pulsar el botón **Atrás** del navegador → debe redirigir de nuevo al login, no mostrar el panel

#### 5.3 Recuperación de contraseña

1. En la pantalla de login, escribir tu email en el campo superior
2. Hacer clic en **"¿Olvidaste tu contraseña?"**
3. Debe aparecer un mensaje en verde confirmando que se envió el correo
4. Verificar que el correo llega a la bandeja de entrada con el enlace para restablecer la contraseña
5. *(Opcional — prueba de bloqueo)* Hacer clic en "¿Olvidaste tu contraseña?" **6 veces seguidas** en menos de 1 minuto → en el sexto intento debe aparecer un mensaje de bloqueo temporal

#### 5.4 Documentación de la API (Swagger)

1. Abrir en el navegador: `https://nutrientrena-production.up.railway.app/api/docs`
2. Debe cargarse una página con todos los endpoints organizados por secciones (Auth, Clientes, Eventos, Dietas, Rutinas, Analytics, etc.)
3. Expandir cualquier sección → hacer clic en un endpoint → debe mostrar una descripción clara y los parámetros que acepta
4. Comprobar que existen al menos las secciones: **Auth**, **Events**, **Diets**, **Routines**, **Analytics**

#### 5.5 Velocidad de respuesta

1. Ir a **Rutinas** → pestaña **Ejercicios** → escribir cualquier letra en el buscador → los resultados deben aparecer de inmediato, sin esperar
2. Ir a **Clientes** → escribir en el buscador → misma respuesta rápida
3. Ir a **Analytics** → las estadísticas y gráficas deben cargarse en menos de 2 segundos
4. Navegar entre distintas páginas del panel → ninguna debería tardar más de 3 segundos en cargar completamente

---

### Verificaciones finales

| Comprobación | Cómo verificar |
|---|---|
| Menú lateral consistente | Cada página muestra los mismos links en el sidebar, incluyendo **Eventos** |
| Enlace Eventos visible | Aparece entre "Clientes" y "Check-ins" en todas las páginas |
| Toast de confirmación | Cada acción guardar/eliminar muestra notificación verde o roja |
| Sesión expirada | Abrir en incógnito sin token → redirige a `login.html` |
| Datos persistentes | Recargar la página tras guardar → los datos siguen ahí |
| Contador de formularios pendientes | El badge rojo sobre "Formularios" muestra el número correcto |
| Formularios de página completa | "Nueva dieta", "Nueva rutina" y "Nuevo cliente" abren página completa, no modal |

---

## Módulos de la API

### Autenticación (`/api/auth`)

| Endpoint | Método | Auth | Descripción |
|----------|--------|------|-------------|
| `/api/auth/login` | POST | Libre | Iniciar sesión, devuelve token JWT |
| `/api/auth/me` | GET | Requerido | Perfil del usuario autenticado |
| `/api/auth/refresh-token` | PUT | Requerido | Renovar token |
| `/api/auth/logout` | POST | Requerido | Cerrar sesión |
| `/api/auth/recover-password` | POST | Libre | Email de recuperación |
| `/api/auth/menus` | GET | Requerido | Menús disponibles según rol |

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
| `/api/public/form/{assignment_id}` | GET | Libre | Obtener template + estado del formulario |
| `/api/public/form/{assignment_id}/submit` | POST | Libre | Cliente envía respuestas desde el email |

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

#### Sesiones de entrenamiento (`/api/session-logs`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/session-logs/client/{id}` | GET | Historial de sesiones del cliente |
| `/api/session-logs` | POST | Registrar sesión completada |
| `/api/session-logs/{id}` | PUT | Actualizar datos de sesión |
| `/api/session-logs/{id}` | DELETE | Eliminar sesión |

#### Tareas semanales del cliente (`/api/client-tasks`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/client-tasks/client/{id}` | GET | Tareas del cliente (filtrable por semana) |
| `/api/client-tasks/week` | GET | Todas las tareas de la semana, agrupadas por cliente |
| `/api/client-tasks` | POST | Crear tarea (tipos: `rutina`, `cardio`, `descanso`, `nutricion`, `checkin`, `foto`, `mensaje`, `video`, `sesion`) |
| `/api/client-tasks/{id}` | PUT | Actualizar o marcar como completada |
| `/api/client-tasks/{id}` | DELETE | Eliminar tarea |

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
| `m1n2o3p4q5r6` | Índices de performance (10 índices en tablas críticas) |

---

## Variables de entorno

### Obligatorias en producción

| Variable | Ejemplo | Descripción |
|----------|---------|-------------|
| `DATABASE_URL` | `mysql+pymysql://user:pass@host:3306/db` | URL completa de MySQL (Railway la provee como `MYSQL_URL`) |
| `SECRET_KEY` | `openssl rand -hex 32` | Clave secreta JWT — cambiar antes del primer deploy |
| `FRONTEND_URL` | `https://tuapp.up.railway.app` | URL pública del frontend (para links en emails) |
| `ALLOWED_ORIGINS` | `https://tuapp.up.railway.app` | Orígenes CORS permitidos. Si se omite, usa `FRONTEND_URL` automáticamente |
| `RESEND_API_KEY` | `re_xxxx` | API key de Resend para emails transaccionales |
| `MAIL_FROM` | `noreply@tudominio.com` | Dirección de envío verificada en Resend |

### Almacenamiento de archivos (Cloudflare R2)

| Variable | Descripción |
|----------|-------------|
| `AWS_ACCESS_KEY_ID` | Access key del token R2 |
| `AWS_SECRET_ACCESS_KEY` | Secret key del token R2 |
| `AWS_BUCKET` | Nombre del bucket (ej. `nutrientrena-files`) |
| `AWS_ENDPOINT_URL` | Endpoint R2: `https://<account-id>.r2.cloudflarestorage.com` |
| `R2_PUBLIC_URL` | URL pública del bucket: `https://pub-xxx.r2.dev` |
| `AWS_DEFAULT_REGION` | Siempre `auto` para R2 |

### Opcionales

| Variable | Defecto | Descripción |
|----------|---------|-------------|
| `ALGORITHM` | `HS256` | Algoritmo de firma JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24 h) | Tiempo de expiración del access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Tiempo de expiración del refresh token |
| `DEBUG` | `false` | En `true` incluye stack traces en errores 500 |
| `PORT` | `8000` | Puerto del servidor |
| `ADMIN_EMAIL` | — | Email del administrador inicial (para seeds) |

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
├── main.py               # Entry point, routers, CORS, security headers
├── config.py             # Variables de entorno + cors_origins property
├── database.py           # Conexión SQLAlchemy
├── core/
│   ├── security.py       # JWT y hash de contraseñas
│   ├── dependencies.py   # require_role_ids, verify_client_access
│   ├── email.py          # Emails transaccionales (Resend / Gmail)
│   ├── limiter.py        # Rate limiting (slowapi)
│   └── responses.py      # send_response / send_error
├── models/               # Modelos SQLAlchemy
├── schemas/              # Schemas Pydantic v2
├── routers/
│   ├── auth.py, users.py, checkins.py, plans.py
│   ├── forms.py, analytics.py, files.py, public.py
│   ├── events.py, notes.py, progress.py, settings.py
│   ├── session_logs.py   # Sesiones de entrenamiento
│   ├── client_tasks.py   # Tareas semanales
│   ├── roles.py, menus.py, parameters.py, countries.py
│   └── nutrition/
│       ├── diets.py, aliments.py, recipes.py
│       └── type_food.py, group_food.py
├── pdf/                  # Generación de PDFs (WeasyPrint)
└── seeds/                # Datos iniciales idempotentes
alembic/
└── versions/             # 10 migraciones aplicadas
tests/
├── conftest.py           # Fixtures: DB SQLite en memoria, admin/coach headers
├── test_auth.py          # Login, tokens, endpoints protegidos
├── test_events.py        # Tipos de evento, eventos únicos y recurrentes
├── test_nutrition.py     # Alimentos, tipos, grupos, recetas
└── test_security.py      # Headers, RBAC, validación de inputs
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

Cada push ejecuta dos jobs en GitHub Actions:

### Job 1 — Lint & Import Check
1. **Lint** con `ruff` (`E`, `F`, `W` — ignora `E501`, `F401`)
2. **Validación de modelos** — ≥33 tablas registradas en SQLAlchemy
3. **Validación de rutas** — ≥50 endpoints registrados en FastAPI
4. **Validación de migraciones** — archivos de migración presentes

### Job 2 — Pytest Suite _(requiere Job 1 exitoso)_
5. **47 tests** sobre base SQLite en memoria
6. **Cobertura ≥ 40%** — falla el pipeline si baja de ese umbral
7. Reporte `.coverage` guardado como artefacto descargable

---

## Estado del proyecto

| Fase | Descripción | Estado |
|------|-------------|--------|
| **Fase 0** | Infraestructura, auth, roles, seeds, CI/CD, deploy en Railway | Completa |
| **Fase 1** | Clientes, kanban, check-ins, planes, formularios, frontend base | Completa |
| **Fase 2** | Analytics, imágenes R2, PDFs, frontend avanzado, roles, emails, CRM | Completa |
| **Fase 3** | Nutrición completa, ajustes, perfil extendido, recetas | Completa |
| **Fase 4** | Eventos recurrentes, notas, progreso con fotos _(con fixes post-entrega)_ | Completa |
| **Fase 5** | Seguridad, testing, documentación API, optimización de BD | Completa |
| **Fase 6** | Formularios de página completa, corrección de bugs frontend | Completa |
| **Fase 7** | Chat en tiempo real, base USDA de alimentos, PDFs en emails, correcciones | Completa |
| **Fase 8** | Librería de contenido, módulo de programas con fases y asignación de clientes | Completa |

### Fase 3 — Detalle

| Ítem | Estado |
|------|--------|
| Catálogos de nutrición (Tipos + Grupos de alimentos) | Completado |
| Alimentos: CRUD + importación masiva CSV | Completado |
| Recetas: CRUD con ingredientes y macros calculados | Completado |
| Dietas: creación, PDF, clonar, asignar a cliente | Completado |
| Ajustes del negocio (nombre, moneda, zona horaria, alertas) | Completado |
| Perfil cliente: pestaña Progreso + fecha de renovación con countdown | Completado |
| Dashboard: métricas reales (nuevos este mes, adherencia check-ins) | Completado |

### Fase 4 — Detalle

| Ítem | Estado |
|------|--------|
| Backend: progreso con 3 fotos + upsert por fecha + rango fechas | Completado |
| Backend: eventos recurrentes (diario / semanal / mensual) | Completado |
| `events.html`: calendario mensual con chips por tipo + navegación | Completado |
| `events.html`: CRUD tipos de evento con selector de color | Completado |
| `events.html`: popover editar/eliminar (uno solo o toda la serie) | Completado |
| `notes.html`: plantillas reutilizables CRUD | Completado |
| `notes.html`: notas por cliente con aplicación de plantilla | Completado |
| `progress.html`: medidas corporales + gráfica SVG de peso | Completado |
| `progress.html`: subida de hasta 3 fotos a R2 + lightbox | Completado |
| Sidebar unificado en las 16 páginas | Completado |
| **Fix:** campo "Repetir hasta" visible en modal de creación de eventos | Fix post-entrega |
| **Fix:** preview de N eventos al configurar recurrencia | Fix post-entrega |
| **Fix:** al editar un evento recurrente regenera toda la serie | Fix post-entrega |
| **Fix:** subida de imágenes en ejercicios de rutina | Fix post-entrega |

### Fase 5 — Detalle

| Ítem | Estado |
|------|--------|
| CORS hardening — sin wildcard en producción, fallback automático a `FRONTEND_URL` | Completado |
| Rate limiting — 10/min en login, 5/min en recuperar contraseña | Completado |
| Security headers en todas las respuestas (CSP, X-Frame, Referrer-Policy…) | Completado |
| Global exception handler — sin stack traces en producción | Completado |
| Suite pytest — 47 tests, cobertura ≥ 40% | Completado |
| 10 índices de performance en tablas críticas (Alembic idempotente) | Completado |
| CI actualizado con job de pytest + reporte de cobertura | Completado |
| Swagger: `summary` + `description` en 111+ endpoints, 30 secciones con tags | Completado |

### Fase 6 — Formularios de página completa y corrección de bugs frontend

#### Formularios de página completa (patrón list/form)

Las páginas de creación de registros complejos dejaron de usar ventanas emergentes (modales) y ahora usan un formulario de página completa con panel lateral de vista previa en vivo. El patrón consiste en un `#listView` (lista + barra de herramientas) y un `#formView` (formulario a pantalla completa), ambos dentro del mismo `.main`, que se alternan ocultando/mostrando según la acción.

| Ítem | Estado |
|------|--------|
| `clients.html`: formulario de página completa con 3 secciones (Acceso, Perfil físico, Asignación) + panel lateral con avatar y resumen en vivo | Completado |
| `diets.html`: formulario con secciones Información, Macros y Comidas + panel lateral con preview de macros y lista de comidas en tiempo real | Completado |
| `routines.html`: formulario en 2 pasos — Paso 1 (info + sidebar resumen) y Paso 2 (constructor de días y bloques a ancho completo, sin sidebar) | Completado |

Los ejercicios y grupos musculares en `routines.html` siguen usando overlays flotantes (son seleccionadores contextuales, no flujos de creación primarios).

#### Corrección de bugs frontend

| Bug | Páginas afectadas | Estado |
|-----|------------------|--------|
| `loadPendingBadge` usaba endpoint inexistente `/form-assignments/pending` → corregido a `/form-assignments?status=pending&per_page=1` | `events.html`, `diets.html`, `routines.html` | Fix |
| `sidebarRole` usaba `u.roles?.[0]?.name` (incorrecto, la API devuelve `role` como objeto) → corregido a `u.role?.name \|\| u.role` | `events.html`, `diets.html` | Fix |
| Calendario de eventos: `grid-template-rows: repeat(6, 1fr)` hardcodeado generaba fila vacía en meses de 5 semanas → ahora se calcula dinámicamente con `weeksRendered` | `events.html` | Fix |
| Overlays de confirmación de borrado (`delEventOverlay`, `delTypeOverlay`) no cerraban al hacer clic en el fondo → añadido `onclick="if(event.target===this)close*()"` | `events.html` | Fix |
| HTML duplicado `<div class="sidebar-nav"><nav class="sidebar-nav">` causaba contenedor sin cerrar → eliminado el `<div>` redundante | `diets.html` | Fix |
| Enlace **Eventos** ausente en la barra lateral de 12 páginas → añadido en todas | todas las páginas | Fix |

---

### Fase 7 — Chat en tiempo real, base USDA de alimentos, PDFs en emails y correcciones

#### 7.1 Chat en tiempo real (`/app/chat.html`)

**Backend**

| Ítem | Estado |
|------|--------|
| Nuevas tablas: `chat_conversations`, `chat_participants`, `chat_messages` | Completado |
| Migración Alembic `q5r6s7t8u9v0` | Completado |
| `GET /api/chat/conversations` — lista conversaciones del usuario autenticado | Completado |
| `POST /api/chat/conversations` — crea conversación individual o grupal (auto-poblado por rol) | Completado |
| `GET /api/chat/conversations/{id}/messages` — historial paginado | Completado |
| `POST /api/chat/conversations/{id}/messages` — envío REST (fallback sin WebSocket) | Completado |
| `DELETE /api/chat/conversations/{id}` — solo el creador o admin | Completado |
| `WS /api/chat/ws?token=<jwt>` — WebSocket autenticado con JWT | Completado |
| Indicador de "escribiendo..." entre participantes via WebSocket | Completado |
| Reconexión automática del WebSocket (cada 3 s si se pierde la conexión) | Completado |

**Frontend**

| Ítem | Estado |
|------|--------|
| `chat.html`: panel de conversaciones + hilo de mensajes + barra de envío | Completado |
| Botones **Individual** / **Grupal** con panel inline (no modal) | Completado |
| Individual: buscador de personas (clientes + coaches) con selección múltiple | Completado |
| Grupal: opciones auto-generadas según rol — coach ve "Mis clientes"; admin ve las 3 opciones | Completado |
| Botón **Grupal** oculto para clientes (rol 6) | Completado |
| Mensajes propios a la derecha (morado), mensajes ajenos a la izquierda | Completado |
| Separadores de fecha (Hoy / Ayer / fecha corta) | Completado |
| Enter para enviar, Shift+Enter para salto de línea | Completado |
| Enlace **Chat** añadido al sidebar de todas las páginas | Completado |

**Grupos auto-generados por rol:**

| Rol del usuario | Opciones de grupo disponibles |
|-----------------|-------------------------------|
| Coach (5) | Mis clientes (clientes asignados a ese coach) |
| Admin (2) / Superadmin (1) | Mis clientes · Todos los coaches · Todos los clientes |
| Cliente (6) | Sin acceso a grupos |

---

#### 7.2 Base de datos de alimentos USDA

| Ítem | Estado |
|------|--------|
| 8 192 alimentos importados desde USDA FoodData Central (Foundation + SR Legacy) | Completado |
| Nombres traducidos al español con DeepL API (lotes de 50, ~500 k caracteres) | Completado |
| 30 grupos de alimentos en español (carnes, lácteos, verduras, legumbres, etc.) | Completado |
| 27 campos de micronutrientes: vitaminas A, B1, B2, B3, B5, B6, B9, B12, C, D, E, K + minerales calcio, fósforo, potasio, sodio, hierro, zinc, magnesio, manganeso, cobre, selenio + fibra, colesterol, agua, alcohol, cafeína | Completado |
| Script idempotente `scripts/import_usda.py` — no duplica si se ejecuta varias veces | Completado |
| Exportación a Excel `scripts/aliments_usda.xlsx` para revisión con el cliente | Completado |

---

#### 7.3 PDFs adjuntos en emails de entrega de planes

| Ítem | Estado |
|------|--------|
| Email de entrega ahora incluye el PDF de **dieta** y el PDF de **rutina** como adjuntos | Completado |
| `send_plan_email` acepta `attachments: list[tuple[bytes, str]]` (bytes + nombre del archivo) | Completado |
| Compatible con Resend (base64) y Gmail SMTP (`MIMEApplication`) | Completado |
| **Fix:** imágenes de ejercicios en PDFs descargadas directamente desde R2 (boto3) con fallback HTTP | Fix |
| **Fix:** ejercicios dentro de **bloques** (agrupaciones) no aparecían en PDF ni en email → ahora se itera `day.details + day.blocks → block.exercises` | Fix |
| **Fix:** `AttributeError: aliment.unit` en dietas → campo `unit` no existe en el modelo; eliminado de `_build_diet_payload` | Fix |

---

#### 7.4 Correcciones generales

| Bug | Archivo | Estado |
|-----|---------|--------|
| `notes.html`: buscador de clientes usaba `/users/search?role_id=6` (no existe) → corregido a `/users/client/search?per_page=200` con parseo `r.data.data` | `notes.html` | Fix |
| `progress.html`: `loadClients()` usaba endpoint incorrecto, no aparecían clientes en el selector | `progress.html` | Fix |
| `progress.html`: `selectClient()` usaba `c.id` en lugar de `c.user_id` (campo real de la respuesta) | `progress.html` | Fix |
| `progress.html`: fotos subidas a carpeta genérica `progress/` → ahora se guardan en `progress/<nombre-cliente>` en R2 | `progress.html` | Fix |

---

#### Guía de pruebas — Fase 7

##### 7.A Chat individual

1. Ir a **Chat** en el menú lateral (`/app/chat.html`)
2. Hacer clic en el botón **Individual** → aparece un panel inline debajo de los botones
3. Escribir el nombre de un cliente o coach en el buscador → seleccionarlo de la lista
4. Hacer clic en **Iniciar conversación** → se abre el hilo de mensajes
5. Escribir un mensaje y pulsar **Enter** (o el botón Enviar) → el mensaje aparece a la derecha en morado
6. Desde otra sesión (con el otro usuario) verificar que el mensaje llega en tiempo real sin recargar
7. El indicador **"Escribiendo…"** debe aparecer cuando el otro usuario está tecleando
8. Comprobar que los mensajes persisten al recargar la página

##### 7.B Chat grupal (coach)

1. Iniciar sesión como **coach**
2. Ir a **Chat** → el botón **Grupal** es visible (no para clientes)
3. Hacer clic en **Grupal** → aparece la opción **"👤 Mis clientes"**
4. (Opcional) Escribir un nombre de grupo → hacer clic en **Mis clientes** para seleccionarlo
5. Hacer clic en **Crear grupo** → se crea una conversación con todos los clientes asignados a ese coach
6. Enviar un mensaje → todos los clientes del grupo deben recibirlo en tiempo real

##### 7.C Chat grupal (admin)

1. Iniciar sesión como **admin**
2. Ir a **Chat** → hacer clic en **Grupal**
3. Aparecen 3 opciones: **Mis clientes**, **Todos los coaches**, **Todos los clientes**
4. Seleccionar **Todos los coaches** → crear grupo → verificar que se añaden todos los coaches como participantes

##### 7.D Alimentos con micronutrientes

1. Ir a **Alimentos** (`/app/aliments.html`)
2. Buscar cualquier alimento (ej. "pollo") → deben aparecer resultados en español
3. Abrir el detalle de un alimento → verificar que los campos de micronutrientes (vitaminas, minerales) están rellenos
4. Verificar que hay al menos 8 000 alimentos disponibles en la biblioteca

##### 7.E Entrega de plan con PDFs adjuntos

1. Ir al **perfil de un cliente** → pestaña **Entregas**
2. Seleccionar una dieta y una rutina → hacer clic en **Entregar plan**
3. El cliente debe recibir un email con **dos archivos adjuntos**: `dieta.pdf` y `rutina.pdf`
4. Abrir el PDF de rutina → verificar que los ejercicios de todos los días aparecen, incluyendo los que están dentro de bloques/agrupaciones
5. Verificar que las imágenes de los ejercicios aparecen dentro del PDF

##### 7.F Progreso — selector de clientes

1. Ir a **Progreso** (`/app/progress.html`)
2. Escribir el nombre de un cliente en el buscador de la barra superior → debe aparecer la lista desplegable
3. Seleccionar un cliente → se carga su historial de progreso
4. Hacer clic en **Nuevo registro** → subir una foto → verificar en Cloudflare R2 que la foto quedó en la carpeta `progress/<nombre-del-cliente>/`

---

#### Migración de base de datos requerida (Fase 7)

```bash
alembic upgrade head
```

Aplica la revisión `q5r6s7t8u9v0` que crea las tablas de chat.

---

### Fase 8 — Librería de contenido y módulo de Programas

#### 8.1 Librería (`/app/library.html`)

Página de acceso rápido que centraliza todos los módulos de contenido reutilizable del coach en tarjetas visuales. No tiene backend propio: es un hub de navegación.

| Tarjeta | Descripción | Enlace destino |
|---------|-------------|----------------|
| **Entrenamiento** | Rutinas y ejercicios del catálogo | `routines.html` |
| **Nutrición** | Dietas, recetas y alimentos | `nutricion.html` |
| **Formularios** | Plantillas de intake para clientes | `formularios.html` |
| **Documentos** | Archivos y documentos de referencia | `documentos.html` |

La librería está disponible en el menú lateral para coaches, admins y superadmins.

---

#### 8.2 Programas (`/app/programas.html`)

Módulo completo para crear programas de entrenamiento estructurados con fases y asignación de clientes.

**Backend — endpoints**

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `GET /api/programs` | GET | Listar todos los programas del coach autenticado |
| `POST /api/programs` | POST | Crear programa con nombre, categoría, descripción y fases |
| `GET /api/programs/{id}` | GET | Ver detalle completo (fases + clientes asignados) |
| `PUT /api/programs/{id}` | PUT | Actualizar nombre, categoría, descripción, estado o fases |
| `DELETE /api/programs/{id}` | DELETE | Eliminar programa |
| `POST /api/programs/{id}/assign` | POST | Asignar uno o varios clientes al programa |
| `DELETE /api/programs/{id}/clients/{client_id}` | DELETE | Quitar un cliente del programa |
| `POST /api/programs/{id}/duplicate` | POST | Duplicar programa (copia fases, sin clientes) |

**Modelo de datos**

| Tabla | Campos principales |
|-------|--------------------|
| `programs` | `name`, `category`, `description`, `status`, `checkins_count`, `coach_id` |
| `program_phases` | `program_id`, `name`, `weeks`, `order` |
| `program_clients` | `program_id`, `client_id`, `assigned_at` |

**Categorías disponibles:** `recomposicion` · `perdida_grasa` · `ganancia_muscular` · `mantenimiento`

**Frontend — funcionalidades**

| Funcionalidad | Descripción |
|---------------|-------------|
| Grid de tarjetas | Muestra todos los programas del coach con nombre, categoría, semanas totales y clientes asignados |
| Filtro por categoría | Pestañas: Todos · Recomposición · Pérdida de grasa · Ganancia muscular · Mantenimiento; cada una muestra el contador |
| Crear programa | Formulario con nombre, categoría, descripción y constructor de fases (nombre + semanas por fase) |
| Drawer de detalle | Panel lateral con 3 pestañas: **Info** (datos generales + semanas totales), **Fases** (lista de fases en orden), **Asignados** (avatares y nombres de clientes) |
| Editar programa | Edición inline dentro del drawer — modifica nombre, descripción y fases |
| Asignar clientes | Modal de búsqueda y selección de clientes para añadirlos al programa |
| Quitar cliente | Botón × junto a cada cliente asignado en la pestaña Asignados |
| Duplicar | Crea una copia del programa con todas sus fases (sin clientes) |
| Archivar / Activar | Cambia el estado del programa entre `activo` y `archivado` |
| Eliminar | Confirmación antes de borrar |

---

#### Guía de pruebas — Fase 8

##### 8.A Librería

1. Ir a **Librería** en el menú lateral (`/app/library.html`)
2. Deben verse 4 tarjetas: **Entrenamiento**, **Nutrición**, **Formularios**, **Documentos**
3. Hacer clic en **Entrenamiento** → redirige a `routines.html`
4. Volver y hacer clic en **Nutrición** → redirige a la página de nutrición
5. Verificar que la tarjeta activa en el sidebar es **Librería**

##### 8.B Crear programa

1. Ir a **Programas** en el menú lateral (`/app/programas.html`)
2. Hacer clic en la tarjeta punteada **"+ Nuevo programa"**
3. Rellenar: nombre (ej. "Transformación 12 semanas"), categoría **Pérdida de grasa**, descripción breve
4. En la sección **Fases**, hacer clic en **+ Fase**:
   - Fase 1: "Adaptación" — 4 semanas
   - Fase 2: "Intensidad" — 4 semanas
   - Fase 3: "Peak" — 4 semanas
5. El total de semanas (12) debe actualizarse automáticamente
6. Hacer clic en **Crear** → el programa aparece como tarjeta en el grid
7. La tarjeta debe mostrar la categoría, el total de semanas y 0 clientes asignados

##### 8.C Filtrar por categoría

1. En la barra de pestañas superior, hacer clic en **Pérdida de grasa**
2. Solo deben verse los programas de esa categoría; el contador de la pestaña debe coincidir
3. Hacer clic en **Todos** → vuelven a aparecer todos los programas

##### 8.D Ver detalle y editar

1. Hacer clic sobre la tarjeta del programa recién creado → se abre el **drawer** lateral
2. Pestaña **Info**: muestra nombre, categoría, descripción y semanas totales
3. Pestaña **Fases**: lista las 3 fases en orden con sus semanas
4. Hacer clic en **Editar** → modificar el nombre o añadir una fase nueva → guardar
5. Verificar que los cambios se reflejan en el drawer y en la tarjeta del grid

##### 8.E Asignar y quitar clientes

1. En el drawer del programa, hacer clic en **Asignar clientes**
2. Se abre un modal con buscador → escribir el nombre de un cliente → seleccionarlo
3. Hacer clic en **Asignar** → en la pestaña **Asignados** aparece el avatar y nombre del cliente
4. La tarjeta del grid debe actualizar el contador de clientes asignados
5. En la pestaña Asignados, hacer clic en el botón **×** junto al cliente → confirmar → el cliente desaparece

##### 8.F Duplicar y eliminar

1. En la tarjeta de un programa, hacer clic en el menú (**⋮**) → seleccionar **Duplicar**
2. Aparece una copia del programa con las mismas fases pero sin clientes asignados
3. En el menú (**⋮**) de la copia → seleccionar **Eliminar** → confirmar en el diálogo
4. El programa desaparece del grid y los contadores de las pestañas se actualizan

---

*Nutrientrena v2.0 — Junio 2026*
