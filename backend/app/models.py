import time
import uuid
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, JSON, String, UniqueConstraint, text
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
    skills: Mapped[list['StudentSkill']] = relationship(cascade='all, delete-orphan')
    availability: Mapped[list['AvailabilityWindow']] = relationship(cascade='all, delete-orphan')

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
    created_at: Mapped[int] = mapped_column(default=now)
    preferred_start: Mapped[int | None]
    deadline: Mapped[int | None]
    status: Mapped[str] = mapped_column(default='OPEN', index=True)
    assigned_session_id: Mapped[str | None] = mapped_column(ForeignKey('sessions.id', use_alter=True))
    skills: Mapped[list['DoubtSkill']] = relationship(cascade='all, delete-orphan')
    __table_args__ = (
        CheckConstraint("status IN ('OPEN','MATCHED','IN_SESSION','RESOLVED','UNMATCHED','CANCELLED')"),
        CheckConstraint("urgency IN ('Urgent','Normal','Flexible')"),
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
    mentor_completed: Mapped[bool] = mapped_column(default=False)
    resolved: Mapped[bool | None]
    notes: Mapped[str | None]
    explanation: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (
        CheckConstraint('start % 900 = 0 AND end = start + 900'),
        CheckConstraint("state IN ('OFFERED','ACCEPTED','ACTIVE','RESOLVED','DECLINED','EXPIRED','CANCELLED')"),
        Index('uq_active_doubt', 'doubt_id', unique=True, sqlite_where=text("state IN ('OFFERED','ACCEPTED','ACTIVE')")),
        Index('uq_active_mentor_slot', 'mentor_id', 'start', unique=True, sqlite_where=text("state IN ('OFFERED','ACCEPTED','ACTIVE')")),
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
