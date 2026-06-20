from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
import json
import zipfile
import io
import csv

from db import models, database
from services import parser, skills, ranker, llm

# Database tables will be managed by Alembic migrations now

app = FastAPI(title="AI Resume Screening API")

# --- Schemas ---
class JobDescription(BaseModel):
    description: str

class CandidateResponse(BaseModel):
    id: int
    filename: str
    email: str | None
    phone: str | None
    skills: list[str]
    summary: str | None
    experience_years: int | None
    education: str | None
    past_titles: list[str] | None

    model_config = ConfigDict(from_attributes=True)

class RankedCandidateResponse(CandidateResponse):
    score: float
    pros: list[str]
    cons: list[str]

# --- Endpoints ---
def _format_resume(c: models.Resume) -> dict:
    try:
        past_titles = json.loads(c.past_titles) if c.past_titles else []
        if not isinstance(past_titles, list):
            past_titles = []
    except json.JSONDecodeError:
        past_titles = []
        
    try:
        skills_list = json.loads(c.skills) if c.skills else []
    except json.JSONDecodeError:
        skills_list = []
        
    return {
        "id": c.id,
        "filename": c.filename,
        "email": c.email,
        "phone": c.phone,
        "skills": skills_list,
        "summary": c.summary,
        "experience_years": c.experience_years,
        "education": c.education,
        "past_titles": past_titles
    }

@app.post("/upload/", response_model=CandidateResponse)
def upload_resume(file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    if not (file.filename.lower().endswith('.pdf') or file.filename.lower().endswith('.docx')):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")
        
    contents = file.file.read()
    
    return process_single_resume(contents, file.filename, db)

def process_single_resume(contents: bytes, filename: str, db: Session):
    try:
        # 1. Parse text
        extracted_text = parser.extract_text(contents, filename)
        
        # 2. Extract basic information
        email = skills.extract_email(extracted_text)
        phone = skills.extract_phone(extracted_text)
        extracted_skills = skills.extract_skills(extracted_text)
        
        # 3. Extract advanced info via LLM
        advanced_info = llm.extract_advanced_info(extracted_text)
        past_titles = advanced_info.get("past_titles") or []
        
        # 4. Save to database
        db_resume = models.Resume(
            filename=filename,
            extracted_text=extracted_text,
            email=email,
            phone=phone,
            skills=json.dumps(extracted_skills),
            summary=advanced_info.get("summary"),
            experience_years=advanced_info.get("experience_years"),
            education=advanced_info.get("education"),
            past_titles=json.dumps(past_titles)
        )
        db.add(db_resume)
        db.commit()
        db.refresh(db_resume)
        
        return CandidateResponse(**_format_resume(db_resume))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing {filename}: {str(e)}")

@app.post("/upload/batch/", response_model=list[CandidateResponse])
def upload_batch_resumes(file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    if not file.filename.lower().endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only ZIP files are supported for batch upload.")
        
    contents = file.file.read()
    results = []
    
    try:
        with zipfile.ZipFile(io.BytesIO(contents)) as z:
            for zip_info in z.infolist():
                if zip_info.is_dir() or zip_info.filename.startswith('__MACOSX/'):
                    continue
                if zip_info.filename.lower().endswith('.pdf') or zip_info.filename.lower().endswith('.docx'):
                    file_bytes = z.read(zip_info.filename)
                    # Use only the base filename
                    base_filename = zip_info.filename.split('/')[-1]
                    res = process_single_resume(file_bytes, base_filename, db)
                    results.append(res)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file.")
        
    return results

@app.get("/candidates/{candidate_id}", response_model=CandidateResponse)
def get_candidate(candidate_id: int, db: Session = Depends(database.get_db)):
    db_resume = db.query(models.Resume).filter(models.Resume.id == candidate_id).first()
    if db_resume is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    return CandidateResponse(**_format_resume(db_resume))

@app.get("/candidates/", response_model=list[CandidateResponse])
def list_candidates(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    candidates = db.query(models.Resume).offset(skip).limit(limit).all()
    return [_format_resume(c) for c in candidates]

@app.post("/rank/", response_model=list[RankedCandidateResponse])
def rank_candidates_endpoint(job: JobDescription, db: Session = Depends(database.get_db)):
    candidates = db.query(models.Resume).all()
    if not candidates:
        return []
        
    candidate_list = []
    for c in candidates:
        formatted = _format_resume(c)
        formatted["text"] = c.extracted_text
        candidate_list.append(formatted)
        
    jd_skills = skills.extract_skills(job.description)
    ranked = ranker.rank_candidates(job.description, jd_skills, candidate_list)
    
    response = []
    for r in ranked:
        response.append(RankedCandidateResponse(**r))
        
    return response

@app.post("/rank/export/")
def export_ranked_candidates_csv(job: JobDescription, db: Session = Depends(database.get_db)):
    ranked_candidates = rank_candidates_endpoint(job, db)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "ID", "Filename", "Score", "Email", "Phone", "Experience Years", 
        "Education", "Summary", "Pros", "Cons", "Skills", "Past Titles"
    ])
    
    for c in ranked_candidates:
        writer.writerow([
            c.id, 
            c.filename, 
            round(c.score, 4), 
            c.email, 
            c.phone, 
            c.experience_years,
            c.education,
            c.summary,
            ", ".join(c.pros),
            ", ".join(c.cons),
            ", ".join(c.skills),
            ", ".join(c.past_titles) if c.past_titles else ""
        ])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ranked_candidates.csv"}
    )
