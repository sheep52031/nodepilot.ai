from pydantic import BaseModel
from database import AnnotationStatus
from typing import Optional
from datetime import datetime

class AnnotationCreate(BaseModel):
    url: str
    selected_text: str
    confusion_note: str

class CreateAnnotationRequest(BaseModel):
    url: str
    selected_text: str
    confusion_note: str
    page_title: Optional[str] = None

class AnnotationResponse(BaseModel):
    id: int
    url: str
    selected_text: str
    confusion_note: str
    audio_transcription: Optional[str] = None
    cognitive_note: Optional[str] = None
    teaching_content: Optional[str] = None
    page_title: Optional[str] = None
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