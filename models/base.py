"""SQLAlchemy base class and mixins."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, relationship


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class."""

    pass


class ModifyModel:
    """Mixin for audit trail columns (created/updated timestamps and user references).

    All new tables should inherit from this mixin to track creation and modification.
    The created_by and updated_by columns reference the public.employee table.
    """

    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    @declared_attr
    def created_by(cls) -> Mapped[int | None]:
        """User ID who created the record."""
        return Column(
            Integer,
            ForeignKey("public.employee.id"),
            nullable=True,
        )

    @declared_attr
    def updated_by(cls) -> Mapped[int | None]:
        """User ID who last updated the record."""
        return Column(
            Integer,
            ForeignKey("public.employee.id"),
            nullable=True,
        )

    @declared_attr
    def creator(cls):
        """Relationship to the creator Employee."""
        return relationship(
            "Employee",
            foreign_keys=[cls.created_by],
            lazy="select",
        )

    @declared_attr
    def updater(cls):
        """Relationship to the updater Employee."""
        return relationship(
            "Employee",
            foreign_keys=[cls.updated_by],
            lazy="select",
        )
