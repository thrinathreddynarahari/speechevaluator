"""Alembic environment configuration.

This module configures Alembic to:
1. Only manage tables in the 'evaluation' schema
2. Store alembic_version table in 'evaluation' schema
3. Exclude all tables in 'public' schema (especially Employee)
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

# Add the project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings
from models.base import Base

# Import all models to ensure they are registered with Base.metadata
from models.evaluation import EmployeeEvaluation, EmployeeEvaluationReports  # noqa: F401

# Alembic Config object
config = context.config

# Setup logging from config file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the SQLAlchemy URL from settings
config.set_main_option("sqlalchemy.url", settings.database_url)

# Target metadata for autogenerate
target_metadata = Base.metadata


def include_object(
    obj,
    name: str,
    type_: str,
    reflected: bool,
    compare_to,
) -> bool:
    """Filter function to include only objects in the 'evaluation' schema.

    This ensures that:
    - Only tables in 'evaluation' schema are managed
    - Tables in 'public' schema (like Employee) are never touched
    - alembic_version table is correctly placed in evaluation schema
    """
    # Always exclude objects from public schema
    if hasattr(obj, "schema"):
        schema = obj.schema
        if schema == "public":
            return False
        if schema == "evaluation":
            return True
        # If schema is None, check if it's one of our evaluation tables
        return False

    # For table objects, check the schema
    if type_ == "table":
        schema = getattr(obj, "schema", None)
        if schema == "public":
            return False
        if schema == "evaluation":
            return True
        return False

    # For other objects (indexes, constraints), include if parent table is in evaluation
    if hasattr(obj, "table") and obj.table is not None:
        table_schema = getattr(obj.table, "schema", None)
        if table_schema == "public":
            return False
        if table_schema == "evaluation":
            return True

    # Default: include objects that are in evaluation schema
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates SQL script without database connection.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_object=include_object,
        version_table_schema="evaluation",
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates database connection and runs migrations.
    """
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_object=include_object,
            version_table_schema="evaluation",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
