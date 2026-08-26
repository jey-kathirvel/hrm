# ADS HRM
Standalone extraction of the HRM module from ADS ERP. The source ERP remains unchanged.

## Local run
Create `.env`, PostgreSQL database/user, install requirements, run `alembic upgrade head`, create an admin with `python -m app.auth.create_admin`, then `uvicorn main:app --host 127.0.0.1 --port 8120`.

Production target: `/opt/hrm`, `hrm.ads-ai.in`, service `ads-hrm.service`.
