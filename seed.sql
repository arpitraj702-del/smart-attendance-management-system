-- Optional starter data: departments, faculty and courses (no students: those need real face photos).
INSERT IGNORE INTO departments (dept_code, dept_name) VALUES
  ('CSE',  'Computer Science and Engineering'),
  ('ECE',  'Electronics and Communication Engineering'),
  ('MECH', 'Mechanical Engineering');

INSERT IGNORE INTO faculty (department_id, name, email, phone)
SELECT department_id, 'Dr. Anita Rao', 'anita.rao@example.edu', '9000000001' FROM departments WHERE dept_code = 'CSE';
INSERT IGNORE INTO faculty (department_id, name, email, phone)
SELECT department_id, 'Prof. Karthik Menon', 'karthik.menon@example.edu', '9000000002' FROM departments WHERE dept_code = 'CSE';
INSERT IGNORE INTO faculty (department_id, name, email, phone)
SELECT department_id, 'Dr. Meera Iyer', 'meera.iyer@example.edu', '9000000003' FROM departments WHERE dept_code = 'ECE';

INSERT IGNORE INTO courses (course_code, course_name, department_id, faculty_id, semester, credits)
SELECT 'CS301', 'Database Management Systems', d.department_id, f.faculty_id, 5, 4
  FROM departments d JOIN faculty f ON f.email = 'anita.rao@example.edu' WHERE d.dept_code = 'CSE';
INSERT IGNORE INTO courses (course_code, course_name, department_id, faculty_id, semester, credits)
SELECT 'CS302', 'Operating Systems', d.department_id, f.faculty_id, 5, 4
  FROM departments d JOIN faculty f ON f.email = 'karthik.menon@example.edu' WHERE d.dept_code = 'CSE';
INSERT IGNORE INTO courses (course_code, course_name, department_id, faculty_id, semester, credits)
SELECT 'CS303', 'Computer Networks', d.department_id, f.faculty_id, 5, 3
  FROM departments d JOIN faculty f ON f.email = 'karthik.menon@example.edu' WHERE d.dept_code = 'CSE';
INSERT IGNORE INTO courses (course_code, course_name, department_id, faculty_id, semester, credits)
SELECT 'EC301', 'Digital Signal Processing', d.department_id, f.faculty_id, 5, 4
  FROM departments d JOIN faculty f ON f.email = 'meera.iyer@example.edu' WHERE d.dept_code = 'ECE';

-- Seed sample faculty user for Dr. Anita Rao (Password: Faculty@123)
INSERT IGNORE INTO users (username, email, password_hash, role, faculty_id, is_active)
SELECT 'anita_rao', 'anita.rao@example.edu',
       'scrypt:32768:8:1$GkuXeTWlvjDuRfNP$e79294837b61e8ff55f5152c36397f7ea87afd03121663a985ebc83426687c3b444b904b661826ff38e2ec916351fb0dd5b675a6d010310183f9da05d2e18a9f',
       'Faculty', faculty_id, 1
  FROM faculty WHERE email = 'anita.rao@example.edu';
