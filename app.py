"""Smart Attendance Management System - Flask application.

Provides role-based access control (Admin / Faculty), REST APIs,
live face recognition, reporting, and hybrid database management
(SQLAlchemy ORM + raw MySQL connector).
"""
import csv
import hmac
import io
import re
import secrets
import threading
import time
from datetime import date, datetime, timedelta
from functools import wraps

import mysql.connector
import numpy as np
from flask import (Flask, Response, abort, flash, jsonify, redirect, render_template,
                   request, send_from_directory, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import db
import db_orm
import models
import services
from config import Config
from face_engine import FaceEngine, FaceIndex, ModelsMissingError, crop_thumbnail, decode_image
from pagination import Pagination

app = Flask(__name__)
app.config.from_object(Config)
Config.check_production_guard()
db.init_app(app)
db_orm.init_app(app)
Config.PHOTO_DIR.mkdir(parents=True, exist_ok=True)

_engine = None
_engine_lock = threading.Lock()
index = FaceIndex()

# --------------------------------------------------------------------------
# Helpers & Security
# --------------------------------------------------------------------------


def get_engine():
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = FaceEngine()  # raises ModelsMissingError if models are absent
        return _engine


def models_ready():
    return Config.DETECTOR_MODEL.exists() and Config.RECOGNIZER_MODEL.exists()


def reload_index():
    index.load(db.query("SELECT student_id, embedding FROM face_encodings"))


def ensure_index():
    if not index.loaded:
        reload_index()


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not session.get("user"):
            if request.path.startswith("/api/"):
                return jsonify(error="Authentication required. Please log in."), 401
            return redirect(url_for("login", next=request.path))
        return fn(*a, **kw)
    return wrapper


def role_required(*roles):
    """Enforce role-based access control on routes and sensitive actions."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if not session.get("user"):
                if request.path.startswith("/api/"):
                    return jsonify(error="Authentication required. Please log in."), 401
                return redirect(url_for("login", next=request.path))
            current_role = session.get("role", "Faculty")
            if current_role not in roles:
                if request.path.startswith("/api/"):
                    return jsonify(error="Forbidden: Access denied for your role."), 403
                abort(403, f"Access denied. This action requires one of the following roles: {', '.join(roles)}.")
            return fn(*a, **kw)
        return wrapper
    return decorator


@app.before_request
def check_csrf():
    if request.method == "POST":
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
        if not sent or not hmac.compare_digest(sent, session.get("csrf", "")):
            if request.path.startswith("/api/"):
                return jsonify(error="Session expired or invalid CSRF token. Reload the page."), 400
            abort(400, "Invalid or missing CSRF token. Reload the page and try again.")


@app.template_filter("fmt_time")
def fmt_time(v):
    if v is None:
        return ""
    if isinstance(v, timedelta):
        mins = int(v.total_seconds() // 60)
        return f"{mins // 60:02d}:{mins % 60:02d}"
    return str(v)[:5]


@app.template_filter("fmt_date")
def fmt_date(v):
    return v.strftime("%d %b %Y") if v else ""


@app.template_filter("pct")
def fmt_pct(v):
    return "—" if v is None else f"{v:.1f}%"


# Jinja globals & context processors
app.jinja_env.globals["csrf_token"] = csrf_token


@app.context_processor
def inject():
    return dict(
        models_ready=models_ready(),
        cfg=Config,
        today=date.today(),
        current_user={
            "user_id": session.get("user_id"),
            "username": session.get("username") or session.get("user"),
            "role": session.get("role", "Faculty"),
            "faculty_id": session.get("faculty_id"),
        },
    )


# Error Handlers
@app.errorhandler(mysql.connector.Error)
def db_error(exc):
    app.logger.exception("Database error")
    if request.path.startswith("/api/"):
        return jsonify(error=f"Database error: {exc}"), 500
    return render_template(
        "error.html",
        title="Database error",
        message=f"{exc}. Check that MySQL is running and that setup_db.py / migrate.py has been run.",
    ), 500


@app.errorhandler(400)
@app.errorhandler(404)
def http_error(exc):
    return render_template("error.html", title=f"{exc.code} {exc.name}", message=exc.description), exc.code


@app.errorhandler(403)
def forbidden_error(exc):
    if request.path.startswith("/api/"):
        return jsonify(error="Forbidden: You do not have permission to access this resource."), 403
    return render_template(
        "error.html",
        title="403 Forbidden",
        message=exc.description or "You do not have permission to access this resource.",
    ), 403


@app.errorhandler(500)
def internal_error(exc):
    app.logger.exception("Internal server error")
    if request.path.startswith("/api/"):
        return jsonify(error="Internal server error."), 500
    return render_template(
        "error.html",
        title="500 Internal Server Error",
        message="An unexpected server error occurred. Please contact system support.",
    ), 500


def to_int(v, default=None):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def csv_response(filename, header, rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return Response("\ufeff" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})


# --------------------------------------------------------------------------
# Authentication & User Management
# --------------------------------------------------------------------------


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        identifier = request.form.get("username", "").strip()
        pwd = request.form.get("password", "")

        orm_sess = db_orm.get_orm_session()
        user = orm_sess.query(models.User).filter(
            (models.User.username == identifier) | (models.User.email == identifier)
        ).first()

        if user:
            if not user.is_active:
                flash("Your account has been deactivated. Please contact the administrator.", "error")
                return render_template("login.html")
            if check_password_hash(user.password_hash, pwd):
                session.clear()
                session["user_id"] = user.user_id
                session["user"] = user.username
                session["username"] = user.username
                session["role"] = user.role
                session["faculty_id"] = user.faculty_id
                if user.faculty:
                    session["faculty_name"] = user.faculty.name
                session["csrf"] = secrets.token_hex(16)
                flash(f"Welcome back, {user.username}! Signed in as {user.role}.", "ok")
                nxt = request.args.get("next", "")
                return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("dashboard"))

        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.post("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "ok")
    return redirect(url_for("login"))


@app.route("/users")
@role_required("Admin")
def users_list():
    orm_sess = db_orm.get_orm_session()
    all_users = orm_sess.query(models.User).order_by(models.User.user_id).all()
    faculty_list = orm_sess.query(models.Faculty).order_by(models.Faculty.name).all()
    return render_template("users.html", users=all_users, faculty_list=faculty_list)


@app.post("/users/create")
@role_required("Admin")
def user_create():
    f = request.form
    username = f.get("username", "").strip()
    email = f.get("email", "").strip()
    pwd = f.get("password", "")
    role = f.get("role", "Faculty")
    fac_id = to_int(f.get("faculty_id")) if role == "Faculty" else None

    if not (3 <= len(username) <= 50):
        flash("Username must be between 3 and 50 characters.", "error")
        return redirect(url_for("users_list"))
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        flash("Invalid email address.", "error")
        return redirect(url_for("users_list"))
    if len(pwd) < 6:
        flash("Password must be at least 6 characters.", "error")
        return redirect(url_for("users_list"))
    if role not in ("Admin", "Faculty"):
        flash("Invalid role selected.", "error")
        return redirect(url_for("users_list"))

    try:
        with db_orm.orm_transaction() as orm_sess:
            existing = orm_sess.query(models.User).filter(
                (models.User.username == username) | (models.User.email == email)
            ).first()
            if existing:
                flash("Username or email already in use.", "error")
                return redirect(url_for("users_list"))
            new_user = models.User(
                username=username,
                email=email,
                password_hash=generate_password_hash(pwd),
                role=role,
                faculty_id=fac_id,
                is_active=1,
            )
            orm_sess.add(new_user)
        flash(f"User '{username}' created successfully.", "ok")
    except Exception as exc:
        flash(f"Error creating user: {exc}", "error")
    return redirect(url_for("users_list"))


@app.post("/users/<int:user_id>/edit")
@role_required("Admin")
def user_edit(user_id):
    f = request.form
    email = f.get("email", "").strip()
    role = f.get("role", "Faculty")
    is_active = 1 if f.get("is_active") == "1" else 0
    fac_id = to_int(f.get("faculty_id")) if role == "Faculty" else None
    new_pwd = f.get("new_password", "").strip()

    try:
        with db_orm.orm_transaction() as orm_sess:
            user = orm_sess.get(models.User, user_id)
            if not user:
                abort(404, "User not found.")
            if user_id == session.get("user_id") and is_active == 0:
                flash("You cannot deactivate your own administrative account.", "error")
                return redirect(url_for("users_list"))
            user.email = email
            user.role = role
            user.faculty_id = fac_id
            user.is_active = is_active
            if new_pwd:
                if len(new_pwd) < 6:
                    flash("New password must be at least 6 characters.", "error")
                    return redirect(url_for("users_list"))
                user.password_hash = generate_password_hash(new_pwd)
        flash("User updated successfully.", "ok")
    except Exception as exc:
        flash(f"Error updating user: {exc}", "error")
    return redirect(url_for("users_list"))


@app.post("/users/<int:user_id>/delete")
@role_required("Admin")
def user_delete(user_id):
    if user_id == session.get("user_id"):
        flash("You cannot delete your own administrative account.", "error")
        return redirect(url_for("users_list"))
    try:
        with db_orm.orm_transaction() as orm_sess:
            user = orm_sess.get(models.User, user_id)
            if not user:
                abort(404, "User not found.")
            orm_sess.delete(user)
        flash("User deleted successfully.", "ok")
    except Exception as exc:
        flash(f"Error deleting user: {exc}", "error")
    return redirect(url_for("users_list"))


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------


@app.route("/")
@login_required
def dashboard():
    faculty_id = session.get("faculty_id") if session.get("role") == "Faculty" else None
    kpi, chart, critical, today_sessions, exams = services.dashboard_data(faculty_id=faculty_id)
    return render_template(
        "dashboard.html",
        kpi=kpi,
        chart=chart,
        critical=critical,
        today_sessions=today_sessions,
        exams=exams,
    )


# --------------------------------------------------------------------------
# Students
# --------------------------------------------------------------------------


@app.route("/students")
@login_required
def students():
    q = request.args.get("q", "").strip()
    dept = to_int(request.args.get("department_id"))
    sem = to_int(request.args.get("semester"))
    page = to_int(request.args.get("page"), 1)
    rows, pagination = services.student_overview(q=q, department_id=dept, semester=sem, page=page, per_page=12)
    depts = db.query("SELECT * FROM departments ORDER BY dept_code")
    return render_template(
        "students.html",
        rows=rows,
        pagination=pagination,
        depts=depts,
        q=q,
        dept=dept,
        sem=sem,
    )


@app.route("/students/register")
@login_required
def register_student():
    depts = db.query("SELECT * FROM departments ORDER BY dept_code")
    return render_template("register_student.html", depts=depts)


@app.post("/api/students/register")
@login_required
def api_register_student():
    d = request.get_json(silent=True) or {}
    name = (d.get("name") or "").strip()
    roll = (d.get("roll_no") or "").strip().upper()
    email = (d.get("email") or "").strip() or None
    dept_id, sem = to_int(d.get("department_id")), to_int(d.get("semester"))
    images = d.get("images") or []

    if not (2 <= len(name) <= 100):
        return jsonify(error="Enter the student's full name."), 400
    if not re.fullmatch(r"[A-Z0-9/_-]{2,30}", roll):
        return jsonify(error="Roll number may contain letters, digits, - _ / only (2-30 characters)."), 400
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return jsonify(error="Email address looks invalid."), 400
    if not dept_id or not db.query("SELECT 1 FROM departments WHERE department_id=%s", (dept_id,), one=True):
        return jsonify(error="Choose a department."), 400
    if not sem or not 1 <= sem <= 12:
        return jsonify(error="Semester must be 1-12."), 400
    if not 1 <= len(images) <= Config.MAX_PHOTOS:
        return jsonify(error=f"Provide 1 to {Config.MAX_PHOTOS} face photos."), 400
    if db.query("SELECT 1 FROM students WHERE roll_no=%s", (roll,), one=True):
        return jsonify(error=f"Roll number {roll} is already registered."), 409
    if email and db.query("SELECT 1 FROM students WHERE email=%s", (email,), one=True):
        return jsonify(error="That email is already registered."), 409

    try:
        engine = get_engine()
    except ModelsMissingError as exc:
        return jsonify(error=str(exc)), 503

    samples, problems = [], []
    for i, raw in enumerate(images, 1):
        try:
            img = decode_image(raw)
        except Exception:  # noqa: BLE001
            problems.append(f"Photo {i}: unreadable image.")
            continue
        faces = engine.analyse(img)
        if not faces:
            problems.append(f"Photo {i}: no face found.")
        elif len(faces) > 1:
            problems.append(f"Photo {i}: more than one face in the picture.")
        elif min(faces[0].box[2:]) < Config.MIN_FACE_PX:
            problems.append(f"Photo {i}: face too small - move closer to the camera.")
        else:
            samples.append((img, faces[0]))
    if not samples:
        return jsonify(error="No usable face photo. " + " ".join(problems)), 422

    # all photos must show the same person
    ref = samples[0][1].embedding
    if any(float(s[1].embedding @ ref) < Config.MATCH_THRESHOLD for s in samples[1:]):
        return jsonify(error="The photos appear to show different people. Use photos of one person only."), 422

    # the face must not already belong to another student
    ensure_index()
    for _, f in samples:
        sid, sim = index.best(f.embedding)
        if sid is not None and sim >= Config.MATCH_THRESHOLD:
            other = db.query("SELECT name, roll_no FROM students WHERE student_id=%s", (sid,), one=True)
            who = f"{other['name']} ({other['roll_no']})" if other else "another student"
            return jsonify(error=f"This face is already registered as {who}."), 409

    largest = max(samples, key=lambda s: s[1].box[2] * s[1].box[3])
    with db.transaction():
        student_id, _ = db.execute(
            "INSERT INTO students (roll_no, name, email, department_id, semester, has_photo) VALUES (%s,%s,%s,%s,%s,1)",
            (roll, name, email, dept_id, sem))
        for _, f in samples:
            db.execute("INSERT INTO face_encodings (student_id, embedding) VALUES (%s,%s)",
                       (student_id, f.embedding.astype(np.float32).tobytes()))
        enrolled = 0
        if d.get("auto_enroll", True):
            _, enrolled = db.execute(
                "INSERT INTO enrollments (student_id, course_id) "
                "SELECT %s, course_id FROM courses WHERE department_id=%s AND semester=%s",
                (student_id, dept_id, sem))
    try:
        (Config.PHOTO_DIR / f"{student_id}.jpg").write_bytes(crop_thumbnail(largest[0], largest[1].box))
    except Exception:  # noqa: BLE001
        app.logger.exception("Could not write thumbnail")
        db.execute("UPDATE students SET has_photo=0 WHERE student_id=%s", (student_id,))
    reload_index()
    services.refresh_debarments()
    return jsonify(ok=True, student_id=student_id, samples=len(samples), enrolled=enrolled,
                   warnings=problems, redirect=url_for("student_detail", student_id=student_id))


@app.route("/students/<int:student_id>")
@login_required
def student_detail(student_id):
    s = db.query("SELECT s.*, d.dept_code, d.dept_name FROM students s JOIN departments d "
                 "ON d.department_id=s.department_id WHERE student_id=%s", (student_id,), one=True)
    if not s:
        abort(404, "Student not found.")
    rows = services.attendance_rows(student_id=student_id)
    available = db.query(
        "SELECT course_id, course_code, course_name FROM courses WHERE course_id NOT IN "
        "(SELECT course_id FROM enrollments WHERE student_id=%s) ORDER BY course_code", (student_id,))
    exams = db.query(
        "SELECT es.*, c.course_code, c.course_name, v.percentage, v.status FROM exam_schedules es "
        "JOIN enrollments e ON e.course_id = es.course_id AND e.student_id = %s "
        "JOIN courses c ON c.course_id = es.course_id "
        "JOIN v_attendance_status v ON v.student_id = e.student_id AND v.course_id = es.course_id "
        "WHERE es.exam_date >= CURDATE() ORDER BY es.exam_date", (student_id,))
    tot_a, tot_t = sum(r["attended"] for r in rows), sum(r["total_sessions"] for r in rows)
    overall = (tot_a * 100.0 / tot_t) if tot_t else None
    depts = db.query("SELECT * FROM departments ORDER BY dept_code")
    return render_template(
        "student_detail.html",
        s=s,
        rows=rows,
        available=available,
        exams=exams,
        overall=overall,
        overall_status=services.status_for(overall),
        depts=depts,
    )


@app.post("/students/<int:student_id>/edit")
@login_required
def edit_student(student_id):
    f = request.form
    name = (f.get("name") or "").strip()
    email = (f.get("email") or "").strip() or None
    dept_id = to_int(f.get("department_id"))
    sem = to_int(f.get("semester"))

    if not (2 <= len(name) <= 100):
        flash("Name must be between 2 and 100 characters.", "error")
        return redirect(url_for("student_detail", student_id=student_id))
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        flash("Invalid email format.", "error")
        return redirect(url_for("student_detail", student_id=student_id))
    if not sem or not (1 <= sem <= 12):
        flash("Semester must be between 1 and 12.", "error")
        return redirect(url_for("student_detail", student_id=student_id))

    try:
        with db_orm.orm_transaction() as orm_sess:
            stu = orm_sess.get(models.Student, student_id)
            if not stu:
                abort(404, "Student not found.")
            if email and email != stu.email:
                dup = orm_sess.query(models.Student).filter(
                    models.Student.email == email, models.Student.student_id != student_id
                ).first()
                if dup:
                    flash("Email address already in use by another student.", "error")
                    return redirect(url_for("student_detail", student_id=student_id))
            stu.name = name
            stu.email = email
            stu.department_id = dept_id
            stu.semester = sem
        flash("Student details updated successfully.", "ok")
    except Exception as exc:
        flash(f"Error updating student: {exc}", "error")
    return redirect(url_for("student_detail", student_id=student_id))


@app.route("/students/<int:student_id>/photo")
@login_required
def student_photo(student_id):
    path = Config.PHOTO_DIR / f"{student_id}.jpg"
    if not path.exists():
        abort(404)
    return send_from_directory(Config.PHOTO_DIR, path.name, max_age=3600)


@app.post("/students/<int:student_id>/enroll")
@login_required
def enroll(student_id):
    course_id = to_int(request.form.get("course_id"))
    try:
        db.execute("INSERT INTO enrollments (student_id, course_id) VALUES (%s,%s)", (student_id, course_id))
        services.refresh_debarments()
        flash("Student enrolled.", "ok")
    except mysql.connector.Error:
        flash("Could not enroll (already enrolled or invalid course).", "error")
    return redirect(url_for("student_detail", student_id=student_id))


@app.post("/students/<int:student_id>/unenroll/<int:course_id>")
@login_required
def unenroll(student_id, course_id):
    db.execute("DELETE FROM enrollments WHERE student_id=%s AND course_id=%s", (student_id, course_id))
    services.refresh_debarments()
    flash("Enrollment removed. Attendance already recorded for that course remains in history.", "ok")
    return redirect(url_for("student_detail", student_id=student_id))


@app.post("/students/<int:student_id>/delete")
@role_required("Admin")
def delete_student(student_id):
    db.execute("DELETE FROM students WHERE student_id=%s", (student_id,))
    (Config.PHOTO_DIR / f"{student_id}.jpg").unlink(missing_ok=True)
    reload_index()
    services.refresh_debarments()
    flash("Student and all related records deleted.", "ok")
    return redirect(url_for("students"))


# --------------------------------------------------------------------------
# Academics: Departments, Faculty, Courses
# --------------------------------------------------------------------------


@app.route("/academics")
@login_required
def academics():
    return render_template(
        "academics.html",
        depts=db.query("SELECT d.*, (SELECT COUNT(*) FROM students s WHERE s.department_id=d.department_id) AS students "
                       "FROM departments d ORDER BY dept_code"),
        faculty=db.query("SELECT f.*, d.dept_code FROM faculty f JOIN departments d ON d.department_id=f.department_id ORDER BY f.name"),
        courses=db.query("SELECT c.*, d.dept_code, f.name AS faculty_name, "
                         "(SELECT COUNT(*) FROM enrollments e WHERE e.course_id=c.course_id) AS enrolled "
                         "FROM courses c JOIN departments d ON d.department_id=c.department_id "
                         "LEFT JOIN faculty f ON f.faculty_id=c.faculty_id ORDER BY c.course_code"),
    )


def _try(sql, args, ok_msg):
    try:
        db.execute(sql, args)
        flash(ok_msg, "ok")
    except mysql.connector.IntegrityError as exc:
        flash("Could not save: duplicate value or the record is still in use." if exc.errno in (1062, 1451, 1452)
              else f"Could not save: {exc}", "error")
    except mysql.connector.Error as exc:
        flash(f"Could not save: {exc}", "error")
    return redirect(url_for("academics"))


@app.post("/academics/department")
@role_required("Admin")
def add_department():
    return _try(
        "INSERT INTO departments (dept_code, dept_name) VALUES (%s,%s)",
        (request.form.get("dept_code", "").strip().upper(), request.form.get("dept_name", "").strip()),
        "Department added.",
    )


@app.post("/academics/department/<int:dept_id>/edit")
@role_required("Admin")
def edit_department(dept_id):
    code = request.form.get("dept_code", "").strip().upper()
    name = request.form.get("dept_name", "").strip()
    if not code or not name:
        flash("Department code and name are required.", "error")
        return redirect(url_for("academics"))
    try:
        with db_orm.orm_transaction() as orm_sess:
            dept = orm_sess.get(models.Department, dept_id)
            if not dept:
                abort(404, "Department not found.")
            dept.dept_code = code
            dept.dept_name = name
        flash("Department updated successfully.", "ok")
    except Exception as exc:
        flash(f"Error updating department: {exc}", "error")
    return redirect(url_for("academics"))


@app.post("/academics/faculty")
@role_required("Admin")
def add_faculty():
    f = request.form
    return _try(
        "INSERT INTO faculty (department_id, name, email, phone) VALUES (%s,%s,%s,%s)",
        (to_int(f.get("department_id")), f.get("name", "").strip(), f.get("email", "").strip(),
         f.get("phone", "").strip() or None),
        "Faculty member added.",
    )


@app.post("/academics/faculty/<int:faculty_id>/edit")
@role_required("Admin")
def edit_faculty(faculty_id):
    f = request.form
    name = f.get("name", "").strip()
    email = f.get("email", "").strip()
    phone = f.get("phone", "").strip() or None
    dept_id = to_int(f.get("department_id"))
    if not name or not email or not dept_id:
        flash("Name, email, and department are required.", "error")
        return redirect(url_for("academics"))
    try:
        with db_orm.orm_transaction() as orm_sess:
            fac = orm_sess.get(models.Faculty, faculty_id)
            if not fac:
                abort(404, "Faculty not found.")
            fac.name = name
            fac.email = email
            fac.phone = phone
            fac.department_id = dept_id
        flash("Faculty member updated successfully.", "ok")
    except Exception as exc:
        flash(f"Error updating faculty member: {exc}", "error")
    return redirect(url_for("academics"))


@app.post("/academics/course")
@role_required("Admin")
def add_course():
    f = request.form
    return _try(
        "INSERT INTO courses (course_code, course_name, department_id, faculty_id, semester, credits) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (f.get("course_code", "").strip().upper(), f.get("course_name", "").strip(),
         to_int(f.get("department_id")), to_int(f.get("faculty_id")), to_int(f.get("semester"), 1),
         to_int(f.get("credits"), 3)),
        "Course added.",
    )


@app.post("/academics/course/<int:course_id>/edit")
@role_required("Admin")
def edit_course(course_id):
    f = request.form
    code = f.get("course_code", "").strip().upper()
    name = f.get("course_name", "").strip()
    dept_id = to_int(f.get("department_id"))
    fac_id = to_int(f.get("faculty_id"))
    sem = to_int(f.get("semester"), 1)
    credits = to_int(f.get("credits"), 3)
    if not code or not name or not dept_id:
        flash("Course code, name, and department are required.", "error")
        return redirect(url_for("academics"))
    try:
        with db_orm.orm_transaction() as orm_sess:
            crs = orm_sess.get(models.Course, course_id)
            if not crs:
                abort(404, "Course not found.")
            crs.course_code = code
            crs.course_name = name
            crs.department_id = dept_id
            crs.faculty_id = fac_id
            crs.semester = sem
            crs.credits = credits
        flash("Course updated successfully.", "ok")
    except Exception as exc:
        flash(f"Error updating course: {exc}", "error")
    return redirect(url_for("academics"))


@app.post("/academics/<kind>/<int:item_id>/delete")
@role_required("Admin")
def delete_academic(kind, item_id):
    table = {"department": ("departments", "department_id"), "faculty": ("faculty", "faculty_id"),
             "course": ("courses", "course_id")}.get(kind)
    if not table:
        abort(404)
    return _try(f"DELETE FROM {table[0]} WHERE {table[1]}=%s", (item_id,), "Deleted.")


# --------------------------------------------------------------------------
# Class Sessions & Live Attendance
# --------------------------------------------------------------------------


@app.route("/sessions")
@login_required
def sessions():
    status = request.args.get("status", "")
    course_id = to_int(request.args.get("course_id"))
    page = to_int(request.args.get("page"), 1)

    faculty_id = session.get("faculty_id") if session.get("role") == "Faculty" else None
    rows, pagination = services.sessions_list(
        status=status,
        course_id=course_id,
        faculty_id=faculty_id,
        page=page,
        per_page=15,
    )

    if session.get("role") == "Faculty" and session.get("faculty_id"):
        courses = db.query(
            "SELECT course_id, course_code, course_name, faculty_id FROM courses "
            "WHERE faculty_id=%s ORDER BY course_code", (session.get("faculty_id"),))
    else:
        courses = db.query("SELECT course_id, course_code, course_name, faculty_id FROM courses ORDER BY course_code")

    all_courses = db.query("SELECT course_id, course_code FROM courses ORDER BY course_code")

    return render_template(
        "sessions.html",
        rows=rows,
        pagination=pagination,
        courses=courses,
        all_courses=all_courses,
        status=status,
        course_id=course_id,
    )


@app.post("/sessions/create")
@login_required
def create_session():
    f = request.form
    course_id = to_int(f.get("course_id"))
    course = db.query("SELECT faculty_id FROM courses WHERE course_id=%s", (course_id,), one=True)
    if not course:
        flash("Choose a valid course.", "error")
        return redirect(url_for("sessions"))

    # Faculty role check
    if session.get("role") == "Faculty":
        user_fac = session.get("faculty_id")
        if course["faculty_id"] != user_fac:
            flash("You can only schedule sessions for courses assigned to you.", "error")
            return redirect(url_for("sessions"))

    start, end = f.get("start_time", ""), f.get("end_time", "")
    if not f.get("session_date") or not start or not end or end <= start:
        flash("Enter a date, and an end time later than the start time.", "error")
        return redirect(url_for("sessions"))

    start_now = bool(f.get("start_now"))
    new_id, _ = db.execute(
        "INSERT INTO class_sessions (course_id, faculty_id, session_date, start_time, end_time, room, topic, status, opened_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (course_id, course["faculty_id"], f["session_date"], start, end, f.get("room", "").strip() or None,
         f.get("topic", "").strip() or None, "Open" if start_now else "Scheduled",
         datetime.now() if start_now else None))

    if start_now:
        return redirect(url_for("session_live", session_id=new_id))
    flash("Class session scheduled.", "ok")
    return redirect(url_for("sessions"))


@app.post("/sessions/<int:session_id>/edit")
@login_required
def edit_session(session_id):
    f = request.form
    start, end = f.get("start_time", ""), f.get("end_time", "")
    s_date = f.get("session_date", "")
    room = f.get("room", "").strip() or None
    topic = f.get("topic", "").strip() or None

    if not s_date or not start or not end or end <= start:
        flash("Provide a valid session date, and end time later than start time.", "error")
        return redirect(url_for("sessions"))

    try:
        with db_orm.orm_transaction() as orm_sess:
            sess = orm_sess.get(models.ClassSession, session_id)
            if not sess:
                abort(404, "Session not found.")
            if session.get("role") == "Faculty" and sess.faculty_id != session.get("faculty_id"):
                abort(403, "You can only edit sessions assigned to you.")
            if sess.status != "Scheduled":
                flash("Only Scheduled sessions can be edited.", "error")
                return redirect(url_for("sessions"))
            sess.session_date = datetime.strptime(s_date, "%Y-%m-%d").date()
            sess.start_time = datetime.strptime(start, "%H:%M").time()
            sess.end_time = datetime.strptime(end, "%H:%M").time()
            sess.room = room
            sess.topic = topic
        flash("Class session updated.", "ok")
    except Exception as exc:
        flash(f"Error updating session: {exc}", "error")
    return redirect(url_for("sessions"))


@app.post("/sessions/<int:session_id>/open")
@login_required
def open_session(session_id):
    sess = db.query("SELECT faculty_id, status FROM class_sessions WHERE session_id=%s", (session_id,), one=True)
    if not sess:
        abort(404, "Session not found.")
    if session.get("role") == "Faculty" and sess["faculty_id"] != session.get("faculty_id"):
        abort(403, "You can only open sessions assigned to you.")

    db.execute("UPDATE class_sessions SET status='Open', opened_at=NOW() WHERE session_id=%s AND status='Scheduled'", (session_id,))
    return redirect(url_for("session_live", session_id=session_id))


@app.post("/sessions/<int:session_id>/close")
@login_required
def close_session(session_id):
    sess = db.query("SELECT faculty_id, status FROM class_sessions WHERE session_id=%s", (session_id,), one=True)
    if not sess:
        abort(404, "Session not found.")
    if session.get("role") == "Faculty" and sess["faculty_id"] != session.get("faculty_id"):
        abort(403, "You can only close sessions assigned to you.")

    db.execute("UPDATE class_sessions SET status='Closed', closed_at=NOW() WHERE session_id=%s AND status='Open'", (session_id,))
    services.refresh_debarments()
    flash("Session closed. Attendance percentages and exam debarments were updated.", "ok")
    return redirect(url_for("session_live", session_id=session_id))


@app.post("/sessions/<int:session_id>/delete")
@login_required
def delete_session(session_id):
    sess = db.query("SELECT faculty_id, status FROM class_sessions WHERE session_id=%s", (session_id,), one=True)
    if not sess:
        abort(404, "Session not found.")
    if session.get("role") == "Faculty" and sess["faculty_id"] != session.get("faculty_id"):
        abort(403, "You can only delete sessions assigned to you.")

    _, n = db.execute("DELETE FROM class_sessions WHERE session_id=%s AND status='Scheduled'", (session_id,))
    flash("Scheduled session deleted." if n else "Only sessions that were never started can be deleted.", "ok" if n else "error")
    return redirect(url_for("sessions"))


def _present_list(session_id):
    return db.query("SELECT s.student_id, s.name, s.roll_no, a.marked_at, a.confidence FROM attendance a "
                    "JOIN students s ON s.student_id=a.student_id WHERE a.session_id=%s ORDER BY a.marked_at DESC",
                    (session_id,))


@app.route("/sessions/<int:session_id>")
@login_required
def session_live(session_id):
    sess = db.query(
        "SELECT cs.*, c.course_code, c.course_name, f.name AS faculty_name, "
        "(SELECT COUNT(*) FROM attendance a WHERE a.session_id=cs.session_id) AS present, "
        "(SELECT COUNT(*) FROM enrollments e WHERE e.course_id=cs.course_id) AS enrolled "
        "FROM class_sessions cs JOIN courses c ON c.course_id=cs.course_id "
        "LEFT JOIN faculty f ON f.faculty_id=cs.faculty_id WHERE cs.session_id=%s", (session_id,), one=True)
    if not sess:
        abort(404, "Class session not found.")
    absent = db.query("SELECT s.name, s.roll_no FROM enrollments e JOIN students s ON s.student_id=e.student_id "
                      "WHERE e.course_id=%s AND s.student_id NOT IN (SELECT student_id FROM attendance WHERE session_id=%s) "
                      "ORDER BY s.roll_no", (sess["course_id"], session_id))
    return render_template("session_live.html", sess=sess, present_rows=_present_list(session_id), absent=absent)


# ---- Live Face Recognition -------------------------------------------------

_streaks, _streak_lock = {}, threading.Lock()


def _confirmed(session_id, student_id):
    """True once the same student was matched in CONFIRM_FRAMES consecutive recent frames."""
    now = time.monotonic()
    with _streak_lock:
        count, last = _streaks.get((session_id, student_id), (0, 0.0))
        count = count + 1 if now - last <= 5 else 1
        _streaks[(session_id, student_id)] = (count, now)
        if len(_streaks) > 2000:
            for k in [k for k, v in _streaks.items() if now - v[1] > 60]:
                _streaks.pop(k, None)
        return count >= Config.CONFIRM_FRAMES


@app.post("/api/recognize")
@login_required
def api_recognize():
    d = request.get_json(silent=True) or {}
    session_id = to_int(d.get("session_id"))
    sess = db.query("SELECT session_id, course_id, status FROM class_sessions WHERE session_id=%s", (session_id,), one=True)
    if not sess:
        return jsonify(error="Class session not found."), 404
    if sess["status"] != "Open":
        return jsonify(error="This session is not open for attendance."), 409
    try:
        engine = get_engine()
    except ModelsMissingError as exc:
        return jsonify(error=str(exc)), 503
    try:
        img = decode_image(d.get("image") or "")
    except Exception:  # noqa: BLE001
        return jsonify(error="Bad image."), 400

    ensure_index()
    enrolled = {r["student_id"] for r in db.query("SELECT student_id FROM enrollments WHERE course_id=%s", (sess["course_id"],))}
    results, used = [], set()
    for f in sorted(engine.analyse(img), key=lambda f: -f.box[2] * f.box[3]):
        r = {"box": list(f.box), "name": "Unknown User", "roll_no": None, "status": "unknown", "similarity": None, "note": ""}
        results.append(r)
        if min(f.box[2:]) < Config.MIN_RECOGNIZE_PX:
            r["note"] = "Move closer"
            continue
        sid, sim = index.match(f.embedding)
        if sid is None or sid in used:
            continue
        used.add(sid)
        stu = db.query("SELECT name, roll_no FROM students WHERE student_id=%s", (sid,), one=True)
        if not stu:
            continue
        r.update(name=stu["name"], roll_no=stu["roll_no"], similarity=round(sim, 3), student_id=sid)
        if sid not in enrolled:
            r["status"], r["note"] = "not_enrolled", "Not enrolled in this course"
            continue
        if not _confirmed(session_id, sid):
            r["status"] = "confirming"
            continue
        try:
            db.execute("INSERT INTO attendance (session_id, student_id, confidence) VALUES (%s,%s,%s)",
                       (session_id, sid, round(sim, 4)))
            r["status"] = "marked"
        except mysql.connector.IntegrityError as exc:
            r["status"] = "already" if exc.errno == 1062 else "rejected"
        except mysql.connector.DatabaseError as exc:
            r["status"], r["note"] = "rejected", str(exc)[:120]

    present = db.query("SELECT COUNT(*) n FROM attendance WHERE session_id=%s", (session_id,), one=True)["n"]
    return jsonify(faces=results, present=present, enrolled=len(enrolled), frame=[int(img.shape[1]), int(img.shape[0])])


# --------------------------------------------------------------------------
# Reports & Exams
# --------------------------------------------------------------------------


def _shortage_filters():
    return (to_int(request.args.get("course_id")), to_int(request.args.get("department_id")),
            ["Critical", "Warning"] if request.args.get("include_warning") else ["Critical"])


@app.route("/reports/shortage")
@login_required
def shortage_report():
    course_id, dept_id, statuses = _shortage_filters()
    rows = services.attendance_rows(course_id=course_id, department_id=dept_id, statuses=statuses)
    return render_template(
        "report_shortage.html",
        rows=rows,
        course_id=course_id,
        dept_id=dept_id,
        include_warning=len(statuses) == 2,
        courses=db.query("SELECT course_id, course_code, course_name FROM courses ORDER BY course_code"),
        depts=db.query("SELECT * FROM departments ORDER BY dept_code"),
    )


@app.route("/reports/shortage.csv")
@login_required
def shortage_csv():
    course_id, dept_id, statuses = _shortage_filters()
    rows = services.attendance_rows(course_id=course_id, department_id=dept_id, statuses=statuses)
    return csv_response("attendance_shortage.csv",
                        ["Roll No", "Name", "Department", "Course", "Attended", "Conducted", "Percentage", "Status", "Classes needed for 75%"],
                        [[r["roll_no"], r["student_name"], r["dept_code"], r["course_code"], r["attended"],
                          r["total_sessions"], f"{r['percentage']:.2f}", r["status"], r["needed"]] for r in rows])


@app.route("/exams")
@login_required
def exams():
    services.refresh_debarments()
    faculty_id = session.get("faculty_id") if session.get("role") == "Faculty" else None

    where = "WHERE es.exam_date >= CURDATE()"
    args = []
    if faculty_id:
        where += " AND c.faculty_id = %s"
        args.append(faculty_id)

    rows = db.query(
        f"SELECT es.*, c.course_code, c.course_name, "
        f"(SELECT COUNT(*) FROM enrollments e WHERE e.course_id=es.course_id) AS enrolled, "
        f"(SELECT COUNT(*) FROM exam_debarments ed WHERE ed.exam_id=es.exam_id) AS debarred "
        f"FROM exam_schedules es JOIN courses c ON c.course_id=es.course_id {where} ORDER BY es.exam_date DESC, es.start_time",
        tuple(args),
    )
    return render_template(
        "exams.html",
        rows=rows,
        courses=db.query("SELECT course_id, course_code, course_name FROM courses ORDER BY course_code"),
    )


@app.post("/exams/create")
@role_required("Admin")
def create_exam():
    f = request.form
    start, end = f.get("start_time", ""), f.get("end_time", "")
    if not to_int(f.get("course_id")) or not f.get("exam_date") or not start or not end or end <= start:
        flash("Choose a course, a date and an end time later than the start time.", "error")
        return redirect(url_for("exams"))
    try:
        db.execute(
            "INSERT INTO exam_schedules (course_id, exam_type, exam_date, start_time, end_time, venue) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (to_int(f.get("course_id")), f.get("exam_type", "End-Term"), f["exam_date"], start, end,
             f.get("venue", "").strip() or None),
        )
        services.refresh_debarments()
        flash("Exam scheduled. Debarment list generated automatically.", "ok")
    except mysql.connector.Error as exc:
        flash(f"Could not schedule exam: {exc}", "error")
    return redirect(url_for("exams"))


@app.post("/exams/<int:exam_id>/edit")
@role_required("Admin")
def edit_exam(exam_id):
    f = request.form
    start, end = f.get("start_time", ""), f.get("end_time", "")
    e_date = f.get("exam_date", "")
    e_type = f.get("exam_type", "End-Term")
    venue = f.get("venue", "").strip() or None

    if not e_date or not start or not end or end <= start:
        flash("Provide a valid date and end time later than start time.", "error")
        return redirect(url_for("exams"))

    try:
        with db_orm.orm_transaction() as orm_sess:
            ex = orm_sess.get(models.ExamSchedule, exam_id)
            if not ex:
                abort(404, "Exam not found.")
            ex.exam_type = e_type
            ex.exam_date = datetime.strptime(e_date, "%Y-%m-%d").date()
            ex.start_time = datetime.strptime(start, "%H:%M").time()
            ex.end_time = datetime.strptime(end, "%H:%M").time()
            ex.venue = venue
        services.refresh_debarments()
        flash("Exam schedule updated and debarments refreshed.", "ok")
    except Exception as exc:
        flash(f"Error updating exam: {exc}", "error")
    return redirect(url_for("exams"))


@app.post("/exams/<int:exam_id>/delete")
@role_required("Admin")
def delete_exam(exam_id):
    db.execute("DELETE FROM exam_schedules WHERE exam_id=%s", (exam_id,))
    services.refresh_debarments()
    flash("Exam deleted.", "ok")
    return redirect(url_for("exams"))


def _exam_or_404(exam_id):
    ex = db.query("SELECT es.*, c.course_code, c.course_name FROM exam_schedules es JOIN courses c "
                  "ON c.course_id=es.course_id WHERE es.exam_id=%s", (exam_id,), one=True)
    if not ex:
        abort(404, "Exam not found.")
    return ex


@app.route("/exams/<int:exam_id>")
@login_required
def exam_detail(exam_id):
    services.refresh_debarments()
    ex = _exam_or_404(exam_id)
    debarred = db.query(
        "SELECT ed.*, s.name, s.roll_no FROM exam_debarments ed JOIN students s ON s.student_id=ed.student_id "
        "WHERE ed.exam_id=%s ORDER BY ed.attendance_pct, s.roll_no", (exam_id,))
    eligible = db.query(
        "SELECT * FROM v_attendance_status WHERE course_id=%s AND (status <> 'Critical') ORDER BY roll_no",
        (ex["course_id"],),
    )
    return render_template("exam_detail.html", ex=ex, debarred=debarred, eligible=eligible)


@app.route("/exams/<int:exam_id>/debarred.csv")
@login_required
def exam_debarred_csv(exam_id):
    ex = _exam_or_404(exam_id)
    rows = db.query(
        "SELECT ed.*, s.name, s.roll_no FROM exam_debarments ed JOIN students s ON s.student_id=ed.student_id "
        "WHERE ed.exam_id=%s ORDER BY s.roll_no", (exam_id,))
    return csv_response(
        f"debarred_{ex['course_code']}_{ex['exam_date']}.csv",
        ["Roll No", "Name", "Course", "Exam", "Attended", "Conducted", "Percentage"],
        [[r["roll_no"], r["name"], ex["course_code"], ex["exam_type"], r["attended_sessions"],
          r["total_sessions"], f"{r['attendance_pct']:.2f}"] for r in rows],
    )


# --------------------------------------------------------------------------
# Main Execution
# --------------------------------------------------------------------------

if __name__ == "__main__":
    with app.app_context():
        try:
            reload_index()
            print(f"Loaded {len(index.ids)} face embeddings.")
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: could not load face data yet ({exc}). Is MySQL running and setup_db.py / migrate.py done?")
    if not models_ready():
        print("WARNING: face models missing. Run:  python download_models.py")
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False, threaded=True)