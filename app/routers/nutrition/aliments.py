from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import csv
import io

from sqlalchemy import or_

from app.database import get_db
from app.core.dependencies import (
    require_role_ids, get_org_context, OrgContext, _user_role_ids,
    SUPERADMIN, ADMIN, COACH, EDITOR_CONTENIDO_GLOBAL,
)
from app.core.responses import send_response, send_error
from app.core.momentos import booleano, momentos_a_claves
from app.models.nutrition.aliment import Aliment, AlimentDescription
from app.schemas.nutrition.aliment import AlimentCreate, AlimentUpdate, AlimentOut
from app.config import settings
from app.core import ai_classifier
from app.services import usda as usda_svc

router = APIRouter(prefix="/aliments", tags=["Nutrition - Aliments"])


def _get_or_404(db: Session, obj_id: str):
    return db.query(Aliment).filter(Aliment.id == obj_id).first()


def _to_float(v: str) -> Optional[float]:
    try:
        return float(v) if v and v.strip() else None
    except ValueError:
        return None


def _to_int(v: str) -> Optional[int]:
    try:
        return int(v) if v and v.strip() else None
    except ValueError:
        return None


def _usda_query(name: str) -> str:
    """Simplify a long translated food name into a short English-safe USDA query."""
    # Take the first segment before a comma (the main food type)
    short = name.split(",")[0].strip()
    # Strip characters that break USDA URL parsing
    for ch in ['«', '»', '"', "'", '/', '\\', '(', ')', '%']:
        short = short.replace(ch, ' ')
    # Collapse multiple spaces and truncate
    short = ' '.join(short.split())[:80]
    return short or name[:80]


# Lo que una dieta copia del alimento del catálogo. La ficha de micros va
# aparte, columna a columna.
CAMPOS_COPIADOS = (
    "group_food_id", "brand", "name", "quantity", "quantity_unit",
    "quantity_type_id", "proteins", "carbohydrates", "fats", "calories",
    "comments",
)

CAMPOS_FICHA = tuple(
    c.name for c in AlimentDescription.__table__.columns
    if c.name not in ("id", "aliment_id")
)


def _copias_de(db: Session, aliment_id: str, tope: int = 5000) -> list:
    """Las copias de un alimento, y las copias de esas copias.

    Meter un alimento en una dieta guarda una copia suya; duplicar o asignar
    esa dieta copia la copia. Una corrección del catálogo tiene que llegar a
    toda la cadena, no solo al primer escalón.
    """
    copias, frontera, vistos = [], [aliment_id], {aliment_id}
    while frontera and len(copias) < tope:
        siguiente = []
        for i in range(0, len(frontera), 500):
            for hijo in db.query(Aliment).filter(
                    Aliment.parent_id.in_(frontera[i:i + 500])).all():
                if hijo.id in vistos:
                    continue
                vistos.add(hijo.id)
                copias.append(hijo)
                siguiente.append(hijo.id)
        frontera = siguiente
    return copias


def propagar_a_las_copias(db: Session, obj: Aliment, antes: dict, antes_ficha: dict) -> int:
    """Lleva la corrección del catálogo a los alimentos de las dietas.

    Corregir un alimento se veía en la biblioteca y en ningún otro sitio: las
    dietas ya montadas seguían con el dato viejo, y el coach no tenía forma de
    arreglarlas salvo rehacerlas. Como esas copias las hace el sistema y nadie
    las edita a mano, la corrección baja a todas.

    Con una excepción: solo se toca lo que en la copia sigue igual que estaba
    en el catálogo ANTES del cambio. Una copia que ya diga otra cosa es que
    alguien la puso así, y eso no se pisa. Se compara campo a campo, que es lo
    que permite corregir las kcal sin tocar un nombre que alguien cambió.

    Devuelve cuántas copias han cambiado.
    """
    if not antes and not antes_ficha:
        return 0

    tocadas = 0
    for copia in _copias_de(db, obj.id):
        cambiada = False

        for campo, viejo in antes.items():
            if getattr(copia, campo) == viejo:
                setattr(copia, campo, getattr(obj, campo))
                cambiada = True

        if antes_ficha and obj.description:
            ficha = copia.description
            if ficha is None:
                # No tenía ficha: se le da la del catálogo entera. Es lo que
                # habría tenido de haberse copiado hoy.
                copia.description = AlimentDescription(**{
                    c: getattr(obj.description, c) for c in CAMPOS_FICHA})
                cambiada = True
            else:
                for campo, viejo in antes_ficha.items():
                    if getattr(ficha, campo) == viejo:
                        setattr(ficha, campo, getattr(obj.description, campo))
                        cambiada = True

        if cambiada:
            tocadas += 1
    return tocadas


def _upsert_description(db: Session, aliment_id: str, desc_data: dict):
    """Create or update the AlimentDescription row for a given aliment."""
    existing = db.query(AlimentDescription).filter(AlimentDescription.aliment_id == aliment_id).first()
    if existing:
        for field, value in desc_data.items():
            setattr(existing, field, value)
    else:
        db.add(AlimentDescription(aliment_id=aliment_id, **desc_data))


@router.get("/findAll", summary="Listar alimentos", description="Retorna todos los alimentos del catálogo (sin clones).")
def find_all(
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, EDITOR_CONTENIDO_GLOBAL)),
    org: OrgContext = Depends(get_org_context),
):
    q = (db.query(Aliment)
         .options(joinedload(Aliment.description))
         .filter(Aliment.parent_id.is_(None)))
    if org.solo_plataforma:
        q = q.filter(Aliment.organization_id.is_(None))
    elif org.org_id:
        q = q.filter(or_(Aliment.organization_id.is_(None), Aliment.organization_id == org.org_id))
    items = q.all()
    return send_response([AlimentOut.model_validate(i).model_dump() for i in items], "OK")


@router.get("/search", summary="Buscar alimentos", description="Búsqueda paginada de alimentos por nombre o grupo de alimentos.")
def search(
    search: Optional[str] = Query(None),
    group_food_id: Optional[int] = Query(None),
    page: int = Query(1),
    per_page: int = Query(15),
    db: Session = Depends(get_db),
    _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, EDITOR_CONTENIDO_GLOBAL)),
    org: OrgContext = Depends(get_org_context),
):
    q = (db.query(Aliment)
         .options(joinedload(Aliment.description))
         .filter(Aliment.parent_id.is_(None)))
    if search:
        q = q.filter(Aliment.name.ilike(f"%{search}%"))
    if group_food_id:
        q = q.filter(Aliment.group_food_id == group_food_id)
    if org.solo_plataforma:
        q = q.filter(Aliment.organization_id.is_(None))
    elif org.org_id:
        q = q.filter(or_(Aliment.organization_id.is_(None), Aliment.organization_id == org.org_id))
    total = q.count()
    items = q.order_by(Aliment.name).offset((page - 1) * per_page).limit(per_page).all()
    return send_response(
        {
            "data": [AlimentOut.model_validate(i).model_dump() for i in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "last_page": max(1, (total + per_page - 1) // per_page),
        },
        "OK",
    )


@router.get("/{id}/edit", summary="Ver alimento", description="Retorna el detalle completo de un alimento incluyendo micronutrientes.")
def edit(id: str, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, EDITOR_CONTENIDO_GLOBAL))):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Alimento no encontrado")
    return send_response(AlimentOut.model_validate(obj).model_dump(), "OK")


@router.post("", summary="Crear alimento", description="Agrega un nuevo alimento al catálogo con sus macros y micronutrientes.")
def create(
    data: AlimentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, EDITOR_CONTENIDO_GLOBAL)),
    org: OrgContext = Depends(get_org_context),
):
    payload = data.model_dump(exclude={"description"})
    obj = Aliment(**payload, created_user_id=current_user.id, organization_id=org.org_id)
    db.add(obj)
    db.flush()

    if data.description:
        desc_data = data.description.model_dump(exclude_none=True)
        if desc_data:
            _upsert_description(db, obj.id, desc_data)

    # Si el coach no marcó los momentos, se los pone la IA. Es "si sale, sale":
    # que falle la clasificación no puede impedir que se guarde el alimento.
    if not obj.meal_moments and ai_classifier.classify_enabled():
        try:
            obj.meal_moments = ai_classifier.classify_one(obj)
        except Exception:
            pass

    db.commit()
    db.refresh(obj)
    return send_response(AlimentOut.model_validate(obj).model_dump(), "Alimento creado")


def _bloqueado_para_editar(obj, org: OrgContext, current_user, db: Session):
    """Motivo por el que no se puede tocar este alimento, o None.

    Cuatro reglas, en orden:
    1. Su autor siempre puede con lo suyo. Va PRIMERO, igual que en rutinas y
       dietas: un coach sin organización crea con organization_id NULL, así
       que su propio alimento queda marcado como de plataforma y la regla 3 le
       bloqueaba lo que acababa de crear.
    2. Bypass total: superadmin, o admin sin organización propia.
    3. Contenido de plataforma (organization_id NULL): solo el editor de
       contenido global, para el que es justamente su único trabajo.
    4. De una organización: tiene que ser la tuya.
    """
    if org.solo_plataforma and obj.organization_id is not None:
        return "No tienes acceso a este alimento"   # actuando solo como plataforma
    # Solo mientras siga siendo suyo: subirlo al catálogo común cambia de quién
    # es. La excepción es el coach SIN organización, que crea con NULL y sin
    # ella se quedaría bloqueado con su propio alimento.
    if obj.created_user_id is not None and obj.created_user_id == current_user.id:
        if obj.organization_id is not None or org.org_id is None:
            return None
    if org.org_id is None and org.is_owner:
        return None
    if obj.organization_id is None:
        if EDITOR_CONTENIDO_GLOBAL not in _user_role_ids(current_user.id, db):
            return "No puedes editar alimentos de la plataforma"
        return None
    if obj.organization_id != org.org_id:
        return "No tienes acceso a este alimento"
    return None


def _alcance_masivo(q, org: OrgContext, current_user, db: Session):
    """Acota una operación masiva a lo que puede tocar quien llama.

    Tiene que coincidir con _bloqueado_para_editar: la primera versión dejaba
    fuera el contenido de otras organizaciones pero SÍ incluía el de
    plataforma, así que un coach no podía editar un alimento del catálogo común
    uno a uno (403) y sin embargo podía reescribirlo entero con una sola
    llamada a classify-moments o usda-sync. Dos puertas al mismo sitio con
    reglas distintas.
    """
    if org.solo_plataforma:
        return q.filter(Aliment.organization_id.is_(None))  # solo el catálogo común
    if org.org_id is None and org.is_owner:
        return q  # superadmin, o admin sin organización propia

    # Lo propio siempre entra, tenga la organización que tenga.
    condiciones = [Aliment.created_user_id == current_user.id]
    if org.org_id:
        condiciones.append(Aliment.organization_id == org.org_id)
    if EDITOR_CONTENIDO_GLOBAL in _user_role_ids(current_user.id, db):
        condiciones.append(Aliment.organization_id.is_(None))
    return q.filter(or_(*condiciones))


@router.put("/{id}/update", summary="Actualizar alimento", description="Modifica los datos nutricionales y micronutrientes de un alimento existente.")
def updated(
    id: str,
    data: AlimentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, EDITOR_CONTENIDO_GLOBAL)),
    org: OrgContext = Depends(get_org_context),
):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Alimento no encontrado")

    motivo = _bloqueado_para_editar(obj, org, current_user, db)
    if motivo:
        return send_error(motivo, code=403)

    # Cómo estaba lo que se va a cambiar: es lo que dice qué copias siguen
    # siendo fieles al catálogo y pueden recibir la corrección.
    cambios = data.model_dump(exclude_unset=True, exclude={"description"})
    antes = {f: getattr(obj, f) for f in cambios if f in CAMPOS_COPIADOS}

    for f, v in cambios.items():
        setattr(obj, f, v)
    obj.updated_user_id = current_user.id
    antes = {f: v for f, v in antes.items() if v != getattr(obj, f)}

    antes_ficha = {}
    if data.description is not None:
        desc_data = data.description.model_dump(exclude_unset=True)
        if desc_data:
            ficha = db.query(AlimentDescription).filter(
                AlimentDescription.aliment_id == obj.id).first()
            antes_ficha = {f: (getattr(ficha, f) if ficha else None) for f in desc_data}
            _upsert_description(db, obj.id, desc_data)
            db.flush()
            db.refresh(obj)
            antes_ficha = {f: v for f, v in antes_ficha.items()
                           if v != getattr(obj.description, f)}

    propagar_a_las_copias(db, obj, antes, antes_ficha)

    db.commit()
    db.refresh(obj)
    return send_response(AlimentOut.model_validate(obj).model_dump(), "Actualizado")


@router.delete("/{id}", summary="Eliminar alimento", description="Elimina un alimento del catálogo. Falla si está en uso en alguna dieta o receta.")
def delete_aliment(
    id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, EDITOR_CONTENIDO_GLOBAL)),
    org: OrgContext = Depends(get_org_context),
):
    obj = _get_or_404(db, id)
    if not obj:
        return send_error("Alimento no encontrado")
    # Borrar no comprobaba nada: cualquier coach podía borrar el alimento
    # privado de otra organización, o uno del catálogo de plataforma.
    motivo = _bloqueado_para_editar(obj, org, current_user, db)
    if motivo:
        return send_error(motivo, code=403)
    try:
        db.delete(obj)
        db.commit()
    except Exception:
        db.rollback()
        return send_error("No se puede eliminar: el alimento está en uso en una dieta o receta")
    return send_response(None, "Alimento eliminado")


@router.post("/import", summary="Importar alimentos desde CSV", description="Importa alimentos masivamente desde un archivo CSV.")
async def import_aliments(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, EDITOR_CONTENIDO_GLOBAL)),
    org: OrgContext = Depends(get_org_context),
):
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    col_map = {
        "nombre": "name",          "name": "name",
        "marca": "brand",          "brand": "brand",
        "grupo_id": "group_food_id", "group_food_id": "group_food_id",
        # El CSV trae la categoría por NOMBRE ("Frutas"), no por su número:
        # nadie que prepare un CSV a mano sabe qué id tiene cada grupo.
        "grupo de alimento": "group_name", "grupo": "group_name",
        "categoria": "group_name", "categoría": "group_name",
        "unidad": "quantity_unit", "quantity_unit": "quantity_unit",
        "momento_sugerido": "meal_moments", "meal_moments": "meal_moments",
        "usar_en_generador": "use_in_generator", "use_in_generator": "use_in_generator",
        "proteinas": "proteins",   "proteins": "proteins",
        "carbohidratos": "carbohydrates", "carbohydrates": "carbohydrates",
        "grasas": "fats",          "fats": "fats",
        "calorias": "calories",    "calories": "calories",
        "cantidad": "quantity",    "quantity": "quantity",
        "comentarios": "comments", "comments": "comments",
        # micronutrients
        "fibra": "fiber",           "fiber": "fiber",
        "sodio": "sodium",          "sodium": "sodium",
        "calcio": "calcium",        "calcium": "calcium",
        "hierro": "iron",           "iron": "iron",
        "potasio": "potassium",     "potassium": "potassium",
        "magnesio": "magnesium",    "magnesium": "magnesium",
        "fosforo": "phosphorus",    "phosphorus": "phosphorus",
        "zinc": "zinc",
        "selenio": "selenium",      "selenium": "selenium",
        "cobre": "copper",          "copper": "copper",
        "manganeso": "manganese",   "manganese": "manganese",
        "colesterol": "cholesterol", "cholesterol": "cholesterol",
        "grasas_saturadas": "saturated_fats",     "saturated_fats": "saturated_fats",
        "grasas_monoinsaturadas": "mono_saturated_fats", "mono_saturated_fats": "mono_saturated_fats",
        "grasas_poliinsaturadas": "poli_saturated_fats", "poli_saturated_fats": "poli_saturated_fats",
        "agua": "water",            "water": "water",
        "indice_glucemico": "glycemic_index", "glycemic_index": "glycemic_index",
        "vita": "vita",   "vitamina_a": "vita",
        "vitb1": "vitb1", "vitamina_b1": "vitb1",
        "vitb2": "vitb2", "vitamina_b2": "vitb2",
        "vitb3": "vitb3", "vitamina_b3": "vitb3",
        "vitb5": "vitb5", "vitamina_b5": "vitb5",
        "vitb6": "vitb6", "vitamina_b6": "vitb6",
        "vitb9": "vitb9", "vitamina_b9": "vitb9",   "acido_folico": "vitb9",
        "vitb12": "vitb12", "vitamina_b12": "vitb12",
        "vitc": "vitc",   "vitamina_c": "vitc",
        "vitd": "vitd",   "vitamina_d": "vitd",
        "vite": "vite",   "vitamina_e": "vite",
        "vitk": "vitk",   "vitamina_k": "vitk",
        # Cabeceras del catálogo exportado (mayúsculas y nombres en inglés).
        "choline": "calina",
        "saturatedfat": "saturated_fats",
        "monounsaturatedfat": "mono_saturated_fats",
        "polyunsaturatedfat": "poli_saturated_fats",
        "glycemicindex": "glycemic_index",
    }

    DESC_FIELDS = {
        "vita", "vitb1", "vitb2", "vitb3", "vitb5", "vitb6", "vitb9", "vitb12",
        "vitc", "vitd", "vite", "vitk",
        "calina", "calcium", "copper", "iron", "magnesium", "manganese",
        "phosphorus", "potassium", "selenium", "sodium", "zinc",
        "water", "fiber", "cholesterol", "saturated_fats",
        "mono_saturated_fats", "poli_saturated_fats", "glycemic_index",
    }

    # La unidad de la plataforma es `g`; los CSV suelen traer `gr`. Y aparece
    # alguna `u` suelta entre las `ud`.
    UNIDADES = {"gr": "g", "g": "g", "ud": "ud", "u": "ud", "ml": "ml", "tz": "ud"}

    def _grupo_por_nombre(nombre):
        """El id de la categoría, creándola si no existe.

        Sin esto, un CSV con "Frutas" en la columna de categoría dejaba los 89
        alimentos sin agrupar, y la biblioteca sale como una lista plana de
        ochocientos nombres.
        """
        from app.models.nutrition.group_food import GroupFood
        limpio = (nombre or "").strip()
        if not limpio:
            return None
        g = db.query(GroupFood).filter(GroupFood.name == limpio).first()
        if not g:
            g = GroupFood(name=limpio)
            db.add(g)
            db.flush()
        return g.id

    reader = csv.DictReader(io.StringIO(text))
    created = 0
    errors  = []

    def _tiene_micros(fila):
        return any((fila.get(k) or "").strip() for k in fila
                   if k and k.strip().lower() in col_map
                   and col_map[k.strip().lower()] in DESC_FIELDS)

    # Dos filas con el mismo nombre son la misma cosa metida dos veces. Se
    # queda la que TIENE micronutrientes: la otra trae solo macros y suele ser
    # la que metió a mano algún cliente. Mismo criterio que el script de carga
    # masiva: si cada camino descartara una distinta, el catálogo saldría
    # diferente según por dónde se cargue.
    filas, mejor = [], {}
    for i, row in enumerate(reader, start=2):
        nombre = " ".join((row.get("Nombre") or row.get("nombre") or row.get("name") or "").split())
        clave = nombre.lower()
        if not clave:
            filas.append((i, row))
            continue
        previa = mejor.get(clave)
        if previa is None:
            mejor[clave] = (i, row)
        elif _tiene_micros(row) and not _tiene_micros(previa[1]):
            errors.append(f"Fila {previa[0]}: '{nombre}' repetido, se queda el que trae micronutrientes")
            mejor[clave] = (i, row)
        else:
            errors.append(f"Fila {i}: '{nombre}' ya venía antes en el fichero, se omite")
    filas += list(mejor.values())
    filas.sort(key=lambda t: t[0])

    for i, row in filas:
        norm = {
            col_map[k.strip().lower()]: v.strip()
            for k, v in row.items()
            if k and k.strip().lower() in col_map
        }
        name = " ".join((norm.get("name") or "").split())
        if not name:
            errors.append(f"Fila {i}: columna 'nombre' requerida")
            continue
        # Muchos vienen en minúscula y en la biblioteca quedan como un renglón
        # desordenado entre cientos.
        name = name[:1].upper() + name[1:]

        unidad = (norm.get("quantity_unit") or "").strip().lower()
        aliment = Aliment(
            name=name,
            brand=norm.get("brand") or None,
            quantity_unit=UNIDADES.get(unidad, "g"),
            # Del vocabulario del fichero al de la pantalla. Guardando la
            # etiqueta larga tal cual, el dato entra pero los chips del
            # formulario no se marcan: ellos comparan las claves cortas.
            meal_moments=momentos_a_claves(norm.get("meal_moments")),
            # `bool("False")` es True, que es exactamente el fallo que se
            # esperaría aquí: marcaría los 160 que el cliente dejó fuera.
            use_in_generator=booleano(norm.get("use_in_generator"), por_defecto=False),
            group_food_id=(_to_int(norm.get("group_food_id", ""))
                           or _grupo_por_nombre(norm.get("group_name"))),
            proteins=_to_float(norm.get("proteins", "")),
            carbohydrates=_to_float(norm.get("carbohydrates", "")),
            fats=_to_float(norm.get("fats", "")),
            calories=_to_float(norm.get("calories", "")),
            quantity=_to_float(norm.get("quantity", "")),
            comments=norm.get("comments") or None,
            created_user_id=current_user.id,
            # Igual que al crear uno a uno: lo que importa un coach con
            # organización es suyo, no del catálogo común de la plataforma.
            organization_id=org.org_id,
        )
        db.add(aliment)
        db.flush()

        desc_data = {f: _to_float(norm.get(f, "")) for f in DESC_FIELDS if norm.get(f)}
        if desc_data:
            db.add(AlimentDescription(aliment_id=aliment.id, **desc_data))

        created += 1

    db.commit()
    suffix = f" ({len(errors)} filas con error)" if errors else ""
    return send_response(
        {"created": created, "errors": errors},
        f"{created} alimentos importados{suffix}",
    )


class UsdaSyncRequest(BaseModel):
    ids: Optional[List[str]] = None
    batch: int = 30  # max aliments per request to avoid gateway timeout


@router.post("/usda-sync", summary="Sincronizar micronutrientes con USDA", description="Busca cada alimento en USDA FoodData Central por nombre y rellena sus micronutrientes.")
async def usda_sync(
    body: UsdaSyncRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, EDITOR_CONTENIDO_GLOBAL)),
    org: OrgContext = Depends(get_org_context),
):
    api_key = settings.USDA_API_KEY
    if not api_key:
        return send_error("USDA_API_KEY no configurada en el servidor")

    # Sin acotar, esto reescribía los micronutrientes de TODO el catálogo,
    # incluidos los alimentos privados de otras organizaciones.
    if body.ids:
        aliments = _alcance_masivo(db.query(Aliment).filter(Aliment.id.in_(body.ids)), org, current_user, db).all()
    else:
        # sync only those without a description row yet
        synced_ids = db.query(AlimentDescription.aliment_id).scalar_subquery()
        aliments = _alcance_masivo(db.query(Aliment).filter(
            Aliment.parent_id.is_(None),
            ~Aliment.id.in_(synced_ids),
        ), org, current_user, db).limit(body.batch).all()

    total_pending = _alcance_masivo(db.query(Aliment).filter(
        Aliment.parent_id.is_(None),
        ~Aliment.id.in_(db.query(AlimentDescription.aliment_id).scalar_subquery()),
    ), org, current_user, db).count() if not body.ids else 0

    synced: List[str] = []
    not_found: List[str] = []
    errors: List[str] = []

    for aliment in aliments:
        try:
            query = _usda_query(aliment.name)
            food = await usda_svc.search_food(api_key, query)
            if not food:
                not_found.append(aliment.name)
                await asyncio.sleep(0.25)
                continue

            micros = usda_svc.extract_micros(food)
            macros = usda_svc.extract_macros(food)

            if aliment.proteins is None and macros.get("proteins") is not None:
                aliment.proteins = macros["proteins"]
            if aliment.carbohydrates is None and macros.get("carbohydrates") is not None:
                aliment.carbohydrates = macros["carbohydrates"]
            if aliment.fats is None and macros.get("fats") is not None:
                aliment.fats = macros["fats"]
            if aliment.calories is None and macros.get("calories") is not None:
                aliment.calories = macros["calories"]

            non_null_micros = {k: v for k, v in micros.items() if v is not None}
            if non_null_micros:
                _upsert_description(db, aliment.id, non_null_micros)

            synced.append(aliment.name)
            await asyncio.sleep(0.25)

        except Exception as e:
            errors.append(f"{aliment.name}: {str(e)[:120]}")

    db.commit()
    remaining = max(0, total_pending - len(aliments)) if not body.ids else 0
    return send_response(
        {
            "synced": len(synced),
            "not_found": not_found,
            "errors": errors,
            "remaining": remaining,
        },
        f"{len(synced)} alimentos sincronizados con USDA",
    )


class ClassifyMomentsRequest(BaseModel):
    ids: Optional[List[str]] = None
    batch: int = 1000         # alimentos por petición (el grupo no gasta llamadas)
    chunk: int = 50           # alimentos por llamada al modelo
    force: bool = False       # recalcular también los que ya tienen momentos


def _sin_momentos():
    """Alimentos a los que todavía no se les ha puesto momento del día."""
    return or_(Aliment.meal_moments.is_(None), Aliment.meal_moments == "")


@router.post(
    "/classify-moments",
    summary="Clasificar alimentos por momento del día",
    description="Etiqueta cada alimento como desayuno / snack / principal con IA, para que el generador de dietas no proponga ternera para desayunar.",
)
def classify_moments(
    body: ClassifyMomentsRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH, EDITOR_CONTENIDO_GLOBAL)),
    org: OrgContext = Depends(get_org_context),
):
    # joinedload: se lee el grupo de cada alimento, y sin esto serían tantas
    # consultas como alimentos.
    q = _alcance_masivo(
        db.query(Aliment)
        .options(joinedload(Aliment.group_food))
        .filter(Aliment.parent_id.is_(None)), org, current_user, db)
    if body.ids:
        q = q.filter(Aliment.id.in_(body.ids))
    elif not body.force:
        # Por defecto no se toca lo que el coach ya etiquetó a mano.
        q = q.filter(_sin_momentos())
    aliments = q.limit(max(1, body.batch)).all()

    pendientes = 0
    if not body.ids and not body.force:
        pendientes = _alcance_masivo(db.query(Aliment).filter(
            Aliment.parent_id.is_(None), _sin_momentos()
        ), org, current_user, db).count()

    # Primero, gratis: el grupo del alimento (Frutas, Aceites y grasas,
    # Mariscos…) ya dice el momento y viene con cada alimento importado. Es más
    # fiable que deducirlo del nombre y no gasta ni una llamada, así que la IA
    # solo se queda con lo que el grupo no resuelve.
    from app.core.diet_builder import moments_from_group

    por_grupo = 0
    pendientes_ia = []
    for a in aliments:
        momentos = moments_from_group(a)
        if momentos:
            a.meal_moments = ",".join(momentos)
            por_grupo += 1
        else:
            pendientes_ia.append(a)
    if por_grupo:
        db.commit()
    aliments = pendientes_ia

    clasificados = por_grupo
    procesados = por_grupo
    errores: List[str] = []
    esperar = 0
    tam = max(1, min(body.chunk, 100))

    # Lo que el grupo no resuelve necesita al modelo. Si no está configurado se
    # dice, pero lo clasificado por categoría ya está guardado: no tener clave
    # no puede impedir que se aproveche lo que sale gratis.
    if aliments and not ai_classifier.classify_enabled():
        return send_response(
            {
                "classified": clasificados,
                "processed": procesados,
                "errors": [],
                "remaining": max(0, pendientes - procesados),
                "retry_after": 0,
                "needs_ai": len(aliments),
            },
            f"{clasificados} clasificados por categoría. Quedan {len(aliments)} "
            f"que necesitan IA: configura {ai_classifier.key_var_name()} y "
            f"AI_CLASSIFY_ENABLED=true.",
        )

    for i in range(0, len(aliments), tam):
        lote = aliments[i:i + tam]
        try:
            momentos = ai_classifier.classify(lote)
        except ai_classifier.RateLimited as e:
            # Se ha agotado el cupo del minuto. Se corta aquí y se dice cuánto
            # esperar: seguir intentando solo gasta llamadas que van a fallar.
            esperar = e.seconds
            break
        except Exception as e:
            errores.append(f"lote {i // tam + 1}: {str(e)[:120]}")
            procesados += len(lote)
            continue
        for a in lote:
            valor = momentos.get(a.id)
            if valor:
                a.meal_moments = valor
                clasificados += 1
        procesados += len(lote)

    db.commit()

    if esperar:
        mensaje = (f"{clasificados} clasificados. Límite por minuto alcanzado, "
                   f"continuando en {esperar} s")
    else:
        mensaje = f"{clasificados} alimentos clasificados"

    return send_response(
        {
            "classified": clasificados,
            "processed": procesados,
            "errors": errores,
            # Lo pendiente se recalcula con lo realmente procesado: al cortar
            # por el límite quedan más de los que se habían pedido.
            "remaining": max(0, pendientes - procesados),
            "retry_after": esperar,
            "by_group": por_grupo,
        },
        mensaje,
    )
