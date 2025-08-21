# app/services/generation_worker.py

from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.config import settings
from netra_backend.app.data.synthetic.content_generator import generate_content_sample
from netra_backend.app.logging_config import central_logger as logger

llm_manager = None

def init_worker():
    """Initializes the generative model for each worker process."""
    global llm_manager
    try:
        llm_manager = LLMManager(settings)
    except Exception as e:
        logger.error(f"Worker initialization failed: {e}")
        raise

def generate_content_for_worker(task_data):
    """The actual content generation function that runs in a worker process."""
    if llm_manager is None:
        raise RuntimeError("LLMManager not initialized in worker.")
        
    w_type, generation_config_dict = task_data
    
    # Get the LLM from the manager
    llm = llm_manager.get_llm('default', generation_config=generation_config_dict)

    # generate_content_sample is now expecting a langchain model
    return generate_content_sample(w_type, llm)