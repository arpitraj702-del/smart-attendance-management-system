-- Migration 001: Create users table with role-based access control and constraints
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
