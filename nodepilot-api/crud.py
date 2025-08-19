from sqlalchemy.orm import Session
from database import Annotation, AnnotationStatus
from typing import List, Optional

def create_annotation(db: Session, url: str, selected_text: str, confusion_note: str, 
                     page_title: Optional[str] = None, audio_transcription: Optional[str] = None, 
                     cognitive_note: Optional[str] = None) -> Annotation:
    annotation = Annotation(
        url=url,
        selected_text=selected_text,
        confusion_note=confusion_note,
        page_title=page_title,
        audio_transcription=audio_transcription,
        cognitive_note=cognitive_note
    )
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return annotation

def get_annotation(db: Session, annotation_id: int) -> Optional[Annotation]:
    return db.query(Annotation).filter(Annotation.id == annotation_id).first()

def get_annotations(db: Session, skip: int = 0, limit: int = 100) -> List[Annotation]:
    return db.query(Annotation).offset(skip).limit(limit).all()

def update_annotation_status(db: Session, annotation_id: int, status: AnnotationStatus) -> Optional[Annotation]:
    annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()
    if annotation:
        annotation.status = status
        db.commit()
        db.refresh(annotation)
    return annotation

def update_teaching_content(db: Session, annotation_id: int, teaching_content: str) -> Optional[Annotation]:
    annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()
    if annotation:
        annotation.teaching_content = teaching_content
        db.commit()
        db.refresh(annotation)
    return annotation