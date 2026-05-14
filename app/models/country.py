from sqlalchemy import Column, Integer, String
from app.database import Base


class Country(Base):
    __tablename__ = "countries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, unique=True)
    country = Column(String(150), nullable=False)
