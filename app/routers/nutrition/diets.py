from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from sqlalchemy import or_
from app.core.dependencies import (
    require_role_ids, get_org_context, OrgContext,
    verify_client_access, SUPERADMIN, ADMIN, COACH,
)
from app.core.responses import send_response, send_error
from app.models.nutrition.diet import Diet, DietDetail, DietFood, DietFoodAliment, Pathology, diet_pathologies_table
from app.models.nutrition.aliment import Aliment
from app.schemas.nutrition.diet import DietCreate, DietUpdate, DietOut, DietFoodCreate, DietFoodAlimentCreate
from app.pdf.diet_pdf import generate_diet_pdf

router = APIRouter(prefix="/diets", tags=["Nutrition - Diets"])


def _get_or_404(db: Session, diet_id: str):
    return db.query(Diet).filter(Diet.id == diet_id).first()


def _get_or_404_with_pathologies(db: Session, diet_id: str):
    return (
        db.query(Diet)
        .options(selectinload(Diet.pathologies))
        .filter(Diet.id == diet_id)
        .first()
    )


def _diet_food_totals(diet: Diet):
    """Suma kcal y macros reales a partir de los alimentos de la dieta."""
    k = p = c = f = 0.0
    for food in (diet.foods or []):
        for dfa in (food.detail or []):
            al = dfa.aliment
            q = dfa.quantity or 0
            if al and q:
                k += (al.calories or 0) / 100.0 * q
                p += (al.proteins or 0) / 100.0 * q
                c += (al.carbohydrates or 0) / 100.0 * q
                f += (al.fats or 0) / 100.0 * q
    return k, p, c, f


def _serialize(diet: Diet) -> dict:
    data = DietOut.model_validate(diet).model_dump()
    # Objetivo nutricional de la plantilla, leído ANTES del relleno de abajo:
    # una dieta "libre" acaba con kcal/macros calculados y ya no se distinguiría.
    det0 = diet.detail
    if det0 and (det0.proteins or det0.carbs or det0.fats):
        data["goal_mode"] = "macros"
    elif diet.calories:
        data["goal_mode"] = "kcal"
    else:
        data["goal_mode"] = "libre"
    # Si la dieta no tiene kcal/macros objetivo guardados (modo "libre"),
    # se muestran los totales reales calculados de sus alimentos.
    if not data.get("calories"):
        k, p, c, f = _diet_food_totals(diet)
        if k > 0:
            data["calories"] = round(k)
            det = data.get("detail")
            if not isinstance(det, dict):
                det = {}
            if not det.get("proteins"):
                det["proteins"] = round(p, 1)
            if not det.get("carbs"):
                det["carbs"] = round(c, 1)
            if not det.get("fats"):
                det["fats"] = round(f, 1)
            data["detail"] = det
    return data


def _clone_aliment(db: Session, source: Aliment) -> Aliment:
    clone = Aliment(
        group_food_id=source.group_food_id,
        brand=source.brand,
        name=source.name,
        quantity=source.quantity,
        quantity_unit=source.quantity_unit,
        quantity_type_id=source.quantity_type_id,
        proteins=source.proteins,
        carbohydrates=source.carbohydrates,
        fats=source.fats,
        calories=source.calories,
        comments=source.comments,
        parent_id=source.id,
        created_user_id=source.created_user_id,
    )
    db.add(clone)
    db.flush()
    return clone


def _save_pathologies(db: Session, diet_id: str, pathology_ids: list):
    db.execute(
        diet_pathologies_table.delete().where(diet_pathologies_table.c.diet_id == diet_id)
    )
    for pid in (pathology_ids or []):
        db.execute(diet_pathologies_table.insert().values(diet_id=diet_id, pathology_id=pid))


def _save_foods(db: Session, diet_id: str, foods_data: list, current_user_id: int):
    for food_data in foods_data:
        if food_data.delete and food_data.id:
            food = db.query(DietFood).filter(
                DietFood.id == food_data.id, DietFood.diet_id == diet_id
            ).first()
            if food:
                db.delete(food)
            continue

        if food_data.id:
            food = db.query(DietFood).filter(
                DietFood.id == food_data.id, DietFood.diet_id == diet_id
            ).first()
            if not food:
                continue
            food.name = food_data.name
            if food_data.time is not None:
                food.time = food_data.time or None
        else:
            food = DietFood(diet_id=diet_id, name=food_data.name, time=food_data.time)
            db.add(food)
            db.flush()

        kept_ids = set()

        for aliment_data in (food_data.detail or []):
            if aliment_data.delete and aliment_data.id:
                dfa = db.query(DietFoodAliment).filter(
                    DietFoodAliment.id == aliment_data.id
                ).first()
                if dfa:
                    db.delete(dfa)
                continue

            source_aliment = db.query(Aliment).filter(
                Aliment.id == aliment_data.aliment_id
            ).first()
            if not source_aliment:
                # Puede ser un alimento personal (client_aliments): clonarlo a
                # aliments para que la dieta lo referencie como cualquier otro.
                from app.models.nutrition.client_aliment import ClientAliment
                ca = db.query(ClientAliment).filter(
                    ClientAliment.id == aliment_data.aliment_id
                ).first()
                if not ca:
                    continue
                source_aliment = Aliment(
                    group_food_id=ca.group_food_id,
                    brand=ca.brand,
                    name=ca.name,
                    quantity=ca.quantity,
                    quantity_unit=ca.quantity_unit,
                    proteins=ca.proteins,
                    carbohydrates=ca.carbohydrates,
                    fats=ca.fats,
                    calories=ca.calories,
                    comments=ca.comments,
                    created_user_id=current_user_id,
                )
                db.add(source_aliment)
                db.flush()

            if aliment_data.id:
                dfa = db.query(DietFoodAliment).filter(
                    DietFoodAliment.id == aliment_data.id
                ).first()
                if dfa:
                    # If the chosen aliment changed, re-clone the new source and repoint.
                    # dfa.aliment_id points to a clone; its parent_id is the source aliment.
                    current_source = dfa.aliment.parent_id if dfa.aliment else None
                    unchanged = (
                        str(dfa.aliment_id) == str(aliment_data.aliment_id)
                        or str(current_source) == str(aliment_data.aliment_id)
                    )
                    if not unchanged:
                        cloned = _clone_aliment(db, source_aliment)
                        cloned.created_user_id = current_user_id
                        dfa.aliment_id = cloned.id
                    dfa.quantity = aliment_data.quantity_calc
                    dfa.order = aliment_data.order or 0
                    kept_ids.add(dfa.id)
                    continue

            cloned = _clone_aliment(db, source_aliment)
            cloned.created_user_id = current_user_id

            dfa = DietFoodAliment(
                diet_id=diet_id,
                diet_food_id=food.id,
                aliment_id=cloned.id,
                quantity=aliment_data.quantity_calc,
                order=aliment_data.order or 0,
            )
            db.add(dfa)
            db.flush()
            kept_ids.add(dfa.id)

        # Remove aliments deleted in the editor (existing rows no longer sent)
        for orphan in db.query(DietFoodAliment).filter(
            DietFoodAliment.diet_food_id == food.id
        ).all():
            if orphan.id not in kept_ids:
                db.delete(orphan)


@router.get("/findAll", summary="Listar dietas", description="Retorna todas las dietas del coach autenticado.")
def find_all(
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
    org: OrgContext = Depends(get_org_context),
):
    # selectinload: Diet.pathologies es lazy="noload" y sin esto llegaría vacío.
    q = db.query(Diet).options(selectinload(Diet.pathologies)).filter(Diet.user_id == current_user.id)
    if org.org_id:
        q = q.filter(or_(Diet.organization_id.is_(None), Diet.organization_id == org.org_id))
    return send_response([_serialize(i) for i in q.all()], "OK")


@router.get("/client/{client_id}", summary="Dietas del cliente", description="Retorna las dietas de un cliente agrupadas por tipo de alimentación.")
def client_diets(client_id: str, db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    verify_client_access(client_id, current_user, db)
    from app.models.user import UserDetail
    from app.models.nutrition.type_food import TypeFood

    client_detail = db.query(UserDetail).filter(UserDetail.id == client_id).first()
    if not client_detail:
        return send_error("Cliente no encontrado")

    diets = db.query(Diet).filter(Diet.user_id == client_detail.user_id).all()

    type_foods = db.query(TypeFood).all()
    grouped = []
    for tf in type_foods:
        matching = [_serialize(d) for d in diets if d.type_id == tf.id]
        if matching:
            grouped.append({"type": {"id": tf.id, "name": tf.name}, "diets": matching})

    untyped = [_serialize(d) for d in diets if d.type_id is None]
    if untyped:
        grouped.append({"type": None, "diets": untyped})

    return send_response(grouped, "OK")


# ── Generación con IA ─────────────────────────────────────────────────────────
class _AIGenerateBody(BaseModel):
    client_id: Optional[str] = None       # UserDetail UUID; opcional
    kcal: float
    proteins: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    fiber: Optional[float] = None
    meal_count: int = 4
    notes: Optional[str] = None           # indicaciones libres del coach
    max_aliments: int = 220


def _client_context(db: Session, client_id: str) -> dict:
    """Lo que necesita saber el modelo para proponer un plan, y nada más.

    Va sin nombre, sin correo y sin identificadores: quien lo recibe no puede
    saber de quién es la ficha. Tampoco viajan los diagnósticos — de una
    patología solo sale la restricción que implica ("evitar gluten"), que es lo
    único que cambia la dieta. El aviso clínico para el coach se calcula aparte,
    aquí en el servidor, y no se le pide a la IA.
    """
    from app.core.diet_builder import exclusions_for
    from app.models.user import UserDetail

    detail = db.query(UserDetail).filter(UserDetail.id == client_id).first()
    if not detail:
        return {}

    patologias = [p.name for p in (detail.pathologies or [])]
    evitar = sorted(exclusions_for(patologias))

    ctx = {
        "Edad": detail.age,
        "Sexo": detail.gender.description if detail.gender else None,
        "Peso (kg)": detail.weight,
        "Altura (cm)": detail.height,
        "Objetivo": detail.objective.description if detail.objective else None,
        "Nivel de actividad": detail.activity.description if detail.activity else None,
        "Alergias": detail.allergies,
        "Intolerancias": detail.intolerances,
        "No le gusta": detail.dislikes,
        "Preferencias alimentarias": detail.food_preferences,
    }
    if evitar:
        ctx["Alimentos a evitar"] = ", ".join(evitar)
    return ctx


def _pick_catalog(aliments: list, limit: int) -> list:
    """Recorta el catálogo a un subconjunto que siga siendo utilizable.

    Mandar los primeros N alimentos podía dejar al modelo sin proteínas o sin
    nada de desayuno, según cómo estuviera ordenada la tabla. Se reparte el
    cupo entre los cuatro roles (proteína, carbohidrato, grasa, verdura) y,
    dentro de cada uno, entre los momentos del día, cogiendo por turnos hasta
    llenar. Así el recorte no deja fuera una categoría entera.
    """
    from app.core.diet_builder import MOMENTS, classify, moments_for

    if len(aliments) <= limit:
        return aliments

    # (rol, momento) -> alimentos
    cajones: dict = {}
    for a in aliments:
        rol = classify(a)
        if not rol:
            continue
        for momento in moments_for(a):
            cajones.setdefault((rol, momento), []).append(a)

    claves = [(r, m) for r in ("protein", "carb", "fat", "veg") for m in MOMENTS]
    elegidos, vistos = [], set()
    # Ronda a ronda: uno de cada cajón, hasta llenar el cupo.
    for vuelta in range(limit):
        if len(elegidos) >= limit:
            break
        for clave in claves:
            grupo = cajones.get(clave) or []
            if vuelta >= len(grupo):
                continue
            a = grupo[vuelta]
            if a.id in vistos:
                continue
            vistos.add(a.id)
            elegidos.append(a)
            if len(elegidos) >= limit:
                break
    # Si algo quedó suelto (sin rol reconocible), se completa con el resto.
    if len(elegidos) < limit:
        for a in aliments:
            if a.id not in vistos:
                elegidos.append(a)
                vistos.add(a.id)
                if len(elegidos) >= limit:
                    break
    return elegidos


def _macros_for(aliment, grams: float) -> tuple:
    f = (grams or 0) / 100.0
    return (
        (aliment.calories or 0) * f,
        (aliment.proteins or 0) * f,
        (aliment.carbohydrates or 0) * f,
        (aliment.fats or 0) * f,
    )


class _AutoGenerateBody(BaseModel):
    client_id: Optional[str] = None
    kcal: float
    proteins: float = 0
    carbs: float = 0
    fats: float = 0
    meal_count: int = 4
    seed: Optional[int] = None            # cambia la variante sin cambiar los datos
    # Directrices del coach: hacia dónde cargar las calorías y qué evitar.
    distribution: Optional[str] = None    # balanced | big_breakfast | big_lunch | light_dinner
    avoid: Optional[str] = None           # términos libres separados por coma


@router.post("/auto-generate", summary="Generar una dieta automáticamente", description="Construye un plan diario con los alimentos del catálogo ajustado a los objetivos de Nutrición. Sin IA ni servicios externos.")
def auto_generate(
    data: _AutoGenerateBody,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
    org: OrgContext = Depends(get_org_context),
):
    from app.core import diet_builder

    if not data.kcal or data.kcal <= 0:
        return send_error("Hace falta un objetivo de calorías para generar el plan", code=422)

    q = db.query(Aliment).filter(Aliment.calories.isnot(None))
    if org.org_id:
        q = q.filter(or_(Aliment.organization_id.is_(None), Aliment.organization_id == org.org_id))
    aliments = q.all()
    if not aliments:
        return send_error("No hay alimentos en el catálogo para construir la dieta", code=422)

    restricciones, avisos, patologias = [], [], []
    if data.client_id:
        from app.models.user import UserDetail
        detail = db.query(UserDetail).filter(UserDetail.id == data.client_id).first()
        if detail:
            restricciones = diet_builder.parse_restrictions(
                detail.allergies, detail.intolerances, detail.dislikes
            )
            patologias = [p.name for p in (detail.pathologies or [])]
            # Las patologías excluyen familias enteras de alimentos (celiaquía →
            # trigo, pan, pasta…), no solo lo que aparezca escrito en su nombre.
            restricciones += diet_builder.exclusions_for(patologias)
            avisos = diet_builder.warnings_for(patologias)
    # Lo que el coach quiera evitar solo en esta dieta, sin tocar la ficha.
    if data.avoid:
        restricciones += diet_builder.parse_restrictions(data.avoid)

    try:
        plan = diet_builder.build_diet(
            aliments=aliments, kcal=data.kcal, proteins=data.proteins,
            carbs=data.carbs, fats=data.fats, meal_count=data.meal_count,
            restrictions=restricciones, seed=data.seed,
            distribution=data.distribution,
        )
    except ValueError as e:
        return send_error(str(e), code=422)

    if not plan["meals"]:
        return send_error("No se pudo construir el plan con los alimentos disponibles", code=422)

    total = plan["totals"]["calories"]
    desvio = round((total - data.kcal) / data.kcal * 100) if data.kcal else 0

    notas = "Plan generado automáticamente a partir de tus objetivos. Revísalo y ajústalo antes de asignarlo."
    if avisos:
        # Los avisos van también en las notas para que viajen con la dieta y
        # salgan en el PDF, no solo en la pantalla de propuesta.
        notas += "\n\nAvisos por patologías:\n" + "\n".join(
            f"· {a['pathology']}: {a['text']}" for a in avisos
        )

    return send_response(
        {
            "title": f"Plan {round(data.kcal)} kcal",
            "notes": notas,
            "warnings": avisos,
            "pathologies": patologias,
            "foods": plan["meals"],
            "totals": plan["totals"],
            "target": {"calories": round(data.kcal), "deviation_pct": desvio},
        },
        "Dieta generada",
    )


@router.post("/ai-generate", summary="Generar una dieta con IA", description="Propone un plan diario con los alimentos del catálogo, ajustado a los objetivos calculados en Nutrición y a los datos del cliente.")
def ai_generate(
    data: _AIGenerateBody,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
    org: OrgContext = Depends(get_org_context),
):
    from app.core import ai_diet

    if not ai_diet.ai_enabled():
        return send_error(
            f"La generación con IA está desactivada. Actívala con AI_DIET_ENABLED=true y una "
            f"{ai_diet.key_var_name()} en las variables de entorno del servidor.",
            code=503,
        )
    if not data.kcal or data.kcal <= 0:
        return send_error("Hace falta un objetivo de calorías para generar el plan", code=422)

    # Catálogo del coach: solo alimentos con calorías, que son los que sirven.
    q = db.query(Aliment).filter(Aliment.calories.isnot(None))
    if org.org_id:
        q = q.filter(or_(Aliment.organization_id.is_(None), Aliment.organization_id == org.org_id))
    aliments = q.limit(1000).all()

    # Cuántos caben en el prompt. El tier gratuito de Groq son 12.000 tokens por
    # minuto y cada alimento ronda los 20, así que el catálogo entero no entra:
    # se recorta a un subconjunto equilibrado en vez de fallar con un 413.
    from app.config import settings

    tope = settings.GROQ_DIET_MAX_ALIMENTS if ai_diet._proveedor() == "groq" else data.max_aliments
    aliments = _pick_catalog(aliments, max(20, min(tope, 400)))
    if not aliments:
        return send_error("No hay alimentos en el catálogo para construir la dieta", code=422)

    client_ctx = _client_context(db, data.client_id) if data.client_id else {}
    target = {
        "kcal": data.kcal, "proteins": data.proteins, "carbs": data.carbs,
        "fats": data.fats, "fiber": data.fiber, "meal_count": data.meal_count,
    }

    try:
        plan = ai_diet.generate_diet(
            client=client_ctx, target=target, aliments=aliments, extra=data.notes
        )
    except Exception as e:
        return send_error(f"No se pudo generar la dieta: {e}", code=502)

    # Los totales NO se toman del modelo: se recalculan con la base de datos,
    # que es la misma fuente que usa el resto de la aplicación.
    meals, totals = [], [0.0, 0.0, 0.0, 0.0]
    for m in plan.get("meals", []):
        detail = []
        for f in m.get("foods", []):
            # El modelo responde por número de catálogo; fuera de rango se
            # descarta en vez de romper el plan.
            n = f.get("n")
            if not isinstance(n, int) or not (0 <= n < len(aliments)):
                continue
            al = aliments[n]
            grams = round(float(f.get("grams") or 0))
            if grams <= 0:
                continue
            k, p, c, g = _macros_for(al, grams)
            totals = [totals[0] + k, totals[1] + p, totals[2] + c, totals[3] + g]
            detail.append({
                "aliment_id": str(al.id), "name": al.name, "quantity_calc": grams,
                "calories": round(k), "proteins": round(p, 1),
                "carbohydrates": round(c, 1), "fats": round(g, 1),
            })
        if detail:
            meals.append({"name": m.get("name") or "Comida", "time": m.get("time"), "detail": detail})

    if not meals:
        return send_error("La IA no propuso alimentos válidos del catálogo. Inténtalo de nuevo.", code=502)

    desvio = round((totals[0] - data.kcal) / data.kcal * 100) if data.kcal else 0
    return send_response(
        {
            "title": plan.get("title") or "Plan generado con IA",
            "notes": plan.get("notes"),
            "foods": meals,
            "totals": {
                "calories": round(totals[0]), "proteins": round(totals[1], 1),
                "carbs": round(totals[2], 1), "fats": round(totals[3], 1),
            },
            "target": {"calories": round(data.kcal), "deviation_pct": desvio},
        },
        "Dieta generada",
    )


@router.get("/{id}/pdf", summary="Exportar dieta a PDF", description="Genera y descarga la dieta en formato PDF.")
def pdf(id: str, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    diet = _get_or_404(db, id)
    if not diet:
        return send_error("Dieta no encontrada")
    try:
        pdf_bytes = generate_diet_pdf(diet)
    except Exception as e:
        return send_error(f"Error generando PDF: {str(e)}", code=500)
    safe_name = (diet.title or "dieta").replace(" ", "_").lower()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.pdf"'},
    )


@router.post("/{client_id}/assigned", summary="Asignar dieta a cliente", description="Crea y asigna una dieta directamente a un cliente.")
def assigned(
    client_id: str,
    data: DietCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    from app.models.user import UserDetail
    client_detail = db.query(UserDetail).filter(UserDetail.id == client_id).first()
    if not client_detail:
        return send_error("Cliente no encontrado")

    diet = Diet(
        title=data.title,
        calories=data.calories,
        quantity=data.quantity,
        type_id=data.type_id,
        notes=data.notes,
        user_id=client_detail.user_id,
        created_user_id=current_user.id,
    )
    db.add(diet)
    db.flush()

    _save_detail(db, diet.id, data)
    _save_foods(db, diet.id, data.foods or [], current_user.id)
    _save_pathologies(db, diet.id, data.pathology_ids or [])
    db.commit()
    db.refresh(diet)
    return send_response(_serialize(diet), "Dieta asignada")


@router.get("/{id}/edit", summary="Ver dieta", description="Retorna el detalle completo de una dieta con alimentos y macros.")
def edit(id: str, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    diet = _get_or_404_with_pathologies(db, id)
    if not diet:
        return send_error("Dieta no encontrada")
    return send_response(_serialize(diet), "OK")


def _save_detail(db: Session, diet_id: str, data: DietCreate):
    detail = db.query(DietDetail).filter(DietDetail.diet_id == diet_id).first()
    detail_fields = {
        "height": data.height,
        "weight": data.weight,
        "body_fat": data.body_fat,
        "level_activity_id": data.level_activity_id,
        "objective_id": data.objective_id,
        "proteins": data.proteins,
        "carbs": data.carbs,
        "fats": data.fats,
        "fiber": data.fiber,
        "deficit": data.deficit,
        "surplus": data.surplus,
    }
    if detail:
        for f, v in detail_fields.items():
            setattr(detail, f, v)
    else:
        db.add(DietDetail(diet_id=diet_id, **detail_fields))


@router.post("", summary="Crear dieta", description="Crea una nueva dieta con sus comidas, alimentos y distribución de macros.")
def create(
    data: DietCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
    org: OrgContext = Depends(get_org_context),
):
    diet = Diet(
        title=data.title,
        calories=data.calories,
        quantity=data.quantity,
        type_id=data.type_id,
        notes=data.notes,
        user_id=current_user.id,
        created_user_id=current_user.id,
        organization_id=org.org_id,
    )
    db.add(diet)
    db.flush()

    _save_detail(db, diet.id, data)
    _save_foods(db, diet.id, data.foods or [], current_user.id)
    _save_pathologies(db, diet.id, data.pathology_ids or [])
    db.commit()
    db.refresh(diet)
    return send_response(_serialize(diet), "Dieta creada")


@router.put("/{id}/update", summary="Actualizar dieta", description="Modifica una dieta existente, incluyendo sus comidas y alimentos.")
def updated(id: str, data: DietUpdate, db: Session = Depends(get_db), current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    diet = _get_or_404(db, id)
    if not diet:
        return send_error("Dieta no encontrada")

    if data.title is not None:
        diet.title = data.title
    if data.calories is not None:
        diet.calories = data.calories
    if data.quantity is not None:
        diet.quantity = data.quantity
    if data.type_id is not None:
        diet.type_id = data.type_id
    if data.notes is not None:
        diet.notes = data.notes
    diet.updated_user_id = current_user.id

    _save_detail(db, diet.id, data)
    _save_foods(db, diet.id, data.foods or [], current_user.id)
    _save_pathologies(db, diet.id, data.pathology_ids or [])
    db.commit()
    db.refresh(diet)
    return send_response(_serialize(diet), "Dieta actualizada")


@router.delete("/{id}", summary="Eliminar dieta", description="Elimina una dieta y todas sus comidas y alimentos asociados.")
def delete(id: str, db: Session = Depends(get_db), _=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH))):
    diet = _get_or_404(db, id)
    if not diet:
        return send_error("Dieta no encontrada")
    # Detach delivery records so the FK doesn't block the delete (history is kept)
    from app.models.plan import PlanDelivery
    db.query(PlanDelivery).filter(PlanDelivery.diet_id == id).update({"diet_id": None})
    db.delete(diet)
    db.commit()
    return send_response(None, "Dieta eliminada")


class _AssignBody(DietCreate):
    client_id: str
    title: str = ""


def copy_diet_to_user(db: Session, source: Diet, target_user_id: int, created_user_id: int) -> Diet:
    """Copia una dieta (detalle + comidas) al usuario destino. No hace commit."""
    new_diet = Diet(
        title=source.title,
        calories=source.calories,
        quantity=source.quantity,
        type_id=source.type_id,
        user_id=target_user_id,
        created_user_id=created_user_id,
    )
    db.add(new_diet)
    db.flush()

    if source.detail:
        d = source.detail
        db.add(DietDetail(
            diet_id=new_diet.id,
            proteins=d.proteins, carbs=d.carbs, fats=d.fats, fiber=d.fiber,
            deficit=d.deficit, surplus=d.surplus,
            height=d.height, weight=d.weight, body_fat=d.body_fat,
            level_activity_id=d.level_activity_id, objective_id=d.objective_id,
        ))

    foods_data = [
        DietFoodCreate(
            name=food.name,
            time=food.time,
            detail=[
                DietFoodAlimentCreate(
                    aliment_id=dfa.aliment_id,
                    quantity_calc=dfa.quantity,
                    order=dfa.order,
                )
                for dfa in food.detail
            ],
        )
        for food in source.foods
    ]
    _save_foods(db, new_diet.id, foods_data, created_user_id)
    return new_diet


@router.post("/{id}/assign", summary="Asignar dieta existente a cliente", description="Copia una dieta del catálogo del coach al cliente especificado.")
def assign_to_client(
    id: str,
    body: _AssignBody,
    db: Session = Depends(get_db),
    current_user=Depends(require_role_ids(SUPERADMIN, ADMIN, COACH)),
):
    from app.models.user import UserDetail
    source = _get_or_404(db, id)
    if not source:
        return send_error("Dieta no encontrada")
    client_detail = db.query(UserDetail).filter(UserDetail.id == body.client_id).first()
    if not client_detail:
        return send_error("Cliente no encontrado")

    new_diet = copy_diet_to_user(db, source, client_detail.user_id, current_user.id)
    db.commit()
    db.refresh(new_diet)
    return send_response(_serialize(new_diet), "Dieta asignada al cliente")
