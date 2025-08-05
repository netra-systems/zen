import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, mock_open

import os
import json
from app.services.generation_service import run_content_generation_job, run_log_generation_job, GENERATION_JOBS
from app.config import settings

# Mark all tests in this file as asynchronous
pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
def clear_generation_jobs():
    """Fixture to automatically clear the GENERATION_JOBS dictionary before each test."""
    GENERATION_JOBS.clear()
    yield

@patch('app.services.generation_service.cpu_count')
@patch('app.services.generation_service.Pool')
@patch('app.data.synthetic.content_generator.genai')
async def test_run_content_generation_job_success(mock_genai, mock_pool, mock_cpu_count):
    # Mock the necessary dependencies
    mock_cpu_count.return_value = 4
    mock_genai.GenerativeModel.return_value = MagicMock()
    mock_pool.return_value.__enter__.return_value.imap_unordered.return_value = [
        {'type': 'simple_chat', 'data': ('What is AI?', 'AI is...')}
    ]

    # Set the required environment variable
    os.environ['GEMINI_API_KEY'] = 'test_key'

    # Define the job parameters
    job_id = 'test_content_job'
    params = {
        'samples_per_type': 1,
        'temperature': 0.7,
        'top_p': 0.9,
        'top_k': 40,
        'max_cores': 2
    }

    # Run the job
    with patch.object(settings, 'corpus_generation_model', 'gemini-1.5-flash'):
        run_content_generation_job(job_id, params)

    # Assert that the job was completed successfully
    assert GENERATION_JOBS[job_id]['status'] == 'completed'
    assert 'result_path' in GENERATION_JOBS[job_id]
    assert 'summary' in GENERATION_JOBS[job_id]

@patch('app.services.generation_service.os.getenv')
async def test_run_content_generation_job_no_api_key(mock_getenv):
    # Mock the environment variable to simulate the API key not being set
    mock_getenv.return_value = None

    # Define the job parameters
    job_id = 'test_content_job_no_key'
    params = {}

    # Run the job
    run_content_generation_job(job_id, params)

    # Assert that the job failed
    assert GENERATION_JOBS[job_id]['status'] == 'failed'
    assert GENERATION_JOBS[job_id]['error'] == 'GEMINI_API_KEY not set'

@patch('app.services.generation_service.cpu_count')
@patch('app.services.generation_service.Pool')
@patch('app.services.generation_service.open', new_callable=mock_open, read_data='{}')
@patch('app.services.generation_service.get_config')
@patch('app.services.generation_service.os.path.exists')
async def test_run_log_generation_job_success(mock_exists, mock_get_config, mock_file, mock_pool, mock_cpu_count):
    # Mock the necessary dependencies
    mock_cpu_count.return_value = 4
    mock_exists.return_value = True
    mock_pool.return_value.__enter__.return_value.imap_unordered.return_value = [
        pd.DataFrame({
            'trace_id': ['test_trace'],
            'span_id': ['test_span'],
            'app_name': ['test_app'],
            'service_name': ['test_service'],
            'model_provider': ['test_provider'],
            'model_name': ['test_model'],
            'model_pricing': [[0.0, 0.0]],
            'user_prompt': ['test_prompt'],
            'assistant_response': ['test_response'],
            'prompt_tokens': [1],
            'completion_tokens': [1],
            'total_tokens': [2],
            'prompt_cost': [0.0],
            'completion_cost': [0.0],
            'total_cost': [0.0],
            'total_e2e_ms': [1],
            'ttft_ms': [1],
            'user_id': ['test_user'],
            'organization_id': ['test_org']
        })
    ]

    # Define the job parameters
    job_id = 'test_log_job'
    params = {
        'num_logs': 10,
        'max_cores': 2,
        'corpus_id': 'test_corpus'
    }

    # Run the job
    with patch('app.services.generation_service.os.makedirs') as mock_makedirs:
        run_log_generation_job(job_id, params)

    # Assert that the job was completed successfully
    assert GENERATION_JOBS[job_id]['status'] == 'completed'
    assert 'result_path' in GENERATION_JOBS[job_id]
    assert 'summary' in GENERATION_JOBS[job_id]

@patch('app.services.generation_service.os.path.exists')
async def test_run_log_generation_job_no_corpus(mock_exists):
    # Mock the os.path.exists to simulate the corpus not being found
    mock_exists.return_value = False

    # Define the job parameters
    job_id = 'test_log_job_no_corpus'
    params = {
        'corpus_id': 'non_existent_corpus',
        'num_logs': 10
    }

    # Run the job
    run_log_generation_job(job_id, params)

    # Assert that the job failed
    assert GENERATION_JOBS[job_id]['status'] == 'failed'
    assert 'Content corpus' in GENERATION_JOBS[job_id]['error']