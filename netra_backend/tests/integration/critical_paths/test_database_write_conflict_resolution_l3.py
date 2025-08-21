"""
L3 Integration Test: Database Write Conflict Resolution and Optimistic Locking

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects concurrent editing across all tiers)
- Business Goal: Data Integrity - Prevent data corruption from concurrent writes
- Value Impact: Protects critical business data for $45K MRR
- Strategic Impact: Enables collaborative features without data loss

L3 Test: Uses real PostgreSQL container to validate optimistic locking, write conflict
detection, resolution strategies, and data consistency under concurrent operations.
"""

import pytest
import asyncio
import time
import uuid
import json
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, OperationalError
from testcontainers.postgres import PostgresContainer

from logging_config import central_logger

logger = central_logger.get_logger(__name__)


class WriteConflictResolutionManager:
    """Manages write conflict resolution testing with real PostgreSQL container."""
    
    def __init__(self):
        self.container = None
        self.db_url = None
        self.engine = None
        self.session_factory = None
        self.conflict_scenarios = []
        self.resolution_metrics = {}
        
    async def setup_postgres_container(self):
        """Setup real PostgreSQL container for write conflict testing."""
        try:
            self.container = PostgresContainer("postgres:15-alpine")
            self.container.start()
            
            self.db_url = self.container.get_connection_url().replace(
                "postgresql://", "postgresql+asyncpg://"
            )
            
            self.engine = create_async_engine(
                self.db_url,
                pool_size=10,  # Higher pool size for concurrent testing
                max_overflow=5,
                pool_pre_ping=True,
                echo=False
            )
            
            self.session_factory = sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )
            
            # Initialize test schema with conflict resolution patterns
            await self.create_conflict_test_schema()
            
            logger.info("Write conflict test container setup complete")
            
        except Exception as e:
            logger.error(f"Failed to setup write conflict container: {e}")
            await self.cleanup()
            raise
    
    async def create_conflict_test_schema(self):
        """Create test schema designed for write conflict scenarios."""
        async with self.engine.begin() as conn:
            # Optimistic locking test table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS optimistic_lock_test (
                    id SERIAL PRIMARY KEY,
                    resource_name VARCHAR(100) UNIQUE NOT NULL,
                    resource_value TEXT,
                    version INTEGER NOT NULL DEFAULT 1,
                    last_modified_by VARCHAR(50),
                    last_modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    lock_token UUID DEFAULT gen_random_uuid()
                )
            """)
            
            # Concurrent edit test table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS concurrent_edit_test (
                    id SERIAL PRIMARY KEY,
                    document_id VARCHAR(50) NOT NULL,
                    editor_id VARCHAR(50) NOT NULL,
                    content_version INTEGER NOT NULL DEFAULT 1,
                    content_data JSONB,
                    edit_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_latest BOOLEAN DEFAULT TRUE,
                    conflict_resolved BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Financial transaction test table (requires strict consistency)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS financial_accounts (
                    id SERIAL PRIMARY KEY,
                    account_number VARCHAR(50) UNIQUE NOT NULL,
                    balance DECIMAL(15,2) NOT NULL DEFAULT 0.00,
                    version INTEGER NOT NULL DEFAULT 1,
                    last_transaction_id UUID,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT positive_balance CHECK (balance >= 0)
                )
            """)
            
            # Transaction log for auditing
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS transaction_log (
                    id SERIAL PRIMARY KEY,
                    transaction_id UUID NOT NULL,
                    account_id INTEGER REFERENCES financial_accounts(id),
                    operation_type VARCHAR(20) NOT NULL,
                    amount DECIMAL(15,2),
                    old_balance DECIMAL(15,2),
                    new_balance DECIMAL(15,2),
                    conflict_detected BOOLEAN DEFAULT FALSE,
                    resolution_strategy VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert test data
            await conn.execute("""
                INSERT INTO optimistic_lock_test (resource_name, resource_value, last_modified_by) VALUES
                ('shared_config', '{"setting1": "value1", "setting2": "value2"}', 'system'),
                ('user_preferences', '{"theme": "dark", "language": "en"}', 'system'),
                ('cache_settings', '{"ttl": 3600, "max_size": 1000}', 'system')
                ON CONFLICT (resource_name) DO NOTHING
            """)
            
            await conn.execute("""
                INSERT INTO financial_accounts (account_number, balance) VALUES
                ('ACC001', 1000.00),
                ('ACC002', 2500.00),
                ('ACC003', 500.00)
                ON CONFLICT (account_number) DO NOTHING
            """)
    
    async def test_optimistic_locking_conflict_detection(self, concurrent_editors: int = 5) -> Dict[str, Any]:
        """Test optimistic locking with concurrent editors."""
        conflict_result = {
            "concurrent_editors": concurrent_editors,
            "conflicts_detected": 0,
            "successful_updates": 0,
            "version_consistency_maintained": False,
            "final_data_integrity": False
        }
        
        async def concurrent_edit_operation(editor_id: int) -> Dict[str, Any]:
            """Simulate concurrent editing with optimistic locking."""
            edit_result = {
                "editor_id": editor_id,
                "success": False,
                "conflicts_encountered": 0,
                "retries_attempted": 0,
                "final_version": None
            }
            
            max_retries = 3
            resource_name = "shared_config"
            
            for retry_attempt in range(max_retries):
                try:
                    async with self.session_factory() as session:
                        # Step 1: Read current version
                        result = await session.execute(
                            """
                            SELECT id, resource_value, version, lock_token
                            FROM optimistic_lock_test 
                            WHERE resource_name = :resource_name
                            """,
                            {"resource_name": resource_name}
                        )
                        
                        row = result.fetchone()
                        if not row:
                            break
                        
                        resource_id, current_value, current_version, lock_token = row
                        
                        # Step 2: Simulate editing delay
                        await asyncio.sleep(0.1)
                        
                        # Step 3: Prepare new value
                        current_data = json.loads(current_value) if current_value else {}
                        current_data[f"editor_{editor_id}_update"] = f"value_from_editor_{editor_id}_attempt_{retry_attempt}"
                        new_value = json.dumps(current_data)
                        new_version = current_version + 1
                        
                        # Step 4: Optimistic update with version check
                        update_result = await session.execute(
                            """
                            UPDATE optimistic_lock_test 
                            SET 
                                resource_value = :new_value,
                                version = :new_version,
                                last_modified_by = :editor,
                                last_modified_at = CURRENT_TIMESTAMP,
                                lock_token = gen_random_uuid()
                            WHERE resource_name = :resource_name 
                            AND version = :expected_version
                            """,
                            {
                                "new_value": new_value,
                                "new_version": new_version,
                                "editor": f"editor_{editor_id}",
                                "resource_name": resource_name,
                                "expected_version": current_version
                            }
                        )
                        
                        if update_result.rowcount == 0:
                            # Version conflict detected
                            edit_result["conflicts_encountered"] += 1
                            edit_result["retries_attempted"] = retry_attempt + 1
                            
                            # Exponential backoff before retry
                            await asyncio.sleep(0.05 * (2 ** retry_attempt))
                            continue
                        
                        await session.commit()
                        edit_result["success"] = True
                        edit_result["final_version"] = new_version
                        break
                        
                except Exception as e:
                    logger.debug(f"Editor {editor_id} attempt {retry_attempt} failed: {e}")
                    edit_result["retries_attempted"] = retry_attempt + 1
            
            return edit_result
        
        try:
            # Execute concurrent editing operations
            tasks = [concurrent_edit_operation(i) for i in range(concurrent_editors)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze conflict resolution results
            for result in results:
                if isinstance(result, dict):
                    conflict_result["conflicts_detected"] += result["conflicts_encountered"]
                    if result["success"]:
                        conflict_result["successful_updates"] += 1
            
            # Verify final state consistency
            async with self.session_factory() as session:
                final_result = await session.execute(
                    "SELECT resource_value, version FROM optimistic_lock_test WHERE resource_name = 'shared_config'"
                )
                final_row = final_result.fetchone()
                
                if final_row:
                    final_value, final_version = final_row
                    
                    # Parse final data to verify integrity
                    try:
                        final_data = json.loads(final_value)
                        
                        # Count successful editor contributions
                        editor_contributions = sum(1 for key in final_data.keys() if key.startswith("editor_"))
                        
                        conflict_result["version_consistency_maintained"] = final_version > 1
                        conflict_result["final_data_integrity"] = (
                            editor_contributions == conflict_result["successful_updates"]
                        )
                        
                    except json.JSONDecodeError:
                        conflict_result["final_data_integrity"] = False
                        
        except Exception as e:
            conflict_result["error"] = str(e)
            logger.error(f"Optimistic locking test failed: {e}")
        
        return conflict_result
    
    async def test_financial_transaction_conflict_safety(self) -> Dict[str, Any]:
        """Test write conflict resolution for financial transactions."""
        financial_result = {
            "concurrent_transactions": 0,
            "successful_transactions": 0,
            "conflicts_resolved": 0,
            "data_consistency_maintained": False,
            "balance_integrity_verified": False
        }
        
        async def concurrent_financial_operation(operation_id: int, account_number: str, amount: float) -> Dict[str, Any]:
            """Execute financial transaction with conflict detection."""
            transaction_result = {
                "operation_id": operation_id,
                "success": False,
                "conflict_detected": False,
                "final_balance": None,
                "transaction_id": str(uuid.uuid4())
            }
            
            max_retries = 5
            
            for retry_attempt in range(max_retries):
                try:
                    async with self.session_factory() as session:
                        # Step 1: Read account with current version
                        account_result = await session.execute(
                            """
                            SELECT id, balance, version 
                            FROM financial_accounts 
                            WHERE account_number = :account_number 
                            FOR UPDATE
                            """,
                            {"account_number": account_number}
                        )
                        
                        account_row = account_result.fetchone()
                        if not account_row:
                            break
                        
                        account_id, current_balance, current_version = account_row
                        new_balance = float(current_balance) + amount
                        
                        # Step 2: Validate business rules
                        if new_balance < 0:
                            transaction_result["error"] = "Insufficient funds"
                            break
                        
                        # Step 3: Log transaction attempt
                        await session.execute(
                            """
                            INSERT INTO transaction_log 
                            (transaction_id, account_id, operation_type, amount, old_balance, new_balance)
                            VALUES (:tx_id, :acc_id, :op_type, :amount, :old_balance, :new_balance)
                            """,
                            {
                                "tx_id": transaction_result["transaction_id"],
                                "acc_id": account_id,
                                "op_type": "credit" if amount > 0 else "debit",
                                "amount": abs(amount),
                                "old_balance": current_balance,
                                "new_balance": new_balance
                            }
                        )
                        
                        # Step 4: Update account with version check
                        update_result = await session.execute(
                            """
                            UPDATE financial_accounts 
                            SET 
                                balance = :new_balance,
                                version = :new_version,
                                last_transaction_id = :tx_id,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE account_number = :account_number 
                            AND version = :expected_version
                            """,
                            {
                                "new_balance": new_balance,
                                "new_version": current_version + 1,
                                "tx_id": transaction_result["transaction_id"],
                                "account_number": account_number,
                                "expected_version": current_version
                            }
                        )
                        
                        if update_result.rowcount == 0:
                            # Version conflict - another transaction modified the account
                            transaction_result["conflict_detected"] = True
                            
                            # Mark conflict in log
                            await session.execute(
                                """
                                UPDATE transaction_log 
                                SET conflict_detected = TRUE, resolution_strategy = 'retry'
                                WHERE transaction_id = :tx_id
                                """,
                                {"tx_id": transaction_result["transaction_id"]}
                            )
                            
                            await session.rollback()
                            
                            # Exponential backoff before retry
                            await asyncio.sleep(0.01 * (2 ** retry_attempt))
                            continue
                        
                        await session.commit()
                        transaction_result["success"] = True
                        transaction_result["final_balance"] = new_balance
                        break
                        
                except Exception as e:
                    logger.debug(f"Transaction {operation_id} attempt {retry_attempt} failed: {e}")
                    await session.rollback()
            
            return transaction_result
        
        try:
            # Test concurrent transactions on same account
            account_number = "ACC001"
            initial_balance = None
            
            # Get initial balance
            async with self.session_factory() as session:
                result = await session.execute(
                    "SELECT balance FROM financial_accounts WHERE account_number = :acc",
                    {"acc": account_number}
                )
                initial_balance = float(result.fetchone()[0])
            
            # Execute concurrent transactions
            transaction_amounts = [50.0, -25.0, 100.0, -30.0, 75.0]  # Mix of credits and debits
            
            tasks = [
                concurrent_financial_operation(i, account_number, amount)
                for i, amount in enumerate(transaction_amounts)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze transaction results
            total_expected_change = 0
            
            for i, result in enumerate(results):
                if isinstance(result, dict):
                    financial_result["concurrent_transactions"] += 1
                    
                    if result["success"]:
                        financial_result["successful_transactions"] += 1
                        total_expected_change += transaction_amounts[i]
                    
                    if result["conflict_detected"]:
                        financial_result["conflicts_resolved"] += 1
            
            # Verify final balance consistency
            async with self.session_factory() as session:
                final_result = await session.execute(
                    "SELECT balance FROM financial_accounts WHERE account_number = :acc",
                    {"acc": account_number}
                )
                final_balance = float(final_result.fetchone()[0])
                
                expected_final_balance = initial_balance + total_expected_change
                
                financial_result["data_consistency_maintained"] = (
                    abs(final_balance - expected_final_balance) < 0.01
                )
                
                financial_result["balance_integrity_verified"] = final_balance >= 0
                
        except Exception as e:
            financial_result["error"] = str(e)
            logger.error(f"Financial transaction conflict test failed: {e}")
        
        return financial_result
    
    async def test_document_collaborative_editing(self) -> Dict[str, Any]:
        """Test collaborative document editing with conflict resolution."""
        collaboration_result = {
            "simultaneous_editors": 0,
            "edit_conflicts_detected": 0,
            "conflict_resolution_successful": 0,
            "document_integrity_maintained": False
        }
        
        async def collaborative_edit_session(editor_id: int, document_id: str) -> Dict[str, Any]:
            """Simulate collaborative editing session."""
            session_result = {
                "editor_id": editor_id,
                "edits_attempted": 0,
                "edits_successful": 0,
                "conflicts_resolved": 0
            }
            
            # Simulate multiple edits per editor
            for edit_number in range(3):
                try:
                    async with self.session_factory() as session:
                        # Get current document version
                        current_result = await session.execute(
                            """
                            SELECT content_version, content_data 
                            FROM concurrent_edit_test 
                            WHERE document_id = :doc_id AND is_latest = TRUE
                            ORDER BY content_version DESC
                            LIMIT 1
                            """,
                            {"doc_id": document_id}
                        )
                        
                        current_row = current_result.fetchone()
                        current_version = current_row[0] if current_row else 0
                        current_content = current_row[1] if current_row and current_row[1] else {}
                        
                        # Simulate editing
                        new_content = dict(current_content) if current_content else {}
                        new_content[f"edit_by_editor_{editor_id}_{edit_number}"] = {
                            "timestamp": datetime.now().isoformat(),
                            "content": f"Content from editor {editor_id}, edit {edit_number}"
                        }
                        
                        new_version = current_version + 1
                        
                        # Mark old versions as not latest
                        await session.execute(
                            """
                            UPDATE concurrent_edit_test 
                            SET is_latest = FALSE 
                            WHERE document_id = :doc_id AND is_latest = TRUE
                            """,
                            {"doc_id": document_id}
                        )
                        
                        # Insert new version
                        await session.execute(
                            """
                            INSERT INTO concurrent_edit_test 
                            (document_id, editor_id, content_version, content_data, is_latest)
                            VALUES (:doc_id, :editor_id, :version, :content, TRUE)
                            """,
                            {
                                "doc_id": document_id,
                                "editor_id": f"editor_{editor_id}",
                                "version": new_version,
                                "content": json.dumps(new_content)
                            }
                        )
                        
                        await session.commit()
                        session_result["edits_successful"] += 1
                        
                except Exception as e:
                    # Handle conflicts
                    if "unique" in str(e).lower() or "conflict" in str(e).lower():
                        session_result["conflicts_resolved"] += 1
                    
                    logger.debug(f"Editor {editor_id} edit {edit_number} failed: {e}")
                
                finally:
                    session_result["edits_attempted"] += 1
                
                # Brief pause between edits
                await asyncio.sleep(0.05)
            
            return session_result
        
        try:
            document_id = f"collaborative_doc_{uuid.uuid4().hex[:8]}"
            editor_count = 4
            
            # Initialize document
            async with self.session_factory() as session:
                await session.execute(
                    """
                    INSERT INTO concurrent_edit_test 
                    (document_id, editor_id, content_version, content_data, is_latest)
                    VALUES (:doc_id, 'system', 1, :content, TRUE)
                    """,
                    {
                        "doc_id": document_id,
                        "content": json.dumps({"title": "Collaborative Document", "created": datetime.now().isoformat()})
                    }
                )
                await session.commit()
            
            # Start collaborative editing
            tasks = [
                collaborative_edit_session(i, document_id)
                for i in range(editor_count)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze collaboration results
            for result in results:
                if isinstance(result, dict):
                    collaboration_result["simultaneous_editors"] += 1
                    collaboration_result["edit_conflicts_detected"] += result["conflicts_resolved"]
                    collaboration_result["conflict_resolution_successful"] += result["edits_successful"]
            
            # Verify document integrity
            async with self.session_factory() as session:
                final_doc_result = await session.execute(
                    """
                    SELECT content_data, content_version 
                    FROM concurrent_edit_test 
                    WHERE document_id = :doc_id AND is_latest = TRUE
                    """,
                    {"doc_id": document_id}
                )
                
                final_doc_row = final_doc_result.fetchone()
                
                if final_doc_row:
                    final_content = json.loads(final_doc_row[0])
                    final_version = final_doc_row[1]
                    
                    # Verify all editors contributed
                    editor_contributions = sum(
                        1 for key in final_content.keys() 
                        if key.startswith("edit_by_editor_")
                    )
                    
                    collaboration_result["document_integrity_maintained"] = (
                        editor_contributions > 0 and
                        final_version > 1 and
                        "title" in final_content
                    )
                    
        except Exception as e:
            collaboration_result["error"] = str(e)
            logger.error(f"Collaborative editing test failed: {e}")
        
        return collaboration_result
    
    async def cleanup(self):
        """Clean up test resources."""
        try:
            if self.engine:
                await self.engine.dispose()
            
            if self.container:
                self.container.stop()
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def conflict_manager():
    """Create write conflict resolution manager for testing."""
    manager = WriteConflictResolutionManager()
    await manager.setup_postgres_container()
    yield manager
    await manager.cleanup()


@pytest.mark.L3
@pytest.mark.integration
class TestDatabaseWriteConflictResolutionL3:
    """L3 integration tests for database write conflict resolution."""
    
    async def test_optimistic_locking_concurrent_edits(self, conflict_manager):
        """Test optimistic locking handles concurrent edits correctly."""
        result = await conflict_manager.test_optimistic_locking_conflict_detection(4)
        
        assert result["successful_updates"] > 0
        assert result["conflicts_detected"] >= 2  # Should detect some conflicts
        assert result["version_consistency_maintained"] is True
        assert result["final_data_integrity"] is True
        
        # At least one editor should succeed
        assert result["successful_updates"] >= 1
    
    async def test_financial_transaction_consistency(self, conflict_manager):
        """Test financial transactions maintain consistency under conflicts."""
        result = await conflict_manager.test_financial_transaction_conflict_safety()
        
        assert result["concurrent_transactions"] >= 5
        assert result["successful_transactions"] >= 3  # Most should succeed
        assert result["data_consistency_maintained"] is True
        assert result["balance_integrity_verified"] is True
        
        # Conflicts should be properly resolved
        if result["conflicts_resolved"] > 0:
            assert result["successful_transactions"] > 0
    
    async def test_collaborative_document_editing(self, conflict_manager):
        """Test collaborative document editing with conflict resolution."""
        result = await conflict_manager.test_document_collaborative_editing()
        
        assert result["simultaneous_editors"] == 4
        assert result["conflict_resolution_successful"] > 0
        assert result["document_integrity_maintained"] is True
        
        # Should handle at least some edit conflicts
        if result["edit_conflicts_detected"] > 0:
            assert result["conflict_resolution_successful"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])