import base64
import hashlib
from datetime import datetime
from Crypto.Hash import SHA256
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from ..config import settings


def ensure_keypair() -> None:
    settings.key_dir.mkdir(parents=True, exist_ok=True)
    if settings.rsa_private_key_path.exists() and settings.rsa_public_key_path.exists():
        return
    key = RSA.generate(2048)
    private_key = key.export_key()
    public_key = key.publickey().export_key()
    settings.rsa_private_key_path.write_bytes(private_key)
    settings.rsa_public_key_path.write_bytes(public_key)


def load_private_key() -> RSA.RsaKey:
    return RSA.import_key(settings.rsa_private_key_path.read_bytes())


def load_public_key() -> RSA.RsaKey:
    return RSA.import_key(settings.rsa_public_key_path.read_bytes())


def rsa_encrypt_sm4_key(sm4_key: bytes) -> str:
    cipher = PKCS1_OAEP.new(load_public_key(), hashAlgo=SHA256)
    encrypted = cipher.encrypt(sm4_key)
    return base64.b64encode(encrypted).decode("utf-8")


def rsa_decrypt_sm4_key(token_b64: str) -> bytes:
    cipher = PKCS1_OAEP.new(load_private_key(), hashAlgo=SHA256)
    encrypted = base64.b64decode(token_b64)
    return cipher.decrypt(encrypted)


_SM4_SBOX = [
    0xD6, 0x90, 0xE9, 0xFE, 0xCC, 0xE1, 0x3D, 0xB7, 0x16, 0xB6, 0x14, 0xC2, 0x28, 0xFB, 0x2C, 0x05,
    0x2B, 0x67, 0x9A, 0x76, 0x2A, 0xBE, 0x04, 0xC3, 0xAA, 0x44, 0x13, 0x26, 0x49, 0x86, 0x06, 0x99,
    0x9C, 0x42, 0x50, 0xF4, 0x91, 0xEF, 0x98, 0x7A, 0x33, 0x54, 0x0B, 0x43, 0xED, 0xCF, 0xAC, 0x62,
    0xE4, 0xB3, 0x1C, 0xA9, 0xC9, 0x08, 0xE8, 0x95, 0x80, 0xDF, 0x94, 0xFA, 0x75, 0x8F, 0x3F, 0xA6,
    0x47, 0x07, 0xA7, 0xFC, 0xF3, 0x73, 0x17, 0xBA, 0x83, 0x59, 0x3C, 0x19, 0xE6, 0x85, 0x4F, 0xA8,
    0x68, 0x6B, 0x81, 0xB2, 0x71, 0x64, 0xDA, 0x8B, 0xF8, 0xEB, 0x0F, 0x4B, 0x70, 0x56, 0x9D, 0x35,
    0x1E, 0x24, 0x0E, 0x5E, 0x63, 0x58, 0xD1, 0xA2, 0x25, 0x22, 0x7C, 0x3B, 0x01, 0x21, 0x78, 0x87,
    0xD4, 0x00, 0x46, 0x57, 0x9F, 0xD3, 0x27, 0x52, 0x4C, 0x36, 0x02, 0xE7, 0xA0, 0xC4, 0xC8, 0x9E,
    0xEA, 0xBF, 0x8A, 0xD2, 0x40, 0xC7, 0x38, 0xB5, 0xA3, 0xF7, 0xF2, 0xCE, 0xF9, 0x61, 0x15, 0xA1,
    0xE0, 0xAE, 0x5D, 0xA4, 0x9B, 0x34, 0x1A, 0x55, 0xAD, 0x93, 0x32, 0x30, 0xF5, 0x8C, 0xB1, 0xE3,
    0x1D, 0xF6, 0xE2, 0x2E, 0x82, 0x66, 0xCA, 0x60, 0xC0, 0x29, 0x23, 0xAB, 0x0D, 0x53, 0x4E, 0x6F,
    0xD5, 0xDB, 0x37, 0x45, 0xDE, 0xFD, 0x8E, 0x2F, 0x03, 0xFF, 0x6A, 0x72, 0x6D, 0x6C, 0x5B, 0x51,
    0x8D, 0x1B, 0xAF, 0x92, 0xBB, 0xDD, 0xBC, 0x7F, 0x11, 0xD9, 0x5C, 0x41, 0x1F, 0x10, 0x5A, 0xD8,
    0x0A, 0xC1, 0x31, 0x88, 0xA5, 0xCD, 0x7B, 0xBD, 0x2D, 0x74, 0xD0, 0x12, 0xB8, 0xE5, 0xB4, 0xB0,
    0x89, 0x69, 0x97, 0x4A, 0x0C, 0x96, 0x77, 0x7E, 0x65, 0xB9, 0xF1, 0x09, 0xC5, 0x6E, 0xC6, 0x84,
    0x18, 0xF0, 0x7D, 0xEC, 0x3A, 0xDC, 0x4D, 0x20, 0x79, 0xEE, 0x5F, 0x3E, 0xD7, 0xCB, 0x39, 0x48,
]

_SM4_FK = [0xA3B1BAC6, 0x56AA3350, 0x677D9197, 0xB27022DC]

_SM4_CK = [
    0x00070E15, 0x1C232A31, 0x383F464D, 0x545B6269, 0x70777E85, 0x8C939AA1, 0xA8AFB6BD, 0xC4CBD2D9,
    0xE0E7EEF5, 0xFC030A11, 0x181F262D, 0x343B4249, 0x50575E65, 0x6C737A81, 0x888F969D, 0xA4ABB2B9,
    0xC0C7CED5, 0xDCE3EAF1, 0xF8FF060D, 0x141B2229, 0x30373E45, 0x4C535A61, 0x686F767D, 0x848B9299,
    0xA0A7AEB5, 0xBCC3CAD1, 0xD8DFE6ED, 0xF4FB0209, 0x10171E25, 0x2C333A41, 0x484F565D, 0x646B7279,
]


def _rotl32(x: int, n: int) -> int:
    n &= 31
    return ((x << n) & 0xFFFFFFFF) | ((x & 0xFFFFFFFF) >> (32 - n))


def _sm4_tau(a: int) -> int:
    b0 = _SM4_SBOX[(a >> 24) & 0xFF]
    b1 = _SM4_SBOX[(a >> 16) & 0xFF]
    b2 = _SM4_SBOX[(a >> 8) & 0xFF]
    b3 = _SM4_SBOX[a & 0xFF]
    return (b0 << 24) | (b1 << 16) | (b2 << 8) | b3


def _sm4_l(b: int) -> int:
    return b ^ _rotl32(b, 2) ^ _rotl32(b, 10) ^ _rotl32(b, 18) ^ _rotl32(b, 24)


def _sm4_l_key(b: int) -> int:
    return b ^ _rotl32(b, 13) ^ _rotl32(b, 23)


def _sm4_t(x: int) -> int:
    return _sm4_l(_sm4_tau(x))


def _sm4_t_key(x: int) -> int:
    return _sm4_l_key(_sm4_tau(x))


def _sm4_round_keys(key: bytes) -> list[int]:
    if len(key) != 16:
        raise ValueError("sm4_key 必须为 16 字节")
    mk = [int.from_bytes(key[i:i + 4], "big") for i in range(0, 16, 4)]
    k = [mk[i] ^ _SM4_FK[i] for i in range(4)]
    rk: list[int] = []
    for i in range(32):
        t = k[i + 1] ^ k[i + 2] ^ k[i + 3] ^ _SM4_CK[i]
        k.append(k[i] ^ _sm4_t_key(t))
        rk.append(k[i + 4] & 0xFFFFFFFF)
    return rk


def _sm4_crypt_block(block16: bytes, rk: list[int]) -> bytes:
    if len(block16) != 16:
        raise ValueError("block 必须为 16 字节")
    x = [int.from_bytes(block16[i:i + 4], "big") for i in range(0, 16, 4)]
    for i in range(32):
        t = x[i + 1] ^ x[i + 2] ^ x[i + 3] ^ rk[i]
        x.append(x[i] ^ _sm4_t(t))
    out = [x[35], x[34], x[33], x[32]]
    return b"".join(v.to_bytes(4, "big") for v in out)


def _inc32(counter_block: bytes) -> bytes:
    if len(counter_block) != 16:
        raise ValueError("counter_block 必须为 16 字节")
    prefix = counter_block[:12]
    ctr = int.from_bytes(counter_block[12:], "big")
    ctr = (ctr + 1) & 0xFFFFFFFF
    return prefix + ctr.to_bytes(4, "big")


def _xor_bytes(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b, strict=True))


def _gcm_gf_mul(x: int, y: int) -> int:
    # GF(2^128) 乘法，按 NIST SP800-38D 的位序（MSB first）实现
    r = 0xE1000000000000000000000000000000
    z = 0
    v = x
    for i in range(128):
        if (y >> (127 - i)) & 1:
            z ^= v
        if v & 1:
            v = (v >> 1) ^ r
        else:
            v >>= 1
    return z & ((1 << 128) - 1)


def _gcm_ghash(h: int, ciphertext: bytes) -> int:
    y = 0
    for i in range(0, len(ciphertext), 16):
        block = ciphertext[i:i + 16]
        if len(block) < 16:
            block = block + b"\x00" * (16 - len(block))
        y = _gcm_gf_mul(y ^ int.from_bytes(block, "big"), h)
    len_block = (0).to_bytes(8, "big") + (len(ciphertext) * 8).to_bytes(8, "big")
    y = _gcm_gf_mul(y ^ int.from_bytes(len_block, "big"), h)
    return y


def sm4_gcm_encrypt(plaintext: bytes, sm4_key: bytes) -> str:
    # 说明：pycryptodome 默认不提供 SM4，这里使用纯 Python 实现 SM4 + GCM。
    # 目标是保证演示项目可运行且加密链路行为可复现（非高性能实现）。
    rk = _sm4_round_keys(sm4_key)
    nonce = get_random_bytes(12)
    j0 = nonce + b"\x00\x00\x00\x01"
    counter = _inc32(j0)
    ciphertext = b""
    for i in range(0, len(plaintext), 16):
        block = plaintext[i:i + 16]
        stream = _sm4_crypt_block(counter, rk)
        counter = _inc32(counter)
        if len(block) < 16:
            stream = stream[: len(block)]
        ciphertext += _xor_bytes(block, stream)
    h = int.from_bytes(_sm4_crypt_block(b"\x00" * 16, rk), "big")
    s = _gcm_ghash(h, ciphertext)
    tag = _xor_bytes(_sm4_crypt_block(j0, rk), s.to_bytes(16, "big"))
    payload = nonce + tag + ciphertext
    return base64.b64encode(payload).decode("utf-8")


def sm4_gcm_decrypt(ciphertext_b64: str, sm4_key: bytes) -> bytes:
    rk = _sm4_round_keys(sm4_key)
    raw = base64.b64decode(ciphertext_b64)
    nonce = raw[:12]
    tag = raw[12:28]
    ciphertext = raw[28:]
    j0 = nonce + b"\x00\x00\x00\x01"
    h = int.from_bytes(_sm4_crypt_block(b"\x00" * 16, rk), "big")
    s = _gcm_ghash(h, ciphertext)
    expected_tag = _xor_bytes(_sm4_crypt_block(j0, rk), s.to_bytes(16, "big"))
    if expected_tag != tag:
        raise ValueError("GCM 标签校验失败")
    counter = _inc32(j0)
    plaintext = b""
    for i in range(0, len(ciphertext), 16):
        block = ciphertext[i:i + 16]
        stream = _sm4_crypt_block(counter, rk)
        counter = _inc32(counter)
        if len(block) < 16:
            stream = stream[: len(block)]
        plaintext += _xor_bytes(block, stream)
    return plaintext


def generate_sm4_key() -> bytes:
    return get_random_bytes(16)


def sha256_sign(bus_id: str, cipher: str, timestamp: int, appsecret: str) -> str:
    raw = f"{bus_id}_{cipher}_{timestamp}_{appsecret}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def now_utc() -> datetime:
    return datetime.utcnow()
