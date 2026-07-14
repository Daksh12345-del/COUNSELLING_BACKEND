from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from models import EnquiryStatus, BookingStatus


# ---------- ENQUIRY ----------

class EnquiryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    phone: str = Field(..., min_length=6, max_length=20)
    email: Optional[str] = Field(None, max_length=120)
    student_class: Optional[str] = Field(None, max_length=60)
    stream: Optional[str] = Field(None, max_length=60)
    course: Optional[str] = Field(None, max_length=120)
    city: Optional[str] = Field(None, max_length=80)
    message: Optional[str] = Field(None, max_length=2000)

    @field_validator("phone")
    @classmethod
    def phone_must_have_digits(cls, v: str) -> str:
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) < 6:
            raise ValueError("Phone number looks invalid")
        return v.strip()

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be blank")
        return v.strip()


class EnquiryStatusUpdate(BaseModel):
    status: EnquiryStatus


class EnquiryOut(BaseModel):
    id: int
    created_at: datetime
    name: str
    phone: str
    email: Optional[str] = None
    student_class: Optional[str] = None
    stream: Optional[str] = None
    course: Optional[str] = None
    city: Optional[str] = None
    message: Optional[str] = None
    status: EnquiryStatus

    class Config:
        from_attributes = True


# ---------- BOOKING ----------

class BookingCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    phone: str = Field(..., min_length=6, max_length=20)
    slot_date: date
    slot_time: str = Field(..., max_length=20)
    session_type: str = Field("Phone Call", max_length=30)
    stream: Optional[str] = Field(None, max_length=60)
    course: Optional[str] = Field(None, max_length=120)

    @field_validator("phone")
    @classmethod
    def phone_must_have_digits(cls, v: str) -> str:
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) < 6:
            raise ValueError("Phone number looks invalid")
        return v.strip()

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be blank")
        return v.strip()


class BookingStatusUpdate(BaseModel):
    status: BookingStatus


class BookingOut(BaseModel):
    id: int
    created_at: datetime
    name: str
    phone: str
    slot_date: date
    slot_time: str
    session_type: str
    stream: Optional[str] = None
    course: Optional[str] = None
    status: BookingStatus

    class Config:
        from_attributes = True


class AvailableSlotsOut(BaseModel):
    slot_date: date
    booked_times: list[str]
    available_times: list[str]
    is_full: bool


# ---------- ADMIN AUTH ----------

class AdminLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- STATS ----------

class StatsOut(BaseModel):
    total_enquiries: int
    new_enquiries: int
    enrolled_enquiries: int
    total_bookings: int
    stream_breakdown: dict[str, int]
    course_breakdown: dict[str, int]
