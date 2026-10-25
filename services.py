"""Business logic, reporting queries, and pagination services."""
import db
from config import Config
from pagination import Pagination


def status_for(pct):
    if pct is None:
        return "No Classes"
    if pct >= Config.GOOD_PCT:
        return "Good"
    if pct >= Config.WARNING_PCT:
        return "Warning"
    return "Critical"


def classes_needed(attended, total):
    """Consecutive classes a student must attend to reach 75%: a+n >= 0.75(t+n)  =>  n >= 3t - 4a."""
    return max(0, 3 * int(total) - 4 * int(attended))


def refresh_debarments():
    """Rebuild debarments for upcoming exams (stored procedure in schema.sql)."""
    db.execute("CALL sp_refresh_debarments(%s)", (Config.WARNING_PCT,))


def attendance_rows(student_id=None, course_id=None, department_id=None, statuses=None, page=None, per_page=20):
    where = " WHERE 1=1"
    args = []
    if student_id:
        where += " AND v.student_id = %s"
        args.append(student_id)
    if course_id:
        where += " AND v.course_id = %s"
        args.append(course_id)
    if department_id:
        where += " AND v.department_id = %s"
        args.append(department_id)
    if statuses:
        where += " AND v.status IN (" + ",".join(["%s"] * len(statuses)) + ")"
        args.extend(statuses)

    count_sql = "SELECT COUNT(*) AS total FROM v_attendance_status v JOIN departments d ON d.department_id = v.department_id" + where
    total_count = db.query(count_sql, tuple(args), one=True)["total"]

    sql = (
        "SELECT v.*, d.dept_code FROM v_attendance_status v JOIN departments d ON d.department_id = v.department_id"
        + where
        + " ORDER BY (v.percentage IS NULL), v.percentage, v.roll_no, v.course_code"
    )

    pagination = None
    if page is not None:
        pagination = Pagination(page, per_page, total_count)
        sql += f" LIMIT {pagination.per_page} OFFSET {pagination.offset}"

    rows = db.query(sql, tuple(args))
    for r in rows:
        r["needed"] = classes_needed(r["attended"], r["total_sessions"]) if r["total_sessions"] else 0

    if page is not None:
        return rows, pagination
    return rows


def student_overview(q="", department_id=None, semester=None, page=None, per_page=15):
    where = " WHERE 1=1"
    args = []
    if q:
        where += " AND (s.name LIKE %s OR s.roll_no LIKE %s)"
        args += [f"%{q}%", f"%{q}%"]
    if department_id:
        where += " AND s.department_id = %s"
        args.append(department_id)
    if semester:
        where += " AND s.semester = %s"
        args.append(semester)

    count_sql = "SELECT COUNT(*) AS total FROM students s" + where
    total_count = db.query(count_sql, tuple(args), one=True)["total"]

    sql = f"""
      SELECT s.student_id, s.roll_no, s.name, s.email, s.semester, s.has_photo, s.registered_at, d.dept_code, d.dept_name,
             COALESCE(o.attended, 0) AS attended, COALESCE(o.total, 0) AS total,
             COALESCE(o.critical_courses, 0) AS critical_courses
        FROM students s
        JOIN departments d ON d.department_id = s.department_id
        LEFT JOIN (SELECT student_id, SUM(attended) AS attended, SUM(total_sessions) AS total,
                          SUM(status = 'Critical') AS critical_courses
                     FROM v_attendance_status GROUP BY student_id) o ON o.student_id = s.student_id
       {where}
       ORDER BY s.roll_no"""

    pagination = None
    if page is not None:
        pagination = Pagination(page, per_page, total_count, args={"q": q, "department_id": department_id or "", "semester": semester or ""})
        sql += f" LIMIT {pagination.per_page} OFFSET {pagination.offset}"

    rows = db.query(sql, tuple(args))
    for r in rows:
        r["pct"] = (r["attended"] * 100.0 / r["total"]) if r["total"] else None
        r["status"] = status_for(r["pct"])

    if page is not None:
        return rows, pagination
    return rows


def sessions_list(status="", course_id=None, faculty_id=None, page=None, per_page=15):
    """Retrieve filtered class sessions with pagination."""
    where = " WHERE 1=1"
    args = []
    if status in ("Scheduled", "Open", "Closed"):
        where += " AND cs.status = %s"
        args.append(status)
    if course_id:
        where += " AND cs.course_id = %s"
        args.append(course_id)
    if faculty_id:
        where += " AND cs.faculty_id = %s"
        args.append(faculty_id)

    count_sql = "SELECT COUNT(*) AS total FROM class_sessions cs" + where
    total_count = db.query(count_sql, tuple(args), one=True)["total"]

    sql = f"""
        SELECT cs.*, c.course_code, c.course_name, f.name AS faculty_name,
               (SELECT COUNT(*) FROM attendance a WHERE a.session_id=cs.session_id) AS present,
               (SELECT COUNT(*) FROM enrollments e WHERE e.course_id=cs.course_id) AS enrolled
          FROM class_sessions cs
          JOIN courses c ON c.course_id=cs.course_id
          LEFT JOIN faculty f ON f.faculty_id=cs.faculty_id
          {where}
         ORDER BY cs.session_date DESC, cs.start_time DESC"""

    pagination = None
    if page is not None:
        pagination = Pagination(page, per_page, total_count, args={"status": status, "course_id": course_id or ""})
        sql += f" LIMIT {pagination.per_page} OFFSET {pagination.offset}"

    rows = db.query(sql, tuple(args))
    if page is not None:
        return rows, pagination
    return rows


def dashboard_data(faculty_id=None):
    """Aggregated KPI, charts, critical students, and upcoming schedule.

    If faculty_id is supplied, scopes metrics to the assigned faculty's courses.
    """
    if faculty_id:
        # Faculty-specific dashboard
        c_args = (faculty_id,)
        kpi = {
            "students": db.query(
                "SELECT COUNT(DISTINCT e.student_id) AS n FROM enrollments e "
                "JOIN courses c ON c.course_id = e.course_id WHERE c.faculty_id = %s", c_args, one=True)["n"],
            "courses": db.query("SELECT COUNT(*) AS n FROM courses WHERE faculty_id = %s", c_args, one=True)["n"],
            "faculty": 1,
            "conducted": db.query(
                "SELECT COUNT(*) AS n FROM class_sessions WHERE faculty_id = %s AND status IN ('Open','Closed')",
                c_args, one=True)["n"],
            "present_today": db.query(
                "SELECT COUNT(*) AS n FROM attendance a "
                "JOIN class_sessions cs ON cs.session_id = a.session_id "
                "WHERE cs.faculty_id = %s AND cs.session_date = CURDATE()", c_args, one=True)["n"],
        }
        dist = {
            r["status"]: r["n"]
            for r in db.query(
                "SELECT v.status, COUNT(*) AS n FROM v_attendance_status v "
                "JOIN courses c ON c.course_id = v.course_id WHERE c.faculty_id = %s GROUP BY v.status", c_args)
        }
        kpi["critical"] = dist.get("Critical", 0)

        course_avg = db.query(
            "SELECT c.course_code, AVG(v.percentage) AS avg_pct FROM v_attendance_status v "
            "JOIN courses c ON c.course_id = v.course_id "
            "WHERE c.faculty_id = %s AND v.total_sessions > 0 GROUP BY c.course_id, c.course_code ORDER BY c.course_code", c_args)

        trend = db.query("""
            SELECT cs.session_date AS d,
                   100 * SUM(COALESCE(p.present, 0)) / NULLIF(SUM(COALESCE(en.enrolled, 0)), 0) AS rate
              FROM class_sessions cs
              LEFT JOIN (SELECT session_id, COUNT(*) present FROM attendance GROUP BY session_id) p ON p.session_id = cs.session_id
              LEFT JOIN (SELECT course_id, COUNT(*) enrolled FROM enrollments GROUP BY course_id) en ON en.course_id = cs.course_id
             WHERE cs.faculty_id = %s AND cs.status IN ('Open','Closed') AND cs.session_date >= CURDATE() - INTERVAL 13 DAY
             GROUP BY cs.session_date ORDER BY cs.session_date""", c_args)

        critical = db.query(
            "SELECT v.* FROM v_attendance_status v JOIN courses c ON c.course_id = v.course_id "
            "WHERE c.faculty_id = %s AND v.status = 'Critical' ORDER BY v.percentage LIMIT 8", c_args)

        today = db.query(
            "SELECT cs.session_id, cs.start_time, cs.end_time, cs.room, cs.status, c.course_code, c.course_name "
            "FROM class_sessions cs JOIN courses c ON c.course_id = cs.course_id "
            "WHERE cs.faculty_id = %s AND cs.session_date = CURDATE() ORDER BY cs.start_time", c_args)

        exams = db.query(
            "SELECT es.exam_id, es.exam_type, es.exam_date, es.start_time, c.course_code, "
            "(SELECT COUNT(*) FROM exam_debarments ed WHERE ed.exam_id = es.exam_id) AS debarred "
            "FROM exam_schedules es JOIN courses c ON c.course_id = es.course_id "
            "WHERE c.faculty_id = %s AND es.exam_date >= CURDATE() ORDER BY es.exam_date LIMIT 5", c_args)
    else:
        # Institutional admin dashboard
        one = lambda sql: db.query(sql, one=True)  # noqa: E731
        kpi = {
            "students": one("SELECT COUNT(*) n FROM students")["n"],
            "courses": one("SELECT COUNT(*) n FROM courses")["n"],
            "faculty": one("SELECT COUNT(*) n FROM faculty")["n"],
            "conducted": one("SELECT COUNT(*) n FROM class_sessions WHERE status IN ('Open','Closed')")["n"],
            "present_today": one(
                "SELECT COUNT(*) n FROM attendance a JOIN class_sessions cs ON cs.session_id = a.session_id "
                "WHERE cs.session_date = CURDATE()")["n"],
        }
        dist = {r["status"]: r["n"] for r in db.query("SELECT status, COUNT(*) n FROM v_attendance_status GROUP BY status")}
        kpi["critical"] = dist.get("Critical", 0)

        course_avg = db.query(
            "SELECT course_code, AVG(percentage) AS avg_pct FROM v_attendance_status "
            "WHERE total_sessions > 0 GROUP BY course_id, course_code ORDER BY course_code")

        trend = db.query("""
            SELECT cs.session_date AS d,
                   100 * SUM(COALESCE(p.present, 0)) / NULLIF(SUM(COALESCE(en.enrolled, 0)), 0) AS rate
              FROM class_sessions cs
              LEFT JOIN (SELECT session_id, COUNT(*) present FROM attendance GROUP BY session_id) p ON p.session_id = cs.session_id
              LEFT JOIN (SELECT course_id, COUNT(*) enrolled FROM enrollments GROUP BY course_id) en ON en.course_id = cs.course_id
             WHERE cs.status IN ('Open','Closed') AND cs.session_date >= CURDATE() - INTERVAL 13 DAY
             GROUP BY cs.session_date ORDER BY cs.session_date""")

        critical = db.query(
            "SELECT * FROM v_attendance_status WHERE status = 'Critical' ORDER BY percentage LIMIT 8")
        today = db.query(
            "SELECT cs.session_id, cs.start_time, cs.end_time, cs.room, cs.status, c.course_code, c.course_name "
            "FROM class_sessions cs JOIN courses c ON c.course_id = cs.course_id "
            "WHERE cs.session_date = CURDATE() ORDER BY cs.start_time")
        exams = db.query(
            "SELECT es.exam_id, es.exam_type, es.exam_date, es.start_time, c.course_code, "
            "(SELECT COUNT(*) FROM exam_debarments ed WHERE ed.exam_id = es.exam_id) AS debarred "
            "FROM exam_schedules es JOIN courses c ON c.course_id = es.course_id "
            "WHERE es.exam_date >= CURDATE() ORDER BY es.exam_date LIMIT 5")

    chart = {
        "status": [dist.get("Good", 0), dist.get("Warning", 0), dist.get("Critical", 0)],
        "course_labels": [r["course_code"] for r in course_avg],
        "course_values": [round(r["avg_pct"], 1) for r in course_avg],
        "trend_labels": [r["d"].strftime("%d %b") for r in trend] if trend else [],
        "trend_values": [round(r["rate"] or 0, 1) for r in trend] if trend else [],
    }
    return kpi, chart, critical, today, exams
