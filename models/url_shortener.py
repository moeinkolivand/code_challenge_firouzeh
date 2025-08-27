from sqlalchemy import Column, String, Text, Index, Integer
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

Base = declarative_base()


class UrlShorter(Base):
    __tablename__ = "url_shorters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_url = Column(String(2048), index=True, nullable=False)
    shorted_url = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_url_shorter_original_url", "original_url"),
    )
