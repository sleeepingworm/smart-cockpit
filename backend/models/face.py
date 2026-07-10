from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


# ============= 数据库表模型 =============
class Face(SQLModel, table=True):
    """驾驶员人脸识别表"""
    __tablename__ = "faces"

    id: int | None = Field(default=None, primary_key=True)
    vehicle_id: int = Field(foreign_key="vehicles.id", nullable=False, index=True, description="关联车辆ID")
    driver_name: str | None = Field(default=None, max_length=50, description="驾驶员姓名")
    face_image_url: str | None = Field(default=None, max_length=500, description="人脸图片路径")
    feature_vector: str | None = Field(default=None, max_length=2000, description="人脸特征向量（JSON字符串）")
    recognition_result: str = Field(default="unknown", max_length=20, description="识别结果：success/failed/unknown")
    confidence: float | None = Field(default=None, description="识别置信度（0~1）")
    captured_at: datetime = Field(default_factory=datetime.now, description="采集时间")
    created_at: datetime | None = Field(default_factory=datetime.now)
    updated_at: datetime | None = Field(default_factory=datetime.now)


# ============= 请求模型 =============
class FaceCreate(SQLModel):
    """创建人脸识别记录"""
    vehicle_id: int = Field(description="车辆ID")
    driver_name: str | None = Field(default=None, description="驾驶员姓名", max_length=50)
    face_image_url: str | None = Field(default=None, description="人脸图片路径", max_length=500)
    feature_vector: str | None = Field(default=None, description="人脸特征向量", max_length=2000)
    recognition_result: str = Field(default="unknown", description="识别结果", max_length=20)
    confidence: float | None = Field(default=None, description="识别置信度")
    captured_at: datetime = Field(default_factory=datetime.now, description="采集时间")


class FaceUpdate(SQLModel):
    """更新人脸识别记录（全部可选）"""
    driver_name: str | None = Field(default=None, description="驾驶员姓名", max_length=50)
    face_image_url: str | None = Field(default=None, description="人脸图片路径", max_length=500)
    feature_vector: str | None = Field(default=None, description="人脸特征向量", max_length=2000)
    recognition_result: str | None = Field(default=None, description="识别结果", max_length=20)
    confidence: float | None = Field(default=None, description="识别置信度")


# ============= 响应模型 =============
class FaceResp(SQLModel):
    """返回给前端的人脸识别信息"""
    id: int
    vehicle_id: int
    driver_name: str | None = None
    face_image_url: str | None = None
    recognition_result: str
    confidence: float | None = None
    captured_at: datetime | None = None
    created_at: datetime | None = None