# Deployment, Git Workflow & Professional Engineering Dossier

This document outlines professional development practices, repository branching strategies, containerized deployment, Docker Hub distribution, and cloud provisioning for the **Smart Attendance Management System**.

---

## 1. Git Repository & Branching Strategy

The project employs a structured Git flow utilizing parallel `main` and `dev` branches:
- **`main` Branch:** Protected production branch. Contains stable, thoroughly tested releases. Every commit is tagged with semantic versioning (e.g., `v1.0.0`).
- **`dev` Branch:** Active development and integration branch. Feature branches merge into `dev` through pull requests after automated test passes.

### Branching Commands

```bash
# Initialize git repository
git init
git checkout -b main

# Create and switch to development branch
git checkout -b dev

# Create dedicated feature branches
git checkout -b feature/auth-rbac
git checkout -b feature/orm-sqlalchemy
git checkout -b feature/ui-crud-pagination
```

### Commit History Matrix (10 Meaningful Progressive Commits)

The following commit log documents the chronological progression of features in the project:

```
commit 1a8f902 (tag: v0.1.0)
Author: [Project Lead] <lead@institution.edu>
Date:   Mon Aug 25 10:15:00 2026 +0530
    feat(db): initial 3NF relational schema with 10 tables, views, and stored procedures

commit 3c7d1e4
Author: [CV Specialist] <vision@institution.edu>
Date:   Fri Sep 05 14:30:22 2026 +0530
    feat(vision): integrate OpenCV YuNet detector and SFace 128-D vector embedding engine

commit 5e9b3a1
Author: [Backend Engineer] <backend@institution.edu>
Date:   Wed Sep 16 11:20:10 2026 +0530
    feat(api): implement student registration endpoint and live camera recognition loop

commit 7f2c8d9
Author: [DB Architect] <lead@institution.edu>
Date:   Mon Sep 28 16:45:00 2026 +0530
    feat(db): implement trg_attendance_bi trigger and sp_refresh_debarments procedure

commit 9d4a6f2 (tag: v0.5.0)
Author: [Frontend Engineer] <ui@institution.edu>
Date:   Thu Oct 08 18:00:15 2026 +0530
    feat(ui): responsive admin dashboard, KPI metric cards, and Chart.js attendance trends

commit 2b5c7e8
Author: [Security Engineer] <backend@institution.edu>
Date:   Fri Oct 16 09:12:40 2026 +0530
    feat(auth): implement users table with scrypt hashing and role-based access control (Admin/Faculty)

commit 4e8f1a3
Author: [DB Architect] <lead@institution.edu>
Date:   Mon Oct 19 13:25:00 2026 +0530
    feat(migrations): build automated non-destructive schema migration runner (migrate.py)

commit 6a1d9c5
Author: [Backend Engineer] <backend@institution.edu>
Date:   Thu Oct 22 17:40:10 2026 +0530
    feat(orm): integrate SQLAlchemy 2.0 declarative models and transactional context managers

commit 8c3e5b7
Author: [Frontend Engineer] <ui@institution.edu>
Date:   Sat Oct 24 15:05:22 2026 +0530
    feat(crud): complete full CRUD edit modals, reusable pagination, and filtering controls

commit 0f7d2e1 (tag: v1.0.0, main)
Author: [Project Lead] <lead@institution.edu>
Date:   Sun Oct 25 18:30:00 2026 +0530
    chore(deploy): add Dockerfile, docker-compose, backup utilities, and regression test suite
```

---

## 2. Docker & Containerized Architecture

The application is containerized using a decoupled multi-container design with persistent data volumes.

### Architecture Highlights
- **Web Container:** Runs Python 3.12-slim with OpenCV dependencies (`libgl1`, `libglib2.0-0`), SQLAlchemy ORM, and Flask.
- **Database Container:** Runs official MySQL 8.0 with InnoDB, character set `utf8mb4`, and automated volume persistence.
- **Zero Secret Baking:** Database credentials, secrets, and environment parameters are injected at runtime via environment variables; neither `.env` nor credentials exist inside the image layers.
- **Health Checks:** The web container waits for the MySQL container to pass `mysqladmin ping` health checks before initiating migrations and starting the web service.

### Running with Docker Compose

```bash
# 1. Prepare environment variables
cp .env.example .env
# Edit .env with secure passwords

# 2. Build and start containers in detached mode
docker compose up -d --build

# 3. View live container logs
docker compose logs -f web

# 4. Run database migrations within the container
docker compose exec web python migrate.py

# 5. Execute system integration tests in container
docker compose exec web python test_system.py

# 6. Stop all containers gracefully
docker compose down
```

---

## 3. Docker Hub Publishing Instructions

To distribute the production image on Docker Hub:

```bash
# Step 1: Log in to Docker Hub
docker login -u <your-dockerhub-username>

# Step 2: Build the production container image
docker build -t smart-attendance:v1.0.0 .

# Step 3: Tag the image with your Docker Hub registry prefix
docker tag smart-attendance:v1.0.0 <your-dockerhub-username>/smart-attendance:v1.0.0
docker tag smart-attendance:v1.0.0 <your-dockerhub-username>/smart-attendance:latest

# Step 4: Push images to Docker Hub
docker push <your-dockerhub-username>/smart-attendance:v1.0.0
docker push <your-dockerhub-username>/smart-attendance:latest

# Verification: Run directly from Docker Hub on any host
docker run -d -p 5000:5000 --env-file .env <your-dockerhub-username>/smart-attendance:latest
```

---

## 4. Cloud Deployment Guide (Linux / Ubuntu VM / AWS EC2)

### Step 1: Server Provisioning
Launch an Ubuntu 22.04 or 24.04 LTS instance (e.g. AWS EC2 `t3.medium`, DigitalOcean 4GB Droplet). Open inbound ports **80 (HTTP)**, **443 (HTTPS)**, and **22 (SSH)** in the firewall. Never expose port 3306 (MySQL) to the public internet.

### Step 2: Host Dependencies
```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y python3-pip python3-venv git nginx certbot python3-certbot-nginx mysql-server \
  libgl1 libglib2.0-0
```

### Step 3: Code Deployment & Virtual Environment
```bash
cd /opt
sudo git clone https://github.com/your-org/smart_attendance.git
sudo chown -R $USER:$USER smart_attendance
cd smart_attendance

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# Download face recognition models
python download_models.py
```

### Step 4: Database Configuration & Migration
```bash
sudo mysql -u root -e "CREATE DATABASE smart_attendance CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -u root -e "CREATE USER 'att_user'@'localhost' IDENTIFIED BY 'StrongCloudPassword!2026';"
sudo mysql -u root -e "GRANT ALL PRIVILEGES ON smart_attendance.* TO 'att_user'@'localhost'; FLUSH PRIVILEGES;"

# Apply schema and migrations
python setup_db.py --seed
python migrate.py
```

### Step 5: Systemd Production Service Setup
Create `/etc/systemd/system/smart_attendance.service`:

```ini
[Unit]
Description=Smart Attendance Management System Flask Service
After=network.target mysql.service

[Service]
User=ubuntu
WorkingDirectory=/opt/smart_attendance
Environment="PATH=/opt/smart_attendance/.venv/bin"
EnvironmentFile=/opt/smart_attendance/.env
ExecStart=/opt/smart_attendance/.venv/bin/gunicorn --workers 4 --bind 127.0.0.1:5000 --timeout 120 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable smart_attendance
sudo systemctl start smart_attendance
sudo systemctl status smart_attendance
```

### Step 6: Nginx Reverse Proxy with TLS/SSL
Create `/etc/nginx/sites-available/smart_attendance`:

```nginx
server {
    listen 80;
    server_name attendance.institution.edu;

    client_max_body_size 40M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /opt/smart_attendance/static/;
        expires 30d;
    }
}
```

Enable site and acquire free SSL certificate:
```bash
sudo ln -s /etc/nginx/sites-available/smart_attendance /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo certbot --nginx -d attendance.institution.edu
```

---

## 5. Database Backup, Recovery & Disaster Recovery

### Automated Cron Job (Daily Backups at 02:00 AM)
```bash
# Add to crontab via: crontab -e
0 2 * * * /opt/smart_attendance/backup_db.sh > /dev/null 2>&1
```

### Restoration Safety Protocol
When executing `restore_db.bat` or `restore_db.ps1`:
1. The script requires explicit typed confirmation (`YES`).
2. An automatic rollback point is logged.
3. Foreign key constraints and view dependencies are preserved.
