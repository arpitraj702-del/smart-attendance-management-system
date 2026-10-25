"""SQLAlchemy ORM models matching the MySQL schema.

Provides an object-relational abstraction layer for CRUD operations,
relationship navigation, and data validation while preserving existing
raw SQL queries and views for analytical and high-performance operations.
"""
from datetime import date, datetime, time
from typing import List, Optional

from sqlalchemy import (
    BLOB, CheckConstraint, Date, DateTime, Enum, ForeignKey,
    Index, Integer, Numeric, SmallInteger, String, Time,
    func
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship
)


class Base(DeclarativeBase):
    pass


class Department(Base):
    __tablename__ = "departments"

    department_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dept_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    dept_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # Relationships
    faculty_members: Mapped[List["Faculty"]] = relationship("Faculty", back_populates="department")
    courses: Mapped[List["Course"]] = relationship("Course", back_populates="department")
    students: Mapped[List["Student"]] = relationship("Student", back_populates="department")

    def __repr__(self) -> str:
        return f"<Department(id={self.department_id}, code='{self.dept_code}')>"


class Faculty(Base):
    __tablename__ = "faculty"

    faculty_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    department_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("departments.department_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Relationships
    department: Mapped["Department"] = relationship("Department", back_populates="faculty_members")
    courses: Mapped[List["Course"]] = relationship("Course", back_populates="faculty")
    class_sessions: Mapped[List["ClassSession"]] = relationship("ClassSession", back_populates="faculty")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="faculty", uselist=False)

    __table_args__ = (
        Index("idx_faculty_dept", "department_id"),
    )

    def __repr__(self) -> str:
        return f"<Faculty(id={self.faculty_id}, name='{self.name}', email='{self.email}')>"


class Course(Base):
    __tablename__ = "courses"

    course_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    course_name: Mapped[str] = mapped_column(String(120), nullable=False)
    department_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("departments.department_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False
    )
    faculty_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("faculty.faculty_id", onupdate="CASCADE", ondelete="SET NULL"), nullable=True
    )
    semester: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    credits: Mapped[int] = mapped_column(SmallInteger, default=3, nullable=False)

    # Relationships
    department: Mapped["Department"] = relationship("Department", back_populates="courses")
    faculty: Mapped[Optional["Faculty"]] = relationship("Faculty", back_populates="courses")
    enrollments: Mapped[List["Enrollment"]] = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
    class_sessions: Mapped[List["ClassSession"]] = relationship("ClassSession", back_populates="course", cascade="all, delete-orphan")
    exam_schedules: Mapped[List["ExamSchedule"]] = relationship("ExamSchedule", back_populates="course", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("semester BETWEEN 1 AND 12", name="chk_course_sem"),
        Index("idx_course_dept", "department_id"),
    )

    def __repr__(self) -> str:
        return f"<Course(id={self.course_id}, code='{self.course_code}')>"


class Student(Base):
    __tablename__ = "students"

    student_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    roll_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(120), unique=True, nullable=True)
    department_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("departments.department_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False
    )
    semester: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    has_photo: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    department: Mapped["Department"] = relationship("Department", back_populates="students")
    encodings: Mapped[List["FaceEncoding"]] = relationship("FaceEncoding", back_populates="student", cascade="all, delete-orphan")
    enrollments: Mapped[List["Enrollment"]] = relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    attendance_records: Mapped[List["Attendance"]] = relationship("Attendance", back_populates="student", cascade="all, delete-orphan")
    debarments: Mapped[List["ExamDebarment"]] = relationship("ExamDebarment", back_populates="student", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("semester BETWEEN 1 AND 12", name="chk_student_sem"),
        Index("idx_student_dept", "department_id"),
    )

    def __repr__(self) -> str:
        return f"<Student(id={self.student_id}, roll_no='{self.roll_no}', name='{self.name}')>"


class FaceEncoding(Base):
    __tablename__ = "face_encodings"

    encoding_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False
    )
    embedding: Mapped[bytes] = mapped_column(BLOB, nullable=False)
    model_name: Mapped[str] = mapped_column(String(40), default="SFace-2021dec", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="encodings")

    def __repr__(self) -> str:
        return f"<FaceEncoding(id={self.encoding_id}, student_id={self.student_id})>"


class Enrollment(Base):
    __tablename__ = "enrollments"

    enrollment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False
    )
    enrolled_on: Mapped[date] = mapped_column(Date, server_default=func.current_date(), nullable=False)

    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="enrollments")
    course: Mapped["Course"] = relationship("Course", back_populates="enrollments")

    __table_args__ = (
        Index("uq_student_course", "student_id", "course_id", unique=True),
    )


class ClassSession(Base):
    __tablename__ = "class_sessions"

    session_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False
    )
    faculty_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("faculty.faculty_id", ondelete="SET NULL"), nullable=True
    )
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    room: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("Scheduled", "Open", "Closed", name="session_status_enum"),
        default="Scheduled",
        nullable=False
    )
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="class_sessions")
    faculty: Mapped[Optional["Faculty"]] = relationship("Faculty", back_populates="class_sessions")
    attendance_records: Mapped[List["Attendance"]] = relationship(
        "Attendance", back_populates="class_session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="chk_session_time"),
        Index("idx_session_course_status", "course_id", "status"),
        Index("idx_session_date", "session_date"),
    )


class Attendance(Base):
    __tablename__ = "attendance"

    attendance_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("class_sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False
    )
    marked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)

    # Relationships
    class_session: Mapped["ClassSession"] = relationship("ClassSession", back_populates="attendance_records")
    student: Mapped["Student"] = relationship("Student", back_populates="attendance_records")

    __table_args__ = (
        Index("uq_session_student", "session_id", "student_id", unique=True),
        Index("idx_att_student", "student_id"),
        Index("idx_att_marked_at", "marked_at"),
    )


class ExamSchedule(Base):
    __tablename__ = "exam_schedules"

    exam_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False
    )
    exam_type: Mapped[str] = mapped_column(
        Enum("Internal", "Mid-Term", "End-Term", "Practical", name="exam_type_enum"),
        default="End-Term",
        nullable=False
    )
    exam_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    venue: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)

    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="exam_schedules")
    debarments: Mapped[List["ExamDebarment"]] = relationship(
        "ExamDebarment", back_populates="exam_schedule", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="chk_exam_time"),
    )


class ExamDebarment(Base):
    __tablename__ = "exam_debarments"

    debarment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exam_schedules.exam_id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False
    )
    attendance_pct: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    total_sessions: Mapped[int] = mapped_column(Integer, nullable=False)
    attended_sessions: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    exam_schedule: Mapped["ExamSchedule"] = relationship("ExamSchedule", back_populates="debarments")
    student: Mapped["Student"] = relationship("Student", back_populates="debarments")

    __table_args__ = (
        Index("uq_exam_student", "exam_id", "student_id", unique=True),
    )


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("Admin", "Faculty", name="user_role_enum"),
        default="Faculty",
        nullable=False
    )
    faculty_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("faculty.faculty_id", onupdate="CASCADE", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    faculty: Mapped[Optional["Faculty"]] = relationship("Faculty", back_populates="user")

    __table_args__ = (
        CheckConstraint("role IN ('Admin', 'Faculty')", name="chk_user_role"),
        CheckConstraint("is_active IN (0, 1)", name="chk_user_active"),
        Index("idx_user_role", "role"),
        Index("idx_user_faculty", "faculty_id"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.user_id}, username='{self.username}', role='{self.role}')>"
