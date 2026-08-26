from datetime import date, time
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.auth.dependencies import login_required
from app.config.database import get_db
from app.hrm.service import HRMService
router=APIRouter(prefix="/hrm",dependencies=[Depends(login_required)]); templates=Jinja2Templates(directory="app/templates")
def optional_time(value:str):
    try: return time.fromisoformat(value) if value else None
    except ValueError: return None
@router.get("",response_class=HTMLResponse)
def dashboard(request:Request,db:Session=Depends(get_db)):
    return templates.TemplateResponse(request=request,name="hrm/dashboard.html",context={"summary":HRMService.dashboard(db),"employees":HRMService.employees(db)[:5],"leaves":HRMService.leaves(db)[:5]})
@router.get("/employees",response_class=HTMLResponse)
def employee_list(request:Request,db:Session=Depends(get_db)): return templates.TemplateResponse(request=request,name="hrm/employees.html",context={"employees":HRMService.employees(db)})
@router.get("/employees/create",response_class=HTMLResponse)
def employee_create_page(request:Request): return templates.TemplateResponse(request=request,name="hrm/employee_form.html",context={"employee":None})
@router.get("/employees/{employee_id}/edit",response_class=HTMLResponse)
def employee_edit_page(employee_id:int,request:Request,db:Session=Depends(get_db)):
    employee=HRMService.employee(db,employee_id)
    if not employee: raise HTTPException(404,"Employee not found")
    return templates.TemplateResponse(request=request,name="hrm/employee_form.html",context={"employee":employee})
@router.post("/employees/save")
def employee_save(employee_id:int|None=Form(None),full_name:str=Form(...),email:str=Form(""),phone:str=Form(""),department:str=Form("General"),designation:str=Form("Staff"),employment_type:str=Form("FULL_TIME"),join_date:date=Form(...),basic_salary:float=Form(0),emergency_contact:str=Form(""),address:str=Form(""),is_active:bool=Form(False),db:Session=Depends(get_db)):
    employee=HRMService.employee(db,employee_id) if employee_id else None
    if employee_id and not employee: raise HTTPException(404,"Employee not found")
    HRMService.save_employee(db,employee,full_name=full_name.strip(),email=email or None,phone=phone or None,department=department,designation=designation,employment_type=employment_type,join_date=join_date,basic_salary=max(basic_salary,0),emergency_contact=emergency_contact or None,address=address or None,is_active=is_active)
    return RedirectResponse("/hrm/employees",303)
@router.get("/attendance",response_class=HTMLResponse)
def attendance_page(request:Request,attendance_date:date|None=None,db:Session=Depends(get_db)):
    selected=attendance_date or date.today(); return templates.TemplateResponse(request=request,name="hrm/attendance.html",context={"employees":HRMService.employees(db,True),"records":HRMService.attendance_for(db,selected),"selected_date":selected})
@router.post("/attendance/save")
def attendance_save(employee_id:int=Form(...),attendance_date:date=Form(...),status:str=Form(...),check_in:str=Form(""),check_out:str=Form(""),notes:str=Form(""),db:Session=Depends(get_db)):
    if status not in {"PRESENT","ABSENT","HALF_DAY","WFH"}: raise HTTPException(400,"Invalid attendance status")
    if not HRMService.employee(db,employee_id): raise HTTPException(404,"Employee not found")
    HRMService.save_attendance(db,employee_id,attendance_date,status=status,check_in=optional_time(check_in),check_out=optional_time(check_out),notes=notes or None)
    return RedirectResponse(f"/hrm/attendance?attendance_date={attendance_date.isoformat()}",303)
@router.get("/leaves",response_class=HTMLResponse)
def leave_list(request:Request,db:Session=Depends(get_db)): return templates.TemplateResponse(request=request,name="hrm/leaves.html",context={"leaves":HRMService.leaves(db),"employees":HRMService.employees(db,True)})
@router.post("/leaves/create")
def leave_create(employee_id:int=Form(...),leave_type:str=Form(...),start_date:date=Form(...),end_date:date=Form(...),reason:str=Form(""),db:Session=Depends(get_db)):
    if end_date<start_date: return RedirectResponse("/hrm/leaves?error=dates",303)
    if not HRMService.employee(db,employee_id): raise HTTPException(404,"Employee not found")
    if leave_type not in {"CASUAL","SICK","EARNED","UNPAID"}: raise HTTPException(400,"Invalid leave type")
    HRMService.create_leave(db,employee_id=employee_id,leave_type=leave_type,start_date=start_date,end_date=end_date,reason=reason or None); return RedirectResponse("/hrm/leaves",303)
@router.post("/leaves/{leave_id}/status")
def leave_status(leave_id:int,status:str=Form(...),db:Session=Depends(get_db)):
    if status not in {"APPROVED","REJECTED","PENDING"}: raise HTTPException(400,"Invalid leave status")
    if not HRMService.update_leave_status(db,leave_id,status): raise HTTPException(404,"Leave request not found")
    return RedirectResponse("/hrm/leaves",303)
