r"""Generator script for the official DBMS Viva and Demonstration Guide.

Creates both:
1. Microsoft Word (.docx) file at C:\Users\arpit\Downloads\smart_attendance (1)\DBMS_Viva_and_Demonstration_Guide.docx
2. Markdown documentation at C:\Users\arpit\Downloads\smart_attendance (1)\smart_attendance\docs\DBMS_VIVA_AND_DEMONSTRATION_GUIDE.md

Strict formatting:
- Times New Roman
- 16 pt bold headings, 14 pt body
- 100% black text
- Simple bordered tables
- Page numbers in footer
"""
import shutil
from pathlib import Path

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

BASE_DIR = Path(r"C:\Users\arpit\Downloads\smart_attendance (1)\smart_attendance")
DOCS_DIR = BASE_DIR / "docs"
OUTPUT_DOCX = Path(r"C:\Users\arpit\Downloads\smart_attendance (1)\DBMS_Viva_and_Demonstration_Guide.docx")
ARTIFACT_DOCX = Path(r"C:\Users\arpit\.gemini\antigravity\brain\d237fb49-c4c3-4c8f-a41c-ce75f13fae52\DBMS_Viva_and_Demonstration_Guide.docx")
OUTPUT_MD = DOCS_DIR / "DBMS_VIVA_AND_DEMONSTRATION_GUIDE.md"


def style_table(table):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblPr = table._tbl.tblPr
    tblBorders = OxmlElement('w:tblBorders')
    for b in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        el = OxmlElement(f'w:{b}')
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), '4')
        el.set(qn('w:space'), '0')
        el.set(qn('w:color'), '000000')
        tblBorders.append(el)
    tblPr.append(tblBorders)


class VivaGuideBuilder:
    def __init__(self):
        self.doc = docx.Document()
        self._setup_page_properties()

    def _setup_page_properties(self):
        for section in self.doc.sections:
            section.top_margin = Inches(1.0)
            section.bottom_margin = Inches(1.0)
            section.left_margin = Inches(1.0)
            section.right_margin = Inches(1.0)
            section.page_width = Inches(8.5)
            section.page_height = Inches(11.0)

            # Footer
            footer = section.footer
            f_p = footer.paragraphs[0]
            f_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            r_foot = f_p.add_run("Page ")
            r_foot.font.name = "Times New Roman"
            r_foot.font.size = Pt(11)
            r_foot.font.color.rgb = RGBColor(0, 0, 0)
            fld = OxmlElement('w:fldSimple')
            fld.set(qn('w:instr'), 'PAGE')
            f_p._p.append(fld)

    def add_title_block(self):
        p_title = self.doc.add_paragraph()
        p_title.paragraph_format.space_before = Pt(0)
        p_title.paragraph_format.space_after = Pt(4)
        r_title = p_title.add_run("Smart Attendance Management System — DBMS Viva & Demonstration Guide")
        r_title.font.name = "Times New Roman"
        r_title.font.size = Pt(16)
        r_title.font.bold = True
        r_title.font.color.rgb = RGBColor(0, 0, 0)

        p_name = self.doc.add_paragraph()
        p_name.paragraph_format.space_before = Pt(0)
        p_name.paragraph_format.space_after = Pt(2)
        r_name = p_name.add_run("Name: Arpit Raj")
        r_name.font.name = "Times New Roman"
        r_name.font.size = Pt(14)
        r_name.font.color.rgb = RGBColor(0, 0, 0)

        p_reg = self.doc.add_paragraph()
        p_reg.paragraph_format.space_before = Pt(0)
        p_reg.paragraph_format.space_after = Pt(14)
        r_reg = p_reg.add_run("Reg. No.: 24BCE2897")
        r_reg.font.name = "Times New Roman"
        r_reg.font.size = Pt(14)
        r_reg.font.color.rgb = RGBColor(0, 0, 0)

    def add_heading(self, text, space_before=14, space_after=6):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(16)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def add_subheading(self, text, space_before=10, space_after=4):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def add_paragraph(self, text, space_after=6):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(space_after)
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(14)
        run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def add_bullet(self, text, bold_prefix="", space_after=3):
        p = self.doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(space_after)
        if bold_prefix:
            r_bold = p.add_run(bold_prefix)
            r_bold.font.name = "Times New Roman"
            r_bold.font.size = Pt(14)
            r_bold.font.bold = True
            r_bold.font.color.rgb = RGBColor(0, 0, 0)
        r_text = p.add_run(text)
        r_text.font.name = "Times New Roman"
        r_text.font.size = Pt(14)
        r_text.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def add_code_block(self, code_text):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.left_indent = Inches(0.2)
        run = p.add_run(code_text)
        run.font.name = "Courier New"
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def add_table(self, headers, rows_data, col_widths=None):
        table = self.doc.add_table(rows=len(rows_data) + 1, cols=len(headers))
        style_table(table)
        for i, header_text in enumerate(headers):
            cell = table.rows[0].cells[i]
            cell.text = header_text
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(12)
                r.font.bold = True
                r.font.color.rgb = RGBColor(0, 0, 0)

        for r_idx, row_values in enumerate(rows_data):
            row_cells = table.rows[r_idx + 1].cells
            for c_idx, val in enumerate(row_values):
                row_cells[c_idx].text = str(val)
                p = row_cells[c_idx].paragraphs[0]
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after = Pt(2)
                for r in p.runs:
                    r.font.name = "Times New Roman"
                    r.font.size = Pt(12)
                    r.font.color.rgb = RGBColor(0, 0, 0)

        if col_widths:
            for row in table.rows:
                for idx, w in enumerate(col_widths):
                    row.cells[idx].width = Inches(w)
        p_after = self.doc.add_paragraph()
        p_after.paragraph_format.space_before = Pt(0)
        p_after.paragraph_format.space_after = Pt(6)
        return table


def generate_viva_guide():
    print("Building DBMS Viva and Demonstration Guide...")
    b = VivaGuideBuilder()
    b.add_title_block()

    b.add_heading("1. Project Demonstration Guide (Step-by-Step)")
    b.add_subheading("1.1 Starting the System on Windows")
    b.add_paragraph(
        "To demonstrate the project to the faculty examiner, open Windows PowerShell and execute the following exact commands:"
    )
    b.add_code_block(
        "# Navigate to project directory\n"
        "cd \"C:\\Users\\arpit\\Downloads\\smart_attendance (1)\\smart_attendance\"\n\n"
        "# Activate virtual environment\n"
        "..\\.venv\\Scripts\\Activate.ps1\n\n"
        "# Verify automated tests (10/10 tests pass)\n"
        "python test_system.py\n\n"
        "# Launch web application\n"
        "python app.py"
    )
    b.add_paragraph(
        "Open Google Chrome or Microsoft Edge and navigate to http://127.0.0.1:5000. When prompted, allow camera permissions."
    )

    b.add_subheading("1.2 Demonstration Login Accounts")
    b.add_table(
        ["Role", "Username", "Password", "What to Demonstrate"],
        [
            ["Administrator", "admin", "Admin@12345", "Full system access: User management (/users), academic CRUD, all course sessions, exam scheduling."],
            ["Faculty Member", "anita_rao", "Faculty@123", "Course-scoped access: Shows Dr. Anita Rao's courses (CS301), taking attendance, scoped dashboard."],
        ],
        [1.5, 1.5, 1.5, 3.0]
    )

    b.add_subheading("1.3 Step-by-Step Faculty Demonstration Sequence")
    b.add_bullet("Sign in as admin. Show the 5 KPI cards (Students, Courses, Faculty, Conducted Sessions, Today's Attendance), the status doughnut chart, and the 14-day trend line.", "Step 1: Executive Dashboard - ")
    b.add_bullet("Navigate to Academics. Show the 3 tables (Departments, Faculty, Courses). Demonstrate the 'Edit' modal on a department and explain how SQLAlchemy ORM commits the update.", "Step 2: Academic CRUD & ORM - ")
    b.add_bullet("Navigate to Students. Show search filtering by name/roll number and pagination controls. Open student profile 'Arpit Raj (24BCE2897)', explain the attendance progress bar, and show the 'Edit Details' modal.", "Step 3: Student Directory - ")
    b.add_bullet("Navigate to Class Sessions. Show scheduled sessions. Click 'Create Session' with 'Start now and open camera' checked. Point your webcam at your face. Show the green bounding box confirming your identity and incrementing the Present counter.", "Step 4: Live Attendance - ")
    b.add_bullet("Show that an unregistered person or covering your face results in a red 'Unknown User' bounding box and zero database inserts. Click 'Close Session'.", "Step 5: Unknown Face Guard - ")
    b.add_bullet("Navigate to Shortage Report. Show how percentages update dynamically via view v_attendance_status and show the 'Classes needed for 75%' formula.", "Step 6: Attendance Shortage - ")
    b.add_bullet("Navigate to Exams & Debarment. Click 'Schedule Exam'. Explain how stored procedure sp_refresh_debarments automatically recalculates debarred students (<75%).", "Step 7: Automated Debarment - ")
    b.add_bullet("Navigate to User Management. Show user roles, active status toggles, and password resetting. Log out and log in as anita_rao to prove role enforcement.", "Step 8: Multi-Role Security - ")

    b.add_heading("2. Database Objects Quick Reference")
    b.add_table(
        ["Database Object", "Type", "Primary Key / Parameters", "Key DBMS Feature & Purpose"],
        [
            ["departments", "Table (1)", "department_id (PK)", "Stores academic departments. UNIQUE(dept_code, dept_name)."],
            ["faculty", "Table (2)", "faculty_id (PK)", "Stores faculty members. FK to departments (RESTRICT). UNIQUE(email)."],
            ["courses", "Table (3)", "course_id (PK)", "Stores courses. FKs to departments & faculty. CHECK(semester BETWEEN 1 AND 12)."],
            ["students", "Table (4)", "student_id (PK)", "Stores students. UNIQUE(roll_no), UNIQUE(email). CHECK(semester 1..12)."],
            ["face_encodings", "Table (5)", "encoding_id (PK)", "Stores 128-D SFace float vectors (BLOB). FK to students (CASCADE)."],
            ["enrollments", "Table (6)", "enrollment_id (PK)", "Associative table (M:N). UNIQUE(student_id, course_id). FKs (CASCADE)."],
            ["class_sessions", "Table (7)", "session_id (PK)", "State machine ('Scheduled','Open','Closed'). CHECK(end_time > start_time)."],
            ["attendance", "Table (8)", "attendance_id (PK)", "Verified marks. UNIQUE(session_id, student_id) prevents duplicates."],
            ["exam_schedules", "Table (9)", "exam_id (PK)", "Exam dates and venues. CHECK(end_time > start_time). FK to courses."],
            ["exam_debarments", "Table (10)", "debarment_id (PK)", "Calculated debarred students (<75%). UNIQUE(exam_id, student_id)."],
            ["users", "Table (11)", "user_id (PK)", "Authentication table. UNIQUE(username, email). CHECK(role IN ('Admin','Faculty'))."],
            ["v_attendance_summary", "View", "N/A", "Computes conducted classes and student attendances using correlated subqueries."],
            ["v_attendance_status", "View", "N/A", "Calculates percentage and standing: Good (>=80%), Warning (75-80%), Critical (<75%)."],
            ["trg_attendance_bi", "Trigger", "BEFORE INSERT", "Signals SQLSTATE 45000 if session is not Open or student not enrolled."],
            ["sp_refresh_debarments", "Procedure", "IN p_threshold DECIMAL", "Transactional routine purging & recalculating debarred students for future exams."],
        ],
        [1.8, 1.0, 1.7, 3.0]
    )

    b.add_heading("3. Top 20 Likely Faculty Viva Questions & High-Scoring Answers")

    qas = [
        ("Q1: Why did you choose MySQL over a NoSQL database (like MongoDB) for this project?",
         "Answer: Our domain requires strict relational integrity across 11 interconnected tables (students, courses, enrollments, sessions, attendance). "
         "Relational features such as foreign key cascading, composite UNIQUE constraints (preventing duplicate attendance), domain CHECK constraints, "
         "BEFORE INSERT triggers, and ACID transactions are essential. A document store lacks declarative engine-level constraint enforcement."),

        ("Q2: How do you prove your database is normalized to 3NF and BCNF?",
         "Answer: 1NF is satisfied because all attributes store atomic scalar values, and repeating groups (photos, enrollments) are normalized into child tables. "
         "2NF is satisfied because all non-key attributes depend on the whole primary key (no partial dependencies on surrogate keys or composite keys). "
         "3NF is satisfied because there are no transitive dependencies (e.g., student links to department_id, not dept_name). "
         "BCNF is satisfied because every determinant in every functional dependency is a superkey."),

        ("Q3: How does the system physically prevent duplicate attendance in the same lecture?",
         "Answer: Duplicate prevention is enforced at three independent levels: "
         "1. Database Engine: The composite UNIQUE KEY uq_session_student on (session_id, student_id) in the attendance table causes MySQL to reject duplicate inserts with error 1062. "
         "2. Application Logic: The live recognition API checks the database before inserting. "
         "3. Camera Streak Lock: A student ID is locked once marked during that lecture session."),

        ("Q4: What is the purpose of the database trigger trg_attendance_bi?",
         "Answer: It is a BEFORE INSERT trigger on the attendance table that guarantees business rules at the DBMS engine level. "
         "It checks two conditions: first, whether class_sessions.status = 'Open'; second, whether the student is legitimately enrolled in that course in enrollments. "
         "If either condition fails, it raises SIGNAL SQLSTATE '45000', aborting the insert even if someone bypassed the web interface and ran a raw SQL statement."),

        ("Q5: How does the stored procedure sp_refresh_debarments work?",
         "Answer: It is an atomic routine that takes an attendance threshold parameter (75.0%). "
         "It opens a transaction (START TRANSACTION), deletes existing debarment records for upcoming exams (preserving past historical exams), "
         "and executes an INSERT INTO ... SELECT query joining exam_schedules with the v_attendance_status view to insert students below 75%. "
         "It includes a DECLARE EXIT HANDLER FOR SQLEXCEPTION that executes ROLLBACK if any error occurs."),

        ("Q6: Why does your project use both SQLAlchemy ORM and raw MySQL Connector?",
         "Answer: This is a deliberate hybrid architecture. SQLAlchemy 2.0 ORM is used for entity CRUD (Users, Students, Departments, Courses) "
         "where type safety, relationship navigation, and model validation are crucial. The raw pooled MySQL Connector (db.py) is retained for "
         "real-time video streaming attendance (up to 30 frames/sec) and stored procedures, where ORM object instantiation overhead would cause frame drops."),

        ("Q7: How does your database calculate student attendance percentages?",
         "Answer: Rather than storing an error-prone percentage column that requires constant updating, the database uses two views: "
         "v_attendance_summary counts conducted classes (status IN ('Open','Closed')) and attended classes via correlated subqueries. "
         "v_attendance_status computes attended / total * 100 and uses a CASE statement to categorize status as Good (>=80%), Warning (75-80%), or Critical (<75%)."),

        ("Q8: How is the number of consecutive classes needed to attain 75% calculated?",
         "Answer: Mathematically, if a student attended 'a' classes out of 't' total, and needs 'n' consecutive future classes to reach 75%: "
         "(a + n) / (t + n) >= 0.75  =>  4(a + n) >= 3(t + n)  =>  4a + 4n >= 3t + 3n  =>  n >= 3t - 4a. "
         "The services.classes_needed function computes max(0, 3*t - 4*a)."),

        ("Q9: How are student biometric face encodings stored in MySQL?",
         "Answer: The SFace deep neural network extracts a 128-dimensional vector of 32-bit floating-point numbers (128 * 4 = 512 bytes). "
         "This is stored directly as raw binary in a BLOB column in the face_encodings table. We do NOT store high-resolution photos in the database; "
         "only a 240px cropped face thumbnail is saved on disk for display."),

        ("Q10: How do you prevent SQL injection?",
         "Answer: All SQL queries in db.py and services.py use parameterized queries with '%s' placeholders and separate argument tuples passed to the driver. "
         "The database engine parses the SQL syntax first and treats user parameters strictly as literals, making SQL injection impossible. "
         "In the ORM layer, SQLAlchemy automatically uses parameterized query compilation."),

        ("Q11: How is user authentication implemented, and why is scrypt used?",
         "Answer: User authentication queries the users table in MySQL. Passwords are encrypted using Werkzeug's scrypt key derivation function. "
         "scrypt is a memory-hard algorithm designed to resist specialized ASIC and GPU brute-force cracking. Plaintext passwords are never logged or stored."),

        ("Q12: How do you enforce Role-Based Access Control (RBAC)?",
         "Answer: The users table contains an ENUM column role with values 'Admin' and 'Faculty'. "
         "Route protection is enforced using the custom Python decorator @role_required('Admin'). "
         "If a user with role 'Faculty' attempts to access administrative routes (like /users), the server immediately returns HTTP 403 Forbidden."),

        ("Q13: How does the camera handle an unregistered person or a photo of someone else?",
         "Answer: The YuNet detector detects the face and extracts its 128-D vector. The vector is compared against all registered vectors using cosine similarity. "
         "If the maximum similarity is below MATCH_THRESHOLD (0.40), or if the difference between the top-two matching students is less than MATCH_MARGIN (0.05), "
         "the person is classified as 'Unknown User' (red box) and zero database writes occur."),

        ("Q14: How does the system handle database migrations without losing existing data?",
         "Answer: The migration runner (migrate.py) maintains a schema_migrations table in MySQL. "
         "When migrations run, it checks which SQL migration files have already been applied, executing only new scripts in a single transaction. "
         "Existing student rows, face vectors, and attendance records are completely preserved."),

        ("Q15: What referential integrity delete actions are used, and why?",
         "Answer: We use three specific actions: "
         "1. ON DELETE RESTRICT on departments: A department cannot be deleted while faculty, courses, or students are linked to it. "
         "2. ON DELETE SET NULL on courses.faculty_id: If a faculty member leaves, the course remains in the catalog. "
         "3. ON DELETE CASCADE on face_encodings, enrollments, and attendance: If a student is deleted, their biometric vectors and attendance records are automatically purged."),

        ("Q16: Can a faculty member open a session for a course they do not teach?",
         "Answer: No. In app.py, the open_session and create_session routes verify whether session.get('role') == 'Faculty'. "
         "If so, they compare the course's assigned faculty_id with the logged-in user's faculty_id. If they do not match, the request is aborted with 403 Forbidden."),

        ("Q17: How is connection pooling implemented, and why is it needed?",
         "Answer: db.py uses mysql.connector.pooling.MySQLConnectionPool with a pool size of 8 connections. "
         "Opening a TCP connection to MySQL takes 10 to 30 ms. Reusing pooled connections allows requests to execute in under 2 ms, which is essential for video streaming."),

        ("Q18: What indexes are implemented in your schema to optimize query performance?",
         "Answer: In addition to primary keys, we have: "
         "1. idx_session_course_status on class_sessions(course_id, status) for view subqueries counting conducted classes. "
         "2. idx_session_date on class_sessions(session_date) for today's schedule query. "
         "3. idx_att_student on attendance(student_id) for student profile history. "
         "4. idx_att_marked_at on attendance(marked_at) for daily attendance trend queries. "
         "5. Foreign key indexes on department_id across students, courses, and faculty."),

        ("Q19: How do your backup and restore scripts ensure safety?",
         "Answer: backup_db.ps1 uses mysqldump with --single-transaction (ensuring read consistency without table locking) and --routines --triggers. "
         "restore_db.ps1 requires the user to type 'YES' before executing, preventing accidental overwrites."),

        ("Q20: What are the primary technical limitations of the system?",
         "Answer: The two primary limitations are: "
         "1. No active liveness detection (a printed photo or phone screen could match an enrolled student if unsupervised). "
         "2. Lighting sensitivity: SFace cosine similarity can vary in dim lighting, which is why we enforce the streak confirmation filter (2 consecutive frames) and ambiguity margins.")
    ]

    for q, a in qas:
        b.add_subheading(q)
        b.add_paragraph(a)

    print(f"Saving Viva Guide DOCX to: {OUTPUT_DOCX}")
    b.doc.save(str(OUTPUT_DOCX))
    print(f"Copying to artifact directory: {ARTIFACT_DOCX}")
    shutil.copy2(OUTPUT_DOCX, ARTIFACT_DOCX)
    print("Viva Guide Word Document generated successfully!")


if __name__ == "__main__":
    generate_viva_guide()
