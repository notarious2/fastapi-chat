from datetime import datetime

from pydantic import UUID4, BaseModel, EmailStr, RootModel


class GetUserSchema(BaseModel):
    guid: UUID4
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    created_at: datetime


class GetUsersResponseSchema(RootModel[GetUserSchema]):
    root: list[GetUserSchema]
