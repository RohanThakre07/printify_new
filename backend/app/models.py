from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from backend.app.core.database import Base


class AppConfig(Base):
    __tablename__ = "app_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProcessedImage(Base):
    __tablename__ = "processed_images"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String(500), unique=True, nullable=False)
    file_hash = Column(String(128), index=True, nullable=False)
    status = Column(String(30), nullable=False, default="queued")
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProcessingLog(Base):
    __tablename__ = "processing_logs"

    id = Column(Integer, primary_key=True, index=True)
    image_path = Column(String(500), nullable=True)
    level = Column(String(20), nullable=False, default="INFO")
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProductRun(Base):
    __tablename__ = "product_runs"

    id = Column(Integer, primary_key=True, index=True)
    image_path = Column(String(500), nullable=False)
    file_hash = Column(String(128), nullable=True)
    status = Column(String(30), default="queued")
    success = Column(Boolean, default=False)

    analysis_json = Column(Text, nullable=True)
    listing_json = Column(Text, nullable=True)

    printify_upload_id = Column(String(100), nullable=True)
    printify_product_id = Column(String(100), nullable=True)

    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
