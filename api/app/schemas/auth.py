from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    user_id: str
    email: str
    organization: str | None


class SessionResponse(BaseModel):
    user_id: str
    email: str
    organization: str | None
