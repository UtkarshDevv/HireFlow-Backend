"""
Cloud Engineer 90-Day Course — SQLAlchemy model.
"""
from sqlalchemy import Column, String, Integer, Boolean, Date, Text, JSON
from app.database import Base


class CourseDay(Base):
    __tablename__ = "cloudprep_course_days"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True, index=True)
    day = Column(Integer, nullable=False, index=True)
    week = Column(Integer, nullable=False)
    domain = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    subtopic = Column(String, nullable=True)
    lab = Column(String, nullable=True)
    resource_url = Column(String, nullable=True)
    youtube_url = Column(String, nullable=True)
    planned_hours = Column(Integer, default=3)
    completed = Column(Boolean, default=False)
    completed_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
