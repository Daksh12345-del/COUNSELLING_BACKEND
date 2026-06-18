import csv
import io
from datetime import date, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from config import settings
from database import Base, engine, get_db
from models import Enquiry, Booking, EnquiryStatus, BookingStatus
from schemas import (
    EnquiryCreate, EnquiryOut, EnquiryStatusUpdate,
    BookingCreate, BookingOut, BookingStatusUpdate, AvailableSlotsOut,
    AdminLogin, Token, StatsOut,
)
from auth import create_access_token, verify_admin_credentials, get_current_admin, get_current_admin_allow_query_token

# Create tables if they don't exist yet (fine for a small single-server app;
# for bigger projects switch fully to Alembic migrations)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sarvpratham Edu Consultants API", version="1.0.0")

origins = ["*"] if settings.allowed_origins.strip() == "*" else [
    o.strip() for o in settings.allowed_origins.split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


# ===================== ADMIN AUTH =====================

@app.post("/api/admin/login", response_model=Token)
def admin_login(payload: AdminLogin):
    if not verify_admin_credentials(payload.username, payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    token = create_access_token({"sub": payload.username})
    return Token(access_token=token)


# ===================== ENQUIRIES =====================

@app.post("/api/enquiries", response_model=EnquiryOut, status_code=status.HTTP_201_CREATED)
def create_enquiry(payload: EnquiryCreate, db: Session = Depends(get_db)):
    enquiry = Enquiry(
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        student_class=payload.student_class,
        stream=payload.stream,
        course=payload.course,
        city=payload.city,
        message=payload.message,
        status=EnquiryStatus.new,
    )
    db.add(enquiry)
    db.commit()
    db.refresh(enquiry)
    return enquiry


@app.get("/api/enquiries", response_model=list[EnquiryOut])
def list_enquiries(
    search: Optional[str] = Query(None),
    status_filter: Optional[EnquiryStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    query = db.query(Enquiry)
    if status_filter:
        query = query.filter(Enquiry.status == status_filter)
    if search:
        like = f"%{search}%"
        query = query.filter(or_(
            Enquiry.name.ilike(like),
            Enquiry.phone.ilike(like),
            Enquiry.course.ilike(like),
            Enquiry.stream.ilike(like),
            Enquiry.city.ilike(like),
        ))
    return query.order_by(Enquiry.created_at.desc()).all()


@app.patch("/api/enquiries/{enquiry_id}/status", response_model=EnquiryOut)
def update_enquiry_status(
    enquiry_id: int,
    payload: EnquiryStatusUpdate,
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    enquiry = db.query(Enquiry).filter(Enquiry.id == enquiry_id).first()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    enquiry.status = payload.status
    db.commit()
    db.refresh(enquiry)
    return enquiry


@app.delete("/api/enquiries/{enquiry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_enquiry(
    enquiry_id: int,
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    enquiry = db.query(Enquiry).filter(Enquiry.id == enquiry_id).first()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    db.delete(enquiry)
    db.commit()
    return None


@app.get("/api/enquiries/export/csv")
def export_enquiries_csv(
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_admin_allow_query_token),
):
    rows = db.query(Enquiry).order_by(Enquiry.created_at.desc()).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["#", "Date", "Name", "Phone", "Email", "Class", "Stream", "Course", "City", "Message", "Status"])
    for i, r in enumerate(rows, start=1):
        writer.writerow([
            i,
            r.created_at.strftime("%d %b %Y, %I:%M %p") if r.created_at else "",
            r.name, r.phone, r.email or "", r.student_class or "",
            r.stream or "", r.course or "", r.city or "", r.message or "", r.status.value,
        ])
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=enquiries.csv"},
    )


# ===================== BOOKINGS / SLOTS =====================

@app.get("/api/bookings/available-slots", response_model=AvailableSlotsOut)
def get_available_slots(slot_date: date = Query(...), db: Session = Depends(get_db)):
    booked = db.query(Booking).filter(
        Booking.slot_date == slot_date,
        Booking.status != BookingStatus.cancelled,
    ).all()
    booked_times = [b.slot_time for b in booked]
    available_times = [t for t in settings.slot_times if t not in booked_times]
    return AvailableSlotsOut(
        slot_date=slot_date,
        booked_times=booked_times,
        available_times=available_times,
        is_full=len(available_times) == 0,
    )


@app.get("/api/bookings/calendar")
def get_booking_calendar(db: Session = Depends(get_db)):
    """Returns booked-out status for each bookable day ahead, so the frontend
    can grey out fully-booked days without a separate call per day."""
    today = date.today()
    result = []
    for i in range(1, settings.days_ahead_bookable + 1):
        d = today + timedelta(days=i)
        booked_count = db.query(Booking).filter(
            Booking.slot_date == d,
            Booking.status != BookingStatus.cancelled,
        ).count()
        result.append({
            "date": d.isoformat(),
            "booked_count": booked_count,
            "total_slots": len(settings.slot_times),
            "is_full": booked_count >= len(settings.slot_times),
        })
    return result


@app.post("/api/bookings", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)):
    if payload.slot_time not in settings.slot_times:
        raise HTTPException(status_code=400, detail="Invalid time slot")

    if payload.slot_date < date.today():
        raise HTTPException(status_code=400, detail="Cannot book a slot in the past")

    # Server-side conflict check - the real source of truth, not just the UI
    existing = db.query(Booking).filter(
        Booking.slot_date == payload.slot_date,
        Booking.slot_time == payload.slot_time,
        Booking.status != BookingStatus.cancelled,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This slot was just booked by someone else. Please pick another time.",
        )

    booking = Booking(
        name=payload.name,
        phone=payload.phone,
        slot_date=payload.slot_date,
        slot_time=payload.slot_time,
        session_type=payload.session_type,
        stream=payload.stream,
        course=payload.course,
        status=BookingStatus.confirmed,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@app.get("/api/bookings", response_model=list[BookingOut])
def list_bookings(
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    return db.query(Booking).order_by(Booking.created_at.desc()).all()


@app.patch("/api/bookings/{booking_id}/status", response_model=BookingOut)
def update_booking_status(
    booking_id: int,
    payload: BookingStatusUpdate,
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = payload.status
    db.commit()
    db.refresh(booking)
    return booking


@app.delete("/api/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    db.delete(booking)
    db.commit()
    return None


# ===================== ADMIN STATS =====================

@app.get("/api/admin/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    enquiries = db.query(Enquiry).all()
    bookings_count = db.query(Booking).count()

    stream_breakdown: dict[str, int] = {}
    course_breakdown: dict[str, int] = {}
    new_count = 0
    enrolled_count = 0

    for e in enquiries:
        if e.status == EnquiryStatus.new:
            new_count += 1
        if e.status == EnquiryStatus.enrolled:
            enrolled_count += 1
        if e.stream:
            stream_breakdown[e.stream] = stream_breakdown.get(e.stream, 0) + 1
        if e.course:
            course_breakdown[e.course] = course_breakdown.get(e.course, 0) + 1

    return StatsOut(
        total_enquiries=len(enquiries),
        new_enquiries=new_count,
        enrolled_enquiries=enrolled_count,
        total_bookings=bookings_count,
        stream_breakdown=stream_breakdown,
        course_breakdown=course_breakdown,
    )
