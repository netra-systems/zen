"""
Database Upgrade Workflow Functions
Orchestrates the table creation process during migration upgrade
"""

from .apex_tables import (
    _create_apex_reports, _create_apex_runs, _add_apex_runs_cols, 
    _add_apex_reports_idx, _add_apex_runs_idx
)
from .user_auth_tables import (
    _create_users, _add_users_cols, _add_users_indexes,
    _create_secrets, _add_secrets_final
)
from .agent_tables import (
    _create_assistants, _add_assistants_cols, _add_assistants_final_cols,
    _create_threads, _create_runs, _add_runs_cols1, _add_runs_cols2, 
    _add_runs_cols3, _add_runs_final, _create_messages, _add_messages_cols,
    _add_messages_final, _add_messages_thread_fk, _create_steps,
    _add_steps_cols1, _add_steps_cols2, _add_steps_cols3, _add_steps_fks
)
from .analysis_tables import (
    _create_analyses, _add_analyses_cols, _create_analysis_results, 
    _add_analysis_results_fk, _create_corpora, _add_corpora_cols, 
    _add_analyses_index, _add_corpora_final
)
from .supply_tables import (
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


def create_agent_tables() -> None:
    """Create agent and AI-related tables."""
    _create_assistants()
    _add_assistants_cols()
    _add_assistants_final_cols()
    _create_threads()
    _create_runs()
    create_agent_runs_extended()


def create_agent_runs_extended() -> None:
    """Create extended agent runs."""
    _add_runs_cols1()
    _add_runs_cols2()
    _add_runs_cols3()
    _add_runs_final()
    _create_messages()
    create_messages_extended()


def create_messages_extended() -> None:
    """Create extended message tables."""
    _add_messages_cols()
    _add_messages_final()
    _add_messages_thread_fk()
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


def create_analysis_extended() -> None:
    """Create extended analysis tables."""
    _add_analyses_cols()
    _create_analysis_results()
    _add_analysis_results_fk()
    _create_corpora()
    create_supply_tables()


def create_supply_tables() -> None:
    """Create supply-related tables."""
    _add_corpora_cols()
    _create_supplies()
    _add_supplies_final()
    _create_supply_options()
    create_supply_options_extended()


def create_supply_options_extended() -> None:
    """Create extended supply options."""
    _add_supply_options_cols()
    _add_supply_options_final()
    _create_references()
    _add_references_cols()
    _add_references_final_cols()


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


def upgrade() -> None:
    """Upgrade schema with organized table creation."""
    create_user_tables()
    create_agent_tables()
    create_metric_tables()
    create_index_definitions()
    add_foreign_keys()
    add_constraints()