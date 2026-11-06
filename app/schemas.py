from pydantic import BaseModel

# Model żądań (REQUEST)
class TechnicianVerifyRequest(BaseModel):
    machine_id: str
    full_name: str

class RecipientPickupRequest(BaseModel):
    recipient_phone: str
    pin_code: str

class SenderCreateRequest(BaseModel):
    recipient_phone: str

class CourierLoginRequest(BaseModel):
    courier_login: str
    password: str

class CourierDeliverRequest(BaseModel):
    package_number: int

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