# main.py 顶部（import区域）
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import models
from config.settings import settings
from db.database import create_tables
from fastapi.staticfiles import StaticFiles
from api.auth import router as auth_router
from api.user import router as users_router
from api.vehicles import router as vehicles_router
from api.faces import router as faces_router
from api.alerts import router as alerts_router
from ai.face_recognition import warm_up as face_warm_up
from sqlmodel import Session, select
from models.face_library import Face
from db.database import engine
from api.amap import router as amap_router
from api.weather import router as weather_router
from api.sensor import router as sensor_router, start_sensor_manager, stop_sensor_manager
from api.fatigue import router as fatigue_router
from ai.fatigue_detection import warm_up as fatigue_warm_up
from api.obstacle import router as obstacle_router
from ai.obstacle_detection import warm_up as obstacle_warm_up

# ========== 应用生命周期 ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    lifespan 控制应用启动和关闭时要做的事。
    yield 之前是启动逻辑，yield 之后是关闭清理逻辑。
    """
    # ========== 启动时执行 ==========
    print("=" * 50)
    print("[启动] 智慧驾舱AI API 正在启动...")

    # 确保上传目录存在
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "faces"), exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "voices"), exist_ok=True)

    # 创建数据库表（根据已import的模型自动建表）
    create_tables()
    print("[启动] 数据库表初始化完成")

    # 人脸识别模型预热（Day7）
    try:
        with Session(engine) as session:
            first_face = session.exec(
                select(Face).where(Face.is_active == True, Face.is_deleted == False).limit(1)
            ).first()
        sample = os.path.join(settings.UPLOAD_DIR, first_face.file_path) if first_face else None
        face_warm_up(sample)
    except Exception as e:
        print(f"[启动] 人脸模型预热失败（不阻塞启动）：{e}")

    # 启动传感器管理器（Day8）
    start_sensor_manager()

    # 疲劳检测模型预热（Day9）
    try:
        fatigue_warm_up()
        print("[启动] 疲劳检测模型预热完成")
    except Exception as e:
        print(f"[启动] 疲劳检测预热失败（不阻塞）: {e}")

    # 障碍物检测模型预热（Day10）
    try:
        obstacle_warm_up()
        print("[启动] 障碍物检测模型预热完成")
    except Exception as e:
        print(f"[启动] 障碍物预热失败（不阻塞）: {e}")

    print("[启动] 启动完成！")
    print("[启动] 访问 http://localhost:8000/docs 查看接口文档")
    print("=" * 50)

    yield   # <-- 应用运行期间停在这里

    # ========== 关闭时执行 ==========
    stop_sensor_manager()
    print("[关闭] 服务已停止")

# ========== 创建FastAPI应用实例 ==========
app = FastAPI(
    title="智慧驾舱AI API",
    description="15天实训项目 - 智能驾驶舱综合解决方案",
    version="0.1.0",
    lifespan=lifespan,
)

# ========== 跨域配置 ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 路由注册 ==========
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(vehicles_router)
app.include_router(faces_router)
app.include_router(alerts_router)

# ========== 测试接口 ==========
@app.get("/health", tags=["系统"])
def health_check():
    """健康检查 - 确认服务是否正常运行"""
    return {"code": 200, "message": "服务运行正常", "data": {"status": "ok"}}


@app.get("/hello", tags=["系统"])
def say_hello(name: str = "驾驶员"):
    """
    打招呼接口 - 你的第一个FastAPI接口！
    访问 /hello?name=张三 试试
    """
    return {
        "code": 200,
        "message": "success",
        "data": {"greeting": f"你好，{name}！欢迎来到智慧驾舱！"}
    }

# ========== 挂载静态文件目录 ==========
app.mount("/static", StaticFiles(directory=settings.UPLOAD_DIR), name="static")
# 注册新路由
app.include_router(amap_router)
app.include_router(weather_router)
app.include_router(sensor_router)
app.include_router(fatigue_router)
app.include_router(obstacle_router)
# ========== 启动入口 ==========
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",          # 指向本文件里的app对象
        host="0.0.0.0",      # 监听所有网卡（同局域网手机也能访问）
        port=8000,           # 端口号
        reload=True,         # 开发模式：代码改了自动重启
    )
