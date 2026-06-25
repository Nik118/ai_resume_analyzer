from sqlalchemy import Column, Integer, String, Text, ForeignKey
from .database import Base

class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    extracted_text = Column(Text)
    email = Column(String, index=True, nullable=True)
    phone = Column(String, index=True, nullable=True)
    skills = Column(Text) # JSON string
    summary = Column(Text, nullable=True)
    experience_years = Column(Integer, nullable=True)
    education = Column(String, nullable=True)
    past_titles = Column(Text, nullable=True) # JSON string
    ats_score = Column(Integer, nullable=True)
    strengths = Column(Text, nullable=True) # JSON string
    weaknesses = Column(Text, nullable=True) # JSON string
    general_feedback = Column(Text, nullable=True) # JSON string

class JobTarget(Base):
    __tablename__ = "job_targets"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resume_versions.id", ondelete="CASCADE"), index=True)
    job_description = Column(Text)
    company_url = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    fit_score = Column(Integer, nullable=True)
    aligned_skills = Column(Text, nullable=True) # JSON string
    missing_skills = Column(Text, nullable=True) # JSON string
    job_quality_summary = Column(Text, nullable=True) # DEPRECATED
    jd_positives = Column(Text, nullable=True) # JSON string
    jd_negatives = Column(Text, nullable=True) # JSON string
    company_stability_summary = Column(Text, nullable=True)
    status = Column(String, default="Saved", nullable=False)
    
    tailored_summary = Column(Text, nullable=True)
    tailored_bullets = Column(Text, nullable=True) # JSON string
    cover_letter = Column(Text, nullable=True)
    interview_prep = Column(Text, nullable=True) # JSON string

