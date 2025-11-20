from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class BaseAgencyModel(BaseModel):
    agency_id: str = Field(..., alias="agencyId")


class StaffBase(BaseAgencyModel):
    display_name: str = Field(..., alias="displayName")
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    status: str = Field("active", pattern="^(active|inactive|invited)$")
    skills: List[str] = Field(default_factory=list)


class StaffCreate(StaffBase):
    pass


class StaffUpdate(BaseModel):
    display_name: Optional[str] = Field(None, alias="displayName")
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive|invited)$")
    skills: Optional[List[str]] = None


class StaffResponse(StaffBase):
    id: str
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")


class JobBase(BaseAgencyModel):
    property_id: str = Field(..., alias="propertyId")
    host_id: str = Field(..., alias="hostId")
    reservation_id: Optional[str] = Field(None, alias="reservationId")
    scheduled_date: str = Field(..., alias="scheduledDate", pattern=r"^\d{4}-\d{2}-\d{2}$")
    planned_start: Optional[datetime] = Field(None, alias="plannedStart")
    planned_end: Optional[datetime] = Field(None, alias="plannedEnd")
    estimated_duration_minutes: int = Field(..., alias="estimatedDurationMinutes", ge=15)
    status: str = Field("pending", pattern="^(pending|scheduled|in_progress|completed|cancelled)$")
    skills_required: List[str] = Field(default_factory=list, alias="skillsRequired")
    notes: Optional[str] = None
    source: str = Field("manual")


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(pending|scheduled|in_progress|completed|cancelled)$")
    planned_start: Optional[datetime] = Field(None, alias="plannedStart")
    planned_end: Optional[datetime] = Field(None, alias="plannedEnd")
    notes: Optional[str] = None
    skills_required: Optional[List[str]] = Field(default=None, alias="skillsRequired")


class JobResponse(JobBase):
    id: str
    plan_id: Optional[str] = Field(None, alias="planId")
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")


class PlanRequest(BaseModel):
    agency_id: str = Field(..., alias="agencyId")
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    force: bool = False


class PlanResponse(BaseModel):
    id: str
    status: str
    date: str
    metrics: dict = Field(default_factory=dict)
    input_jobs: List[str] = Field(default_factory=list, alias="inputJobs")


class RouteStop(BaseModel):
    job_id: Optional[str] = Field(None, alias="jobId")
    property_id: Optional[str] = Field(None, alias="propertyId")
    eta: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class RouteResponse(BaseModel):
    id: str
    agency_id: str = Field(..., alias="agencyId")
    staff_id: Optional[str] = Field(None, alias="staffId")
    date: str
    distance_km: Optional[float] = Field(0, alias="distanceKm")
    travel_time_minutes: Optional[float] = Field(0, alias="travelTimeMinutes")
    stops: List[RouteStop] = Field(default_factory=list)


class SkillBase(BaseAgencyModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None


class SkillCreate(SkillBase):
    pass


class SkillResponse(SkillBase):
    id: str
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")


class AgencyStats(BaseModel):
    staff_active: int
    jobs_today: int
    routes_optimized: int
    jobs_completed: int

