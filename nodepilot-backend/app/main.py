"""
NodePilot API - 重構後的主應用檔案
使用清晰的分層架構
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.models.database import create_tables
from app.api.v1.agents import router as agents_router
from app.api.voxtral_localai import router as voxtral_router
from app.api.voxtral_audio import router as voxtral_audio_router
from app.services.integrated_system import integrated_system


def create_application() -> FastAPI:
    """建立 FastAPI 應用"""
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        debug=settings.debug
    )
    
    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 註冊路由
    app.include_router(
        agents_router,
        prefix=settings.api_v1_prefix,
        tags=["agents"]
    )
    
    # Voxtral LocalAI 路由 (用於 AnythingLLM 整合)
    app.include_router(
        voxtral_router,
        tags=["voxtral-localai"]
    )
    
    # Voxtral Audio 路由 (語音處理)
    app.include_router(
        voxtral_audio_router,
        tags=["voxtral-audio"]
    )
    
    # 掛載靜態檔案目錄
    import os
    static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    if os.path.exists(static_path):
        app.mount("/static", StaticFiles(directory=static_path), name="static")
    
    return app


app = create_application()


@app.on_event("startup")
async def startup_event():
    """應用啟動事件"""
    create_tables()
    await integrated_system.initialize()
    print("🎉 NodePilot API 已啟動")


@app.get("/")
def read_root():
    """根路徑"""
    return {
        "message": f"{settings.app_name} is running",
        "version": settings.version,
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """健康檢查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.debug
    )