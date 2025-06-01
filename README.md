# 📅 Calendar Summary Service

This is a FastAPI-based web service that allows users to securely log in, link multiple Google Calendar accounts, and receive daily HTML summaries of their upcoming events. It's built to run locally with PostgreSQL and supports multiple users.

## ✨ Features

- 🔐 User registration and login (with hashed passwords)
- 🔄 Google OAuth2 login to link calendar accounts
- 🗓️ Daily calendar summary using the Google Calendar API
- 📥 Multi-account support per user
- 💌 Email-ready HTML summaries
- 🛠️ Admin cron job support to email summaries automatically
- 🗃️ PostgreSQL backend with SQLAlchemy
- 📦 Token storage handled securely and excluded from Git

## 🚀 Tech Stack

- Python 3.13+
- [FastAPI](https://fastapi.tiangolo.com/)
- [Jinja2](https://palletsprojects.com/p/jinja/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [psycopg2](https://www.psycopg.org/)
- Google Calendar API + OAuth2
- PostgreSQL (local)

## 🛠️ Local Setup

### 1. Clone the Repo

```bash
git clone https://github.com/AlexanderPW/Calendar-Service.git
cd Calendar-Service
```

### 2. Set Up Your Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file (if using) or edit `db.py` with your PostgreSQL credentials:

```python
dbname="myappdb"
user="youruser"
password="yourpassword"
host="localhost"
```

Make sure you have a `client_secret.json` for Google API OAuth in the root folder.

### 4. Initialize the Database

```bash
python
>>> from db import Base, engine
>>> Base.metadata.create_all(bind=engine)
>>> exit()
```

### 5. Run the App

```bash
uvicorn main:app --reload
```

Open in browser: [http://localhost:8000](http://localhost:8000)

## 🧪 Cron Job (Optional)

To email summaries daily:

- Create a cron job that runs a script which calls the `/summary` route or directly uses the `generate_summary_html()` function with user tokens from the database.

## 🛡️ Security

- Google tokens are stored as `.json` files and excluded from Git via `.gitignore`.
- Passwords are stored hashed using `passlib[bcrypt]`.
- No secrets are committed to GitHub.

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

MIT License © Alex Waldrop
# calendar-service
