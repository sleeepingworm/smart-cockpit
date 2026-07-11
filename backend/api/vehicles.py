from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from datetime import datetime
from db.database import SessionDep
from models.vehicle import Vehicle, VehicleCreate, VehicleUpdate, VehicleResp
from core.security import get_current_user

router = APIRouter(
    prefix="/vehicles",
    tags=["车辆管理"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/", response_model=dict)
def list_vehicles(
    db: SessionDep,                                                  # ⚠️ 无默认值的参数放前面！
    page: int = Query(1, ge=1, description="页码，从1开始"),
    size: int = Query(10, ge=1, le=100, description="每页条数"),
):
    """分页查询车辆列表"""
    # 1. 查询总数
    total = len(db.exec(select(Vehicle)).all())

    # 2. 分页查询
    statement = select(Vehicle).offset((page - 1) * size).limit(size)
    vehicles = db.exec(statement).all()

    # 3. 转成Resp模型
    data = [VehicleResp.model_validate(v) for v in vehicles]

    return {
        "code": 200,
        "message": "查询成功",
        "data": data,
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/{vehicle_id}", response_model=dict)
def get_vehicle(vehicle_id: int, db: SessionDep):
    """根据ID查单个车辆"""
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        return {"code": 404, "message": f"车辆{vehicle_id}不存在", "data": None}
    return {
        "code": 200,
        "message": "success",
        "data": VehicleResp.model_validate(vehicle),
    }


@router.post("/", response_model=dict, status_code=201)
def create_vehicle(req: VehicleCreate, db: SessionDep):
    """新建车辆"""
    # 1. 检查车牌号是否已存在
    exists = db.exec(
        select(Vehicle).where(Vehicle.plate_number == req.plate_number)
    ).first()
    if exists:
        return {"code": 400, "message": f"车牌号{req.plate_number}已存在", "data": None}

    # 2. 创建对象
    vehicle = Vehicle.model_validate(req)

    # 3. 加入session + 提交
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)   # refresh后拿到自动生成的id和created_at

    return {
        "code": 200,
        "message": "创建成功",
        "data": VehicleResp.model_validate(vehicle),
    }


@router.put("/{vehicle_id}", response_model=dict)
def update_vehicle(vehicle_id: int, req: VehicleUpdate, db: SessionDep):
    """更新车辆信息"""
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        return {"code": 404, "message": f"车辆{vehicle_id}不存在", "data": None}

    # 只更新客户端传了的字段（排除None值）
    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vehicle, field, value)
    vehicle.updated_at = datetime.now()

    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)

    return {
        "code": 200,
        "message": "更新成功",
        "data": VehicleResp.model_validate(vehicle),
    }


@router.delete("/{vehicle_id}", response_model=dict)
def delete_vehicle(vehicle_id: int, db: SessionDep):
    """删除车辆"""
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        return {"code": 404, "message": f"车辆{vehicle_id}不存在", "data": None}

    db.delete(vehicle)
    db.commit()

    return {"code": 200, "message": "删除成功", "data": None}
