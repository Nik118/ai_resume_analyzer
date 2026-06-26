import re

COMMON_SKILLS = {
    "python",
    "java",
    "c++",
    "javascript",
    "react",
    "node",
    "sql",
    "aws",
    "docker",
    "kubernetes",
    "machine learning",
    "data science",
    "nlp",
    "fastapi",
    "django",
    "flask",
    "git",
    "linux",
    "agile",
    "scrum",
    "html",
    "css",
    "c#",
    "azure",
    "gcp",
}

# Precompile regex patterns for performance optimization
SKILL_PATTERNS = {}
for skill in COMMON_SKILLS:
    if skill in ["c++", "c#"]:
        # For skills with special chars, avoid standard word boundaries which might fail
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(skill) + r"(?![a-zA-Z0-9])"
    else:
        pattern = r"\b" + re.escape(skill) + r"\b"
    SKILL_PATTERNS[skill] = re.compile(pattern)


def extract_email(text: str) -> str | None:
    email_regex = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    match = re.search(email_regex, text)
    return match.group(0) if match else None


def extract_phone(text: str) -> str | None:
    phone_regex = r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
    match = re.search(phone_regex, text)
    return match.group(0) if match else None


def extract_skills(text: str) -> list[str]:
    text_lower = text.lower()
    # Fast whole-word matching using precompiled regex
    extracted = [
        skill for skill, pattern in SKILL_PATTERNS.items() if pattern.search(text_lower)
    ]
    return extracted
