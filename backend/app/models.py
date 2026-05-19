from sqlalchemy import (
    Column, Integer, String, Date, ForeignKey, UniqueConstraint, Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from .database import Base


class Seiyuu(Base):
    __tablename__ = "seiyuu"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name_zh = Column(String(100))
    name_ja = Column(String(100))
    name_romaji = Column(String(150))
    gender = Column(String(1))
    birth_date = Column(Date)
    blood_type = Column(String(5))
    height_cm = Column(Integer)
    agency = Column(String(200))
    debut_year = Column(Integer)
    image_url = Column(String(500))
    bangumi_id = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    roles = relationship("Role", back_populates="seiyuu", lazy="selectin")


class Work(Base):
    __tablename__ = "work"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title_zh = Column(String(300))
    title_ja = Column(String(300))
    type = Column(String(20))
    premiere_year = Column(Integer)
    episodes = Column(Integer)
    studio = Column(String(200))
    image_url = Column(String(500))
    bangumi_id = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    roles = relationship("Role", back_populates="work", lazy="selectin")


class Role(Base):
    __tablename__ = "role"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seiyuu_id = Column(Integer, ForeignKey("seiyuu.id", ondelete="CASCADE"), nullable=False)
    work_id = Column(Integer, ForeignKey("work.id", ondelete="CASCADE"), nullable=False)
    character_name = Column(String(200))

    seiyuu = relationship("Seiyuu", back_populates="roles")
    work = relationship("Work", back_populates="roles")

    __table_args__ = (
        UniqueConstraint("seiyuu_id", "work_id", "character_name"),
    )


class CoAppearance(Base):
    __tablename__ = "co_appearance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seiyuu_a_id = Column(Integer, ForeignKey("seiyuu.id", ondelete="CASCADE"), nullable=False)
    seiyuu_b_id = Column(Integer, ForeignKey("seiyuu.id", ondelete="CASCADE"), nullable=False)
    work_count = Column(Integer, default=1)
    shared_work_ids = Column(Text)  # JSON array, e.g. "[1,2,3]"

    seiyuu_a = relationship("Seiyuu", foreign_keys=[seiyuu_a_id])
    seiyuu_b = relationship("Seiyuu", foreign_keys=[seiyuu_b_id])

    __table_args__ = (
        UniqueConstraint("seiyuu_a_id", "seiyuu_b_id"),
    )
