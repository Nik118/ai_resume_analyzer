import json
import datetime
from google import genai
from pydantic import BaseModel

client = genai.Client()

class ExtractedInfo(BaseModel):
    summary: str
    experience_years: int
    education: str
    past_titles: list[str]
    ats_score: int
    strengths: list[str]
    weaknesses: list[str]
    room_for_improvements: list[str]

class TailoredResume(BaseModel):
    summary: str
    bullets: list[str]

class InterviewPrep(BaseModel):
    questions: list[str]

class CompanyInsights(BaseModel):
    insights: list[str]

def extract_advanced_info(resume_text: str) -> dict:
    current_date = datetime.date.today().strftime("%B %Y")
    
    prompt = f"""
    Analyze the following resume text and extract the following information:
    1. A short, professional 2-3 sentence executive summary of the candidate.
    2. The total number of professional experience in years (integer only). Calculate this by carefully summing the duration of all work experiences listed. Assume the current date is {current_date} for any roles marked 'Present' or 'Current'.
    3. The highest level of education attained, including the institution name (e.g. 'B.S. Computer Science from MIT').
    4. A list of all past job titles held by the candidate.
    5. An estimated ATS Score from 0 to 100 based on standard industry criteria (impact, keywords, completeness).
    6. A list of 3 key strengths of the candidate.
    7. A list of 3 potential weaknesses or areas for improvement.
    8. 'room_for_improvements': A list of 3-4 actionable bullet points on basic mistakes in the resume and how to fix them to boost the ATS score (e.g. formatting, metrics, cliches).

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
        if response.parsed:
            return response.parsed.model_dump()
        else:
            return json.loads(response.text)
    except Exception as e:
        print(f"LLM Extraction failed: {e}")
        return {
            "summary": f"Failed: {str(e)}",
            "experience_years": 0,
            "education": "Unknown",
            "past_titles": [],
            "ats_score": 0,
            "strengths": [],
            "weaknesses": [],
            "room_for_improvements": []
        }

def tailor_resume(resume_text: str, jd_text: str) -> dict:
    prompt = f"""
    You are an expert technical recruiter and resume writer. 
    Your goal is to tailor the candidate's resume to perfectly match the provided Job Description.
    Do NOT invent or fabricate any experience. Only rephrase, emphasize, and highlight the existing skills and experiences that are relevant to the JD.

    Job Description:
    {jd_text}

    Original Resume:
    {resume_text}

    Please provide:
    1. A new, tailored executive summary (2-3 sentences) that positions the candidate perfectly for this role.
    2. A list of 5-7 tailored bullet points that rewrite their existing experience to strongly highlight the keywords and requirements in the JD. Use strong action verbs.
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': TailoredResume,
            },
        )
        if response.parsed:
            return response.parsed.model_dump()
        else:
            return json.loads(response.text)
    except Exception as e:
        print(f"LLM Tailoring failed: {e}")
        return {"summary": "", "bullets": []}

def generate_cover_letter(resume_text: str, jd_text: str) -> str:
    prompt = f"""
    You are an expert career coach. Write a compelling, professional cover letter (3-4 paragraphs) for the candidate applying to this job.
    Bridge their background from the resume to the requirements of the job description. Do not use generic placeholders like [Company Name], infer as much as possible, or write it so that placeholders aren't needed if info is missing.

    Job Description:
    {jd_text}

    Original Resume:
    {resume_text}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"LLM Cover Letter failed: {e}")
        return ""

def generate_interview_prep(resume_text: str, jd_text: str) -> list[str]:
    prompt = f"""
    You are a hiring manager for this job. Based on the candidate's resume and the job description, 
    identify the skill gaps or the most critical technical areas they will be tested on.
    Generate a list of exactly 5 probable, specific interview questions (technical or behavioral) that you would ask this candidate to grill them.

    Job Description:
    {jd_text}

    Original Resume:
    {resume_text}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': InterviewPrep,
            },
        )
        if response.parsed:
            return response.parsed.model_dump().get("questions", [])
        else:
            return json.loads(response.text).get("questions", [])
    except Exception as e:
        print(f"LLM Interview Prep failed: {e}")
        return []

def generate_resume_roast(resume_text: str) -> str:
    prompt = f"""
    You are a brutally honest, no-nonsense hiring manager who has seen a million terrible resumes.
    "Roast" this candidate's resume. Point out cliches, fluff, weak bullet points, and anything else that makes you roll your eyes.
    Be witty, funny, but ultimately provide some tough love that they actually need to hear to improve.
    Keep it to 2 short paragraphs.

    Original Resume:
    {resume_text}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"LLM Roast failed: {e}")
        return ""

class JDAnalysis(BaseModel):
    company_name: str | None
    fit_score: int
    aligned_skills: list[str]
    missing_skills: list[str]
    jd_positives: list[str]
    jd_negatives: list[str]

def analyze_job_fit(resume_text: str, jd_text: str, company_text: str) -> dict:
    jd_prompt = f"""
    You are an expert career strategist and tech recruiter. Analyze the fit between the candidate's resume and the job description.
    Original Resume:
    {resume_text}

    Job Description:
    {jd_text}

    Please provide:
    1. 'company_name': The name of the company hiring for this role, or null if it cannot be found.
    2. 'fit_score': An integer from 0 to 100 representing how well the resume matches the job description.
    3. 'aligned_skills': A list of exactly 3-5 key skills the candidate possesses that match the JD perfectly.
    4. 'missing_skills': A list of exactly 2-4 critical skills mentioned in the JD that the candidate lacks.
    5. 'jd_positives': A list of 2-3 green flags about the job description (e.g., clear requirements, salary posted, realistic expectations).
    6. 'jd_negatives': A list of 2-3 red flags about the job description (e.g., "fast-paced" implying chaotic, vague responsibilities, "unicorn" requirements).
    """
    
    company_prompt = f"""
    You are a career researcher. Identify the company from this job description:
    {jd_text}
    Or from this URL text:
    {company_text}

    Use Google Search to look up the company's employee reviews and recent news (e.g., search for "[Company Name] reviews Glassdoor Blind layoffs"). 
    Summarize 3-4 specific bullet points regarding the quality of the company, specifically looking for:
    - Recent layoffs or high churn
    - Salary competitiveness and growth opportunities
    - Overall work culture and stability
    If no information exists, state that.
    """
    
    result = {
        "company_name": None,
        "fit_score": 0,
        "aligned_skills": [],
        "missing_skills": [],
        "jd_positives": ["Analysis failed."],
        "jd_negatives": ["Analysis failed."],
        "company_stability_insights": ["Analysis failed."]
    }
    
    try:
        jd_response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=jd_prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': JDAnalysis,
            },
        )
        if jd_response.parsed:
            result.update(jd_response.parsed.model_dump())
        else:
            result.update(json.loads(jd_response.text))
            
    except Exception as e:
        print(f"LLM JD Analysis failed: {e}")
        raise ValueError(f"LLM Analysis failed: {str(e)}")

    try:
        company_response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=company_prompt,
            config={
                'tools': [{'google_search': {}}],
                'response_mime_type': 'application/json',
                'response_schema': CompanyInsights,
            },
        )
        if company_response.parsed:
            result["company_stability_insights"] = company_response.parsed.model_dump().get("insights", [])
        else:
            result["company_stability_insights"] = json.loads(company_response.text).get("insights", [])
            
    except Exception as e:
        print(f"LLM Company Analysis failed: {e}")
        result["company_stability_insights"] = ["Could not fetch company insights."]
        
    return result
