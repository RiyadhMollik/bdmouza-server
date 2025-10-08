import jwt
from django.conf import settings

def encode_jwt(payload):
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')