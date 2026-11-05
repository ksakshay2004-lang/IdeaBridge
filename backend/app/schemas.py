from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from .security import validate_password_strength

Stage = Literal["concept", "research", "prototype", "mvp", "launched"]
Visibility = Literal["public", "restricted", "private"]
STAGES = ["concept", "research", "prototype", "mvp", "launched"]


def _clean_list(v: List[str], max_items: int = 12, max_len: int = 60) -> List[str]:
    out, seen = [], set()
    for item in v or []:
        s = str(item).strip()[:max_len]
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out[:max_items]


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    full_name: str = Field(min_length=2, max_length=120)
    role: Literal["creator", "entrepreneur"]
    company_name: Optional[str] = Field(default=None, max_length=160)

    @field_validator("password")
    @classmethod
    def _pw(cls, v):
        return validate_password_strength(v)

    @field_validator("full_name")
    @classmethod
    def _name(cls, v):
        return " ".join(v.split())


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _pw(cls, v):
        return validate_password_strength(v)


class CreatorProfileIn(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    headline: str = Field(default="", max_length=160)
    bio: str = Field(default="", max_length=3000)
    organization: str = Field(default="", max_length=160)
    location: str = Field(default="", max_length=120)
    website: str = Field(default="", max_length=255)
    skills: List[str] = []

    @field_validator("skills")
    @classmethod
    def _skills(cls, v):
        return _clean_list(v, 20)

    @field_validator("website")
    @classmethod
    def _site(cls, v):
        if v and not v.lower().startswith(("http://", "https://")):
            raise ValueError("Website must start with http:// or https://")
        return v


class EntrepreneurProfileIn(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    company_name: str = Field(default="", max_length=160)
    company_type: Literal["startup", "investor", "corporate", "other"] = "startup"
    bio: str = Field(default="", max_length=3000)
    website: str = Field(default="", max_length=255)
    location: str = Field(default="", max_length=120)
    industries: List[str] = []
    technologies: List[str] = []
    interests: str = Field(default="", max_length=2000)
    preferred_stages: List[Stage] = []
    target_markets: List[str] = []
    investment_min: Optional[int] = Field(default=None, ge=0, le=10**10)
    investment_max: Optional[int] = Field(default=None, ge=0, le=10**10)

    @field_validator("industries", "technologies", "target_markets")
    @classmethod
    def _lists(cls, v):
        return _clean_list(v, 20)

    @field_validator("website")
    @classmethod
    def _site(cls, v):
        if v and not v.lower().startswith(("http://", "https://")):
            raise ValueError("Website must start with http:// or https://")
        return v

    @field_validator("investment_max")
    @classmethod
    def _range(cls, v, info):
        lo = info.data.get("investment_min")
        if v is not None and lo is not None and v < lo:
            raise ValueError("investment_max must be >= investment_min")
        return v


class IdeaIn(BaseModel):
    title: str = Field(min_length=5, max_length=160)
    short_description: str = Field(min_length=20, max_length=500)
    problem: str = Field(min_length=30, max_length=5000)
    solution: str = Field(min_length=30, max_length=5000)
    industry: str = Field(min_length=2, max_length=80)
    target_audience: str = Field(min_length=3, max_length=500)
    technologies: List[str] = []
    stage: Stage = "concept"
    expected_impact: str = Field(default="", max_length=3000)
    business_potential: str = Field(default="", max_length=3000)
    funding_needed: Optional[int] = Field(default=None, ge=0, le=10**10)
    visibility: Visibility = "public"

    @field_validator("technologies")
    @classmethod
    def _tech(cls, v):
        return _clean_list(v, 12, 40)

    @field_validator("title", "short_description", "problem", "solution", "target_audience")
    @classmethod
    def _strip(cls, v):
        return v.strip()


class IdeaUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=5, max_length=160)
    short_description: Optional[str] = Field(default=None, min_length=20, max_length=500)
    problem: Optional[str] = Field(default=None, min_length=30, max_length=5000)
    solution: Optional[str] = Field(default=None, min_length=30, max_length=5000)
    industry: Optional[str] = Field(default=None, min_length=2, max_length=80)
    target_audience: Optional[str] = Field(default=None, min_length=3, max_length=500)
    technologies: Optional[List[str]] = None
    stage: Optional[Stage] = None
    expected_impact: Optional[str] = Field(default=None, max_length=3000)
    business_potential: Optional[str] = Field(default=None, max_length=3000)
    funding_needed: Optional[int] = Field(default=None, ge=0, le=10**10)
    visibility: Optional[Visibility] = None

    @field_validator("technologies")
    @classmethod
    def _tech(cls, v):
        return None if v is None else _clean_list(v, 12, 40)


class CollabIn(BaseModel):
    idea_id: int
    kind: Literal["collaborate", "fund", "develop"] = "collaborate"
    message: str = Field(min_length=10, max_length=3000)


class CollabRespondIn(BaseModel):
    action: Literal["accept", "decline"]
    message: str = Field(default="", max_length=3000)


class MessageIn(BaseModel):
    recipient_id: int
    body: str = Field(min_length=1, max_length=5000)
    idea_id: Optional[int] = None


class ReportIn(BaseModel):
    reason: Literal["spam", "plagiarism", "inappropriate", "confidential", "other"]
    details: str = Field(default="", max_length=2000)


class CategoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    kind: Literal["industry", "technology"]
    description: str = Field(default="", max_length=255)
    is_active: bool = True


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    description: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None


class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class AdminIdeaUpdate(BaseModel):
    moderation_status: Literal["active", "hidden", "removed"]
    note: str = Field(default="", max_length=300)


class AdminReportResolve(BaseModel):
    action: Literal["dismiss", "hide_idea", "remove_idea"]
    note: str = Field(default="", max_length=400)
