from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.config.settings import settings
from app.auth.routes import router as auth_router
from app.hrm.routes import router as hrm_router
from app.hrm.payroll_routes import router as payroll_router

if not settings.session_secret or len(settings.session_secret)<32:
    raise RuntimeError("SESSION_SECRET must be configured with at least 32 characters")
settings.upload_root.mkdir(parents=True, exist_ok=True)
app=FastAPI(title=settings.app_name, docs_url=None if settings.app_env=="production" else "/docs")
app.add_middleware(SessionMiddleware,secret_key=settings.session_secret,https_only=settings.app_env=="production",same_site="lax")
app.mount("/static",StaticFiles(directory="app/static"),name="static")
app.mount("/uploads",StaticFiles(directory=str(settings.upload_root)),name="uploads")
app.include_router(auth_router); app.include_router(hrm_router); app.include_router(payroll_router)
@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest(): return FileResponse("app/static/manifest.webmanifest", media_type="application/manifest+json")
@app.get("/service-worker.js", include_in_schema=False)
def service_worker(): return FileResponse("app/static/service-worker.js", media_type="application/javascript", headers={"Service-Worker-Allowed":"/", "Cache-Control":"no-cache"})
@app.get("/")
def root(): return RedirectResponse("/hrm",303)
@app.get("/health")
def health(): return {"status":"ok","application":"ADS HRM"}
