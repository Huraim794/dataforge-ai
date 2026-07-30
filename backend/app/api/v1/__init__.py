from fastapi import APIRouter

from app.api.v1 import (
    auth,
    jobs,
    proxies,
    schedules,
    extractions,
    targets,
    monitoring,
    projects,
    users,
)

router = APIRouter(prefix="/v1")

router.include_router(auth.router, tags=["Authentication"])
router.include_router(users.router, prefix="/users", tags=["Users"])
router.include_router(projects.router, prefix="/projects", tags=["Projects"])
router.include_router(targets.router, prefix="/targets", tags=["Targets"])
router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
router.include_router(proxies.router, prefix="/proxies", tags=["Proxies"])
router.include_router(schedules.router, prefix="/schedules", tags=["Schedules"])
router.include_router(extractions.router, prefix="/extractions", tags=["Extractions"])
router.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])
