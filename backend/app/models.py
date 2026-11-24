import time
import uuid
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

def uid():
    return str(uuid.uuid4())

def now():
    return int(time.time())

class Student(Base):
    __tablename__ = 'students'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(80))
    mentoring: Mapped[bool] = mapped_column(Boolean, default=False)
    points_balance: Mapped[int] = mapped_column(Integer, default=100)
    skills: Mapped[list['StudentSkill']] = relationship(cascade='all, delete-orphan')
    availability: Mapped[list['AvailabilityWindow']] = relationship(cascade='all, delete-orphan')
    __table_args__ = (
        CheckConstraint('points_balance >= 0'),
    )

class PointLedger(Base):
    __tablename__ = 'point_ledger'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    student_id: Mapped[str] = mapped_column(ForeignKey('students.id'), index=True)
    amount: Mapped[int]
    transaction_type: Mapped[str]
    doubt_id: Mapped[str | None] = mapped_column(ForeignKey('doubts.id'), index=True, nullable=True)
    session_id: Mapped[str | None] = mapped_column(ForeignKey('sessions.id'), index=True, nullable=True)
    reference_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    balance_after: Mapped[int]
    created_at: Mapped[int] = mapped_column(default=now)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    __table_args__ = (
        CheckConstraint("transaction_type IN ('INITIAL_GRANT','BOUNTY_RESERVED','BOUNTY_AWARDED','BOUNTY_REFUNDED','BOUNTY_ADJUSTED')"),
    )

class StudentSkill(Base):
    __tablename__ = 'student_skills'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    student_id: Mapped[str] = mapped_column(ForeignKey('students.id'), index=True)
    domain: Mapped[str]
    tag: Mapped[str]
    level: Mapped[int]
    __table_args__ = (UniqueConstraint('student_id', 'domain', 'tag'), CheckConstraint('level BETWEEN 1 AND 5'))

class AvailabilityWindow(Base):
    __tablename__ = 'availability_windows'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    student_id: Mapped[str] = mapped_column(ForeignKey('students.id'), index=True)
    start: Mapped[int]
    end: Mapped[int]
    __table_args__ = (CheckConstraint('end > start'),)

class DoubtRequest(Base):
    __tablename__ = 'doubts'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    requester_id: Mapped[str] = mapped_column(ForeignKey('students.id'), index=True)
    title: Mapped[str]
    description: Mapped[str]
    domain: Mapped[str] = mapped_column(index=True)
    urgency: Mapped[str]
    bounty: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[int] = mapped_column(default=now)
    preferred_start: Mapped[int | None]
    deadline: Mapped[int | None]
    status: Mapped[str] = mapped_column(default='OPEN', index=True)
    assigned_session_id: Mapped[str | None] = mapped_column(ForeignKey('sessions.id', use_alter=True))
    skills: Mapped[list['DoubtSkill']] = relationship(cascade='all, delete-orphan')
    __table_args__ = (
        CheckConstraint("status IN ('OPEN','MATCHED','IN_SESSION','AWAITING_CONFIRMATION','RESOLVED','UNMATCHED','CANCELLED')"),
        CheckConstraint("urgency IN ('Urgent','Normal','Flexible')"),
        CheckConstraint('bounty >= 0'),
        CheckConstraint('deadline IS NULL OR preferred_start IS NULL OR deadline > preferred_start'),
    )

class DoubtSkill(Base):
    __tablename__ = 'doubt_skills'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    doubt_id: Mapped[str] = mapped_column(ForeignKey('doubts.id'), index=True)
    tag: Mapped[str]
    __table_args__ = (UniqueConstraint('doubt_id', 'tag'),)

class AssessmentQuestion(Base):
    __tablename__ = 'assessment_questions'
    id: Mapped[str] = mapped_column(primary_key=True)
    domain: Mapped[str] = mapped_column(index=True)
    prompt: Mapped[str]
    options: Mapped[list] = mapped_column(JSON)
    correct: Mapped[int]
    version: Mapped[int] = mapped_column(default=1)

class AssessmentAttempt(Base):
    __tablename__ = 'assessment_attempts'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    student_id: Mapped[str] = mapped_column(ForeignKey('students.id'), index=True)
    domain: Mapped[str]
    score: Mapped[int]
    question_count: Mapped[int]
    correct_count: Mapped[int]
    created_at: Mapped[int] = mapped_column(default=now)
    version: Mapped[int]
    __table_args__ = (CheckConstraint('score BETWEEN 0 AND 100'),)

class AssessmentResponse(Base):
    __tablename__ = 'assessment_responses'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    attempt_id: Mapped[str] = mapped_column(ForeignKey('assessment_attempts.id'), index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey('assessment_questions.id'))
    answer: Mapped[int]
    __table_args__ = (UniqueConstraint('attempt_id', 'question_id'),)

class DispatchRun(Base):
    __tablename__ = 'dispatch_runs'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    created_at: Mapped[int] = mapped_column(default=now)
    result: Mapped[dict] = mapped_column(JSON)

class Session(Base):
    __tablename__ = 'sessions'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    doubt_id: Mapped[str] = mapped_column(ForeignKey('doubts.id'), index=True)
    mentor_id: Mapped[str] = mapped_column(ForeignKey('students.id'), index=True)
    dispatch_run_id: Mapped[str | None] = mapped_column(ForeignKey('dispatch_runs.id'))
    start: Mapped[int]
    end: Mapped[int]
    state: Mapped[str] = mapped_column(default='OFFERED')
    offer_expires_at: Mapped[int]
    accepted_at: Mapped[int | None] = mapped_column(nullable=True)
    actual_started_at: Mapped[int | None] = mapped_column(nullable=True)
    mentor_completed_at: Mapped[int | None] = mapped_column(nullable=True)
    outcome_deadline: Mapped[int | None] = mapped_column(nullable=True)
    completed_at: Mapped[int | None] = mapped_column(nullable=True)
    is_demo_accelerated: Mapped[bool] = mapped_column(Boolean, default=False)
    mentor_completed: Mapped[bool] = mapped_column(default=False)
    resolved: Mapped[bool | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(nullable=True)
    explanation: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (
        CheckConstraint('start % 900 = 0 AND end = start + 900'),
        CheckConstraint("state IN ('OFFERED','ACCEPTED','ACTIVE','AWAITING_CONFIRMATION','RESOLVED','DECLINED','EXPIRED','CANCELLED')"),
        Index('uq_active_doubt', 'doubt_id', unique=True, sqlite_where=text("state IN ('OFFERED','ACCEPTED','ACTIVE','AWAITING_CONFIRMATION')")),
        Index('uq_active_mentor_slot', 'mentor_id', 'start', unique=True, sqlite_where=text("state IN ('OFFERED','ACCEPTED','ACTIVE','AWAITING_CONFIRMATION')")),
    )

class SessionMessage(Base):
    __tablename__ = 'session_messages'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'), index=True)
    sender_id: Mapped[str] = mapped_column(ForeignKey('students.id'), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[int] = mapped_column(default=now, index=True)
    __table_args__ = (
        CheckConstraint('length(content) > 0 AND length(content) <= 4000'),
    )

class SessionFeedback(Base):
    __tablename__ = 'session_feedback'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'), unique=True)
    student_id: Mapped[str] = mapped_column(ForeignKey('students.id'))
    rating: Mapped[int]
    notes: Mapped[str]
    __table_args__ = (CheckConstraint('rating BETWEEN 1 AND 5'),)

class BenchmarkRun(Base):
    __tablename__ = 'benchmark_runs'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    created_at: Mapped[int] = mapped_column(default=now)
    result: Mapped[dict] = mapped_column(JSON)

# Mentoring Workspace Entities (P0 & P1)

class SessionMeeting(Base):
    __tablename__ = 'session_meetings'
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id', ondelete='CASCADE'), primary_key=True)
    meeting_url: Mapped[str] = mapped_column(String, nullable=False)
    attached_by_id: Mapped[str] = mapped_column(ForeignKey('students.id'), nullable=False)
    attached_at: Mapped[int] = mapped_column(default=now)
    updated_at: Mapped[int] = mapped_column(default=now)

class SessionCodeSnippet(Base):
    __tablename__ = 'session_code_snippets'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id', ondelete='CASCADE'), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey('students.id'), index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    filename: Mapped[str | None] = mapped_column(String, nullable=True)
    language: Mapped[str] = mapped_column(String, default='text')
    content: Mapped[str] = mapped_column(Text, nullable=False)
    snippet_type: Mapped[str] = mapped_column(String, default='ORIGINAL')  # ORIGINAL, PROPOSED_FIX, EXAMPLE, ERROR_LOG, OTHER
    parent_snippet_id: Mapped[str | None] = mapped_column(ForeignKey('session_code_snippets.id'), nullable=True)
    created_at: Mapped[int] = mapped_column(default=now, index=True)
    __table_args__ = (
        CheckConstraint('length(content) > 0 AND length(content) <= 65536'),
        CheckConstraint("snippet_type IN ('ORIGINAL', 'PROPOSED_FIX', 'EXAMPLE', 'ERROR_LOG', 'OTHER')"),
    )

class SessionResolution(Base):
    __tablename__ = 'session_resolutions'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id', ondelete='CASCADE'), unique=True, index=True)
    doubt_id: Mapped[str] = mapped_column(ForeignKey('doubts.id'), index=True)
    mentor_id: Mapped[str] = mapped_column(ForeignKey('students.id'))
    requester_id: Mapped[str] = mapped_column(ForeignKey('students.id'))
    root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    solution_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    follow_up_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_snippet_id: Mapped[str | None] = mapped_column(ForeignKey('session_code_snippets.id'), nullable=True)
    corrected_snippet_id: Mapped[str | None] = mapped_column(ForeignKey('session_code_snippets.id'), nullable=True)
    reference_urls: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[int] = mapped_column(default=now)
    updated_at: Mapped[int] = mapped_column(default=now)
    submitted_at: Mapped[int | None] = mapped_column(nullable=True)
    confirmed_at: Mapped[int | None] = mapped_column(nullable=True)
    requester_status: Mapped[str] = mapped_column(String, default='PENDING')  # PENDING, CONFIRMED_RESOLVED, CONFIRMED_UNRESOLVED
    __table_args__ = (
        CheckConstraint("requester_status IN ('PENDING', 'CONFIRMED_RESOLVED', 'CONFIRMED_UNRESOLVED')"),
    )

class AuthIdentityMapping(Base):
    __tablename__ = 'auth_identity_mappings'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    supabase_user_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    student_id: Mapped[str] = mapped_column(ForeignKey('students.id', ondelete='CASCADE'), unique=True, index=True, nullable=False)
    created_at: Mapped[int] = mapped_column(default=now)


