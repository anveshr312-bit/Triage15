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

# Mentoring Workspace Schemas (P0 & P1)

import re
from urllib.parse import urlparse

GOOGLE_MEET_REGEX = re.compile(r'^[a-z]{3}-[a-z]{4}-[a-z]{3}$')

class MeetingInput(Input):
    meeting_url: str = Field(min_length=10, max_length=200)

    @field_validator('meeting_url')
    @classmethod
    def validate_meeting_url(cls, v: str) -> str:
        v = v.strip()
        parsed = urlparse(v)
        if parsed.scheme != 'https':
            raise ValueError('Google Meet URL must use https scheme')
        if parsed.netloc.lower() != 'meet.google.com':
            raise ValueError('Hostname must be exactly meet.google.com')
        if parsed.username or parsed.password:
            raise ValueError('Credentials not permitted in meeting URL')
        if parsed.query or parsed.fragment:
            raise ValueError('Query parameters and fragments not permitted in meeting URL')
        path = parsed.path.strip('/')
        if not GOOGLE_MEET_REGEX.match(path):
            raise ValueError('Invalid Google Meet meeting code format (expected xxx-yyyy-zzz)')
        return f'https://meet.google.com/{path}'

class SnippetInput(Input):
    title: str = Field(min_length=1, max_length=120)
    filename: str | None = Field(default=None, max_length=120)
    language: str = Field(default='text', max_length=30)
    content: str = Field(min_length=1, max_length=65536)
    snippet_type: Literal['ORIGINAL', 'PROPOSED_FIX', 'EXAMPLE', 'ERROR_LOG', 'OTHER'] = 'ORIGINAL'
    parent_snippet_id: str | None = None

class ResolutionRecordInput(Input):
    root_cause: str = Field(min_length=5, max_length=5000)
    solution_explanation: str = Field(min_length=5, max_length=5000)
    follow_up_steps: str | None = Field(default=None, max_length=3000)
    original_snippet_id: str | None = None
    corrected_snippet_id: str | None = None
    reference_urls: list[str] = Field(default_factory=list, max_length=10)

    @field_validator('reference_urls')
    @classmethod
    def validate_urls(cls, urls: list[str]) -> list[str]:
        cleaned = []
        for u in urls:
            u = u.strip()
            if not u:
                continue
            parsed = urlparse(u)
            if parsed.scheme not in ('http', 'https') or not parsed.netloc:
                raise ValueError(f'Invalid reference URL: {u}')
            cleaned.append(u)
        return cleaned

