from langchain_openai import ChatOpenAI
from app.config import settings

def get_default_model():
    return ChatOpenAI(model_name="gpt-4", openai_api_key=settings.openai_api_key, temperature=0.7)