from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel

load_dotenv()


class ExtractedInfo(BaseModel):
    summary: str
    experience_years: int
    education: str
    past_titles: list[str]


try:
    client = genai.Client()
    prompt = "Resume:\n"
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": ExtractedInfo,
        },
    )
    print("SUCCESS")
except Exception as e:
    print("ERROR:", e)
