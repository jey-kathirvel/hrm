import base64, hashlib, hmac, os
ITERATIONS=600_000

def hash_password(password:str)->str:
    salt=os.urandom(16); digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"
def verify_password(password:str,encoded:str)->bool:
    try:
        algo,it,salt,digest=encoded.split('$',3)
        if algo!='pbkdf2_sha256': return False
        actual=hashlib.pbkdf2_hmac('sha256',password.encode(),base64.b64decode(salt),int(it))
        return hmac.compare_digest(actual,base64.b64decode(digest))
    except (ValueError,TypeError): return False
