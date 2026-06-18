import enum

from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Enum as SAEnum, func

from database import Base


class EnquiryStatus(str, enum.Enum):
    new = "New"
    contacted = "Contacted"
    enrolled = "Enrolled"
    not_interested = "Not interested"


class BookingStatus(str, enum.Enum):
    confirmed = "Confirmed"
    completed = "Completed"
    cancelled = "Cancelled"
    no_show = "No-show"


class Enquiry(Base):
    __tablename__ = "enquiries"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    name = Column(String(120), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    email = Column(String(120), nullable=True)
    student_class = Column(String(60), nullable=True)   # f-class
    stream = Column(String(60), nullable=True)           # f-stream
    course = Column(String(120), nullable=True)          # f-course
    city = Column(String(80), nullable=True)
    message = Column(Text, nullable=True)

    status = Column(SAEnum(EnquiryStatus, name="enquiry_status"), nullable=False, default=EnquiryStatus.new)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    name = Column(String(120), nullable=False)
    phone = Column(String(20), nullable=False, index=True)

    slot_date = Column(Date, nullable=False, index=True)   # actual calendar date of the slot
    slot_time = Column(String(20), nullable=False)         # e.g. "10:00 AM"
    session_type = Column(String(30), nullable=False, default="Phone Call")  # Phone Call / Google Meet / WhatsApp

    stream = Column(String(60), nullable=True)
    course = Column(String(120), nullable=True)

    status = Column(SAEnum(BookingStatus, name="booking_status"), nullable=False, default=BookingStatus.confirmed)
