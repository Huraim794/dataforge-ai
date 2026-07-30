from dataforge.backend.app.core.security import (
    hash_password,
    verify_password,
    generate_api_key,
    hash_api_key,
)


class TestSecurity:
    def test_hash_and_verify_password(self):
        password = "test-password-123"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong-password", hashed) is False

    def test_hash_api_key(self):
        key = "test-api-key"
        hashed = hash_api_key(key)
        assert hashed != key
        assert len(hashed) == 64
        assert hash_api_key(key) == hashed

    def test_generate_api_key_format(self):
        key = generate_api_key()
        assert key.startswith("df_")
        assert len(key) > 30
