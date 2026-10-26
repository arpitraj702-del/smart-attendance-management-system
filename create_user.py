"""Command-line tool to create and manage system users (Admin or Faculty).

Usage:
    python create_user.py --username prof_anita --email anita@example.edu --role Faculty --faculty-id 1
    python create_user.py --username superadmin --email admin2@example.edu --role Admin
    python create_user.py (interactive prompt)
"""
import argparse
import getpass
import re
import sys

import mysql.connector
from werkzeug.security import generate_password_hash

from config import Config


def get_db():
    return mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        autocommit=True,
        use_pure=True,
        ssl_disabled=False,
    )


def main():
    parser = argparse.ArgumentParser(description="Create a new user account with role-based access")
    parser.add_argument("--username", help="Unique username")
    parser.add_argument("--email", help="Unique email address")
    parser.add_argument("--password", help="Account password (leave empty to prompt securely)")
    parser.add_argument("--role", choices=["Admin", "Faculty"], default=None, help="User role (Admin or Faculty)")
    parser.add_argument("--faculty-id", type=int, default=None, help="Linked faculty ID (optional for Faculty role)")
    args = parser.parse_args()

    username = (args.username or input("Username: ")).strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,50}", username):
        print("Error: Username must be 3-50 alphanumeric characters (._- allowed).")
        sys.exit(1)

    email = (args.email or input("Email: ")).strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        print("Error: Invalid email format.")
        sys.exit(1)

    role = args.role
    if not role:
        r_input = input("Role ([A]dmin / [F]aculty) [default Faculty]: ").strip().lower()
        role = "Admin" if r_input.startswith("a") else "Faculty"

    faculty_id = args.faculty_id
    if role == "Faculty" and faculty_id is None:
        f_input = input("Linked Faculty ID (optional, press Enter to skip): ").strip()
        faculty_id = int(f_input) if f_input.isdigit() else None

    password = args.password
    if not password:
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm Password: ")
        if password != confirm:
            print("Error: Passwords do not match.")
            sys.exit(1)

    if len(password) < 6:
        print("Error: Password must be at least 6 characters long.")
        sys.exit(1)

    password_hash = generate_password_hash(password)

    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        # Check existing
        cur.execute("SELECT username, email FROM users WHERE username = %s OR email = %s", (username, email))
        existing = cur.fetchone()
        if existing:
            field = "Username" if existing["username"].lower() == username.lower() else "Email"
            print(f"Error: {field} already registered in the system.")
            sys.exit(1)

        # Validate faculty_id if provided
        if faculty_id:
            cur.execute("SELECT faculty_id, name FROM faculty WHERE faculty_id = %s", (faculty_id,))
            fac = cur.fetchone()
            if not fac:
                print(f"Error: Faculty with ID {faculty_id} does not exist.")
                sys.exit(1)
            print(f"Linking user to Faculty: {fac['name']} (ID {fac['faculty_id']})")

        cur.execute("""
            INSERT INTO users (username, email, password_hash, role, faculty_id, is_active)
            VALUES (%s, %s, %s, %s, %s, 1)
        """, (username, email, password_hash, role, faculty_id))

        user_id = cur.lastrowid
        print(f"Success: User '{username}' ({role}) created successfully with ID {user_id}!")
        cur.close()
        conn.close()
    except mysql.connector.Error as exc:
        print(f"Database error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
