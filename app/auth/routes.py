from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.auth.models import User
from app.auth.service import verify_password
from app.config.database import get_db

router=APIRouter(); templates=Jinja2Templates(directory="app/templates")
@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("user_id"): return RedirectResponse("/hrm",303)
    return templates.TemplateResponse(request=request,name="auth/login.html",context={"error":None})
@router.post("/login", response_class=HTMLResponse)
def login(request: Request,email:str=Form(...),password:str=Form(...),db:Session=Depends(get_db)):
    user=db.query(User).filter(User.email==email.strip().lower(),User.is_active.is_(True)).first()
    if not user or not verify_password(password,user.password_hash):
        return templates.TemplateResponse(request=request,name="auth/login.html",context={"error":"Invalid email or password"},status_code=401)
    request.session.clear(); request.session["user_id"]=user.id; request.session["email"]=user.email
    return RedirectResponse("/hrm",303)
@router.post("/logout")
def logout(request: Request):
    request.session.clear(); return RedirectResponse("/login",303)
