from fastapi import APIRouter

from . import jobs, plans, routes_board, skills, staff, stats

router = APIRouter()
router.include_router(stats.router, tags=["stats"])
router.include_router(staff.router, prefix="/staff", tags=["staff"])
router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
router.include_router(plans.router, prefix="/plans", tags=["plans"])
router.include_router(skills.router, prefix="/skills", tags=["skills"])
router.include_router(routes_board.router, prefix="/routes", tags=["routes"])

