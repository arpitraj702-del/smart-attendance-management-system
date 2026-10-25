-- =====================================================================
-- Smart Attendance Management System  |  MySQL 8.0+  |  InnoDB, utf8mb4
-- Run with:  python setup_db.py          (recommended)
-- =====================================================================
CREATE DATABASE IF NOT EXISTS smart_attendance CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_attendance;

-- ---------------------------------------------------------------------
-- 1. departments
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS departments (
  department_id INT AUTO_INCREMENT PRIMARY KEY,
  dept_code     VARCHAR(10)  NOT NULL UNIQUE,
  dept_name     VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 2. faculty
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS faculty (
  faculty_id    INT AUTO_INCREMENT PRIMARY KEY,
  department_id INT          NOT NULL,
  name          VARCHAR(100) NOT NULL,
  email         VARCHAR(120) NOT NULL UNIQUE,
  phone         VARCHAR(20)  NULL,
  KEY idx_faculty_dept (department_id),
  CONSTRAINT fk_faculty_dept FOREIGN KEY (department_id)
    REFERENCES departments(department_id) ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 3. courses
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS courses (
  course_id     INT AUTO_INCREMENT PRIMARY KEY,
  course_code   VARCHAR(20)  NOT NULL UNIQUE,
  course_name   VARCHAR(120) NOT NULL,
  department_id INT          NOT NULL,
  faculty_id    INT          NULL,
  semester      TINYINT      NOT NULL,
  credits       TINYINT      NOT NULL DEFAULT 3,
  KEY idx_course_dept (department_id),
  CONSTRAINT chk_course_sem CHECK (semester BETWEEN 1 AND 12),
  CONSTRAINT fk_course_dept FOREIGN KEY (department_id)
    REFERENCES departments(department_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_course_faculty FOREIGN KEY (faculty_id)
    REFERENCES faculty(faculty_id) ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 4. students
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS students (
  student_id    INT AUTO_INCREMENT PRIMARY KEY,
  roll_no       VARCHAR(30)  NOT NULL UNIQUE,
  name          VARCHAR(100) NOT NULL,
  email         VARCHAR(120) NULL UNIQUE,
  department_id INT          NOT NULL,
  semester      TINYINT      NOT NULL,
  has_photo     TINYINT(1)   NOT NULL DEFAULT 0,
  registered_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_student_dept (department_id),
  CONSTRAINT chk_student_sem CHECK (semester BETWEEN 1 AND 12),
  CONSTRAINT fk_student_dept FOREIGN KEY (department_id)
    REFERENCES departments(department_id) ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 5. face_encodings  (128-D SFace embeddings, float32 little-endian = 512 bytes)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS face_encodings (
  encoding_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id  INT          NOT NULL,
  embedding   BLOB         NOT NULL,
  model_name  VARCHAR(40)  NOT NULL DEFAULT 'SFace-2021dec',
  created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_face_student FOREIGN KEY (student_id)
    REFERENCES students(student_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 6. enrollments  (student <-> course, many-to-many)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS enrollments (
  enrollment_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id    INT  NOT NULL,
  course_id     INT  NOT NULL,
  enrolled_on   DATE NOT NULL DEFAULT (CURRENT_DATE),
  UNIQUE KEY uq_student_course (student_id, course_id),
  CONSTRAINT fk_enr_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
  CONSTRAINT fk_enr_course  FOREIGN KEY (course_id)  REFERENCES courses(course_id)  ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 7. class_sessions  (Scheduled -> Open -> Closed)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS class_sessions (
  session_id   INT AUTO_INCREMENT PRIMARY KEY,
  course_id    INT          NOT NULL,
  faculty_id   INT          NULL,
  session_date DATE         NOT NULL,
  start_time   TIME         NOT NULL,
  end_time     TIME         NOT NULL,
  room         VARCHAR(30)  NULL,
  topic        VARCHAR(150) NULL,
  status       ENUM('Scheduled','Open','Closed') NOT NULL DEFAULT 'Scheduled',
  opened_at    DATETIME     NULL,
  closed_at    DATETIME     NULL,
  CONSTRAINT chk_session_time CHECK (end_time > start_time),
  KEY idx_session_course_status (course_id, status),
  KEY idx_session_date (session_date),
  CONSTRAINT fk_session_course  FOREIGN KEY (course_id)  REFERENCES courses(course_id) ON DELETE CASCADE,
  CONSTRAINT fk_session_faculty FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 8. attendance  (a row = "present"; absence = no row for an enrolled student)
--    UNIQUE (session_id, student_id) is what prevents duplicate attendance.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance (
  attendance_id INT AUTO_INCREMENT PRIMARY KEY,
  session_id    INT          NOT NULL,
  student_id    INT          NOT NULL,
  marked_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  confidence    DECIMAL(5,4) NOT NULL,
  UNIQUE KEY uq_session_student (session_id, student_id),
  KEY idx_att_student (student_id),
  KEY idx_att_marked_at (marked_at),
  CONSTRAINT fk_att_session FOREIGN KEY (session_id) REFERENCES class_sessions(session_id) ON DELETE CASCADE,
  CONSTRAINT fk_att_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 9. exam_schedules
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS exam_schedules (
  exam_id    INT AUTO_INCREMENT PRIMARY KEY,
  course_id  INT         NOT NULL,
  exam_type  ENUM('Internal','Mid-Term','End-Term','Practical') NOT NULL DEFAULT 'End-Term',
  exam_date  DATE        NOT NULL,
  start_time TIME        NOT NULL,
  end_time   TIME        NOT NULL,
  venue      VARCHAR(60) NULL,
  CONSTRAINT chk_exam_time CHECK (end_time > start_time),
  CONSTRAINT fk_exam_course FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 10. exam_debarments  (maintained by sp_refresh_debarments)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS exam_debarments (
  debarment_id      INT AUTO_INCREMENT PRIMARY KEY,
  exam_id           INT          NOT NULL,
  student_id        INT          NOT NULL,
  attendance_pct    DECIMAL(6,2) NOT NULL,
  total_sessions    INT          NOT NULL,
  attended_sessions INT          NOT NULL,
  generated_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_exam_student (exam_id, student_id),
  CONSTRAINT fk_deb_exam    FOREIGN KEY (exam_id)    REFERENCES exam_schedules(exam_id) ON DELETE CASCADE,
  CONSTRAINT fk_deb_student FOREIGN KEY (student_id) REFERENCES students(student_id)    ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 11. users  (Authentication & Role-Based Access Control)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  user_id       INT AUTO_INCREMENT PRIMARY KEY,
  username      VARCHAR(50)  NOT NULL UNIQUE,
  email         VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role          ENUM('Admin', 'Faculty') NOT NULL DEFAULT 'Faculty',
  faculty_id    INT          NULL,
  is_active     TINYINT(1)   NOT NULL DEFAULT 1,
  created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT chk_user_role CHECK (role IN ('Admin', 'Faculty')),
  CONSTRAINT chk_user_active CHECK (is_active IN (0, 1)),
  KEY idx_user_role (role),
  KEY idx_user_faculty (faculty_id),
  CONSTRAINT fk_user_faculty FOREIGN KEY (faculty_id)
    REFERENCES faculty(faculty_id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 12. schema_migrations  (Tracks applied database migrations)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_migrations (
  version    VARCHAR(100) PRIMARY KEY,
  applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- =====================================================================
-- VIEWS
-- "Conducted" sessions = sessions whose status is Open or Closed.
-- Percentage = attended / conducted * 100 (NULL when nothing conducted yet).
-- Status: >= 80 Good, 75..79.99 Warning, < 75 Critical.
-- =====================================================================
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

CREATE OR REPLACE VIEW v_attendance_status AS
SELECT t.*,
       CASE WHEN t.total_sessions = 0 THEN NULL
            ELSE t.attended * 100.0 / t.total_sessions END AS percentage,
       CASE WHEN t.total_sessions = 0 THEN 'No Classes'
            WHEN t.attended * 100.0 / t.total_sessions >= 80 THEN 'Good'
            WHEN t.attended * 100.0 / t.total_sessions >= 75 THEN 'Warning'
            ELSE 'Critical' END AS status
FROM v_attendance_summary t;

-- =====================================================================
-- TRIGGER: the database itself refuses attendance for a closed/unopened
-- session or for a student who is not enrolled in the course.
-- =====================================================================
DELIMITER $$

DROP TRIGGER IF EXISTS trg_attendance_bi$$
CREATE TRIGGER trg_attendance_bi BEFORE INSERT ON attendance
FOR EACH ROW
BEGIN
  DECLARE v_status VARCHAR(20);
  DECLARE v_course INT;
  DECLARE v_enrolled INT;

  SELECT status, course_id INTO v_status, v_course
    FROM class_sessions WHERE session_id = NEW.session_id;

  IF v_status IS NULL OR v_status <> 'Open' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Attendance can only be marked while the class session is Open';
  END IF;

  SELECT COUNT(*) INTO v_enrolled
    FROM enrollments WHERE student_id = NEW.student_id AND course_id = v_course;

  IF v_enrolled = 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Student is not enrolled in this course';
  END IF;
END$$

-- =====================================================================
-- STORED PROCEDURE: rebuild debarment list for all upcoming exams.
-- A student is debarred when course attendance is below p_threshold.
-- Past exams keep their historical rows.
-- =====================================================================
DROP PROCEDURE IF EXISTS sp_refresh_debarments$$
CREATE PROCEDURE sp_refresh_debarments(IN p_threshold DECIMAL(5,2))
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  START TRANSACTION;

  DELETE ed FROM exam_debarments ed
    JOIN exam_schedules es ON es.exam_id = ed.exam_id
   WHERE es.exam_date >= CURDATE();

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
