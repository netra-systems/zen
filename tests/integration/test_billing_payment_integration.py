import pytest
from unittest.mock import MagicMock, AsyncMock
from decimal import Decimal

from netra_backend.app.services.billing.billing_engine import (
    BillingEngine,
    BillingStatus,
)
from netra_backend.app.services.billing.payment_processor import PaymentProcessor


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def mock_usage_tracker():
    mock = MagicMock()
    mock.get_usage_for_period = AsyncMock(return_value={"total_usage": 100})
    return mock


@pytest.fixture
def mock_cost_calculator():
    mock = MagicMock()
    mock.calculate_cost = AsyncMock(return_value=Decimal("10.00"))
    return mock


@pytest.fixture
def mock_payment_gateway():
    mock = MagicMock()
    mock.charge = AsyncMock(return_value={"success": True, "transaction_id": "ch_123"})
    return mock


@pytest.fixture
def billing_engine(mock_db_session, mock_usage_tracker, mock_cost_calculator):
    engine = BillingEngine(db_session=mock_db_session)
    engine.usage_tracker = mock_usage_tracker
    engine.cost_calculator = mock_cost_calculator
    return engine


@pytest.fixture
def payment_processor(mock_db_session, mock_payment_gateway):
    processor = PaymentProcessor(db_session=mock_db_session)
    processor.payment_gateway = mock_payment_gateway
    return processor


async def test_generate_bill(billing_engine):
    bill = await billing_engine.generate_bill("user_123")
    assert bill.status == BillingStatus.PENDING
    assert bill.amount == Decimal("10.00")


async def test_process_payment(payment_processor):
    payment_result = await payment_processor.process_payment(
        "user_123", Decimal("20.00")
    )
    assert payment_result["success"] == True
    assert payment_result["transaction_id"] == "ch_123"
