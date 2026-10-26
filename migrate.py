"""Database migration runner.

Tracks applied migrations in a `schema_migrations` table so they are safely
applied once without dropping or altering existing tables destructively.

Usage:
    python migrate.py          Apply all pending migrations
    python migrate.py --status Show status of all migrations
"""
import argparse
import sys
from pathlib import Path

import mysql.connector
from werkzeug.security import generate_password_hash

from config import Config

BASE = Path(__file__).resolve().parent
MIGRATIONS_DIR = BASE / "migrations"


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
    return [s for s in statements if s.strip()]


def get_connection():
    conn_kwargs = {
        "host": Config.DB_HOST,
        "port": Config.DB_PORT,
        "user": Config.DB_USER,
        "password": Config.DB_PASSWORD,
        "database": Config.DB_NAME,
        "autocommit": True,
        "use_pure": True,
        "ssl_disabled": False,
    }
    if Config.DB_SSL_CA and Path(Config.DB_SSL_CA).exists():
        conn_kwargs["ssl_ca"] = Config.DB_SSL_CA
    return mysql.connector.connect(**conn_kwargs)


def ensure_migration_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(100) PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
    """)


def get_applied_migrations(cur):
    ensure_migration_table(cur)
    cur.execute("SELECT version FROM schema_migrations ORDER BY version")
    return {row[0] for row in cur.fetchall()}


def apply_migration(conn, file_path):
    version = file_path.name
    print(f"Applying migration: {version} ... ", end="", flush=True)
    cur = conn.cursor()
    try:
        sql = file_path.read_text(encoding="utf-8")
        stmts = split_sql(sql)
        for stmt in stmts:
            head = stmt.lstrip().upper()
            if head.startswith("CREATE DATABASE") or head.startswith("USE "):
                continue
            cur.execute(stmt)
        cur.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
        print("DONE")
    except Exception as exc:
        print(f"FAILED!\nError applying {version}: {exc}")
        cur.close()
        raise
    finally:
        cur.close()



def ensure_initial_admin(conn):
    """Create the initial administrator only when a password is configured."""
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT COUNT(*) AS cnt FROM users")
        row = cur.fetchone()

        if row and row["cnt"] == 0:
            admin_user = Config.ADMIN_USERNAME
            admin_pass = Config.ADMIN_PASSWORD

            if not admin_user or not admin_pass:
                print(
                    "[AUTH INIT] No administrator created. "
                    "Set ADMIN_USERNAME and ADMIN_PASSWORD in .env."
                )
                return

            pass_hash = generate_password_hash(admin_pass)

            cur.execute("""
                INSERT INTO users (username, email, password_hash, role, is_active)
                VALUES (%s, %s, %s, 'Admin', 1)
            """, (admin_user, f"{admin_user}@institution.edu", pass_hash))

            print(
                f"[AUTH INIT] Initial administrator account created: '{admin_user}'"
            )

    except mysql.connector.Error as exc:
        print(f"[AUTH INIT] Could not initialize administrator: {exc}")
        raise
    finally:
        cur.close()



def main():
    parser = argparse.ArgumentParser(description="Database migration runner")
    parser.add_argument("--status", action="store_true", help="Show migration status")
    args = parser.parse_args()

    try:
        conn = get_connection()
    except mysql.connector.Error as exc:
        print(f"Database connection error: {exc}")
        sys.exit(1)

    try:
        cur = conn.cursor()
        applied = get_applied_migrations(cur)
        cur.close()

        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

        if args.status:
            print("\nMigration Status:")
            print(f"{'Migration':<45} {'Status':<15}")
            print("-" * 60)
            for f in migration_files:
                st = "Applied" if f.name in applied else "Pending"
                print(f"{f.name:<45} {st:<15}")
            return

        pending = [f for f in migration_files if f.name not in applied]
        if not pending:
            print("Database is up to date. No pending migrations.")
        else:
            print(f"Found {len(pending)} pending migration(s):")
            for f in pending:
                apply_migration(conn, f)

        # After migrations, ensure admin account exists
        ensure_initial_admin(conn)
        print("Migration process complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
