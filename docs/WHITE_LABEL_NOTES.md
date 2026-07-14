# Marca blanca (white-label) — nota de arquitectura

> Estado: **pendiente / anotado para el futuro**. NO implementado todavía.
> Objetivo: que cada coach/organización configure su **nombre, logo y colores**
> (en "Negocio/Configuración") y eso reemplace la marca "Alzum" por defecto en
> todos los sitios donde aparece (PDF de contratos, sidebar, emails, etc.).
> Por defecto se mantiene la marca Alzum.

## Cimientos que YA existen (no rehacer)

1. **Colores centralizados**: la paleta vive en variables CSS `:root`
   (`--lib-primary`, `--lib-primary-hover`, `--cat-entrenamiento`,
   `--cat-nutricion`, `--cat-formularios`, `--cat-documentos`, `--lib-*`).
   Para aplicar los colores de un coach basta con **sobrescribir esas
   variables** en runtime (inyectar un `<style>` o `document.documentElement
   .style.setProperty('--lib-primary', color)`). No hay que tocar cada pantalla.
2. **Entidad dueña de la marca**: modelo `Organization`
   (`app/models/organization.py`) con `name`, `slug`, `owner_id`, miembros.
   Es el sitio natural para la marca. Un coach solo = su propia organización.

## Dónde está "Alzum" hardcodeado hoy (alcance del trabajo)

- **Backend / PDF** (color índigo + texto "Alzum.io"):
  - `app/pdf/contract_pdf.py` (marca en cabecera + footer + color `INDIGO`)
  - `app/pdf/routine_pdf.py`
  - `app/pdf/diet_pdf.py`
  - `app/routers/contracts.py` (envío por email)
  - Plantillas de email (Resend)
- **Frontend**: ~37 archivos, sobre todo el logo del sidebar
  (`ALZUM<em>.io</em>` en `.sidebar-logo`).

## Arquitectura recomendada (cuando se implemente)

1. **Fuente de verdad**: añadir a `organizations` los campos
   `brand_name` (o reutilizar `name`), `logo_url`, `primary_color`,
   `secondary_color` (o un único `branding` JSON). Migración nueva.
2. **Distribución al frontend**: incluir la marca en la respuesta de
   **`/auth/me`** (que todas las páginas ya llaman al cargar). Una función
   compartida `applyBrand(brand)` pone el logo del sidebar y las variables CSS.
   Así **no se editan 37 archivos** uno a uno, solo un helper.
3. **PDFs / emails**: que los generadores acepten un parámetro `brand`
   (dict con `name`, `logo_url`/bytes, `color`) con **Alzum por defecto**;
   el router carga la marca de la organización del coach y la pasa.

## Disciplina a mantener AHORA (para no complicarlo luego)

- **No hardcodear colores en hex** en código nuevo: usar siempre las
  variables `:root`.
- **No esparcir más "Alzum"** en código nuevo: que la marca salga de un
  único sitio (variable/parámetro), no repetida.

## Prep opcional (no hecho — se puede hacer en 1 commit sin activar la función)

- (a) Que `contract_pdf.py` / `routine_pdf.py` / `diet_pdf.py` acepten un
  `brand` opcional (default Alzum).
- (b) Añadir columnas `logo_url` / `primary_color` / `secondary_color`
  (nullable) a `organizations`.

Recomendación: abordarlo **entero** más adelante como un trabajo acotado, en
lugar de a medias.
