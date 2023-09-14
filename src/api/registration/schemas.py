from pydantic import BaseModel, EmailStr, Extra


class UserRegisterSchema(BaseModel):
    email: EmailStr
    username: str
    password: str
    first_name: str
    last_name: str

    class Config:
        extra = Extra.forbid
