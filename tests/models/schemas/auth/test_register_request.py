import pytest
from pydantic import ValidationError

from app.models.schemas.auth.register_request import RegisterRequest

def test_valid_register_request():
    request = RegisterRequest(
        username="valid_user123",
        password="ValidPass123!"
    )
    assert request.username == "valid_user123"
    assert request.password == "ValidPass123!"

def test_username_too_short():
    with pytest.raises(ValidationError) as exc_info:
        RegisterRequest(
            username="ab",
            password="ValidPass123!"
        )
    assert "must be at least 3 characters long" in str(exc_info.value)

def test_username_too_long():
    with pytest.raises(ValidationError) as exc_info:
        RegisterRequest(
            username="a" * 21,
            password="ValidPass123!"
        )
    assert "must be at most 20 characters long" in str(exc_info.value)

def test_username_invalid_chars():
    with pytest.raises(ValidationError) as exc_info:
        RegisterRequest(
            username="valid-user@123",
            password="ValidPass123!"
        )
    assert "can only contain alphanumeric characters and underscores" in str(exc_info.value)

def test_password_too_short():
    with pytest.raises(ValidationError) as exc_info:
        RegisterRequest(
            username="valid_user123",
            password="Short1!"
        )
    assert "must be at least 8 characters long" in str(exc_info.value)

def test_password_too_long():
    with pytest.raises(ValidationError) as exc_info:
        RegisterRequest(
            username="valid_user123",
            password="a" * 33
        )
    assert "must be at most 32 characters long" in str(exc_info.value)

def test_password_no_uppercase():
    with pytest.raises(ValidationError) as exc_info:
        RegisterRequest(
            username="valid_user123",
            password="validpass123!"
        )
    assert "must contain at least one uppercase letter" in str(exc_info.value)

def test_password_no_lowercase():
    with pytest.raises(ValidationError) as exc_info:
        RegisterRequest(
            username="valid_user123",
            password="VALIDPASS123!"
        )
    assert "must contain at least one lowercase letter" in str(exc_info.value)

def test_password_no_digit():
    with pytest.raises(ValidationError) as exc_info:
        RegisterRequest(
            username="valid_user123",
            password="ValidPass!"
        )
    assert "must contain at least one digit" in str(exc_info.value)

def test_password_no_special_char():
    with pytest.raises(ValidationError) as exc_info:
        RegisterRequest(
            username="valid_user123",
            password="ValidPass123"
        )
    assert "must contain at least one special character" in str(exc_info.value) 