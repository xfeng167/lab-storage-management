import re

from pydantic import BaseModel, field_validator


USERNAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,29}$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_username(value: str) -> str:
    username = value.strip()
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError(
            "Username must be 3-30 characters, start with a letter, and use only letters, numbers, or underscores."
        )
    return username


def validate_password(value: str) -> str:
    if not 8 <= len(value) <= 72:
        raise ValueError("Password must be 8-72 characters.")
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must include at least one letter and one number.")
    return value


class UserCreate(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("username")
    @classmethod
    def username_must_match_policy(cls, value: str) -> str:
        return validate_username(value)

    @field_validator("email")
    @classmethod
    def email_must_match_policy(cls, value: str) -> str:
        email = value.strip().lower()
        if len(email) > 255 or not EMAIL_PATTERN.fullmatch(email):
            raise ValueError("Enter a valid email address up to 255 characters.")
        return email

    @field_validator("password")
    @classmethod
    def password_must_match_policy(cls, value: str) -> str:
        return validate_password(value)


class UserProfileUpdate(BaseModel):
    username: str
    email: str
    profile_picture: str | None = None

    @field_validator("username")
    @classmethod
    def username_must_match_policy(cls, value: str) -> str:
        return validate_username(value)

    @field_validator("email")
    @classmethod
    def email_must_match_policy(cls, value: str) -> str:
        email = value.strip().lower()
        if len(email) > 255 or not EMAIL_PATTERN.fullmatch(email):
            raise ValueError("Enter a valid email address up to 255 characters.")
        return email

    @field_validator("profile_picture")
    @classmethod
    def profile_picture_must_be_supported(cls, value: str | None) -> str | None:
        if value is None:
            return None
        picture = value.strip()
        if not picture:
            return None
        if len(picture) > 500_000:
            raise ValueError("Profile picture is too large.")
        if not (picture.startswith("data:image/") or picture.startswith("https://") or picture.startswith("http://")):
            raise ValueError("Profile picture must be an image upload or image URL.")
        return picture


class UserLogin(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_must_not_be_blank(cls, value: str) -> str:
        username = value.strip()
        if not username:
            raise ValueError("Username is required.")
        return username

    @field_validator("password")
    @classmethod
    def password_must_not_be_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("Password is required.")
        return value

class Token(BaseModel):
    token: str

class UserRead(BaseModel):
    id: int
    username: str
    email: str
    role: str
    profile_picture: str | None = None

class LoginResponse(BaseModel):
    user: UserRead
    token: str


class LogoutResponse(BaseModel):
    message: str
