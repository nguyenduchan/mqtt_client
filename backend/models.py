from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint
from datetime import datetime
from database import Base

class GatewayConfig(Base):
    __tablename__ = "gateway_configs"
    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(String(50), index=True)
    filename = Column(String(100))
    content = Column(Text)
    version = Column(Integer, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow)
    # Đảm bảo 1 board không bị trùng tên file
    __table_args__ = (UniqueConstraint('board_id', 'filename', name='_board_file_uc'),)

class OfficialVersion(Base):
    __tablename__ = "official_versions"
    id = Column(Integer, primary_key=True, index=True)
    version_name = Column(String(50), unique=True) # v1.0, v2.0
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
