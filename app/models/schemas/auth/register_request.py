from pydantic import BaseModel, field_validator

class RegisterRequest(BaseModel):
    username: str
    password: str

    @field_validator('username')
    def validate_username(cls, v: str):
        if len(v) < 3:
            raise ValueError('must be at least 3 characters long')
        if len(v) > 20:
            raise ValueError('must be at most 20 characters long')
        if not v.replace('_', '').isalnum():
            raise ValueError('can only contain alphanumeric characters and underscores')
        return v

    @field_validator('password')
    def validate_password(cls, v: str):
        if len(v) < 8:
            raise ValueError('must be at least 8 characters long')
        if len(v) > 32:
            raise ValueError('must be at most 32 characters long')
        if not any(char.isupper() for char in v):
            raise ValueError('must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('must contain at least one lowercase letter')
        if not any(char.isdigit() for char in v):
            raise ValueError('must contain at least one digit')
        if not any(char in '!@#$%^&*()_+-=[]{}|;:,.<>?`~' for char in v):
            raise ValueError('must contain at least one special character')
        return v