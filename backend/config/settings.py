from pydantic_settings import BaseSettings, SettingsConfigDict
import json
from typing import List


class Settings(BaseSettings):
    # ...已有配置...

    # ============ Day9: 疲劳检测阈值 ============
    FATIGUE_EAR_THRESHOLD: float = 0.22    # EAR 闭眼判定阈值
    FATIGUE_MAR_THRESHOLD: float = 0.60    # MAR 张嘴阈值
    FATIGUE_WINDOW_FRAMES: int = 50        # PERCLOS 滑窗长度（帧）
    FATIGUE_PERCLOS_THRESHOLD: float = 0.3 # PERCLOS 疲劳阈值
    FATIGUE_YAWN_MIN_FRAMES: int = 8       # 连续多少帧张嘴才计 1 次哈欠
    FATIGUE_ALERT_COOLDOWN: int = 60       # 两次疲劳告警最短间隔秒数
    # ...已有配置...

    # 第三方 API
    AMAP_KEY: str = ""

    # 传感器
    SENSOR_ENABLED: bool = False
    SENSOR_PORT: str = "COM3"
    SENSOR_BAUDRATE: int = 115200
    SENSOR_READ_INTERVAL: float = 0.05     # 串口读间隔
    SENSOR_DATA_TTL: int = 5               # 数据过期秒数
    SENSOR_MOCK_ENABLED_FALLBACK: bool = True
    """应用配置 - 从 .env 文件和环境变量自动读取"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 数据库
    MYSQL_URL: str = "mysql+pymysql://root:123456@127.0.0.1:3307/cockpit_db?charset=utf8mb4"
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    # JWT
    JWT_SECRET: str = "dev-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7
    # CORS（.env里是JSON字符串，自动解析成List[str]）
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]
    # 上传目录
    UPLOAD_DIR: str = "uploads"
    # 调试模式
    DEBUG: bool = True


settings = Settings()