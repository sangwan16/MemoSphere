from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)


class UsernameUpdate(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_]+$")


class AccountPrivacyUpdate(BaseModel):
    is_public: bool


class CurrentUserResponse(BaseModel):
    id: int
    email: EmailStr
    username: str | None
    is_active: bool
    is_email_verified: bool
    is_public: bool


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1)


class EmailRequest(BaseModel):
    email: EmailStr


class MessageResponse(BaseModel):
    message: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"