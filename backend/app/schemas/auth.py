from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    role: str = Field(pattern="^(mentor|teacher|student)$")
    # Staff: email. Student: USN. One field keeps the login form simple.
    identifier: str = Field(min_length=3, max_length=190)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str


class UserOut(BaseModel):
    id: int
    role: str
    name: str
    email: str | None = None
    usn: str | None = None
    # Role-specific profile ids so the frontend can call the right endpoints.
    profile_id: int | None = None
    class_id: int | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)
