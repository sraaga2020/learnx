import os
from dotenv import load_dotenv
from openai import OpenAI

# Force fresh environment variables loading from your local .env file
load_dotenv(override=True)

# Fetch the Groq API key
api_key = os.getenv("GROQ_API_KEY")

# Initialize the standard client, pointing it to Groq's endpoint
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=api_key
)

def gem3(prompt: str) -> str:
    """
    Unified communication wrapper for Career Granny.
    Routes queries directly to Meta's Llama 3.3 70B via Groq's ultra-fast API.
    """
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # High-quality flagship model on Groq
            messages=[
                {"role": "user", "content": prompt}
            ],
            stream=False,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Groq API Error: {str(e)}"
