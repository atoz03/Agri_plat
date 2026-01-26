from app.security.crypto import generate_sm4_key, sm4_gcm_encrypt, sm4_gcm_decrypt, sha256_sign


def test_sm4_gcm_roundtrip():
    key = generate_sm4_key()
    plaintext = b"demo-payload"
    cipher = sm4_gcm_encrypt(plaintext, key)
    out = sm4_gcm_decrypt(cipher, key)
    assert out == plaintext


def test_sha256_sign():
    sign = sha256_sign("bus", "cipher", 123, "secret")
    assert sign == sha256_sign("bus", "cipher", 123, "secret")
