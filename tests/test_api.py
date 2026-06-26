from io import BytesIO

import pytest


def create_dummy_pdf():
    # pdfplumber requires a valid PDF structure, so we create a minimal valid PDF using reportlab
    # Wait, reportlab is not in requirements. Since we just need bytes, let's mock parser.extract_text instead
    # to avoid needing complex PDF generation libraries just for testing.
    return b"%PDF-1.4\n%EOF\n"


@pytest.fixture(autouse=True)
def mock_parser(monkeypatch):
    from services import parser

    def dummy_extract(contents, filename):
        return "Software Engineer with 5 years python experience. john@example.com (555) 123-4567"

    monkeypatch.setattr(parser, "extract_text", dummy_extract)


def test_upload_resume(client):
    file_content = create_dummy_pdf()
    response = client.post(
        "/upload/", files={"file": ("resume.pdf", file_content, "application/pdf")}
    )
    if response.status_code != 200:
        print("ERROR:", response.json())
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "resume.pdf"
    assert data["email"] == "john@example.com"
    assert data["phone"] == "(555) 123-4567"
    assert "python" in data["skills"]
    # LLM Mock checks
    assert data["experience_years"] == 5
    assert data["education"] == "B.S. Computer Science"


def test_list_candidates(client):
    # First upload one
    test_upload_resume(client)

    response = client.get("/candidates/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["email"] == "john@example.com"


def test_rank_candidates_endpoint(client):
    # Upload one
    test_upload_resume(client)

    jd_payload = {"description": "Looking for a python developer."}
    response = client.post("/rank/", json=jd_payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["filename"] == "resume.pdf"
    assert "python" in data[0]["pros"]
