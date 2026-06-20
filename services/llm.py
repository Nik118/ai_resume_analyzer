import json
from google import genai
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini client (it will automatically pick up GEMINI_API_KEY from env)
client = genai.Client()

class ExtractedInfo(BaseModel):
    summary: str
    experience_years: int
    education: str
    past_titles: list[str]

def extract_advanced_info(resume_text: str) -> dict:
    """
    Uses Gemini to extract summary, experience, education, and past titles from resume text.
    """
    prompt = f"""
    Analyze the following resume text and extract the following information:
    1. A short, professional 2-3 sentence executive summary of the candidate.
    2. The total number of professional experience in years (integer only, 0 if none).
    3. The highest level of education attained (e.g. 'B.S. Computer Science', 'High School').
    4. A list of all past job titles held by the candidate.

    Resume Text:
    {resume_text}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': ExtractedInfo,
            },
        )
        # Using Structured Outputs (response_schema) guarantees correct JSON.
        # The SDK natively parses it into the Pydantic model at `response.parsed`
        if response.parsed:
            return response.parsed.model_dump()
        else:
            return json.loads(response.text)
    except Exception as e:
        print(f"LLM Extraction failed: {e}")
        return {
            "summary": "Failed to generate summary.",
            "experience_years": 0,
            "education": "Unknown",
            "past_titles": []
        }
