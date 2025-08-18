"""
Database Upgrade Workflow Functions
Orchestrates the table creation process during migration upgrade
"""

from app.alembic.migrations_helpers.apex_tables import (
    _create_apex_reports, _create_apex_runs, _add_apex_runs_cols, 
    _add_apex_reports_idx, _add_apex_runs_idx
)
from app.alembic.migrations_helpers.user_auth_tables import (
    _create_users, _add_users_cols, _add_users_indexes,
    _create_secrets, _add_secrets_final
)
from app.alembic.migrations_helpers.agent_tables import (
    _create_assistants, _add_assistants_cols, _add_assistants_final_cols,
    _create_threads, _create_runs, _add_runs_cols1, _add_runs_cols2, 
    _add_runs_cols3, _add_runs_final, _create_messages, _add_messages_cols,
    _add_messages_final, _add_messages_thread_fk, _create_steps,
    _add_steps_cols1, _add_steps_cols2, _add_steps_cols3, _add_steps_fks
)
from app.alembic.migrations_helpers.analysis_tables import (
    _create_analyses, _add_analyses_cols, _create_analysis_results, 
    _add_analysis_results_fk, _create_corpora, _add_corpora_cols, 
    _add_analyses_index, _add_corpora_final
)
from app.alembic.migrations_helpers.supply_tables import (
    _create_supplies, _add_supplies_final, _create_supply_options, 
    _add_supply_options_cols, _add_supply_options_final, _create_references, 
    _add_references_cols, _add_references_final_cols
)


def create_user_tables() -> None:
    """Create user-related tables."""
    _create_users()
    _add_users_cols()
    _add_users_indexes()
    _create_secrets()
    _add_secrets_final()


def _create_assistant_structures() -> None:
    """Create assistant table structures."""
    _create_assistants()
    _add_assistants_cols()
    _add_assistants_final_cols()

def create_agent_tables() -> None:
    """Create agent and AI-related tables."""
    _create_assistant_structures()
    _create_threads()
    _create_runs()
    create_agent_runs_extended()


def _add_agent_runs_columns() -> None:
    """Add agent runs columns."""
    _add_runs_cols1()
    _add_runs_cols2()
    _add_runs_cols3()
    _add_runs_final()

def create_agent_runs_extended() -> None:
    """Create extended agent runs."""
    _add_agent_runs_columns()
    _create_messages()
    create_messages_extended()


def _add_message_columns() -> None:
    """Add message columns."""
    _add_messages_cols()
    _add_messages_final()
    _add_messages_thread_fk()

def create_messages_extended() -> None:
    """Create extended message tables."""
    _add_message_columns()
    _create_steps()
    create_steps_extended()


def create_steps_extended() -> None:
    """Create extended step tables."""
    _add_steps_cols1()
    _add_steps_cols2()
    _add_steps_cols3()


def create_metric_tables() -> None:
    """Create metric and analysis tables."""
    _create_apex_reports()
    _create_apex_runs()
    _add_apex_runs_cols()
    _create_analyses()
    create_analysis_extended()


def _create_analysis_components() -> None:
    """Create analysis components."""
    _add_analyses_cols()
    _create_analysis_results()
    _add_analysis_results_fk()

def create_analysis_extended() -> None:
    """Create extended analysis tables."""
    _create_analysis_components()
    _create_corpora()
    create_supply_tables()


def create_supply_tables() -> None:
    """Create supply-related tables."""
    _add_corpora_cols()
    _create_supplies()
    _add_supplies_final()
    _create_supply_options()
    create_supply_options_extended()


def _create_supply_options_components() -> None:
    """Create supply options components."""
    _add_supply_options_cols()
    _add_supply_options_final()

def _create_references_components() -> None:
    """Create references components."""
    _create_references()
    _add_references_cols()
    _add_references_final_cols()

def create_supply_options_extended() -> None:
    """Create extended supply options."""
    _create_supply_options_components()
    _create_references_components()


def create_index_definitions() -> None:
    """Create all index definitions."""
    _add_apex_reports_idx()
    _add_apex_runs_idx()
    _add_analyses_index()


def add_foreign_keys() -> None:
    """Add foreign key constraints."""
    _add_steps_fks()


def add_constraints() -> None:
    """Add additional constraints."""
    _add_corpora_final()


def _create_core_structures() -> None:
    """Create core database structures."""
    create_user_tables()
    create_agent_tables()
    create_metric_tables()

def _add_relationships() -> None:
    """Add relationships and constraints."""
    create_index_definitions()
    add_foreign_keys()
    add_constraints()

def upgrade() -> None:
    """Upgrade schema with organized table creation."""
    _create_core_structures()
    _add_relationships()