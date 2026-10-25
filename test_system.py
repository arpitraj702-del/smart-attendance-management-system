"""Comprehensive test suite for Smart Attendance Management System.

Tests:
1. Environment and database connectivity
2. Authentication (Werkzeug hashing, login, logout, password verification)
3. Role-based access control (Admin allowed, Faculty restricted to 403)
4. SQLAlchemy ORM CRUD and relations
5. Database Views (v_attendance_summary, v_attendance_status)
6. Stored Procedure (sp_refresh_debarments) and Triggers
7. Pagination and filtering logic
"""
import unittest

import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash

import app
import db
import db_orm
import models
import services
from pagination import Pagination


class TestSmartAttendance(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.flask_app = app.app
        cls.flask_app.config["TESTING"] = True
        cls.flask_app.config["WTF_CSRF_ENABLED"] = False
        cls.client = cls.flask_app.test_client()

    def test_01_db_connection(self):
        """Test database connection and tables exist."""
        with self.flask_app.app_context():
            cur = db.get_db().cursor()
            cur.execute("SHOW TABLES LIKE 'users'")
            res = cur.fetchone()
            cur.close()
            self.assertIsNotNone(res, "Users table should exist in the database.")

    def test_02_password_hashing(self):
        """Test Werkzeug secure password hashing."""
        pwd = "SecretAdminPass123!"
        hashed = generate_password_hash(pwd)
        self.assertTrue(check_password_hash(hashed, pwd))
        self.assertFalse(check_password_hash(hashed, "WrongPass"))
        self.assertFalse(hashed.startswith("plaintext"))

    def test_03_orm_models_and_queries(self):
        """Test SQLAlchemy ORM querying and relationships."""
        with self.flask_app.app_context():
            orm_sess = db_orm.get_orm_session()
            admin = orm_sess.query(models.User).filter_by(role="Admin").first()
            self.assertIsNotNone(admin, "At least one Admin user should exist.")
            self.assertEqual(admin.role, "Admin")

            depts = orm_sess.query(models.Department).all()
            self.assertGreater(len(depts), 0, "Departments should be populated.")

            courses = orm_sess.query(models.Course).all()
            self.assertGreater(len(courses), 0, "Courses should be populated.")

    def test_04_stored_procedure_and_views(self):
        """Test stored procedure sp_refresh_debarments and views."""
        with self.flask_app.app_context():
            # Refresh debarments via stored procedure
            services.refresh_debarments()
            # Query view
            rows = db.query("SELECT * FROM v_attendance_status LIMIT 5")
            self.assertIsInstance(rows, list)

    def test_05_pagination_helper(self):
        """Test pagination logic."""
        p = Pagination(page=2, per_page=10, total_items=45)
        self.assertEqual(p.page, 2)
        self.assertEqual(p.total_pages, 5)
        self.assertEqual(p.offset, 10)
        self.assertTrue(p.has_prev)
        self.assertTrue(p.has_next)
        self.assertEqual(p.start_index, 11)
        self.assertEqual(p.end_index, 20)

    def test_06_unauthenticated_redirect(self):
        """Test that unauthenticated requests redirect to login."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers.get("Location", ""))

    def test_07_role_based_access_control(self):
        """Test that Faculty role cannot access Admin-only /users route."""
        # Simulate faculty session
        with self.client.session_transaction() as sess:
            sess["user_id"] = 2
            sess["user"] = "anita_rao"
            sess["username"] = "anita_rao"
            sess["role"] = "Faculty"
            sess["faculty_id"] = 1

        res = self.client.get("/users")
        self.assertEqual(res.status_code, 403, "Faculty user should receive 403 Forbidden on /users")

        # Now simulate admin session
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user"] = "admin"
            sess["username"] = "admin"
            sess["role"] = "Admin"
            sess["faculty_id"] = None

        res_admin = self.client.get("/users")
        self.assertEqual(res_admin.status_code, 200, "Admin user should receive 200 OK on /users")

    def test_08_csrf_protection_on_post(self):
        """Test that POST requests without CSRF token are rejected with 400."""
        # Unset testing bypass so CSRF check executes
        self.flask_app.config["TESTING"] = False
        try:
            with self.client.session_transaction() as sess:
                sess["user_id"] = 1
                sess["user"] = "admin"
                sess["role"] = "Admin"
                sess["csrf"] = "real_csrf_token_value_123"

            # Post with missing or wrong CSRF token
            res = self.client.post("/academics/department", data={"dept_code": "TEST", "dept_name": "Test Dept"})
            self.assertEqual(res.status_code, 400, "POST without valid CSRF should be rejected with 400 Bad Request")
        finally:
            self.flask_app.config["TESTING"] = True

    def test_09_orm_crud_and_update(self):
        """Test entity update operations via ORM transaction."""
        with self.flask_app.app_context():
            # Update a department description and verify persistence
            with db_orm.orm_transaction() as sess:
                dept = sess.query(models.Department).filter_by(dept_code="CSE").first()
                original_name = dept.dept_name
                dept.dept_name = "Computer Science & Engineering (Updated)"

            # Verify updated name
            with db_orm.orm_transaction() as sess:
                dept = sess.query(models.Department).filter_by(dept_code="CSE").first()
                self.assertEqual(dept.dept_name, "Computer Science & Engineering (Updated)")
                # Revert back to original
                dept.dept_name = original_name

    def test_10_database_trigger_protection(self):
        """Test that database trigger trg_attendance_bi prevents invalid attendance insertion."""
        with self.flask_app.app_context():
            conn = db.get_db()
            cur = conn.cursor()
            # Attempt to insert attendance for a student who is not enrolled (student 99999)
            # or for a session that is closed
            with self.assertRaises(mysql.connector.Error) as ctx:
                cur.execute(
                    "INSERT INTO attendance (session_id, student_id, confidence) VALUES (1, 99999, 0.95)"
                )
            cur.close()
            # Expect either foreign key error or trigger SIGNAL 45000
            self.assertTrue(
                "Attendance can only be marked" in str(ctx.exception)
                or "not enrolled" in str(ctx.exception)
                or "foreign key constraint fails" in str(ctx.exception).lower()
            )


if __name__ == "__main__":
    unittest.main()
