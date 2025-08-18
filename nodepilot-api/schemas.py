from pydantic import BaseModel
from database import AnnotationStatus
from typing import Optional
from datetime import datetime

class AnnotationCreate(BaseModel):
    url: str
    selected_text: str
    confusion_note: str

class AnnotationResponse(BaseModel):
    id: int
    url: str
    selected_text: str
    confusion_note: str
    teaching_content: Optional[str] = None
    status: AnnotationStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class StatusUpdate(BaseModel):
    status: AnnotationStatus

class TeachingRequest(BaseModel):
    url: str
    selected_text: str
    confusion_note: str