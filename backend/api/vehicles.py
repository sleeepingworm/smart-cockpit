from fastapi import APIRouter, Query, Depends
from sqlmodel import Session, select, or_
from typing import Optional
from datetime import datetime

from db.database import SessionDep
from models.vehicle import Vehicle, VehicleCreate, VehicleUpdate, VehicleResp
from core.security import get_current_user, require_role

router = APIRouter(
    prefix="/vehicles",
    tags=["车辆管理"],
    dependencies=[Depends(get_current_user)],    # 所有接口要登录
)


@router.get("/", summary="分页查询车辆列表")
def list_vehicles(
    db: SessionDep,
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页条数"),
    keyword: Optional[str] = Query(None, description="搜索关键字（车牌号/品牌/车主）"),
    status: Optional[int] = Query(None, ge=0, le=1, description="按状态筛选"),
):
    """分页搜索车辆列表"""
    # 构建查询
    statement = select(Vehicle)
    count_statement = select(Vehicle)

    # 关键字模糊搜索（车牌号或品牌或车主包含keyword）
    if keyword:
        like = f"%{keyword}%"
        statement = statement.where(or_(
            Vehicle.plate_number.like(like),
            Vehicle.brand.like(like),
            Vehicle.owner.like(like),
        ))
        count_statement = count_statement.where(or_(
            Vehicle.plate_number.like(like),
            Vehicle.brand.like(like),
            Vehicle.owner.like(like),
        ))

    if status is not None:
        statement = statement.where(Vehicle.status == status)
        count_statement = count_statement.where(Vehicle.status == status)

    # 总数
    total = len(db.exec(count_statement).all())

    # 分页
    statement = statement.offset((page - 1) * size).limit(size).order_by(Vehicle.created_at.desc())
    vehicles = db.exec(statement).all()

    return {
        "code": 200,
        "message": "查询成功",
        "data": [VehicleResp.model_validate(v) for v in vehicles],
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/{vehicle_id}", summary="获取车辆详情")
def get_vehicle(vehicle_id: int, db: SessionDep):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        return {"code": 404, "message": "车辆不存在", "data": None}
    return {"code": 200, "message": "success", "data": VehicleResp.model_validate(vehicle)}


@router.post("/", summary="新增车辆", status_code=201)
def create_vehicle(
    req: VehicleCreate,
    db: SessionDep,
    current_user: Vehicle = Depends(require_role(["admin"])),
):
    """新增车辆（管理员）"""
    # 车牌号唯一校验
    if db.exec(select(Vehicle).where(Vehicle.plate_number == req.plate_number)).first():
        return {"code": 400, "message": f"车牌号 {req.plate_number} 已存在", "data": None}

    vehicle = Vehicle.model_validate(req)
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)

    return {"code": 200, "message": "创建成功", "data": VehicleResp.model_validate(vehicle)}


@router.put("/{vehicle_id}", summary="更新车辆")
def update_vehicle(
    vehicle_id: int,
    req: VehicleUpdate,
    db: SessionDep,
    current_user: Vehicle = Depends(require_role(["admin"])),
):
    """更新车辆信息（管理员）"""
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        return {"code": 404, "message": "车辆不存在", "data": None}

    # 车牌号唯一校验（如果改了车牌号）
    if req.plate_number and req.plate_number != vehicle.plate_number:
        if db.exec(select(Vehicle).where(Vehicle.plate_number == req.plate_number)).first():
            return {"code": 400, "message": f"车牌号 {req.plate_number} 已存在", "data": None}

    # 只更新客户端传了的字段
    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vehicle, field, value)
    vehicle.updated_at = datetime.now()

    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return {"code": 200, "message": "更新成功", "data": VehicleResp.model_validate(vehicle)}


@router.delete("/{vehicle_id}", summary="删除车辆")
def delete_vehicle(
    vehicle_id: int,
    db: SessionDep,
    current_user: Vehicle = Depends(require_role(["admin"])),
):
    """删除车辆（管理员）"""
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        return {"code": 404, "message": "车辆不存在", "data": None}

    db.delete(vehicle)
    db.commit()
    return {"code": 200, "message": "删除成功", "data": None}