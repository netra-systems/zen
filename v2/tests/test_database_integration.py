import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models_postgres import (
    User,
    Thread,
    Message,
    Run,
    Assistant,
    Reference,
    Supply
)
# Try to import from app, fall back to test helpers
try:
    from app.auth.auth import hash_password
except ImportError:
    from test_helpers import hash_password

@pytest.mark.asyncio
async def test_create_user(async_session: AsyncSession):
    """Test creating a user in the database"""
    
    user = User(
        id=str(uuid.uuid4()),
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=hash_password("password123"),
        full_name="Test User",
        is_active=True,
        is_superuser=False
    )
    
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    assert user.id is not None
    assert user.created_at is not None
    
    result = await async_session.execute(
        select(User).where(User.id == user.id)
    )
    db_user = result.scalar_one()
    
    assert db_user.email == user.email
    assert db_user.full_name == "Test User"

@pytest.mark.asyncio
async def test_user_uniqueness(async_session: AsyncSession):
    """Test email uniqueness constraint"""
    
    email = f"unique_{uuid.uuid4().hex[:8]}@example.com"
    
    user1 = User(
        id=str(uuid.uuid4()),
        email=email,
        hashed_password=hash_password("password123")
    )
    
    async_session.add(user1)
    await async_session.commit()
    
    user2 = User(
        id=str(uuid.uuid4()),
        email=email,
        hashed_password=hash_password("password456")
    )
    
    async_session.add(user2)
    
    with pytest.raises(Exception):
        await async_session.commit()

@pytest.mark.asyncio
async def test_create_thread_with_messages(async_session: AsyncSession):
    """Test creating a thread with associated messages"""
    
    thread = Thread(
        id=str(uuid.uuid4()),
        object="thread",
        created_at=int(datetime.now().timestamp()),
        metadata_={"source": "test"}
    )
    
    async_session.add(thread)
    await async_session.commit()
    
    messages = []
    for i in range(3):
        message = Message(
            id=str(uuid.uuid4()),
            object="thread.message",
            created_at=int(datetime.now().timestamp()),
            thread_id=thread.id,
            role="user" if i % 2 == 0 else "assistant",
            content=f"Test message {i}",
            assistant_id="netra-assistant" if i % 2 == 1 else None,
            run_id=None,
            file_ids=[],
            metadata_={}
        )
        messages.append(message)
        async_session.add(message)
    
    await async_session.commit()
    
    result = await async_session.execute(
        select(Message).where(Message.thread_id == thread.id)
    )
    db_messages = result.scalars().all()
    
    assert len(db_messages) == 3
    assert all(msg.thread_id == thread.id for msg in db_messages)

@pytest.mark.asyncio
async def test_create_run_with_status_updates(async_session: AsyncSession):
    """Test creating and updating run status"""
    
    thread = Thread(
        id=str(uuid.uuid4()),
        object="thread",
        created_at=int(datetime.now().timestamp())
    )
    async_session.add(thread)
    
    run = Run(
        id=str(uuid.uuid4()),
        object="thread.run",
        created_at=int(datetime.now().timestamp()),
        thread_id=thread.id,
        assistant_id="netra-assistant",
        status="queued",
        required_action=None,
        last_error=None,
        expires_at=int((datetime.now() + timedelta(hours=1)).timestamp()),
        started_at=None,
        cancelled_at=None,
        failed_at=None,
        completed_at=None,
        model="gpt-4",
        instructions="Test instructions",
        tools=[{"type": "data_analysis"}],
        file_ids=[],
        metadata_={}
    )
    
    async_session.add(run)
    await async_session.commit()
    
    assert run.status == "queued"
    
    run.status = "in_progress"
    run.started_at = int(datetime.now().timestamp())
    await async_session.commit()
    
    result = await async_session.execute(
        select(Run).where(Run.id == run.id)
    )
    db_run = result.scalar_one()
    
    assert db_run.status == "in_progress"
    assert db_run.started_at is not None

@pytest.mark.asyncio
async def test_assistant_creation(async_session: AsyncSession):
    """Test creating an assistant"""
    
    assistant = Assistant(
        id="test-assistant",
        object="assistant",
        created_at=int(datetime.now().timestamp()),
        name="Test Assistant",
        description="A test assistant",
        model="gpt-4",
        instructions="You are a test assistant",
        tools=[
            {"type": "data_analysis"},
            {"type": "code_interpreter"}
        ],
        file_ids=[],
        metadata_={"version": "1.0"}
    )
    
    async_session.add(assistant)
    await async_session.commit()
    
    result = await async_session.execute(
        select(Assistant).where(Assistant.id == "test-assistant")
    )
    db_assistant = result.scalar_one()
    
    assert db_assistant.name == "Test Assistant"
    assert len(db_assistant.tools) == 2

@pytest.mark.asyncio
async def test_reference_storage(async_session: AsyncSession):
    """Test storing references for messages"""
    
    thread = Thread(
        id=str(uuid.uuid4()),
        object="thread",
        created_at=int(datetime.now().timestamp())
    )
    async_session.add(thread)
    
    message = Message(
        id=str(uuid.uuid4()),
        object="thread.message",
        created_at=int(datetime.now().timestamp()),
        thread_id=thread.id,
        role="assistant",
        content="Here is the analysis",
        assistant_id="netra-assistant"
    )
    async_session.add(message)
    
    reference = Reference(
        id=str(uuid.uuid4()),
        message_id=message.id,
        file_id="file-123",
        file_name="analysis.pdf",
        file_path="/data/analysis.pdf",
        quote="Important finding on page 5",
        metadata_={"page": 5, "confidence": 0.95}
    )
    async_session.add(reference)
    
    await async_session.commit()
    
    result = await async_session.execute(
        select(Reference).where(Reference.message_id == message.id)
    )
    db_reference = result.scalar_one()
    
    assert db_reference.file_name == "analysis.pdf"
    assert db_reference.metadata_["confidence"] == 0.95

@pytest.mark.asyncio
async def test_supply_catalog(async_session: AsyncSession):
    """Test supply catalog CRUD operations"""
    
    catalog_item = SupplyCatalog(
        id=str(uuid.uuid4()),
        provider="openai",
        model_name="gpt-4",
        model_variant="gpt-4-turbo",
        tier="premium",
        input_token_price=0.03,
        output_token_price=0.06,
        batch_input_token_price=0.015,
        batch_output_token_price=0.03,
        requests_per_minute_limit=500,
        tokens_per_minute_limit=150000,
        tokens_per_day_limit=5000000,
        context_window=128000,
        max_output_tokens=4096,
        training_data_cutoff=datetime(2023, 4, 1),
        supports_vision=True,
        supports_function_calling=True,
        supports_parallel_function_calling=True,
        metadata_={
            "features": ["streaming", "json_mode"],
            "deprecation_date": None
        }
    )
    
    async_session.add(catalog_item)
    await async_session.commit()
    
    result = await async_session.execute(
        select(SupplyCatalog).where(
            and_(
                SupplyCatalog.provider == "openai",
                SupplyCatalog.model_name == "gpt-4"
            )
        )
    )
    db_item = result.scalar_one()
    
    assert db_item.context_window == 128000
    assert db_item.supports_vision == True
    assert "streaming" in db_item.metadata_["features"]

@pytest.mark.asyncio
async def test_cascade_delete(async_session: AsyncSession):
    """Test cascade deletion of related records"""
    
    thread = Thread(
        id=str(uuid.uuid4()),
        object="thread",
        created_at=int(datetime.now().timestamp())
    )
    async_session.add(thread)
    
    message = Message(
        id=str(uuid.uuid4()),
        object="thread.message",
        created_at=int(datetime.now().timestamp()),
        thread_id=thread.id,
        role="user",
        content="Test message"
    )
    async_session.add(message)
    
    run = Run(
        id=str(uuid.uuid4()),
        object="thread.run",
        created_at=int(datetime.now().timestamp()),
        thread_id=thread.id,
        assistant_id="netra-assistant",
        status="completed"
    )
    async_session.add(run)
    
    await async_session.commit()
    
    await async_session.delete(thread)
    await async_session.commit()
    
    message_result = await async_session.execute(
        select(Message).where(Message.id == message.id)
    )
    assert message_result.scalar_one_or_none() is None
    
    run_result = await async_session.execute(
        select(Run).where(Run.id == run.id)
    )
    assert run_result.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_transaction_rollback(async_session: AsyncSession):
    """Test transaction rollback on error"""
    
    user = User(
        id=str(uuid.uuid4()),
        email=f"rollback_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=hash_password("password123")
    )
    
    async_session.add(user)
    
    try:
        await async_session.flush()
        
        raise Exception("Simulated error")
        
        await async_session.commit()
    except Exception:
        await async_session.rollback()
    
    result = await async_session.execute(
        select(User).where(User.id == user.id)
    )
    assert result.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_query_performance(async_session: AsyncSession):
    """Test query performance with indexes"""
    import time
    
    thread_ids = []
    for i in range(100):
        thread = Thread(
            id=str(uuid.uuid4()),
            object="thread",
            created_at=int(datetime.now().timestamp()),
            metadata_={"batch": i // 10}
        )
        async_session.add(thread)
        thread_ids.append(thread.id)
    
    await async_session.commit()
    
    start_time = time.time()
    
    result = await async_session.execute(
        select(Thread).where(Thread.id.in_(thread_ids[:50]))
    )
    threads = result.scalars().all()
    
    query_time = time.time() - start_time
    
    assert len(threads) == 50
    assert query_time < 1.0

@pytest.mark.asyncio
async def test_concurrent_updates(async_session: AsyncSession):
    """Test handling concurrent updates to same record"""
    
    user = User(
        id=str(uuid.uuid4()),
        email=f"concurrent_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=hash_password("password123"),
        full_name="Original Name"
    )
    
    async_session.add(user)
    await async_session.commit()
    
    result1 = await async_session.execute(
        select(User).where(User.id == user.id)
    )
    user1 = result1.scalar_one()
    
    result2 = await async_session.execute(
        select(User).where(User.id == user.id)
    )
    user2 = result2.scalar_one()
    
    user1.full_name = "Updated by Session 1"
    user2.full_name = "Updated by Session 2"
    
    await async_session.commit()
    await async_session.refresh(user1)
    
    assert user1.full_name in ["Updated by Session 1", "Updated by Session 2"]