from sqladmin import ModelView

from src.models import Chat, Message, ReadStatus, User


class ChatAdmin(ModelView, model=Chat):
    icon = "fa-solid fa-comments"
    column_list = [Chat.id, Chat.chat_type, Chat.users, Chat.guid, Chat.is_deleted, Chat.created_at]


class MessageAdmin(ModelView, model=Message):
    icon = "fas fa-commenting"
    column_list = [Message.id, Message.content, Message.user, Message.chat, Message.guid, Message.created_at]


class UserAdmin(ModelView, model=User):
    icon = "fa-solid fa-user"
    column_list = [User.id, User.email, User.username, User.guid, User.is_deleted, User.created_at]


class ReadStatusAdmin(ModelView, model=ReadStatus):
    icon = "fas fa-check-double"
    name_plural = "Read Statuses"
    column_list = [ReadStatus.id, ReadStatus.user, ReadStatus.chat]


admin_models = [UserAdmin, ChatAdmin, MessageAdmin, ReadStatusAdmin]
