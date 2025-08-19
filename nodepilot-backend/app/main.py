"""
NodePilot API - 重構後的主應用檔案
使用清晰的分層架構
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.models.database import create_tables
from app.api.v1.agents import router as agents_router
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