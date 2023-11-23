from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import BaseModel


class AdminUser(BaseModel):
    __tablename__ = "admin_user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    username: Mapped[str] = mapped_column(String(150), unique=True)
    password: Mapped[str] = mapped_column(String(128))
