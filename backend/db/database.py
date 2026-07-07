from sqlmodel import SQLModel, create_engine, Session
from typing import Generator, Annotated
from fastapi import Depends
from config.settings import settings

# 创建数据库引擎（连接池）
engine = create_engine(
    settings.MYSQL_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
)
# DEBUG=true时打印所有SQL语句，方便学习


def create_tables() -> None:
    """
    启动时调用，根据所有已注册的SQLModel模型自动建表。

    注意：必须在调用此函数前 import 了所有模型类，否则表不会创建！
    Day1 models/__init__.py 是空的，所以今天不会创建任何表——正常现象！
    后续每天添加模型后，在 models/__init__.py 里 import 进来即可。
    """
    SQLModel.metadata.create_all(engine)


def get_db() -> Generator[Session, None, None]:
    """
    依赖注入：每个HTTP请求获取一个独立的数据库Session，请求结束自动关闭。
    用法：在路由函数参数里写 db: Session = Depends(get_db)
    """
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


# 类型别名，路由里写起来更简洁
SessionDep = Annotated[Session, Depends(get_db)]