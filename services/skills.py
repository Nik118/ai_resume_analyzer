import re
import spacy

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import spacy.cli
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# A naive list of skills for MVP. In a real app, you would use an LLM or a large taxonomy.
COMMON_SKILLS = {
    "python", "java", "c++", "javascript", "react", "node", "sql", "aws", "docker", 
    "kubernetes", "machine learning", "data science", "nlp", "fastapi", "django", 
    "flask", "git", "linux", "agile", "scrum", "html", "css", "c#", "azure", "gcp"
}

def extract_email(text: str) -> str:
    email_regex = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    match = re.search(email_regex, text)
    return match.group(0) if match else None

def extract_phone(text: str) -> str:
    phone_regex = r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
    match = re.search(phone_regex, text)
    return match.group(0) if match else None

def extract_skills(text: str) -> list[str]:
    # Basic skill extraction using keyword matching and Spacy NER
    extracted = set()
    doc = nlp(text.lower())
    
    # Keyword matching
    for token in doc:
        if token.text in COMMON_SKILLS:
            extracted.add(token.text)
            
    # Check multi-word skills
    text_lower = text.lower()
    for skill in COMMON_SKILLS:
        if " " in skill and skill in text_lower:
            extracted.add(skill)

    return list(extracted)
