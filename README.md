# AI Resume Analyzer

An AI-powered application to screen, parse, and tailor resumes against job descriptions using Google's Gemini LLM.

## Features

- **Resume Parsing**: Automatically extract text from `.pdf` and `.docx` resume files.
- **LLM-Powered Analysis**: Uses Google Gemini to extract contact information, technical skills, strengths, weaknesses, and ATS scores from unstructured resume text.
- **Job Matching**: Analyzes a candidate's resume against a Job Description (JD) to calculate a "Fit Score", highlighting aligned skills and missing skills.
- **Tailoring & Generation**: Automatically tailors resume bullet points, generates cover letters, and creates custom interview prep questions based on the specific job target.
- **Brutal Roasts**: A fun feature to get a brutal, humorous roast of a resume from the AI.
- **RESTful API & Kanban UI**: Built with FastAPI for high performance, featuring an integrated Kanban-board frontend for tracking job applications.

## How to Run

### Prerequisites
- Python 3.10+
- PostgreSQL database
- Google Gemini API Key (`GEMINI_API_KEY`)

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

4. **Environment Variables**:
   Create a `.env` file in the root directory:
   ```env
   DATABASE_URL=postgresql://user:password@localhost/ai_resume_analyzer
   GEMINI_API_KEY=your_gemini_api_key_here
   ADMIN_SECRET=superadmin
   ```

5. **Database Migrations**:
   ```bash
   alembic upgrade head
   ```

6. **Run the FastAPI server**:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### API Endpoints

Once the server is running, access the interactive API documentation at `http://127.0.0.1:8000/docs`.

**Core Endpoints:**
- `GET /`: Serves the Kanban frontend UI.
- `GET /health`: Uptime monitoring endpoint.
- `POST /resumes/`: Upload and parse a new candidate resume (`.pdf` or `.docx`).
- `GET /resumes/`: List all uploaded resumes.
- `DELETE /resumes/{id}`: Delete a resume and cascade-delete its job targets.
- `GET /resumes/{id}/analytics`: Get a summary of missing skills across all applied jobs.
- `POST /resumes/{id}/roast`: Generate a brutal AI roast of the resume.

**Job Target Endpoints:**
- `POST /resumes/{id}/jobs`: Analyze a resume against a new Job Description.
- `GET /resumes/{id}/jobs`: Get all job targets for a specific resume.
- `PATCH /job_targets/{id}/status`: Update the Kanban status of a job application.
- `POST /job_targets/{id}/refresh`: Re-run the LLM analysis for a job target.
- `POST /job_targets/{id}/tailor`: Auto-tailor resume bullet points for this specific job.
- `POST /job_targets/{id}/cover_letter`: Generate a custom cover letter.
- `POST /job_targets/{id}/interview_prep`: Generate probable interview questions.
- `DELETE /job_targets/{id}`: Delete a job target.