from pydantic import UUID4, BaseModel, EmailStr, Field


class GoogleLoginSchema(BaseModel):
    access_token: str


class UserLoginResponseSchema(BaseModel):
    guid: UUID4 = Field(..., serialization_alias="user_guid")
    username: str
    email: EmailStr
    first_name: str
    last_name: str

    class Config:
        from_attributes = True
