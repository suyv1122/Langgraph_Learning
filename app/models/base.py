# models实际上就是模型，这里我们说的模型应该是和数据库中的表格一一对应的
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass