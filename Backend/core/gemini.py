import google.generativeai as genai
from config import GEMINI_KEY

genai.configure(api_key=GEMINI_KEY)

model = genai.GenerativeModel(
    model_name="models/gemini-2.0-flash"
)
