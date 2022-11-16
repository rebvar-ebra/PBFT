from nacl.signing import SigningKey
from nacl.signing import VerifyKey
import hashlib

def generate_sign(chk_msg):
    signing_key = SigningKey.generate()

    signed_preprepare = signing_key.sign(str(chk_msg).encode())

    verify_key = signing_key.verify_key

    public_key = verify_key.encode()

    return signed_preprepare + (b'split') + public_key

def generate_verfiy(public_key,rece_msg):
    verify_key= VerifyKey(public_key)
    return verify_key.verify(rece_msg).decode()

def hashing_function(entity):
    h=hashlib.sha256
    h.update(str(entity).encode())
    return h.hexdisgest()