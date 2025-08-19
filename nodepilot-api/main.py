from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db, create_tables
from schemas import AnnotationCreate, AnnotationResponse, StatusUpdate, TeachingRequest, CreateAnnotationRequest
from openai_service import ai_service
import crud
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

app = FastAPI(title="NodePilot AI Teaching API", version="1.0.0")

# CORS 配置
origins = [
    "chrome-extension://*",
    "http://localhost:*",
    "https://manus.im"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 啟動時初始化資料庫
@app.on_event("startup")
def startup_event():
    create_tables()

@app.get("/")
def read_root():
    return {"message": "NodePilot AI Teaching API", "version": "1.0.0"}

@app.post("/generate-teaching", response_model=AnnotationResponse)
def generate_teaching(request: TeachingRequest, db: Session = Depends(get_db)):
    # 建立標註記錄
    annotation = crud.create_annotation(
        db=db,
        url=request.url,
        selected_text=request.selected_text,
        confusion_note=request.confusion_note
    )
    
    # 使用 OpenAI API 生成教學內容
    teaching_content = ai_service.generate_teaching_content(
        url=request.url,
        selected_text=request.selected_text,
        confusion_note=request.confusion_note
    )
    
    # 更新教學內容
    annotation = crud.update_teaching_content(db, annotation.id, teaching_content)
    
    return annotation

@app.get("/annotations", response_model=list[AnnotationResponse])
def get_annotations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    annotations = crud.get_annotations(db, skip=skip, limit=limit)
    return annotations

@app.get("/annotations/{annotation_id}", response_model=AnnotationResponse)
def get_annotation(annotation_id: int, db: Session = Depends(get_db)):
    annotation = crud.get_annotation(db, annotation_id=annotation_id)
    if annotation is None:
        raise HTTPException(status_code=404, detail="Annotation not found")
    return annotation

@app.put("/annotations/{annotation_id}/status", response_model=AnnotationResponse)
def update_annotation_status(annotation_id: int, status_update: StatusUpdate, db: Session = Depends(get_db)):
    annotation = crud.update_annotation_status(db, annotation_id, status_update.status)
    if annotation is None:
        raise HTTPException(status_code=404, detail="Annotation not found")
    return annotation

@app.post("/annotations", response_model=AnnotationResponse)
async def create_annotation(
    url: str = Form(...),
    selected_text: str = Form(...),
    confusion_note: str = Form(...),
    page_title: Optional[str] = Form(None),
    audio_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """建立標註並處理音檔轉錄和認知記錄生成"""
    
    audio_transcription = None
    cognitive_note = None
    
    # 處理音檔轉錄
    if audio_file and audio_file.size > 0:
        # 檢查檔案大小限制（20MB）
        if audio_file.size > 20 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="音檔檔案過大，限制 20MB")
        
        # 檢查檔案格式
        allowed_types = ["audio/webm", "audio/mp4", "audio/mpeg", "audio/wav"]
        if audio_file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="不支援的音檔格式")
        
        # 轉錄音檔
        audio_transcription = ai_service.transcribe_audio(audio_file.file)
        
        # 如果轉錄成功，生成認知記錄
        if audio_transcription:
            cognitive_note = ai_service.generate_cognitive_note(
                audio_transcription, selected_text, confusion_note
            )
    
    # 建立標註記錄
    annotation = crud.create_annotation(
        db=db,
        url=url,
        selected_text=selected_text,
        confusion_note=confusion_note,
        page_title=page_title,
        audio_transcription=audio_transcription,
        cognitive_note=cognitive_note
    )
    
    return annotation

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
