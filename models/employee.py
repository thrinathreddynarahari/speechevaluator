"""Legacy Employee model in public schema.

This model represents the existing public.employee table.
DO NOT modify this table through migrations - it is managed externally.
"""

from sqlalchemy import BigInteger, Boolean, Column, Date, String, Text

from models.base import Base


class Employee(Base):
    """Employee model mapping to the public.employee table.

    This is a legacy/existing table. Migrations must not create, alter, or drop this table.
    """

    __tablename__ = "employee"
    __table_args__ = {"schema": "public"}

    id = Column(BigInteger, primary_key=True, index=True)
    employeename = Column(String(255), nullable=False)
    email = Column(Text, unique=True, nullable=False)
    doj = Column(Date)
    jobtitle = Column(Text)
    department = Column(String(255))
    reportsto = Column(Text)
    isactive = Column(Boolean, default=True)
    newreportinghead = Column(Text)
