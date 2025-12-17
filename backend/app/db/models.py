from typing import Optional, List
from sqlmodel import Field, SQLModel, JSON, Relationship
from datetime import datetime
import enum

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    resumes: List["Resume"] = Relationship(back_populates="user")
    user_jobs: List["UserJob"] = Relationship(back_populates="user")

class Resume(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    filename: str
    content_text: str
    extracted_skills: List[str] = Field(default=[], sa_type=JSON)
    parsed_titles: List[str] = Field(default=[], sa_type=JSON)
    search_preferences: dict = Field(default={}, sa_type=JSON)
    is_active: bool = Field(default=False)
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    
    user: Optional[User] = Relationship(back_populates="resumes")

class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    company: str
    location: str
    description: str
    job_url: str = Field(unique=True) # Added unique constraint
    site: str
    date_posted: Optional[str] = None
    
    # Matching fields
    description_snippet: Optional[str] = None
    match_score: int = 0
    matching_skills: List[str] = Field(default=[], sa_type=JSON)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

class JobStatus(str, enum.Enum):
    SAVED = "Saved"
    APPLIED = "Applied"
    INTERVIEWING = "Interviewing"
    OFFER = "Offer"
    REJECTED = "Rejected"

class UserJob(SQLModel, table=True):
    """Link table for Users and Jobs (Tracking)"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    job_id: int = Field(foreign_key="job.id")
    status: JobStatus = Field(default=JobStatus.SAVED)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: Optional[User] = Relationship(back_populates="user_jobs")
    job: Optional[Job] = Relationship()
