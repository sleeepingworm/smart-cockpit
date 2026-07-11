# main.py 顶部（import区域）
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import models
from config.settings import settings
from db.database import create_tables
from api.auth import router as auth_router
from api.user import router as users_router      # 新增
from api.vehicles import router as vehicles_router
from api.faces import router as faces_router


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

    # 创建数据库表（根据已import的模型自动建表）
    create_tables()
    print("[启动] 数据库表初始化完成")

    # 🌟 Day7之后才会加AI模型预热
    print("[启动] 启动完成！")
    print("[启动] 访问 http://localhost:8000/docs 查看接口文档")
    print("=" * 50)

    yield   # <-- 应用运行期间停在这里

    # ========== 关闭时执行（今天没什么要清理的）==========
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
app.include_router(vehicles_router)
app.include_router(faces_router)

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
app.include_router(auth_router)
app.include_router(users_router)                  # 新增
app.include_router(vehicles_router)
app.include_router(faces_router)

# ========== 启动入口 ==========
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",          # 指向本文件里的app对象
        host="0.0.0.0",      # 监听所有网卡（同局域网手机也能访问）
        port=8000,           # 端口号
        reload=True,         # 开发模式：代码改了自动重启
    )
