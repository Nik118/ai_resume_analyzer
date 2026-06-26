import json
import os

from dotenv import load_dotenv

load_dotenv()
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from db import database, models
from services import llm, parser, scraper, skills

app = FastAPI()

# Simple in-memory rate limiter for Gemini
IP_REFRESH_COUNTS = {}
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "superadmin")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")


# --- Schemas ---
class ResumeVersionResponse(BaseModel):
    id: int
    filename: str
    email: str | None
    phone: str | None
    skills: list[str]
    summary: str | None
    experience_years: int | None
    education: str | None
    past_titles: list[str] | None
    ats_score: int | None
    strengths: list[str] | None
    weaknesses: list[str] | None
    room_for_improvements: list[str] | None

    model_config = ConfigDict(from_attributes=True)


class JobTargetResponse(BaseModel):
    id: int
    resume_id: int
    job_description: str
    company_url: str | None
    company_name: str | None
    fit_score: int | None
    aligned_skills: list[str] | None
    missing_skills: list[str] | None
    jd_positives: list[str] | None
    jd_negatives: list[str] | None
    company_stability_insights: list[str] | None
    tailored_summary: str | None
    tailored_bullets: list[str] | None
    cover_letter: str | None
    interview_prep: list[dict] | None
    status: str

    model_config = ConfigDict(from_attributes=True)


class JDAnalyzePayload(BaseModel):
    job_description: str
    company_url: str | None = None


def _safe_json_loads(value, default=None):
    """Safely parse a JSON string, returning default on failure."""
    if default is None:
        default = []
    if not value:
        return default
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else [str(parsed)]
    except (json.JSONDecodeError, TypeError):
        return [value] if value else default


def _format_resume(c: models.ResumeVersion) -> dict:
    return {
        "id": c.id,
        "filename": c.filename,
        "email": c.email,
        "phone": c.phone,
        "skills": _safe_json_loads(c.skills),
        "summary": c.summary,
        "experience_years": c.experience_years,
        "education": c.education,
        "past_titles": _safe_json_loads(c.past_titles),
        "ats_score": c.ats_score,
        "strengths": _safe_json_loads(c.strengths),
        "weaknesses": _safe_json_loads(c.weaknesses),
        "room_for_improvements": _safe_json_loads(c.general_feedback),
    }


def _format_job_target(jt: models.JobTarget) -> dict:
    return {
        "id": jt.id,
        "resume_id": jt.resume_id,
        "job_description": jt.job_description,
        "company_url": jt.company_url,
        "company_name": jt.company_name,
        "fit_score": jt.fit_score,
        "aligned_skills": _safe_json_loads(jt.aligned_skills),
        "missing_skills": _safe_json_loads(jt.missing_skills),
        "jd_positives": _safe_json_loads(jt.jd_positives),
        "jd_negatives": _safe_json_loads(jt.jd_negatives),
        "company_stability_insights": _safe_json_loads(jt.company_stability_summary),
        "tailored_summary": jt.tailored_summary,
        "tailored_bullets": _safe_json_loads(jt.tailored_bullets),
        "cover_letter": jt.cover_letter,
        "interview_prep": _safe_json_loads(jt.interview_prep),
        "status": jt.status,
    }


# --- Endpoints ---


@app.get("/resumes/", response_model=list[ResumeVersionResponse])
def get_resumes(db: Session = Depends(database.get_db)):
    resumes = (
        db.query(models.ResumeVersion).order_by(models.ResumeVersion.id.desc()).all()
    )
    return [_format_resume(r) for r in resumes]


@app.post("/resumes/", response_model=ResumeVersionResponse)
def upload_resume(file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    if not (
        file.filename.lower().endswith(".pdf")
        or file.filename.lower().endswith(".docx")
    ):
        raise HTTPException(
            status_code=400, detail="Only PDF and DOCX files are supported."
        )

    contents = file.file.read()

    try:
        extracted_text = parser.extract_text(contents, file.filename)
        email = skills.extract_email(extracted_text)
        phone = skills.extract_phone(extracted_text)
        extracted_skills = skills.extract_skills(extracted_text)

        advanced_info = llm.extract_advanced_info(extracted_text)
        past_titles = advanced_info.get("past_titles") or []

        db_resume = models.ResumeVersion(
            filename=file.filename,
            extracted_text=extracted_text,
            email=email,
            phone=phone,
            skills=json.dumps(extracted_skills),
            summary=advanced_info.get("summary"),
            experience_years=advanced_info.get("experience_years"),
            education=advanced_info.get("education"),
            past_titles=json.dumps(past_titles),
            ats_score=advanced_info.get("ats_score"),
            strengths=json.dumps(advanced_info.get("strengths") or []),
            weaknesses=json.dumps(advanced_info.get("weaknesses") or []),
            general_feedback=json.dumps(
                advanced_info.get("room_for_improvements") or []
            ),
        )
        db.add(db_resume)
        db.commit()
        db.refresh(db_resume)

        return ResumeVersionResponse(**_format_resume(db_resume))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing {file.filename}: {str(e)}"
        )


@app.delete("/resumes/{resume_id}")
def delete_resume(resume_id: int, db: Session = Depends(database.get_db)):
    resume = (
        db.query(models.ResumeVersion)
        .filter(models.ResumeVersion.id == resume_id)
        .first()
    )
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    # Cascade delete all associated job targets
    db.query(models.JobTarget).filter(models.JobTarget.resume_id == resume_id).delete()
    db.delete(resume)
    db.commit()
    return {"status": "deleted"}


@app.post("/resumes/{resume_id}/roast")
def roast_resume(resume_id: int, db: Session = Depends(database.get_db)):
    resume = (
        db.query(models.ResumeVersion)
        .filter(models.ResumeVersion.id == resume_id)
        .first()
    )
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    roast = llm.generate_resume_roast(resume.extracted_text)
    return {"roast": roast}


# --- Job Target Endpoints ---


@app.get("/resumes/{resume_id}/jobs", response_model=list[JobTargetResponse])
def get_job_targets(resume_id: int, db: Session = Depends(database.get_db)):
    # Rank by fit_score descending
    jobs = (
        db.query(models.JobTarget)
        .filter(models.JobTarget.resume_id == resume_id)
        .order_by(models.JobTarget.fit_score.desc())
        .all()
    )
    return [_format_job_target(jt) for jt in jobs]


@app.post("/resumes/{resume_id}/jobs", response_model=JobTargetResponse)
async def analyze_job(
    resume_id: int, payload: JDAnalyzePayload, db: Session = Depends(database.get_db)
):
    resume = (
        db.query(models.ResumeVersion)
        .filter(models.ResumeVersion.id == resume_id)
        .first()
    )
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Scrape company info if URL provided
    company_text = ""
    if payload.company_url:
        company_text = await scraper.scrape_company_url(payload.company_url)

    # Analyze fit
    try:
        fit_data = llm.analyze_job_fit(
            resume.extracted_text, payload.job_description, company_text
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    jt = models.JobTarget(
        resume_id=resume.id,
        job_description=payload.job_description,
        company_url=payload.company_url,
        company_name=fit_data.get("company_name", "Unknown Company")
        or "Unknown Company",
        fit_score=fit_data.get("fit_score", 0),
        aligned_skills=json.dumps(fit_data.get("aligned_skills", [])),
        missing_skills=json.dumps(fit_data.get("missing_skills", [])),
        jd_positives=json.dumps(fit_data.get("jd_positives", [])),
        jd_negatives=json.dumps(fit_data.get("jd_negatives", [])),
        company_stability_summary=json.dumps(
            fit_data.get("company_stability_insights", [])
        ),
    )
    db.add(jt)
    db.commit()
    db.refresh(jt)

    return JobTargetResponse(**_format_job_target(jt))


@app.delete("/job_targets/{jt_id}")
def delete_job_target(jt_id: int, db: Session = Depends(database.get_db)):
    jt = db.query(models.JobTarget).filter(models.JobTarget.id == jt_id).first()
    if not jt:
        raise HTTPException(status_code=404, detail="Job Target not found")
    db.delete(jt)
    db.commit()
    return {"status": "deleted"}


class StatusUpdate(BaseModel):
    status: str


@app.patch("/job_targets/{jt_id}/status", response_model=JobTargetResponse)
def update_job_status(
    jt_id: int, payload: StatusUpdate, db: Session = Depends(database.get_db)
):
    jt = db.query(models.JobTarget).filter(models.JobTarget.id == jt_id).first()
    if not jt:
        raise HTTPException(status_code=404, detail="Job Target not found")
    jt.status = payload.status
    db.commit()
    db.refresh(jt)
    return JobTargetResponse(**_format_job_target(jt))


@app.get("/resumes/{resume_id}/analytics")
def get_resume_analytics(resume_id: int, db: Session = Depends(database.get_db)):
    jobs = (
        db.query(models.JobTarget).filter(models.JobTarget.resume_id == resume_id).all()
    )
    if not jobs:
        return {"average_fit": 0, "missing_skills_freq": []}

    total_fit = 0
    missing_freq = {}
    original_casing = {}

    for jt in jobs:
        total_fit += jt.fit_score or 0
        try:
            missing = json.loads(jt.missing_skills) if jt.missing_skills else []
            for skill in missing:
                skill_clean = skill.strip().lower()
                if skill_clean not in missing_freq:
                    original_casing[skill_clean] = skill.strip()
                missing_freq[skill_clean] = missing_freq.get(skill_clean, 0) + 1
        except:
            pass

    avg_fit = total_fit // len(jobs)

    # Sort by frequency descending and limit to top 5
    sorted_items = sorted(missing_freq.items(), key=lambda item: item[1], reverse=True)[
        :5
    ]
    sorted_skills = [{"skill": original_casing[k], "count": v} for k, v in sorted_items]

    return {"average_fit": avg_fit, "missing_skills_freq": sorted_skills}


@app.post("/job_targets/{jt_id}/refresh", response_model=JobTargetResponse)
async def refresh_job_target(
    jt_id: int, request: Request, db: Session = Depends(database.get_db)
):
    jt = db.query(models.JobTarget).filter(models.JobTarget.id == jt_id).first()
    if not jt:
        raise HTTPException(status_code=404, detail="Job Target not found")

    # Rate Limiting Logic (after validating job exists)
    admin_token = request.headers.get("X-Admin-Token")
    if admin_token != ADMIN_SECRET:
        client_ip = request.client.host if request.client else "unknown"
        current_count = IP_REFRESH_COUNTS.get(client_ip, 0)
        if current_count >= 2:
            raise HTTPException(
                status_code=429,
                detail="You have reached the free limit of 2 refreshes. Please provide the admin token.",
            )
        IP_REFRESH_COUNTS[client_ip] = current_count + 1

    resume = (
        db.query(models.ResumeVersion)
        .filter(models.ResumeVersion.id == jt.resume_id)
        .first()
    )

    # Scrape company info if URL provided
    company_text = ""
    if jt.company_url:
        company_text = await scraper.scrape_company_url(jt.company_url)

    # Analyze fit
    try:
        fit_data = llm.analyze_job_fit(
            resume.extracted_text, jt.job_description, company_text
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    jt.company_name = fit_data.get("company_name", jt.company_name) or jt.company_name
    jt.fit_score = fit_data.get("fit_score", 0)
    jt.aligned_skills = json.dumps(fit_data.get("aligned_skills", []))
    jt.missing_skills = json.dumps(fit_data.get("missing_skills", []))
    jt.jd_positives = json.dumps(fit_data.get("jd_positives", []))
    jt.jd_negatives = json.dumps(fit_data.get("jd_negatives", []))
    jt.company_stability_summary = json.dumps(
        fit_data.get("company_stability_insights", [])
    )

    db.commit()
    db.refresh(jt)

    return JobTargetResponse(**_format_job_target(jt))


@app.post("/job_targets/{jt_id}/tailor", response_model=JobTargetResponse)
def tailor_resume(jt_id: int, db: Session = Depends(database.get_db)):
    jt = db.query(models.JobTarget).filter(models.JobTarget.id == jt_id).first()
    if not jt:
        raise HTTPException(status_code=404, detail="Job Target not found")

    resume = (
        db.query(models.ResumeVersion)
        .filter(models.ResumeVersion.id == jt.resume_id)
        .first()
    )

    tailored_data = llm.tailor_resume(resume.extracted_text, jt.job_description)

    jt.tailored_summary = tailored_data.get("summary")
    jt.tailored_bullets = json.dumps(tailored_data.get("bullets", []))
    db.commit()

    return JobTargetResponse(**_format_job_target(jt))


@app.post("/job_targets/{jt_id}/cover_letter")
def generate_cover_letter(jt_id: int, db: Session = Depends(database.get_db)):
    jt = db.query(models.JobTarget).filter(models.JobTarget.id == jt_id).first()
    if not jt:
        raise HTTPException(status_code=404, detail="Job Target not found")

    resume = (
        db.query(models.ResumeVersion)
        .filter(models.ResumeVersion.id == jt.resume_id)
        .first()
    )

    cover_letter = llm.generate_cover_letter(resume.extracted_text, jt.job_description)
    jt.cover_letter = cover_letter
    db.commit()
    return {"cover_letter": cover_letter}


@app.post("/job_targets/{jt_id}/interview_prep")
def generate_interview_prep(jt_id: int, db: Session = Depends(database.get_db)):
    jt = db.query(models.JobTarget).filter(models.JobTarget.id == jt_id).first()
    if not jt:
        raise HTTPException(status_code=404, detail="Job Target not found")

    resume = (
        db.query(models.ResumeVersion)
        .filter(models.ResumeVersion.id == jt.resume_id)
        .first()
    )

    prep = llm.generate_interview_prep(resume.extracted_text, jt.job_description)
    jt.interview_prep = json.dumps(prep)
    db.commit()
    return {"questions": prep}
