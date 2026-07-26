from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    token: str

class UserRead(BaseModel):
    id: int
    username: str
    email: str


class LoginResponse(BaseModel):
    user: UserRead
    token: str


class LogoutResponse(BaseModel):
    message: str
