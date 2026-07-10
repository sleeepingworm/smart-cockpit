"""
初始化数据库种子数据
用法：cd backend && uv run python -m scripts.seed
"""
from sqlmodel import Session, select
from db.database import engine
from models.user import User
from models.vehicle import Vehicle
from core.security import hash_password


def seed():
    with Session(engine) as db:
        # 创建默认管理员
        admin_exists = db.exec(select(User).where(User.username == "admin")).first()
        if not admin_exists:
            admin = User(
                username="admin",
                email="admin@example.com",
                hashed_password=hash_password("admin123"),
                full_name="系统管理员",
                role="admin",
            )
            db.add(admin)
            print("✅ 创建默认管理员 admin/admin123")

        # 创建一个示例驾驶员
        driver_exists = db.exec(select(User).where(User.username == "driver1")).first()
        if not driver_exists:
            driver = User(
                username="driver1",
                email="driver1@example.com",
                hashed_password=hash_password("123456"),
                full_name="张师傅",
                role="driver",
            )
            db.add(driver)
            print("✅ 创建示例驾驶员 driver1/123456")

        # 示例车辆
        vehicle_exists = db.exec(select(Vehicle).where(Vehicle.plate_number == "京A12345")).first()
        if not vehicle_exists:
            v = Vehicle(plate_number="京A12345", brand="比亚迪", model="汉EV", color="珍珠白", owner="张师傅")
            db.add(v)
            print("✅ 创建示例车辆 京A12345")

        db.commit()
        print("\n种子数据初始化完成！")


if __name__ == "__main__":
    seed()