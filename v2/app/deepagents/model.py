from langchain_google_genai import ChatGoogleGenerativeAI
from ...config import settings

def get_default_model():
    return ChatGoogleGenerativeAI(model=settings.google_model.analysis_model, google_api_key=settings.google_model.gemini_api_key, temperature=0.7)