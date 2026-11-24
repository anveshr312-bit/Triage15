from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from .config import DOMAINS

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

def valid_domain(value):
    if value not in DOMAINS:
        raise ValueError('Unknown domain')
    return value

def utc_time(value):
    if value is not None and value.tzinfo is None:
        raise ValueError('Timestamp must include a timezone')
    return value

class DoubtInput(Input):
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=5, max_length=3000)
    domain: str
    skills: list[str] = Field(min_length=1, max_length=10)
    urgency: Literal['Urgent','Normal','Flexible'] = 'Normal'
    bounty: int = Field(default=0, ge=0, le=1000)
    preferred_start: datetime | None = None
    deadline: datetime | None = None
    _domain = field_validator('domain')(valid_domain)
    _times = field_validator('preferred_start', 'deadline')(utc_time)

    @model_validator(mode='after')
    def check(self):
        if len(set(self.skills)) != len(self.skills) or not set(self.skills) <= set(DOMAINS[self.domain]):
            raise ValueError('Use unique skills from the selected domain')
        if self.preferred_start and self.deadline and (self.deadline-self.preferred_start).total_seconds() < 900:
            raise ValueError('Time window must allow a 15-minute session')
        return self

class SkillInput(Input):
    domain: str
    tag: str
    level: int = Field(ge=1, le=5)
    _domain = field_validator('domain')(valid_domain)
    @model_validator(mode='after')
    def check(self):
        if self.tag not in DOMAINS[self.domain]:
            raise ValueError('Invalid skill tag')
        return self

class ProfileInput(Input):
    mentoring: bool
    skills: list[SkillInput] = Field(max_length=40)
    @model_validator(mode='after')
    def check(self):
        if len({(s.domain,s.tag) for s in self.skills}) != len(self.skills):
            raise ValueError('Duplicate skills')
        return self

class StudentInput(Input):
    name: str = Field(min_length=2, max_length=80)

class WindowInput(Input):
    start: datetime
    end: datetime
    _times = field_validator('start','end')(utc_time)
    @model_validator(mode='after')
    def check(self):
        if (self.end-self.start).total_seconds() < 900:
            raise ValueError('Availability must span at least 15 minutes')
        if (self.end-self.start).total_seconds() > 86400:
            raise ValueError('Use windows of at most 24 hours')
        return self

class AssessmentInput(Input):
    domain: str
    answers: dict[str,int]
    _domain = field_validator('domain')(valid_domain)

class ResolutionInput(Input):
    resolved: bool
    rating: int = Field(ge=1, le=5)
    notes: str = Field(default='', max_length=2000)

class MessageInput(Input):
    content: str = Field(min_length=1, max_length=4000)

class ClaimInput(Input):
    slot_start: datetime | None = None
    _times = field_validator('slot_start')(utc_time)
