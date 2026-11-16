from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

class Machine(Base):
    __tablename__= "machines"

    machine_id = Column(String, primary_key=True)
    address = Column(String, nullable=False)
    service_locker_id = Column(String, nullable=False)
    is_service_open = Column(Boolean, default=False, nullable=False)

    #Relacje
    lockers = relationship("Locker", back_populates="machine")
    service_logs = relationship("ServiceLog", back_populates="machine")
    packages = relationship("Package", back_populates="target_machine")

class Locker(Base):
    __tablename__= "lockers"
    
    locker_id = Column(String, primary_key=True)
    machine_id = Column(String, ForeignKey("machines.machine_id"), nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    package_number = Column(Integer, ForeignKey("packages.package_number"), nullable=True, unique=True)
    pin_code = Column(String, nullable=True)
    
    #Relacje
    machine = relationship("Machine", back_populates="lockers")
    package = relationship("Package", back_populates="locker", uselist=False)
    
class Package(Base):
    __tablename__= "packages"
    package_number = Column(Integer, primary_key=True)
    recipient_phone = Column(String, nullable=False, index=True)
    target_machine_id = Column(String, ForeignKey("machines.machine_id"), nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    courier_login = Column(String, ForeignKey("couriers.courier_login"), nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    #Relacje
    courier = relationship("Courier", back_populates="packages")
    locker = relationship("Locker", back_populates="package", uselist=False)
    target_machine = relationship("Machine", back_populates="packages")

class Courier(Base):
    __tablename__= "couriers"

    courier_login = Column(String, primary_key=True)
    password_hash = Column(String, nullable=False)
    token_session = Column(String, nullable=True, index=True)
    token_expires_at = Column(DateTime, nullable=True)

    #Relacje
    packages = relationship("Package", back_populates="courier")

class Technician(Base):
    __tablename__= "technicians"

    tech_id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)

    #Relacje
    service_logs = relationship("ServiceLog", back_populates="technician")

class ServiceLog(Base):
    __tablename__= "service_logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(String, ForeignKey("machines.machine_id"), nullable=False, index=True)
    tech_id = Column(Integer, ForeignKey("technicians.tech_id"), nullable=True, index=True)
    action = Column(String, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    #Relacje
    machine = relationship("Machine", back_populates="service_logs")
    technician = relationship("Technician", back_populates="service_logs")