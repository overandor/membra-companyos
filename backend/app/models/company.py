"""MEMBRA CompanyOS — CompanyOS models."""
from sqlalchemy import Column, String, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, ULIDMixin


class Company(Base, ULIDMixin):
    """An operating company or unit within MEMBRA."""

    name = Column(String(255), nullable=False)
    slug = Column(String(128), unique=True, nullable=False, index=True)
    description = Column(Text)
    status = Column(String(32), default="active", index=True)  # active, suspended, dissolved
    owner_wallet = Column(String(64), index=True)
    metadata_json = Column(JSON, default=dict)

    departments = relationship("Department", back_populates="company", lazy="selectin")
    agents = relationship("Agent", back_populates="company", lazy="selectin")
    objectives = relationship("Objective", back_populates="company", lazy="selectin")
    jobs = relationship("Job", back_populates="company", lazy="selectin")
    governance_policies = relationship("GovernancePolicy", back_populates="company", lazy="selectin")
    kpi_records = relationship("KPIRecord", back_populates="company", lazy="selectin")


class Department(Base, ULIDMixin):
    """Department within a company."""

    company_id = Column(String(26), ForeignKey("companies.id"), index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text)
    sop_json = Column(JSON, default=dict)  # Standard Operating Procedures
    metrics_json = Column(JSON, default=dict)
    status = Column(String(32), default="active")

    company = relationship("Company", back_populates="departments")
    agents = relationship("Agent", back_populates="department", lazy="selectin")


class KPIRecord(Base, ULIDMixin):
    """KPI snapshot for a company or department."""

    company_id = Column(String(26), ForeignKey("companies.id"), index=True)
    department_id = Column(String(26), ForeignKey("departments.id"), index=True, nullable=True)
    kpi_name = Column(String(128), nullable=False, index=True)
    kpi_value = Column(String(128))
    unit = Column(String(32))
    period_start = Column(String(64))
    period_end = Column(String(64))
    metadata_json = Column(JSON, default=dict)

    company = relationship("Company", back_populates="kpi_records")
