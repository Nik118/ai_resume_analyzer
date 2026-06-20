from sqlalchemy import Column, Integer, String, Text
from .database import Base

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    extracted_text = Column(Text)
    email = Column(String, index=True, nullable=True)
    phone = Column(String, index=True, nullable=True)
    skills = Column(Text) # Stored as JSON string or comma-separated
    summary = Column(Text, nullable=True)
    experience_years = Column(Integer, nullable=True)
    education = Column(String, nullable=True)
    past_titles = Column(Text, nullable=True) # JSON string
