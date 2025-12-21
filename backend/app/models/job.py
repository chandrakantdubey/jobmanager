from typing import Optional, List
from enum import Enum
from pydantic import BaseModel
from datetime import date

class JobType(Enum):
    FULL_TIME = "fulltime"
    PART_TIME = "parttime"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"
    FREELANCE = "freelance"

class Country(Enum):
    USA = "usa"
    INDIA = "india"
    # Add others as needed
    
class ScraperInput(BaseModel):
    search_term: str
    location: str
    results_wanted: int = 15
    country: str = "usa"
    is_remote: bool = False
    details: bool = False
    offset: int = 0
    hours_old: Optional[int] = None
    job_type: Optional[List[JobType]] = None
    min_experience: Optional[int] = None
    max_experience: Optional[int] = None
    
class JobPost(BaseModel):
    id: Optional[str] = None
    title: str
    company: str
    job_url: str
    location: Optional[str] = None
    description: Optional[str] = None
    date_posted: Optional[date] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = None
    compensation: Optional[str] = None
    job_type: Optional[List[JobType]] = None
    is_remote: bool = False
    emails: Optional[List[str]] = None
    site: str
    match_score: Optional[int] = None  # Resume-based matching score (0-100)


class ScraperError(Exception):
    pass
