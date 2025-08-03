
import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import json
from app.services.generation_service import run_content_generation_job, run_log_generation_job, GENERATION_JOBS

class TestGenerationService(unittest.TestCase):

    def setUp(self):
        # Reset the jobs dictionary before each test
        GENERATION_JOBS.clear()

    @patch('app.services.generation_service.cpu_count')
    @patch('app.services.generation_service.Pool')
    @patch('app.services.generation_service.genai')
    def test_run_content_generation_job_success(self, mock_genai, mock_pool, mock_cpu_count):
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
        run_content_generation_job(job_id, params)

        # Assert that the job was completed successfully
        self.assertEqual(GENERATION_JOBS[job_id]['status'], 'completed')
        self.assertIn('result_path', GENERATION_JOBS[job_id])
        self.assertIn('summary', GENERATION_JOBS[job_id])

    @patch('app.services.generation_service.os.getenv')
    def test_run_content_generation_job_no_api_key(self, mock_getenv):
        # Mock the environment variable to simulate the API key not being set
        mock_getenv.return_value = None

        # Define the job parameters
        job_id = 'test_content_job_no_key'
        params = {}

        # Run the job
        run_content_generation_job(job_id, params)

        # Assert that the job failed
        self.assertEqual(GENERATION_JOBS[job_id]['status'], 'failed')
        self.assertEqual(GENERATION_JOBS[job_id]['progress']['error'], 'GEMINI_API_KEY not set')

    @patch('app.services.generation_service.cpu_count')
    @patch('app.services.generation_service.Pool')
    @patch('app.services.generation_service.open', new_callable=mock_open, read_data='{}')
    @patch('app.services.generation_service.os.path.exists')
    def test_run_log_generation_job_success(self, mock_exists, mock_file, mock_pool, mock_cpu_count):
        # Mock the necessary dependencies
        mock_cpu_count.return_value = 4
        mock_exists.return_value = True
        mock_pool.return_value.__enter__.return_value.imap_unordered.return_value = [
            # Mock a dataframe
            MagicMock()
        ]

        # Define the job parameters
        job_id = 'test_log_job'
        params = {
            'num_logs': 10,
            'max_cores': 2,
            'corpus_id': 'test_corpus'
        }

        # Run the job
        run_log_generation_job(job_id, params)

        # Assert that the job was completed successfully
        self.assertEqual(GENERATION_JOBS[job_id]['status'], 'completed')
        self.assertIn('result_path', GENERATION_JOBS[job_id])
        self.assertIn('summary', GENERATION_JOBS[job_id])

    @patch('app.services.generation_service.os.path.exists')
    def test_run_log_generation_job_no_corpus(self, mock_exists):
        # Mock the os.path.exists to simulate the corpus not being found
        mock_exists.return_value = False

        # Define the job parameters
        job_id = 'test_log_job_no_corpus'
        params = {
            'corpus_id': 'non_existent_corpus'
        }

        # Run the job
        run_log_generation_job(job_id, params)

        # Assert that the job failed
        self.assertEqual(GENERATION_JOBS[job_id]['status'], 'failed')
        self.assertIn('Content corpus', GENERATION_JOBS[job_id]['progress']['error'])

if __name__ == '__main__':
    unittest.main()
