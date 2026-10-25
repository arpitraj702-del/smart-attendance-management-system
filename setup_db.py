"""Create the MySQL database, tables, views, trigger and stored procedure.

Usage:
    python setup_db.py            create everything (safe to re-run)
    python setup_db.py --seed     also add sample departments/faculty/courses
    python setup_db.py --reset    DROP the database first (deletes all data!)
"""
import argparse
import sys
from pathlib import Path

import mysql.connector

from config import Config
from migrate import ensure_initial_admin, ensure_migration_table, MIGRATIONS_DIR

BASE = Path(__file__).resolve().parent


def split_sql(text):
    """Split a .sql script into statements; understands the DELIMITER command."""
    statements, buf, delim = [], [], ";"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("DELIMITER "):
            delim = stripped.split(None, 1)[1].strip()
            continue
        if not stripped or stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(delim):
            stmt = "\n".join(buf).rstrip()
            statements.append(stmt[: -len(delim)].rstrip())
            buf = []
    if buf:
        statements.append("\n".join(buf).rstrip())
    return statements


def run_file(cur, path):
    for stmt in split_sql(path.read_text(encoding="utf-8")):
        head = stmt.lstrip().upper()
        if head.startswith("CREATE DATABASE") or head.startswith("USE "):
            continue  # the database name comes from .env
        cur.execute(stmt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", action="store_true", help="insert sample departments, faculty, courses")
    ap.add_argument("--reset", action="store_true", help="drop the database first")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation for --reset")
    args = ap.parse_args()

    try:
        conn = mysql.connector.connect(
            host=Config.DB_HOST, port=Config.DB_PORT, user=Config.DB_USER,
            password=Config.DB_PASSWORD, autocommit=True, use_pure=True,
        )
    except mysql.connector.Error as exc:
        print(f"\nCould not connect to MySQL: {exc}")
        print("Check that the MySQL service is running and DB_HOST / DB_USER / DB_PASSWORD in .env are correct.")
        sys.exit(1)

    cur = conn.cursor()
    name = Config.DB_NAME
    try:
        if args.reset:
            if not args.yes and input(f"Type YES to delete database '{name}': ").strip() != "YES":
                print("Cancelled.")
                return
            cur.execute(f"DROP DATABASE IF EXISTS `{name}`")
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cur.execute(f"USE `{name}`")
        run_file(cur, BASE / "schema.sql")
        print("Schema created.")
        ensure_migration_table(cur)
        for mf in sorted(MIGRATIONS_DIR.glob("*.sql")):
            cur.execute("INSERT IGNORE INTO schema_migrations (version) VALUES (%s)", (mf.name,))
        ensure_initial_admin(conn)
        if args.seed:
            run_file(cur, BASE / "seed.sql")
            print("Sample data inserted.")
        cur.execute("SHOW FULL TABLES")
        print("\nObjects in database:")
        for row in cur.fetchall():
            print(f"  {row[1]:<11} {row[0]}")
    except mysql.connector.Error as exc:
        print(f"\nMySQL error while creating the schema: {exc}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
