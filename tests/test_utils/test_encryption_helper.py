import pytest
from app.utils.encryption_helper import encrypt_token, decrypt_token

def test_encrypt_and_decrypt_token():
    # Test with a simple token
    original_token = "test_token_123"
    encrypted = encrypt_token(original_token)
    decrypted = decrypt_token(encrypted)
    
    assert decrypted == original_token
    assert encrypted != original_token
    assert isinstance(encrypted, str)
    assert isinstance(decrypted, str)

def test_encrypt_empty_token():
    # Test with an empty token
    original_token = ""
    encrypted = encrypt_token(original_token)
    decrypted = decrypt_token(encrypted)
    
    assert decrypted == original_token
    assert encrypted != original_token

def test_encrypt_special_characters():
    # Test with special characters
    original_token = "!@#$%^&*()_+{}[]|\\:;\"'<>,.?/~`"
    encrypted = encrypt_token(original_token)
    decrypted = decrypt_token(encrypted)
    
    assert decrypted == original_token
    assert encrypted != original_token

def test_encrypt_long_token():
    # Test with a long token
    original_token = "a" * 1000
    encrypted = encrypt_token(original_token)
    decrypted = decrypt_token(encrypted)
    
    assert decrypted == original_token
    assert encrypted != original_token

def test_decrypt_invalid_token():
    # Test with invalid encrypted token
    with pytest.raises(Exception):
        decrypt_token("invalid_token") 