"""initial schema

Revision ID: bb298e505f5b
Revises:
Create Date: 2026-05-14 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "bb298e505f5b"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- No FK dependencies ---
    op.create_table(
        "countries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(10), nullable=False, unique=True),
        sa.Column("country", sa.String(150), nullable=False),
    )
    op.create_table(
        "parameters",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("description", sa.String(255), nullable=False),
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("slug", sa.String(100), nullable=True, unique=True),
    )
    op.create_table(
        "menus",
        sa.Column("menuId", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("menuParentId", sa.Integer, sa.ForeignKey("menus.menuId"), nullable=True),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("path", sa.String(200), nullable=True),
    )
    op.create_table(
        "muscle_groups",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("image", sa.String(500), nullable=True),
        sa.Column("state", sa.Integer, default=1),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "group_foods",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("status", sa.Integer, default=1),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "type_foods",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("status", sa.Integer, default=1),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "type_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("color", sa.String(50), nullable=True),
        sa.Column("state", sa.Integer, default=1),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # --- Depend on: roles, menus ---
    op.create_table(
        "menu_role",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("menu_id", sa.Integer, sa.ForeignKey("menus.menuId"), nullable=False),
    )

    # --- Depend on: parameters ---
    op.create_table(
        "parameter_details",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("parameter_id", sa.Integer, sa.ForeignKey("parameters.id"), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("value_1", sa.String(100), nullable=True),
        sa.Column("value_1_description", sa.String(100), nullable=True),
    )

    # --- Core: users (no FKs) ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("email_verified_at", sa.DateTime, nullable=True),
        sa.Column("password", sa.String(255), nullable=False),
        sa.Column("remember_token", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # --- Depend on: roles, users ---
    op.create_table(
        "role_user",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
    )

    # --- Depend on: users, parameter_details, countries ---
    op.create_table(
        "user_details",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("last_name", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("height", sa.Float, nullable=True),
        sa.Column("weight", sa.Float, nullable=True),
        sa.Column("occupation", sa.String(255), nullable=True),
        sa.Column("country_code", sa.String(10), sa.ForeignKey("countries.code"), nullable=True),
        sa.Column("gender_id", sa.Integer, sa.ForeignKey("parameter_details.id"), nullable=True),
        sa.Column("activity_id", sa.Integer, sa.ForeignKey("parameter_details.id"), nullable=True),
        sa.Column("status_id", sa.Integer, sa.ForeignKey("parameter_details.id"), nullable=True),
        sa.Column("objective_id", sa.Integer, sa.ForeignKey("parameter_details.id"), nullable=True),
        sa.Column("start_date", sa.DateTime, nullable=True),
        sa.Column("end_date", sa.DateTime, nullable=True),
        sa.Column("defecit", sa.Float, nullable=True),
        sa.Column("excedente", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # --- Depend on: user_details ---
    op.create_table(
        "user_parents",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_detail_id", sa.String(36), sa.ForeignKey("user_details.id"), nullable=False),
        sa.Column("parent_user_detail_id", sa.String(36), sa.ForeignKey("user_details.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # --- Depend on: users ---
    op.create_table(
        "client_targets",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("target_weight", sa.Float, nullable=True),
        sa.Column("target_body_fat", sa.Float, nullable=True),
        sa.Column("target_muscle_mass", sa.Float, nullable=True),
        sa.Column("calories", sa.Float, nullable=True),
        sa.Column("proteins", sa.Float, nullable=True),
        sa.Column("carbs", sa.Float, nullable=True),
        sa.Column("fats", sa.Float, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "event_users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type_event_id", sa.Integer, sa.ForeignKey("type_events.id"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("start_date", sa.DateTime, nullable=False),
        sa.Column("end_date", sa.DateTime, nullable=True),
        sa.Column("all_day", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "template_notes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("instructor_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("state", sa.Integer, default=1),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "note_users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("instructor_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("template_note_id", sa.Integer, sa.ForeignKey("template_notes.id"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("state", sa.Integer, default=1),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "progress_day_users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("weight", sa.Float, nullable=True),
        sa.Column("body_fat", sa.Float, nullable=True),
        sa.Column("muscle_mass", sa.Float, nullable=True),
        sa.Column("waist", sa.Float, nullable=True),
        sa.Column("hip", sa.Float, nullable=True),
        sa.Column("chest", sa.Float, nullable=True),
        sa.Column("arm", sa.Float, nullable=True),
        sa.Column("thigh", sa.Float, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("photo", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # --- Depend on: muscle_groups ---
    op.create_table(
        "trainings",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("muscle_group_id", sa.Integer, sa.ForeignKey("muscle_groups.id"), nullable=True),
        sa.Column("image", sa.String(500), nullable=True),
        sa.Column("video_url", sa.String(500), nullable=True),
        sa.Column("state", sa.Integer, default=1),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "muscle_group_clients",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("muscle_group_id", sa.Integer, sa.ForeignKey("muscle_groups.id"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    # --- Depend on: trainings, users ---
    op.create_table(
        "training_clients",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("training_id", sa.Integer, sa.ForeignKey("trainings.id"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    # --- Depend on: users, parameter_details ---
    op.create_table(
        "routines",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("gender_id", sa.Integer, sa.ForeignKey("parameter_details.id"), nullable=True),
        sa.Column("training", sa.String(255), nullable=True),
        sa.Column("training_level_id", sa.Integer, sa.ForeignKey("parameter_details.id"), nullable=True),
        sa.Column("time", sa.Integer, nullable=True),
        sa.Column("days", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # --- Depend on: routines ---
    op.create_table(
        "routine_days",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("routine_id", sa.Integer, sa.ForeignKey("routines.id"), nullable=False),
        sa.Column("day_name", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # --- Depend on: routines, routine_days, muscle_groups, trainings ---
    op.create_table(
        "routine_day_details",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("routine_id", sa.Integer, sa.ForeignKey("routines.id"), nullable=False),
        sa.Column("routine_day_id", sa.Integer, sa.ForeignKey("routine_days.id"), nullable=False),
        sa.Column("muscle_group_id", sa.Integer, sa.ForeignKey("muscle_groups.id"), nullable=True),
        sa.Column("training_id", sa.Integer, sa.ForeignKey("trainings.id"), nullable=True),
        sa.Column("series", sa.Integer, nullable=True),
        sa.Column("repetitions", sa.String(50), nullable=True),
        sa.Column("break_time", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # --- Nutrition: aliments (self-ref parent_id) ---
    op.create_table(
        "aliments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("group_food_id", sa.Integer, sa.ForeignKey("group_foods.id"), nullable=True),
        sa.Column("brand", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Float, nullable=True),
        sa.Column("quantity_type_id", sa.Integer, sa.ForeignKey("parameter_details.id"), nullable=True),
        sa.Column("proteins", sa.Float, nullable=True),
        sa.Column("carbohydrates", sa.Float, nullable=True),
        sa.Column("fats", sa.Float, nullable=True),
        sa.Column("calories", sa.Float, nullable=True),
        sa.Column("comments", sa.Text, nullable=True),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("aliments.id"), nullable=True),
        sa.Column("created_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # --- Depend on: aliments ---
    op.create_table(
        "aliment_descriptions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("aliment_id", sa.String(36), sa.ForeignKey("aliments.id"), nullable=False),
        sa.Column("vita", sa.Float, nullable=True),
        sa.Column("vitb1", sa.Float, nullable=True),
        sa.Column("vitb2", sa.Float, nullable=True),
        sa.Column("vitb3", sa.Float, nullable=True),
        sa.Column("vitb5", sa.Float, nullable=True),
        sa.Column("vitb6", sa.Float, nullable=True),
        sa.Column("vitb9", sa.Float, nullable=True),
        sa.Column("vitb12", sa.Float, nullable=True),
        sa.Column("vitc", sa.Float, nullable=True),
        sa.Column("vitd", sa.Float, nullable=True),
        sa.Column("vite", sa.Float, nullable=True),
        sa.Column("vitk", sa.Float, nullable=True),
        sa.Column("calina", sa.Float, nullable=True),
        sa.Column("calcium", sa.Float, nullable=True),
        sa.Column("copper", sa.Float, nullable=True),
        sa.Column("iron", sa.Float, nullable=True),
        sa.Column("magnesium", sa.Float, nullable=True),
        sa.Column("manganese", sa.Float, nullable=True),
        sa.Column("phosphorus", sa.Float, nullable=True),
        sa.Column("potassium", sa.Float, nullable=True),
        sa.Column("selenium", sa.Float, nullable=True),
        sa.Column("sodium", sa.Float, nullable=True),
        sa.Column("zinc", sa.Float, nullable=True),
        sa.Column("water", sa.Float, nullable=True),
        sa.Column("fiber", sa.Float, nullable=True),
        sa.Column("cholesterol", sa.Float, nullable=True),
        sa.Column("saturated_fats", sa.Float, nullable=True),
        sa.Column("mono_saturated_fats", sa.Float, nullable=True),
        sa.Column("poli_saturated_fats", sa.Float, nullable=True),
        sa.Column("glycemic_index", sa.Float, nullable=True),
    )

    # --- Depend on: type_foods, users ---
    op.create_table(
        "diets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("calories", sa.Float, nullable=True),
        sa.Column("quantity", sa.Float, nullable=True),
        sa.Column("type_id", sa.Integer, sa.ForeignKey("type_foods.id"), nullable=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # --- Depend on: diets, parameter_details ---
    op.create_table(
        "diet_details",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("diet_id", sa.String(36), sa.ForeignKey("diets.id"), nullable=False),
        sa.Column("gender_id", sa.Integer, sa.ForeignKey("parameter_details.id"), nullable=True),
        sa.Column("age", sa.Integer, nullable=True),
        sa.Column("height", sa.Float, nullable=True),
        sa.Column("weight", sa.Float, nullable=True),
        sa.Column("body_fat", sa.Float, nullable=True),
        sa.Column("level_activity_id", sa.Integer, sa.ForeignKey("parameter_details.id"), nullable=True),
        sa.Column("objective_id", sa.Integer, sa.ForeignKey("parameter_details.id"), nullable=True),
        sa.Column("proteins", sa.Float, nullable=True),
        sa.Column("carbs", sa.Float, nullable=True),
        sa.Column("fats", sa.Float, nullable=True),
        sa.Column("deficit", sa.Float, nullable=True),
        sa.Column("surplus", sa.Float, nullable=True),
    )

    # --- Depend on: diets ---
    op.create_table(
        "diet_foods",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("diet_id", sa.String(36), sa.ForeignKey("diets.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # --- Depend on: diets, diet_foods, aliments ---
    op.create_table(
        "diet_food_aliments",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("diet_id", sa.String(36), sa.ForeignKey("diets.id"), nullable=False),
        sa.Column("diet_food_id", sa.Integer, sa.ForeignKey("diet_foods.id"), nullable=False),
        sa.Column("aliment_id", sa.String(36), sa.ForeignKey("aliments.id"), nullable=False),
        sa.Column("quantity", sa.Float, nullable=True),
        sa.Column("order", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # --- Depend on: users, parameter_details ---
    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("instructions", sa.Text, nullable=True),
        sa.Column("instructor_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("category_id", sa.Integer, sa.ForeignKey("parameter_details.id"), nullable=True),
        sa.Column("calories", sa.Float, nullable=True),
        sa.Column("proteins", sa.Float, nullable=True),
        sa.Column("carbs", sa.Float, nullable=True),
        sa.Column("fats", sa.Float, nullable=True),
        sa.Column("servings", sa.Integer, nullable=True),
        sa.Column("prep_time", sa.Integer, nullable=True),
        sa.Column("image", sa.String(500), nullable=True),
        sa.Column("state", sa.Integer, default=1),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # --- Depend on: recipes, aliments, parameter_details ---
    op.create_table(
        "recipe_details",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("recipe_id", sa.Integer, sa.ForeignKey("recipes.id"), nullable=False),
        sa.Column("aliment_id", sa.String(36), sa.ForeignKey("aliments.id"), nullable=False),
        sa.Column("quantity", sa.Float, nullable=True),
        sa.Column("unit_id", sa.Integer, sa.ForeignKey("parameter_details.id"), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("order", sa.Integer, default=0),
    )


def downgrade() -> None:
    op.drop_table("recipe_details")
    op.drop_table("recipes")
    op.drop_table("diet_food_aliments")
    op.drop_table("diet_foods")
    op.drop_table("diet_details")
    op.drop_table("diets")
    op.drop_table("aliment_descriptions")
    op.drop_table("aliments")
    op.drop_table("routine_day_details")
    op.drop_table("routine_days")
    op.drop_table("routines")
    op.drop_table("training_clients")
    op.drop_table("muscle_group_clients")
    op.drop_table("trainings")
    op.drop_table("progress_day_users")
    op.drop_table("note_users")
    op.drop_table("template_notes")
    op.drop_table("event_users")
    op.drop_table("client_targets")
    op.drop_table("user_parents")
    op.drop_table("user_details")
    op.drop_table("role_user")
    op.drop_table("users")
    op.drop_table("parameter_details")
    op.drop_table("menu_role")
    op.drop_table("parameters")
    op.drop_table("menus")
    op.drop_table("roles")
    op.drop_table("type_events")
    op.drop_table("type_foods")
    op.drop_table("group_foods")
    op.drop_table("muscle_groups")
    op.drop_table("countries")
