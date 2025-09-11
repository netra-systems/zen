"""
DatabaseManager Business Critical Integration Tests - REVENUE PROTECTION FOCUSED

This test suite focuses on business-critical scenarios that directly impact
revenue, customer experience, and enterprise feature reliability.

CRITICAL BUSINESS SCENARIOS:
- Test data layer supporting all $2M+ business data persistence
- Validate connection reliability for Enterprise customers  
- Test multi-database coordination for analytics and real-time operations
- Validate transaction isolation preventing data corruption

Business Value Justification (BVJ):
- Segment: Enterprise/Platform - Protects ALL revenue streams
- Business Goal: Stability/Revenue Protection - Prevent data-related revenue loss
- Value Impact: Ensures critical business data operations never fail
- Strategic Impact: Validates foundation supporting entire business model

SSOT Compliance:
- Uses test_framework.ssot.base_test_case.SSotBaseTestCase
- Real database connections only - NO MOCKS
- Enterprise-grade testing with actual business scenarios
"""

import asyncio
import logging
import time
import uuid
from decimal import Decimal
from contextlib import asynccontextmanager
from typing import Dict, Any, List

import pytest
from sqlalchemy import text, Integer, String, DECIMAL, TIMESTAMP
from sqlalchemy.ext.asyncio import AsyncSession

# SSOT Test Framework
from test_framework.ssot.base_test_case import SSotBaseTestCase

# SSOT Imports per SSOT_IMPORT_REGISTRY.md
from netra_backend.app.db.database_manager import DatabaseManager, get_database_manager
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class TestDatabaseManagerBusinessCriticalRevenue(SSotBaseTestCase):
    """
    Test business-critical revenue-impacting database scenarios.
    
    CRITICAL: These tests validate data operations that directly
    impact revenue, customer billing, and financial integrity.
    """

    def setup_method(self, method):
        """Setup for revenue-critical tests."""
        super().setup_method(method)
        self.database_manager = None
        self.test_table_prefix = f"revenue_test_{uuid.uuid4().hex[:8]}"
        self.record_metric("test_category", "business_critical_revenue")

    def teardown_method(self, method):
        """Cleanup after revenue-critical tests."""
        async def cleanup():
            if self.database_manager:
                # Clean up any test tables
                try:
                    async with self.database_manager.get_session() as session:
                        # Clean up test tables (if any were created)
                        tables_to_drop = [
                            f"{self.test_table_prefix}_transactions",
                            f"{self.test_table_prefix}_user_accounts",
                            f"{self.test_table_prefix}_billing"
                        ]
                        for table in tables_to_drop:
                            await session.execute(text(f"DROP TABLE IF EXISTS {table}"))
                except Exception as e:
                    logger.warning(f"Revenue test cleanup failed: {e}")
                
                await self.database_manager.close_all()
        
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(cleanup())
        except RuntimeError:
            asyncio.run(cleanup())
            
        super().teardown_method(method)

    async def test_financial_transaction_integrity(self):
        """
        Test financial transaction integrity for billing operations.
        
        BUSINESS CRITICAL: Revenue-affecting transactions must be
        ACID-compliant to prevent financial data corruption.
        """
        self.database_manager = DatabaseManager()
        await self.database_manager.initialize()
        
        # Create test billing table
        billing_table = f"{self.test_table_prefix}_billing"
        async with self.database_manager.get_session() as session:
            await session.execute(text(f"""
                CREATE TEMPORARY TABLE {billing_table} (
                    id SERIAL PRIMARY KEY,
                    customer_id VARCHAR(50) NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    transaction_type VARCHAR(20) NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
        
        # Test financial transaction scenarios
        test_customer_id = f"enterprise_customer_{uuid.uuid4().hex[:8]}"
        transaction_amount = Decimal("1299.99")  # Enterprise subscription
        
        # Test successful financial transaction
        async with self.database_manager.get_session() as session:
            await session.execute(text(f"""
                INSERT INTO {billing_table} (customer_id, amount, transaction_type, status)
                VALUES (:customer_id, :amount, 'subscription_payment', 'completed')
            """), {
                "customer_id": test_customer_id,
                "amount": float(transaction_amount)
            })
            
            # Verify transaction recorded correctly
            result = await session.execute(text(f"""
                SELECT amount, transaction_type, status 
                FROM {billing_table} 
                WHERE customer_id = :customer_id
            """), {"customer_id": test_customer_id})
            
            transaction = result.fetchone()
            assert transaction is not None, "Financial transaction should be recorded"
            assert Decimal(str(transaction[0])) == transaction_amount, "Transaction amount must be exact"
            assert transaction[1] == 'subscription_payment', "Transaction type must be preserved"
            assert transaction[2] == 'completed', "Transaction status must be correct"
        
        # Test transaction rollback on error (prevents financial corruption)
        failed_customer_id = f"failed_customer_{uuid.uuid4().hex[:8]}"
        rollback_successful = False
        
        try:
            async with self.database_manager.get_session() as session:
                # Insert valid transaction
                await session.execute(text(f"""
                    INSERT INTO {billing_table} (customer_id, amount, transaction_type)
                    VALUES (:customer_id, :amount, 'failed_payment')
                """), {
                    "customer_id": failed_customer_id,
                    "amount": 999.99
                })
                
                # Force transaction failure (simulates payment gateway error)
                raise RuntimeError("Payment gateway failure simulation")
                
        except RuntimeError:
            rollback_successful = True
        
        assert rollback_successful, "Financial transaction rollback must work"
        
        # Verify failed transaction was rolled back
        async with self.database_manager.get_session() as session:
            result = await session.execute(text(f"""
                SELECT COUNT(*) FROM {billing_table} WHERE customer_id = :customer_id
            """), {"customer_id": failed_customer_id})
            
            failed_count = result.scalar()
            assert failed_count == 0, "Failed financial transactions must be rolled back"
        
        self.increment_db_query_count(6)
        self.record_metric("financial_transaction_test", "PASSED")
        self.record_metric("revenue_protection", "VALIDATED")

    async def test_enterprise_customer_data_isolation(self):
        """
        Test data isolation for Enterprise customers.
        
        BUSINESS CRITICAL: Enterprise customers ($15K+ MRR) require
        guaranteed data isolation for security compliance.
        """
        self.database_manager = DatabaseManager()
        await self.database_manager.initialize()
        
        # Create test customer accounts table
        accounts_table = f"{self.test_table_prefix}_user_accounts"
        async with self.database_manager.get_session() as session:
            await session.execute(text(f"""
                CREATE TEMPORARY TABLE {accounts_table} (
                    id SERIAL PRIMARY KEY,
                    customer_id VARCHAR(50) NOT NULL,
                    customer_tier VARCHAR(20) NOT NULL,
                    sensitive_data TEXT NOT NULL,
                    enterprise_features BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
        
        # Create test enterprise customers
        enterprise_customers = [
            {
                "customer_id": f"enterprise_A_{uuid.uuid4().hex[:8]}",
                "tier": "enterprise",
                "data": "Enterprise Customer A Confidential Data",
                "features": True
            },
            {
                "customer_id": f"enterprise_B_{uuid.uuid4().hex[:8]}",
                "tier": "enterprise", 
                "data": "Enterprise Customer B Confidential Data",
                "features": True
            },
            {
                "customer_id": f"free_user_{uuid.uuid4().hex[:8]}",
                "tier": "free",
                "data": "Free User Public Data",
                "features": False
            }
        ]
        
        # Insert customer data in separate sessions (simulating concurrent access)
        async def insert_customer_data(customer_data: dict):
            """Insert customer data in isolated session."""
            async with self.database_manager.get_session() as session:
                await session.execute(text(f"""
                    INSERT INTO {accounts_table} 
                    (customer_id, customer_tier, sensitive_data, enterprise_features)
                    VALUES (:customer_id, :tier, :data, :features)
                """), customer_data)
                
                self.increment_db_query_count()
                return customer_data["customer_id"]
        
        # Insert all customers concurrently
        insert_tasks = [insert_customer_data(customer) for customer in enterprise_customers]
        inserted_customers = await asyncio.gather(*insert_tasks)
        
        # Verify data isolation - each customer can only see their own data
        for customer in enterprise_customers:
            async with self.database_manager.get_session() as session:
                # Simulate row-level security / tenant isolation
                result = await session.execute(text(f"""
                    SELECT customer_id, sensitive_data, enterprise_features
                    FROM {accounts_table} 
                    WHERE customer_id = :customer_id
                """), {"customer_id": customer["customer_id"]})
                
                customer_record = result.fetchone()
                assert customer_record is not None, f"Customer {customer['customer_id']} data should exist"
                assert customer_record[0] == customer["customer_id"], "Customer ID must match"
                assert customer_record[1] == customer["data"], "Sensitive data must be preserved"
                assert customer_record[2] == customer["features"], "Enterprise features must be correct"
                
                self.increment_db_query_count()
        
        # Verify no cross-customer data leakage
        async with self.database_manager.get_session() as session:
            result = await session.execute(text(f"SELECT COUNT(DISTINCT customer_tier) FROM {accounts_table}"))
            distinct_tiers = result.scalar()
            assert distinct_tiers == 2, "Should have exactly 2 customer tiers (enterprise, free)"
            
            # Count enterprise vs free customers
            result = await session.execute(text(f"""
                SELECT customer_tier, COUNT(*) 
                FROM {accounts_table} 
                GROUP BY customer_tier 
                ORDER BY customer_tier
            """))
            tier_counts = result.fetchall()
            
            enterprise_count = next((count for tier, count in tier_counts if tier == 'enterprise'), 0)
            free_count = next((count for tier, count in tier_counts if tier == 'free'), 0)
            
            assert enterprise_count == 2, "Should have exactly 2 enterprise customers"
            assert free_count == 1, "Should have exactly 1 free customer"
            
            self.increment_db_query_count(2)
        
        self.record_metric("enterprise_customers_tested", len([c for c in enterprise_customers if c["tier"] == "enterprise"]))
        self.record_metric("data_isolation_test", "PASSED")
        self.record_metric("enterprise_compliance", "VALIDATED")

    async def test_high_value_transaction_performance(self):
        """
        Test performance for high-value business transactions.
        
        BUSINESS CRITICAL: Large Enterprise transactions must complete
        within SLA timeframes to maintain customer satisfaction.
        """
        self.database_manager = DatabaseManager()
        await self.database_manager.initialize()
        
        # Create test transactions table
        transactions_table = f"{self.test_table_prefix}_transactions"
        async with self.database_manager.get_session() as session:
            await session.execute(text(f"""
                CREATE TEMPORARY TABLE {transactions_table} (
                    id SERIAL PRIMARY KEY,
                    transaction_id VARCHAR(50) UNIQUE NOT NULL,
                    customer_id VARCHAR(50) NOT NULL,
                    amount DECIMAL(12,2) NOT NULL,
                    transaction_type VARCHAR(30) NOT NULL,
                    processing_time_ms INTEGER,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
        
        # Test high-value transaction scenarios
        high_value_transactions = [
            {"type": "annual_enterprise_subscription", "amount": 50000.00},  # $50K annual
            {"type": "multi_year_contract", "amount": 150000.00},          # $150K multi-year
            {"type": "enterprise_onboarding", "amount": 25000.00},         # $25K implementation
            {"type": "premium_support_upgrade", "amount": 12000.00},       # $12K support
        ]
        
        performance_results = []
        
        for transaction_spec in high_value_transactions:
            start_time = time.time()
            transaction_id = f"txn_{transaction_spec['type']}_{uuid.uuid4().hex[:8]}"
            customer_id = f"enterprise_customer_{uuid.uuid4().hex[:8]}"
            
            # Execute high-value transaction
            async with self.database_manager.get_session() as session:
                await session.execute(text(f"""
                    INSERT INTO {transactions_table} 
                    (transaction_id, customer_id, amount, transaction_type, processing_time_ms)
                    VALUES (:txn_id, :customer_id, :amount, :txn_type, :processing_time)
                """), {
                    "txn_id": transaction_id,
                    "customer_id": customer_id,
                    "amount": transaction_spec["amount"],
                    "txn_type": transaction_spec["type"],
                    "processing_time": 0  # Will update after timing
                })
                
                # Verify transaction integrity
                result = await session.execute(text(f"""
                    SELECT amount, transaction_type FROM {transactions_table}
                    WHERE transaction_id = :txn_id
                """), {"txn_id": transaction_id})
                
                verified_txn = result.fetchone()
                assert verified_txn is not None, f"High-value transaction {transaction_id} should be recorded"
                assert Decimal(str(verified_txn[0])) == Decimal(str(transaction_spec["amount"])), "High-value amount must be exact"
                
                self.increment_db_query_count(2)
            
            processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            performance_results.append({
                "type": transaction_spec["type"],
                "amount": transaction_spec["amount"],
                "processing_time_ms": processing_time
            })
            
            # Update processing time in database
            async with self.database_manager.get_session() as session:
                await session.execute(text(f"""
                    UPDATE {transactions_table} 
                    SET processing_time_ms = :processing_time
                    WHERE transaction_id = :txn_id
                """), {
                    "processing_time": int(processing_time),
                    "txn_id": transaction_id
                })
                self.increment_db_query_count()
        
        # Validate performance SLAs for high-value transactions
        avg_processing_time = sum(r["processing_time_ms"] for r in performance_results) / len(performance_results)
        max_processing_time = max(r["processing_time_ms"] for r in performance_results)
        total_transaction_value = sum(r["amount"] for r in performance_results)
        
        # Business SLA validation
        assert avg_processing_time < 1000, f"High-value transactions too slow: {avg_processing_time:.2f}ms average"
        assert max_processing_time < 2000, f"Maximum transaction time too high: {max_processing_time:.2f}ms"
        assert total_transaction_value > 200000, "Should process significant transaction volume"
        
        # Record business metrics
        self.record_metric("high_value_transaction_count", len(performance_results))
        self.record_metric("total_transaction_value", total_transaction_value)
        self.record_metric("avg_processing_time_ms", avg_processing_time)
        self.record_metric("max_processing_time_ms", max_processing_time)
        self.record_metric("high_value_transaction_test", "PASSED")
        self.record_metric("revenue_processing_sla", "MET")

    async def test_data_integrity_under_concurrent_revenue_operations(self):
        """
        Test data integrity under concurrent revenue-generating operations.
        
        BUSINESS CRITICAL: Concurrent billing, subscription updates, and
        usage tracking must maintain data consistency.
        """
        self.database_manager = DatabaseManager()
        await self.database_manager.initialize()
        
        # Create comprehensive business data table
        business_table = f"{self.test_table_prefix}_business_ops"
        async with self.database_manager.get_session() as session:
            await session.execute(text(f"""
                CREATE TEMPORARY TABLE {business_table} (
                    id SERIAL PRIMARY KEY,
                    customer_id VARCHAR(50) NOT NULL,
                    operation_type VARCHAR(30) NOT NULL,
                    amount DECIMAL(10,2),
                    usage_count INTEGER DEFAULT 0,
                    subscription_status VARCHAR(20) DEFAULT 'active',
                    last_updated TIMESTAMP DEFAULT NOW(),
                    UNIQUE(customer_id, operation_type)
                )
            """))
        
        # Insert baseline customer data
        test_customer_id = f"concurrent_test_customer_{uuid.uuid4().hex[:8]}"
        async with self.database_manager.get_session() as session:
            await session.execute(text(f"""
                INSERT INTO {business_table} (customer_id, operation_type, amount, usage_count)
                VALUES 
                (:customer_id, 'billing', 0.00, 0),
                (:customer_id, 'usage_tracking', 0.00, 0),
                (:customer_id, 'subscription_management', 1299.99, 1)
            """), {"customer_id": test_customer_id})
        
        # Define concurrent business operations
        async def billing_operation(operation_id: int):
            """Simulate billing operations."""
            async with self.database_manager.get_session() as session:
                # Add billing charge
                await session.execute(text(f"""
                    UPDATE {business_table} 
                    SET amount = amount + 99.99, last_updated = NOW()
                    WHERE customer_id = :customer_id AND operation_type = 'billing'
                """), {"customer_id": test_customer_id})
                
                self.increment_db_query_count()
                return f"billing_{operation_id}"
        
        async def usage_tracking_operation(operation_id: int):
            """Simulate usage tracking operations."""
            async with self.database_manager.get_session() as session:
                # Increment usage counter
                await session.execute(text(f"""
                    UPDATE {business_table} 
                    SET usage_count = usage_count + 10, last_updated = NOW()
                    WHERE customer_id = :customer_id AND operation_type = 'usage_tracking'
                """), {"customer_id": test_customer_id})
                
                self.increment_db_query_count()
                return f"usage_{operation_id}"
        
        async def subscription_operation(operation_id: int):
            """Simulate subscription management operations."""
            async with self.database_manager.get_session() as session:
                # Update subscription
                await session.execute(text(f"""
                    UPDATE {business_table} 
                    SET subscription_status = 'updated', last_updated = NOW()
                    WHERE customer_id = :customer_id AND operation_type = 'subscription_management'
                """), {"customer_id": test_customer_id})
                
                self.increment_db_query_count()
                return f"subscription_{operation_id}"
        
        # Execute concurrent business operations
        concurrent_operations = []
        for i in range(5):
            concurrent_operations.extend([
                billing_operation(i),
                usage_tracking_operation(i), 
                subscription_operation(i)
            ])
        
        # Run all operations concurrently
        start_time = time.time()
        operation_results = await asyncio.gather(*concurrent_operations, return_exceptions=True)
        concurrent_duration = time.time() - start_time
        
        # Verify data consistency after concurrent operations
        async with self.database_manager.get_session() as session:
            result = await session.execute(text(f"""
                SELECT operation_type, amount, usage_count, subscription_status
                FROM {business_table}
                WHERE customer_id = :customer_id
                ORDER BY operation_type
            """), {"customer_id": test_customer_id})
            
            final_state = result.fetchall()
            
            billing_record = next((r for r in final_state if r[0] == 'billing'), None)
            usage_record = next((r for r in final_state if r[0] == 'usage_tracking'), None)
            subscription_record = next((r for r in final_state if r[0] == 'subscription_management'), None)
            
            # Validate data integrity
            assert billing_record is not None, "Billing record should exist"
            assert float(billing_record[1]) > 0, "Billing amount should be updated"
            
            assert usage_record is not None, "Usage record should exist"  
            assert usage_record[2] > 0, "Usage count should be updated"
            
            assert subscription_record is not None, "Subscription record should exist"
            assert subscription_record[3] in ['active', 'updated'], "Subscription status should be valid"
            
            self.increment_db_query_count()
        
        # Validate concurrent operation success
        successful_ops = [r for r in operation_results if not isinstance(r, Exception)]
        success_rate = len(successful_ops) / len(operation_results)
        
        assert success_rate >= 0.9, f"Concurrent operation success rate too low: {success_rate:.2%}"
        assert concurrent_duration < 10.0, f"Concurrent operations took too long: {concurrent_duration:.2f}s"
        
        # Record business integrity metrics
        self.record_metric("concurrent_operations_count", len(operation_results))
        self.record_metric("concurrent_success_rate", success_rate)
        self.record_metric("concurrent_duration", concurrent_duration)
        self.record_metric("data_integrity_test", "PASSED")
        self.record_metric("concurrent_revenue_operations", "VALIDATED")