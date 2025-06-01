from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from passlib.hash import bcrypt
from pathlib import Path
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session
from db import get_db, User, UserToken
from calendar_summary import generate_summary_html
import os

app = FastAPI()

# CORS (optional, based on frontend needs)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Template setup
templates = Jinja2Templates(directory="templates")

# OAuth2 config
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
REDIRECT_URI = "http://localhost:8000/oauth2callback"

# In-memory user store for demonstration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Password helpers
def hash_password(password: str) -> str:
    return bcrypt.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.verify(password, hashed)

# Session helpers
def get_current_user(request: Request, db: Session = Depends(get_db)):
    email = request.cookies.get("user_email")
    if not email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.query(User).filter_by(email=email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    email = request.cookies.get("user_email")
    return templates.TemplateResponse("index.html", {"request": request, "email": email})

@app.post("/register")
def register(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(email=email, password_hash=hash_password(password))
    db.add(new_user)
    db.commit()
    return RedirectResponse("/login", status_code=302)

@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    response = RedirectResponse("/", status_code=302)
    response.set_cookie("user_email", email)
    return response

@app.get("/login-google")
def login_google():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return RedirectResponse(auth_url)

@app.get("/oauth2callback")
def oauth2callback(request: Request, db: Session = Depends(get_db)):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(code=request.query_params["code"])
    creds = flow.credentials

    calendar_service = build("calendar", "v3", credentials=creds)
    calendar_list = calendar_service.calendarList().list().execute()
    primary_calendar = next(
        (c for c in calendar_list["items"] if c.get("primary")),
        calendar_list["items"][0]
    )
    email = primary_calendar["id"]

    user_email = request.cookies.get("user_email")
    if not user_email:
        raise HTTPException(status_code=401, detail="Login required")

    user = db.query(User).filter_by(email=user_email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    token_path = f"token_{email}.json"
    with open(token_path, "w") as token_file:
        token_file.write(creds.to_json())

    if not db.query(UserToken).filter_by(user_id=user.id, google_email=email).first():
        token = UserToken(user_id=user.id, google_email=email, token_path=token_path)
        db.add(token)
        db.commit()

    return RedirectResponse("/accounts")

@app.get("/accounts", response_class=HTMLResponse)
def accounts(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    tokens = db.query(UserToken).filter_by(user_id=user.id).all()
    return templates.TemplateResponse("accounts.html", {
        "request": request,
        "email": user.email,
        "tokens": tokens
    })

@app.get("/summary", response_class=HTMLResponse)
def summary(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tokens = db.query(UserToken).filter_by(user_id=user.id).all()
    creds_map = {
        token.google_email: Credentials.from_authorized_user_file(token.token_path)
        for token in tokens
    }
    html = generate_summary_html(creds_map)
    return HTMLResponse(content=html)

@app.get("/auth/google")
def auth_google(request: Request):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt='consent', include_granted_scopes='true')
    return RedirectResponse(auth_url)

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("user_email")
    return response

@app.get("/login", response_class=HTMLResponse)
def show_login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})
