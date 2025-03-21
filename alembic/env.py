from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
from sqlalchemy import create_engine
# Import your Base model to enable autogeneration
from database import Base, engine  

DATABASE_URL = os.getenv("DATABASE_URL")  # Get from .env
engine = create_engine(DATABASE_URL)  # Fix engine creation
# Alembic configuration
config = context.config

# Configure logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Ensure Alembic knows about your models
target_metadata = Base.metadata  # ✅ Fix: Assign correct metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
