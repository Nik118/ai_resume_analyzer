# AI Resume Analyzer

An AI-powered application to screen, parse, and rank resumes against job descriptions.

## Features

- **Resume Parsing**: Automatically extract text from `.pdf` and `.docx` resume files.
- **Skill & Information Extraction**: Uses NLP (`spacy`) to extract contact information (email, phone) and technical skills from unstructured resume text.
- **Candidate Ranking**: Uses sentence embeddings (`sentence-transformers`) to semantically match extracted candidate profiles against a target job description, generating a ranked list of the best matches.
- **RESTful API**: Built with FastAPI for high performance, featuring auto-generated interactive documentation.

## How to Run

### Prerequisites
- Python 3.10+

### Setup Instructions

1. **Navigate into the directory**:
   ```bash
   cd ai_resume_analyzer
   ```

2. **Create a virtual environment and activate it**:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install the dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Download the required Spacy language model**:
   ```bash
   python -m spacy download en_core_web_sm
   ```

5. **Run the FastAPI server**:
   ```bash
   uvicorn main:app --reload
   ```

### Usage

Once the server is running, you can access the interactive API documentation at:
http://127.0.0.1:8000/docs

Here, you can:
- Use the `POST /upload/` endpoint to upload candidate resumes (`.pdf` or `.docx`).
- Use the `GET /candidates/` endpoint to view the parsed data.
- Use the `POST /rank/` endpoint to supply a job description and receive a ranked list of candidates based on semantic matching.