from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


# Las mismas patologías que las dietas: un solo catálogo, no dos listas
# parecidas que acaban diciendo cosas distintas.
recipe_pathologies_table = Table(
    'recipe_pathologies', Base.metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('recipe_id', Integer, ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False),
    Column('pathology_id', Integer, ForeignKey('pathologies.id', ondelete='CASCADE'), nullable=False),
)


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    categories = Column(String(255), nullable=True)  # ids de tipo de dieta separados por coma (multi)
    calories = Column(Float, nullable=True)
    proteins = Column(Float, nullable=True)
    carbs = Column(Float, nullable=True)
    fats = Column(Float, nullable=True)
    servings = Column(Integer, nullable=True)
    prep_time = Column(Integer, nullable=True)
    image = Column(String(500), nullable=True)
    meal_type = Column(String(100), nullable=True)
    # Etiquetas libres ("Alta proteína", "Meal prep"...) y notas del
    # nutricionista, separadas de la preparación: una cosa son los pasos y otra
    # las variaciones y sustituciones.
    tags = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    difficulty = Column(String(20), nullable=True)
    # Lo clínico: qué alérgenos NO lleva, a qué estilo pertenece y cómo queda
    # de índice glucémico, sodio y fibra.
    allergen_free = Column(String(500), nullable=True)
    diet_styles = Column(String(500), nullable=True)
    glycemic_index = Column(String(20), nullable=True)
    sodium_level = Column(String(20), nullable=True)
    fiber = Column(Float, nullable=True)
    state = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    instructor = relationship("User")
    category = relationship("ParameterDetail", foreign_keys=[category_id])
    details = relationship("RecipeDetail", back_populates="recipe", cascade="all, delete-orphan")
    pathologies = relationship("Pathology", secondary=recipe_pathologies_table, lazy="noload")


class RecipeDetail(Base):
    __tablename__ = "recipe_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    aliment_id = Column(String(36), ForeignKey("aliments.id"), nullable=False)
    quantity = Column(Float, nullable=True)
    unit_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    notes = Column(Text, nullable=True)
    order = Column(Integer, default=0)

    recipe = relationship("Recipe", back_populates="details")
    aliment = relationship("Aliment", back_populates="recipe_details")
    unit = relationship("ParameterDetail", foreign_keys=[unit_id])
