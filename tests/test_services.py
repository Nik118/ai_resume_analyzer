from services import ranker, skills


def test_extract_email():
    text = "Contact me at john.doe@example.com for more info."
    assert skills.extract_email(text) == "john.doe@example.com"

    text_no_email = "Call me at 555-1234."
    assert skills.extract_email(text_no_email) is None


def test_extract_phone():
    text = "My phone is (555) 123-4567."
    assert skills.extract_phone(text) == "(555) 123-4567"

    text2 = "Call 555.123.4567 today."
    assert skills.extract_phone(text2) == "555.123.4567"


def test_extract_skills():
    text = "I have 5 years of experience in Python and C++. Also familiar with Docker."
    extracted = skills.extract_skills(text)
    assert "python" in extracted
    assert "c++" in extracted
    assert "docker" in extracted
    assert "java" not in extracted


def test_rank_candidates():
    jd = "Looking for a Python backend engineer with FastAPI and Docker experience."
    jd_skills = ["python", "fastapi", "docker"]

    candidates = [
        {
            "id": 1,
            "text": "I write Python and build APIs using FastAPI.",
            "skills": ["python", "fastapi"],
        },
        {
            "id": 2,
            "text": "Java and Spring Boot developer. Some SQL.",
            "skills": ["java", "sql"],
        },
        {
            "id": 3,
            "text": "Expert in Python, Docker, FastAPI, and Kubernetes.",
            "skills": ["python", "docker", "fastapi", "kubernetes"],
        },
    ]

    ranked = ranker.rank_candidates(jd, jd_skills, candidates)

    # Candidate 3 should be ranked first because they have all skills
    assert ranked[0]["id"] == 3
    assert "python" in ranked[0]["pros"]
    assert "docker" in ranked[0]["pros"]
    assert "fastapi" in ranked[0]["pros"]
    assert len(ranked[0]["cons"]) == 0

    # Candidate 2 should be ranked last
    assert ranked[-1]["id"] == 2
    assert "java" not in ranked[-1]["pros"]  # Java is not a pros for this JD
    assert "python" in ranked[-1]["cons"]
