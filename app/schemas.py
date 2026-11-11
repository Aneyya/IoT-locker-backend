from pydantic import BaseModel, Field

# Model żądań (REQUEST)
class TechnicianVerifyRequest(BaseModel):
    machine_id: str = Field(..., min_length=1, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=100)

class RecipientPickupRequest(BaseModel):
    recipient_phone: str = Field(..., pattern=r"^[1-9]\d{8}$")
    pin_code: str =  Field(..., pattern=r"^\d{6}$")

class SenderCreateRequest(BaseModel):
    recipient_phone: str = Field(..., pattern=r"^[1-9]\d{8}$")

class CourierLoginRequest(BaseModel):
    courier_login: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=12, max_length=128)

class CourierDeliverRequest(BaseModel):
    package_number: int = Field(..., ge=100000000, le=999999999)

# Modele odpowiedzi (RESPONSE)
class SuccessResponse(BaseModel):
    success: bool
    message: str

class LockerStatusResponse(BaseModel):
    locker_id: str
    status: str

class MachineStatusResponse(BaseModel):
    machine_id: str
    service_locker_id: str
    is_service_open: bool
    lockers: list[LockerStatusResponse]

class TechnicianVerifyResponse(BaseModel):
    access_granted: bool
    message: str
    machine_id: str
    service_locker: str

class CourierLoginResponse(BaseModel):
    authenticated: bool
    token_session: str
    message: str

class CourierPickupsResponse(BaseModel):
    success: bool
    message: str
    lockers_to_open: list[str]

class CourierDeliveryResponse(BaseModel):
    success: bool
    message: str
    locker_id: str

class ClientPickupResponse(BaseModel):
    success: bool
    message: str
    locker_id: str

class ClientSenderResponse(BaseModel):
    success: bool
    message: str
    package_number: int
    locker_id: str