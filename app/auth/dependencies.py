from fastapi import HTTPException, Request

def login_required(request: Request):
    if not request.session.get("user_id"):
        raise HTTPException(status_code=303, headers={"Location":"/login"})
    return True
