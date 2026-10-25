# DBMS Implementation Guide: Hybrid ORM, Advanced SQL, Triggers & Procedures

## 1. Hybrid DBMS Architecture: SQLAlchemy ORM + Raw MySQL Connector

A central architectural decision in the **Smart Attendance Management System** is its **Hybrid Persistence Pattern**. Rather than forcing a single access pattern that creates either performance bottlenecks or brittle unstructured SQL, the system combines **SQLAlchemy 2.0 Declarative ORM** with **Raw MySQL Connector 9.0 Pure-Python Connection Pooling**.

```
                           +-------------------------------------+
                           |         Flask Application           |
                           +------------------+------------------+
                                              |
                   +--------------------------+--------------------------+
                   |                                                     |
                   v                                                     v
       +-----------------------+                             +-----------------------+
       |   SQLAlchemy 2.0 ORM  |                             |  Raw MySQL Connector  |
       |     (models/orm.py)   |                             |        (db.py)        |
       +-----------+-----------+                             +-----------+-----------+
                   |                                                     |
                   | • User CRUD & Authentication                        | • Live Video Attendance Marking
                   | • Student Demographic Updates                       | • Database Views Querying
                   | • Academic Entity Editing                           | • Stored Procedure Execution
                   | • Foreign Key Navigation                            | • Complex Analytical Trends
                   | • Transaction Contexts                              | • Connection Pooling (8 conns)
                   |                                                     |
                   +--------------------------+--------------------------+
                                              |
                                              v
                              +-------------------------------+
                              |    MySQL 8.0 Database Engine   |
                              |   (InnoDB, utf8mb4, ACID)     |
                              +-------------------------------+
```

### Architectural Justification: Why Both Layers Are Maintained

| Characteristic | SQLAlchemy ORM Layer (`models/orm.py`) | Direct MySQL Connector Layer (`db.py`) |
| :--- | :--- | :--- |
| **Primary Use Cases** | Entity updates, user account management, academic structure edits, relationship integrity. | Live streaming frame matching, high-throughput attendance inserts, executing database views and stored procedures. |
| **Performance Profile** | Overhead from Python object instantiation and identity mapping is acceptable for transactional management. | Near-zero latency execution. Critical for processing up to 30 frames/second during multi-face classroom attendance. |
| **Type Safety & Schema Validation** | Enforces Python type annotations, length constraints, and relationship integrity before touching database. | Bypasses ORM overhead; directly receives raw dictionaries or tuples for high-speed streaming. |
| **SQL Injection Prevention** | Abstracted queries with automatic parameterization. | Strictly parameterized using `%s` placeholders with tuple arguments; no dynamic string concatenation. |

---

## 2. Parameterization and Security Against SQL Injection

All direct database interactions in `db.py` and `services.py` use parameterized queries. Parameters are passed as separate tuples to the MySQL driver, ensuring the database engine treats all user inputs strictly as literals:

```python
# Safe Parameterized Query Example in services.py
sql = "SELECT v.*, d.dept_code FROM v_attendance_status v JOIN departments d ON d.department_id = v.department_id WHERE 1=1"
args = []
if student_id:
    sql += " AND v.student_id = %s"
    args.append(student_id)
if department_id:
    sql += " AND v.department_id = %s"
    args.append(department_id)

rows = db.query(sql, tuple(args))  # Never uses f-strings or string formatting on inputs!
```

---

## 3. Database Views: Analysis & Design

The database incorporates two interconnected analytical views that calculate live student attendance rates without storing redundant aggregated counters.

### View 1: `v_attendance_summary`
Aggregates total conducted sessions (sessions that were either `Open` or `Closed`, excluding future `Scheduled` ones) and total verified attendance records per student-course enrollment.

```sql
CREATE OR REPLACE VIEW v_attendance_summary AS
SELECT s.student_id, s.roll_no, s.name AS student_name, s.department_id,
       c.course_id, c.course_code, c.course_name,
       (SELECT COUNT(*) FROM class_sessions cs
         WHERE cs.course_id = c.course_id AND cs.status IN ('Open','Closed')) AS total_sessions,
       (SELECT COUNT(*) FROM attendance a
          JOIN class_sessions cs2 ON cs2.session_id = a.session_id
         WHERE a.student_id = s.student_id AND cs2.course_id = c.course_id) AS attended
FROM enrollments e
JOIN students s ON s.student_id = e.student_id
JOIN courses  c ON c.course_id  = e.course_id;
```

### View 2: `v_attendance_status`
Computes the dynamic percentage and categorizes attendance standing into discrete institutional tiers:
- **Good:** $\ge 80.0\%$
- **Warning:** $75.0\% \le \text{rate} < 80.0\%$
- **Critical:** $< 75.0\%$ (Qualifies for automated exam debarment)
- **No Classes:** When 0 sessions have been conducted to date.

```sql
CREATE OR REPLACE VIEW v_attendance_status AS
SELECT t.*,
       CASE WHEN t.total_sessions = 0 THEN NULL
            ELSE t.attended * 100.0 / t.total_sessions END AS percentage,
       CASE WHEN t.total_sessions = 0 THEN 'No Classes'
            WHEN t.attended * 100.0 / t.total_sessions >= 80 THEN 'Good'
            WHEN t.attended * 100.0 / t.total_sessions >= 75 THEN 'Warning'
            ELSE 'Critical' END AS status
FROM v_attendance_summary t;
```

---

## 4. Database Trigger: `trg_attendance_bi`

To guarantee that business rules are enforced at the database engine level (independent of application code), a `BEFORE INSERT` trigger defends the `attendance` table against illegal records:

```sql
DELIMITER $$

DROP TRIGGER IF EXISTS trg_attendance_bi$$
CREATE TRIGGER trg_attendance_bi BEFORE INSERT ON attendance
FOR EACH ROW
BEGIN
  DECLARE v_status VARCHAR(20);
  DECLARE v_course INT;
  DECLARE v_enrolled INT;

  -- 1. Enforce that session exists and is currently OPEN
  SELECT status, course_id INTO v_status, v_course
    FROM class_sessions WHERE session_id = NEW.session_id;

  IF v_status IS NULL OR v_status <> 'Open' THEN
    SIGNAL SQLSTATE '45000' 
      SET MESSAGE_TEXT = 'Attendance can only be marked while the class session is Open';
  END IF;

  -- 2. Enforce that the student is legitimately enrolled in this course
  SELECT COUNT(*) INTO v_enrolled
    FROM enrollments WHERE student_id = NEW.student_id AND course_id = v_course;

  IF v_enrolled = 0 THEN
    SIGNAL SQLSTATE '45000' 
      SET MESSAGE_TEXT = 'Student is not enrolled in this course';
  END IF;
END$$

DELIMITER ;
```

### Business Rules Enforced by the Trigger:
1. **Temporal Guard:** Attendance cannot be marked for a session that is still in `Scheduled` status or has already been marked `Closed`.
2. **Curriculum Guard:** Even if a face matches a registered student, attendance is rejected if the student is not registered in that specific course.

---

## 5. Stored Procedure: `sp_refresh_debarments`

The stored procedure `sp_refresh_debarments` provides an atomic, transactional engine for calculating exam debarments across all scheduled upcoming exams:

```sql
DELIMITER $$

DROP PROCEDURE IF EXISTS sp_refresh_debarments$$
CREATE PROCEDURE sp_refresh_debarments(IN p_threshold DECIMAL(5,2))
BEGIN
  -- Automatic transaction rollback on SQL exceptions
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  START TRANSACTION;

  -- 1. Purge existing debarments for UPCOMING exams only (preserving historical audit rows)
  DELETE ed FROM exam_debarments ed
    JOIN exam_schedules es ON es.exam_id = ed.exam_id
   WHERE es.exam_date >= CURDATE();

  -- 2. Populate debarred students who fall below the required threshold
  INSERT INTO exam_debarments (exam_id, student_id, attendance_pct, total_sessions, attended_sessions)
  SELECT es.exam_id, v.student_id, ROUND(v.percentage, 2), v.total_sessions, v.attended
    FROM exam_schedules es
    JOIN v_attendance_status v ON v.course_id = es.course_id
   WHERE es.exam_date >= CURDATE()
     AND v.total_sessions > 0
     AND v.percentage < p_threshold;

  COMMIT;
END$$

DELIMITER ;
```

---

## 6. Indexing & Query Performance Optimization

The database schema utilizes both clustered and non-clustered composite indexes to optimize the most frequent queries:

| Index Name | Table | Columns | Purpose |
| :--- | :--- | :--- | :--- |
| `idx_session_course_status` | `class_sessions` | `(course_id, status)` | Speeds up view subquery counting conducted classes (`Open` / `Closed`) |
| `idx_session_date` | `class_sessions` | `(session_date)` | Optimizes dashboard query fetching sessions scheduled for today |
| `idx_att_student` | `attendance` | `(student_id)` | Accelerates student attendance history and percentage aggregation |
| `idx_att_marked_at` | `attendance` | `(marked_at)` | Accelerates daily attendance activity queries |
| `idx_student_dept` | `students` | `(department_id)` | Optimizes department-level student roster filtering |
| `idx_course_dept` | `courses` | `(department_id)` | Optimizes course list filtering by academic department |
| `idx_faculty_dept` | `faculty` | `(department_id)` | Speeds up faculty assignment queries by department |
| `idx_user_role` | `users` | `(role)` | Optimizes authorization checks and user management filtering |
| `idx_user_faculty` | `users` | `(faculty_id)` | Speeds up linking between user login and faculty course scope |
| `uq_session_student` | `attendance` | `(session_id, student_id)` | **Enforces physical uniqueness:** Guarantees zero duplicate attendance marks per session |
| `uq_student_course` | `enrollments` | `(student_id, course_id)` | Prevents duplicate student course enrollment |
