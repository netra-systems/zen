"""E2E Tests for Model Selection Example Messages



Tests model selection related example prompts (5 remaining prompts)

with real message submission and processing. No mocks used.



Business Value: Validates model selection guidance for users

"""



from datetime import datetime, timezone

from typing import Any, Dict

from uuid import uuid4

from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig

from shared.isolated_environment import IsolatedEnvironment





import pytest



from netra_backend.app.handlers.example_message_handler import ExampleMessageHandler



# Model selection prompts from SPEC/exampleNetraPrompts.xml

MODEL_SELECTION_PROMPTS = [

    {

        "id": "model_effectiveness",

        "content": "I'm considering using the new 'gpt-4o' and LLMModel.GEMINI_2_5_FLASH.value models. How effective would they be in my current setup?",

        "category": "model-selection",

        "complexity": "intermediate"

    },

    {

        "id": "kv_cache_audit",

        "content": "I want to audit all uses of KV caching in my system to find optimization opportunities.",

        "category": "advanced",

        "complexity": "advanced"

    },

    {

        "id": "multi_objective_optimization",

        "content": "I need to reduce costs by 20% and improve latency by 2x. I'm also expecting a 30% increase in usage. What should I do?",

        "category": "cost-optimization",

        "complexity": "advanced"

    },

    {

        "id": "gpt5_migration",

        "content": "@Netra which of our Agent tools should switch to GPT-5? Which versions? What to set the verbosity to?",

        "category": "model-selection",

        "complexity": "advanced"

    },

    {

        "id": "upgrade_analysis",

        "content": "@Netra was the upgrade yesterday to GPT-5 worth it? Rollback anything where quality didn't improve much but cost was higher",

        "category": "model-selection",

        "complexity": "intermediate"

    }

]





@pytest.fixture

async def example_handler():

    """Get example message handler instance"""

    return ExampleMessageHandler()





@pytest.fixture 

@pytest.mark.e2e

async def test_user_id():

    """Generate test user ID"""

    return f"test_user_{uuid4()}"





@pytest.mark.e2e

class TestModelSelectionPrompts:

    """Test model selection example prompts"""



    @pytest.mark.e2e

    async def test_model_effectiveness_evaluation(self, example_handler, test_user_id):

        """Test model effectiveness evaluation prompt"""

        prompt = MODEL_SELECTION_PROMPTS[0]

        message_id = str(uuid4())

        

        request = self._create_request(prompt, message_id, test_user_id)

        response = await example_handler.handle_example_message(request)

        

        assert response.status == "completed"

        assert response.result is not None

        assert "model" in response.result.get("optimization_type", "").lower()



    @pytest.mark.e2e

    async def test_kv_cache_audit_prompt(self, example_handler, test_user_id):

        """Test KV cache audit prompt"""

        prompt = MODEL_SELECTION_PROMPTS[1]

        message_id = str(uuid4())

        

        request = self._create_request(prompt, message_id, test_user_id)

        response = await example_handler.handle_example_message(request)

        

        assert response.status == "completed"

        assert response.result.get("agent_name") is not None



    @pytest.mark.e2e

    async def test_multi_objective_optimization_prompt(self, example_handler, test_user_id):

        """Test multi-objective optimization prompt"""

        prompt = MODEL_SELECTION_PROMPTS[2]

        message_id = str(uuid4())

        

        request = self._create_request(prompt, message_id, test_user_id)

        response = await example_handler.handle_example_message(request)

        

        assert response.status == "completed"

        assert "multi" in response.result.get("optimization_type", "").lower()



    @pytest.mark.e2e

    async def test_gpt5_migration_prompt(self, example_handler, test_user_id):

        """Test GPT-5 migration prompt"""

        prompt = MODEL_SELECTION_PROMPTS[3]

        message_id = str(uuid4())

        

        request = self._create_request(prompt, message_id, test_user_id)

        response = await example_handler.handle_example_message(request)

        

        assert response.status == "completed"

        assert response.result is not None



    @pytest.mark.e2e

    async def test_upgrade_analysis_prompt(self, example_handler, test_user_id):

        """Test upgrade worth analysis prompt"""

        prompt = MODEL_SELECTION_PROMPTS[4]

        message_id = str(uuid4())

        

        request = self._create_request(prompt, message_id, test_user_id)

        response = await example_handler.handle_example_message(request)

        

        assert response.status == "completed"

        assert response.result is not None



    def _create_request(self, prompt: Dict[str, Any], message_id: str, user_id: str) -> Dict[str, Any]:

        """Create example message request"""

        return {

            "content": prompt["content"],

            "example_message_id": message_id,

            "example_message_metadata": {

                "title": f"Test: {prompt['id']}",

                "category": prompt["category"],

                "complexity": prompt["complexity"],

                "businessValue": "conversion",

                "estimatedTime": "2-3 minutes"

            },

            "user_id": user_id,

            "timestamp": int(datetime.now(timezone.utc).timestamp())

        }





@pytest.mark.e2e

class TestModelSelectionBusinessValue:

    """Test business value tracking for model selection"""



    @pytest.mark.e2e

    async def test_model_selection_insights(self, example_handler, test_user_id):

        """Test business insights for model selection"""

        prompt = MODEL_SELECTION_PROMPTS[0]

        message_id = str(uuid4())

        

        request = self._create_request(prompt, message_id, test_user_id)

        response = await example_handler.handle_example_message(request)

        

        assert response.status == "completed"

        if response.business_insights:

            assert "business_value_type" in response.business_insights

            assert "performance_score" in response.business_insights



    @pytest.mark.e2e

    async def test_advanced_complexity_handling(self, example_handler, test_user_id):

        """Test handling of advanced complexity prompts"""

        advanced_prompts = [p for p in MODEL_SELECTION_PROMPTS if p["complexity"] == "advanced"]

        

        for prompt in advanced_prompts:

            message_id = str(uuid4())

            request = self._create_request(prompt, message_id, test_user_id)

            response = await example_handler.handle_example_message(request)

            

            assert response.status == "completed"

            assert response.processing_time_ms is not None



    def _create_request(self, prompt: Dict[str, Any], message_id: str, user_id: str) -> Dict[str, Any]:

        """Create example message request"""

        return {

            "content": prompt["content"],

            "example_message_id": message_id,

            "example_message_metadata": {

                "title": f"Test: {prompt['id']}",

                "category": prompt["category"],

                "complexity": prompt["complexity"],

                "businessValue": "retention",

                "estimatedTime": "3-4 minutes"

            },

            "user_id": user_id,

            "timestamp": int(datetime.now(timezone.utc).timestamp())

        }

