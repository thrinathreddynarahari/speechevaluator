"""Initial evaluation schema and tables

Revision ID: 001_initial
Revises: 
Create Date: 2026-01-02

This migration:
1. Creates the 'evaluation' schema if it does not exist
2. Creates the employee_evaluation table
3. Creates the employee_evaluation_reports table
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create evaluation schema
    op.execute("CREATE SCHEMA IF NOT EXISTS evaluation")

    # Create employee_evaluation table
    op.create_table(
        "employee_evaluation",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["public.employee.id"],
            name="fk_employee_evaluation_employee_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["public.employee.id"],
            name="fk_employee_evaluation_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["public.employee.id"],
            name="fk_employee_evaluation_updated_by",
        ),
        sa.UniqueConstraint("employee_id", name="uq_employee_evaluation_employee_id"),
        schema="evaluation",
    )

    # Create employee_evaluation_reports table
    op.create_table(
        "employee_evaluation_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_evaluation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["employee_evaluation_id"],
            ["evaluation.employee_evaluation.id"],
            name="fk_employee_evaluation_reports_evaluation_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["public.employee.id"],
            name="fk_employee_evaluation_reports_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["public.employee.id"],
            name="fk_employee_evaluation_reports_updated_by",
        ),
        schema="evaluation",
    )

    # Create indexes for common queries
    op.create_index(
        "ix_employee_evaluation_employee_id",
        "employee_evaluation",
        ["employee_id"],
        schema="evaluation",
    )
    op.create_index(
        "ix_employee_evaluation_reports_evaluation_id",
        "employee_evaluation_reports",
        ["employee_evaluation_id"],
        schema="evaluation",
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index(
        "ix_employee_evaluation_reports_evaluation_id",
        table_name="employee_evaluation_reports",
        schema="evaluation",
    )
    op.drop_index(
        "ix_employee_evaluation_employee_id",
        table_name="employee_evaluation",
        schema="evaluation",
    )

    # Drop tables
    op.drop_table("employee_evaluation_reports", schema="evaluation")
    op.drop_table("employee_evaluation", schema="evaluation")

    # Drop schema (optional - uncomment if you want full cleanup)
    # op.execute("DROP SCHEMA IF EXISTS evaluation CASCADE")
