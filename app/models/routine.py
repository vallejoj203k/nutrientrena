from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Routine(Base):
    __tablename__ = "routines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    gender_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    training = Column(String(255), nullable=True)
    training_level_id = Column(Integer, ForeignKey("parameter_details.id"), nullable=True)
    time = Column(Integer, nullable=True)
    days = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")
    gender = relationship("ParameterDetail", foreign_keys=[gender_id])
    training_level = relationship("ParameterDetail", foreign_keys=[training_level_id])
    days_list = relationship("RoutineDay", back_populates="routine",
                             cascade="all, delete-orphan", order_by="RoutineDay.id")


class RoutineBlock(Base):
    __tablename__ = "routine_blocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    routine_id = Column(Integer, ForeignKey("routines.id"), nullable=False)
    routine_day_id = Column(Integer, ForeignKey("routine_days.id"), nullable=False)
    block_type = Column(String(20), default="normal")  # warmup/normal/superset/circuit/text
    content = Column(Text, nullable=True)  # free text for 'text' blocks
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    routine_day = relationship("RoutineDay", back_populates="blocks")
    exercises = relationship("RoutineDayDetail", back_populates="block",
                             cascade="all, delete-orphan", order_by="RoutineDayDetail.order_index")


class RoutineDay(Base):
    __tablename__ = "routine_days"

    id = Column(Integer, primary_key=True, autoincrement=True)
    routine_id = Column(Integer, ForeignKey("routines.id"), nullable=False)
    day_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    routine = relationship("Routine", back_populates="days_list")
    blocks = relationship("RoutineBlock", back_populates="routine_day",
                          cascade="all, delete-orphan", order_by="RoutineBlock.order_index")
    details = relationship("RoutineDayDetail",
                           primaryjoin="and_(RoutineDayDetail.routine_day_id==RoutineDay.id, RoutineDayDetail.block_id==None)",
                           foreign_keys="RoutineDayDetail.routine_day_id",
                           order_by="RoutineDayDetail.id",
                           viewonly=True)


class RoutineDayDetail(Base):
    __tablename__ = "routine_day_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    routine_id = Column(Integer, ForeignKey("routines.id"), nullable=False)
    routine_day_id = Column(Integer, ForeignKey("routine_days.id"), nullable=False)
    block_id = Column(Integer, ForeignKey("routine_blocks.id"), nullable=True)
    muscle_group_id = Column(Integer, ForeignKey("muscle_groups.id"), nullable=True)
    training_id = Column(Integer, ForeignKey("trainings.id"), nullable=True)
    series = Column(Integer, nullable=True)
    repetitions = Column(String(50), nullable=True)
    break_time = Column(Integer, nullable=True)
    intensity_type = Column(String(20), nullable=True)  # rpe/rir/pct1rm/weight
    intensity_value = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    routine_day = relationship("RoutineDay", foreign_keys=[routine_day_id])
    block = relationship("RoutineBlock", back_populates="exercises")
    training = relationship("Training")
    muscle_group = relationship("MuscleGroup")
