import re
from io import BytesIO
from typing import Set, List
from pypdf import PdfReader

# Common tech keywords to look for
TECH_KEYWORDS = {
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "php", "ruby", "swift", "kotlin",
    "html", "css", "react", "angular", "vue", "node.js", "node", "django", "flask", "fastapi", "spring",
    "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
    "aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "git", "linux",
    "machine learning", "ai", "data science", "nlp", "computer vision",
    "frontend", "backend", "fullstack", "devops", "sre", "api", "rest", "graphql"
}

# Heuristic list of common job titles
COMMON_JOB_TITLES = {
    "software engineer", "frontend developer", "backend developer", "fullstack developer",
    "devops engineer", "data scientist", "machine learning engineer", "product manager",
    "project manager", "business analyst", "qa engineer", "mobile developer", 
    "android developer", "ios developer", "ui/ux designer", "web developer",
    "systems administrator", "cloud architect", "data analyst", "technical lead",
    "engineering manager", "cto", "vp of engineering", "python developer", 
    "java developer", "react developer", "node.js developer", "go developer"
}

def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""

def extract_keywords(text: str) -> Set[str]:
    text_lower = text.lower()
    found_keywords = set()
    for keyword in TECH_KEYWORDS:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, text_lower):
            found_keywords.add(keyword)
    return found_keywords

def extract_job_titles(text: str) -> List[str]:
    """
    Extracts likely job titles from text using a predefined list.
    """
    text_lower = text.lower()
    found_titles = set()
    
    # Check for direct matches
    for title in COMMON_JOB_TITLES:
        # Use simple word boundary check
        pattern = r'\b' + re.escape(title) + r'\b'
        if re.search(pattern, text_lower):
            found_titles.add(title.title()) # Capitalize for display
            
    return list(found_titles)

def score_job(job_keywords: Set[str], resume_keywords: Set[str]) -> int:
    return len(job_keywords.intersection(resume_keywords))
