from enum import Enum

from pydantic import BaseModel


class ThemeEnum(str, Enum):
    teal = "teal"
    midnight = "midnight"


class UserThemeSchema(BaseModel):
    theme: ThemeEnum
