-- Migration 002: Add complementary indexes for query performance optimization
-- MySQL requires procedure or conditional block to avoid errors on duplicate index names if re-run

DELIMITER $$

DROP PROCEDURE IF EXISTS _add_migration_002_indexes$$
CREATE PROCEDURE _add_migration_002_indexes()
BEGIN
  -- index on students department_id
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'students' AND index_name = 'idx_student_dept'
  ) THEN
    ALTER TABLE students ADD INDEX idx_student_dept (department_id);
  END IF;

  -- index on courses department_id
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'courses' AND index_name = 'idx_course_dept'
  ) THEN
    ALTER TABLE courses ADD INDEX idx_course_dept (department_id);
  END IF;

  -- index on faculty department_id
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'faculty' AND index_name = 'idx_faculty_dept'
  ) THEN
    ALTER TABLE faculty ADD INDEX idx_faculty_dept (department_id);
  END IF;

  -- index on attendance marked_at
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'attendance' AND index_name = 'idx_att_marked_at'
  ) THEN
    ALTER TABLE attendance ADD INDEX idx_att_marked_at (marked_at);
  END IF;
END$$

DELIMITER ;

CALL _add_migration_002_indexes();
DROP PROCEDURE IF EXISTS _add_migration_002_indexes;
