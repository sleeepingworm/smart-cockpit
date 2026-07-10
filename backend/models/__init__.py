# models/__init__.py
# 必须import所有模型，SQLModel才能在create_all时建表
from models.vehicle import Vehicle, VehicleCreate, VehicleUpdate, VehicleResp
from models.user import User, UserCreate, UserUpdate, UserResp, UserLogin
from models.alert import Alert, AlertCreate, AlertUpdate, AlertResp
from models.face import Face, FaceCreate, FaceUpdate, FaceResp
from models.vehicle import Vehicle, VehicleCreate, VehicleUpdate, VehicleResp
from models.user import User, UserCreate, UserLogin, UserResp, TokenResp