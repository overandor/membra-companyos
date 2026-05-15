"""MEMBRA CompanyOS — Base model with ULID primary keys."""
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Index, func
from sqlalchemy.orm import declarative_base, declared_attr
import ulid

Base = declarative_base()


class ULIDMixin:
    """Mixin providing ULID primary keys and timestamps."""

    @declared_attr.directive
    def __tablename__(cls):
        return cls.__name__.lower() + "s"

    id = Column(String(26), primary_key=True, default=lambda: str(ulid.new()))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    @property
    def ulid_timestamp(self) -> datetime:
        return ulid.parse(self.id).timestamp().datetime
