# app/services/generation_worker.py

import os
import google.generativeai as genai
from ..config import settings

model = None

def init_worker():
    """Initializes the generative model for each worker process."""
    global model
    try:
        gemini_api_key = settings.llm_configs['default'].api_key
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY not set")
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel(settings.llm_configs['default'].model_name)
    except (ImportError, ValueError) as e:
        # Handle initialization error, maybe log it
        print(f"Worker initialization failed: {e}")
        # Or raise an exception to stop the pool
        raise

def generate_content_for_worker(task_data):
    """The actual content generation function that runs in a worker process."""
    if model is None:
        raise RuntimeError("Model not initialized in worker.")
        
    w_type, generation_config_dict = task_data
    
    # Re-create the GenerationConfig object from the dictionary
    generation_config = genai.types.GenerationConfig(**generation_config_dict)

    # This is a simplified stand-in for your actual content generation logic
    # You would replace this with the logic from your original `generate_content_sample`
    from ..data.synthetic.content_generator import META_PROMPTS, generate_content_sample

    # Since generate_content_sample expects the model, we pass the global one
    return generate_content_sample(w_type, model, generation_config)
