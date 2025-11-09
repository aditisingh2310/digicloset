from fastapi import Request, HTTPException
import jwt

SECRET = "CHANGE_ME"

async def jwt_middleware(request: Request, call_next):
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        jwt.decode(token.split(" ")[1], SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    return await call_next(request)
