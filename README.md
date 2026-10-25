# Smart Attendance Management System (SAMS)

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-black.svg)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-orange.svg)](https://www.mysql.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.36-red.svg)](https://www.sqlalchemy.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-YuNet%20%2B%20SFace-green.svg)](https://opencv.org/)

An automated, biometric computer-vision and relational database attendance platform designed for academic institutions. Combines deep neural network edge face recognition (OpenCV YuNet + SFace) with an ACID-compliant, 3NF-normalized relational database management system (MySQL 8.0+ and SQLAlchemy ORM).

---

## 1. System Architecture & Features

| Capability | Technical Implementation |
| :--- | :--- |
| **Authentication & RBAC** | Database-backed `users` table with `scrypt` cryptographic password hashing (Werkzeug). Role-based authorization (`Admin` vs `Faculty`) enforced on routes, views, and actions. |
| **Dual DBMS Architecture** | **Hybrid model:** SQLAlchemy 2.0 ORM for declarative model validation and entity CRUD; pooled pure-python MySQL Connector for analytical views, stored procedures, and high-throughput vector ingestion. |
| **Relational Database Design**| 11 normalized tables adhering strictly to 3NF and BCNF, with primary keys, foreign keys (`CASCADE`, `SET NULL`, `RESTRICT`), unique business keys, and domain `CHECK` constraints. |
| **Automated Debarment** | Database stored procedure (`sp_refresh_debarments`) recalculates attendance thresholds across upcoming exams, automatically debarring students with $< 75\%$ course attendance. |
| **Database Integrity Trigger**| BEFORE INSERT trigger (`trg_attendance_bi`) enforces temporal validity (session must be `Open`) and curricular validity (student must be enrolled in course) at the DBMS engine level. |
| **Facial Biometrics Engine** | OpenCV YuNet DNN face detector and SFace 128-dimensional embedding extractor. Vector cosine similarity matching with ambiguity margin and consecutive frame streak confirmation. |
| **Full CRUD Management** | Complete Create, Read, Update, Delete for Users, Students, Departments, Faculty, Courses, Class Sessions, and Exam Schedules. |
| **Search, Filter & Pagination**| Server-side pagination helper, dynamic student search by roll number or name, department filters, and session status selectors. |
| **Backup & Recovery** | Windows batch (`.bat`) and PowerShell (`.ps1`) utilities for single-transaction database backups and confirmation-guarded restoration. |
| **Containerization** | Production-ready `Dockerfile` and `docker-compose.yml` with persistent MySQL storage volumes and container health checks. |

---

## 2. Windows Installation & Setup Guide

### Prerequisites
1. **Windows 10/11 64-bit**
2. **Python 3.12 64-bit** (<https://www.python.org/downloads/windows/>)
   - *Ensure "Add python.exe to PATH" is ticked during installation.*
3. **MySQL Server 8.0+** (<https://dev.mysql.com/downloads/installer/>)
   - *Ensure MySQL service is running on port 3306.*

---

### Step-by-Step Setup Commands (PowerShell)

#### Step 1: Open PowerShell and Navigate to Project Directory
```powershell
cd "C:\Users\arpit\Downloads\smart_attendance (1)\smart_attendance"
```

#### Step 2: Activate Virtual Environment
```powershell
# Parent virtual environment
..\.venv\Scripts\Activate.ps1
```
*(If PowerShell blocks script execution, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

#### Step 3: Install Required Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 4: Environment Configuration
Copy `.env.example` to `.env` if not already present:
```powershell
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
notepad .env
```
Ensure your database password (`DB_PASSWORD`) and port (`DB_PORT=3306`) are correct.

#### Step 5: Verify Face Recognition Models
The deep neural network models (`face_detection_yunet_2023mar.onnx` and `face_recognition_sface_2021dec.onnx`) reside in `models/`. If missing, download them:
```powershell
python download_models.py
```

#### Step 6: Apply Database Migrations & Initialize Admin
Run the automated migration runner:
```powershell
python migrate.py
```
This automatically applies pending migrations, creates the `users` table and indexes, and seeds the initial administrator account.

To view migration status at any time:
```powershell
python migrate.py --status
```

To create additional administrators or faculty accounts:
```powershell
python create_user.py --username prof_anita --email anita@example.edu --password "Faculty@123" --role Faculty --faculty-id 1
```

#### Step 7: Run System Verification Tests
Execute the automated test suite covering all 10 DBMS and application requirements:
```powershell
python test_system.py
```

#### Step 8: Start the Application
```powershell
python app.py
```
Open **<http://127.0.0.1:5000>** in your web browser (Chrome or Edge recommended for webcam access).

---

## 3. User Roles & Default Credentials

| Role | Username | Initial Password | Permissions & Access Scope |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `Admin@12345` | Full administrative control: User management, Departments, Faculty, Courses, Students, Exam Scheduling, System Settings. |
| **Faculty** | `anita_rao` | `Faculty@123` | Scoped faculty access: Courses assigned to faculty member, starting/taking live attendance for their sessions, viewing their student rosters. |

*Security Tip: Change initial passwords immediately upon first login via the User Management interface.*

---

## 4. Database Design & Documentation Dossier

Detailed architectural and database engineering documents are located in the `docs/` folder:

- **[Project Planning Document](docs/PROJECT_PLANNING.md):** Problem statement, objectives, scope, team responsibility matrix, deliverables, and Mermaid Gantt chart.
- **[Database Design Specification](docs/DATABASE_DESIGN.md):** 11 tables, 3NF & BCNF functional dependency proofs, Relational Schema notation, Mermaid ER diagram, and complete Data Dictionary.
- **[DBMS Implementation Guide](docs/ORM_AND_QUERIES.md):** Hybrid ORM pattern analysis, SQL joins, database views, trigger definitions, stored procedure logic, and indexing strategies.
- **[Deployment & Git Engineering Dossier](docs/DEPLOYMENT_AND_GIT.md):** Main/dev branching workflow, 10 progressive commit milestones, Docker Compose orchestration, Docker Hub publishing, and cloud deployment guides.

---

## 5. Database Backup and Recovery

### Taking a Database Backup
```powershell
# PowerShell backup utility
.\backup_db.ps1

# Or via Windows Batch
.\backup_db.bat
```
Backups are saved to `backups/backup_smart_attendance_YYYYMMDD_HHMMSS.sql`.

### Restoring from Backup
> **Safety Warning:** Restoring will replace data in the `smart_attendance` database. Explicit confirmation (`YES`) is mandatory before restore proceeds.

```powershell
# PowerShell restore utility
.\restore_db.ps1 -BackupFile "backups\backup_smart_attendance_20261025_181100.sql"

# Or via Windows Batch
.\restore_db.bat "backups\backup_smart_attendance_20261025_181100.sql"
```

---

## 6. Docker & Containerized Execution

To build and run the entire application stack (MySQL 8.0 + Flask Web Application) with Docker Compose:

```bash
# Build and start in detached mode
docker compose up -d --build

# Run database migrations in container
docker compose exec web python migrate.py

# Run regression test suite in container
docker compose exec web python test_system.py

# Stop containers
docker compose down
```

---

## 7. Verification Status & Test Results

The system was verified against a live local **MySQL 8.0.40** instance on Windows:
- **Test Suite (`test_system.py`):** 10 out of 10 tests passing (0 failures, 0 errors).
- **Authentication:** Werkzeug `scrypt` password verification, invalid password rejection, inactive account blocking, and login session clearing tested.
- **RBAC Enforcement:** Route-level restriction verified; Faculty requests to `/users` return `403 Forbidden`; Admin access returns `200 OK`.
- **Database Trigger (`trg_attendance_bi`):** Rejects invalid attendance insertion for un-enrolled students or non-Open sessions.
- **Stored Procedure (`sp_refresh_debarments`):** Successfully executes and rebuilds upcoming exam debarments based on the 75% attendance threshold.
- **SQLAlchemy ORM:** Model relations and transactional entity updates verified against real database tables.
- **Pagination:** Reusable pagination helper tested with bounds checking and sequence generation.
- **CSRF Defense:** Verified rejection (`400 Bad Request`) of POST submissions lacking valid HMAC CSRF tokens.

---

## 8. Limitations & Viva Speaking Points

When presenting this project:
1. **Liveness Detection:** The computer vision pipeline utilizes single-frame YuNet detection and SFace cosine similarity. While it features consecutive-frame streak confirmation (`CONFIRM_FRAMES=2`), physical classroom supervision is recommended to prevent photo/screen spoofing.
2. **Lighting Sensitivity:** Accuracy depends on ambient illumination. For optimal results, student face registrations should be performed under typical classroom lighting conditions.
3. **Dual Persistence Justification:** Highlight the deliberate engineering rationale behind combining SQLAlchemy ORM (for entity domain safety) and raw pooled MySQL Connector (for high-speed frame-rate video ingestion).
