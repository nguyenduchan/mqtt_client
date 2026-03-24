from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Lấy URL từ biến môi trường (Docker-compose đã thiết lập)
# Ưu tiên lấy từ Docker-compose, nếu không thấy thì dùng giá trị mặc định khớp với compose
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:admin@postgres_db:5432/iot_center" # Đã sửa thành admin:admin
)



engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Hàm để lấy session DB cho mỗi request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
