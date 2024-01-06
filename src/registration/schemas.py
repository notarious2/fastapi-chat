from fastapi import File, Form, UploadFile
from pydantic import EmailStr


class UserRegisterSchema:
    def __init__(
        self,
        email: EmailStr = Form(...),
        username: str = Form(max_length=150),
        password: str = Form(min_length=6, max_length=128),
        first_name: str = Form(max_length=150),
        last_name: str = Form(max_length=150),
        uploaded_image: UploadFile = File(None, media_type="image/jpeg"),
    ):
        self.email = email
        self.username = username
        self.password = password
        self.first_name = first_name
        self.last_name = last_name
        self.uploaded_image = uploaded_image
