from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Parameter(Base):
    __tablename__ = "parameters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(String(255), nullable=False)

    details = relationship("ParameterDetail", back_populates="parameter")


class ParameterDetail(Base):
    __tablename__ = "parameter_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    parameter_id = Column(Integer, ForeignKey("parameters.id"), nullable=False)
    description = Column(String(255), nullable=False)
    value_1 = Column(String(100), nullable=True)
    value_1_description = Column(String(100), nullable=True)

    parameter = relationship("Parameter", back_populates="details")
