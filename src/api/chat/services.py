from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.chat.schemas import GetDirectChatsSchema, GetMessageSchema
from src.models import Chat, ChatType, Message, ReadStatus, User


async def create_direct_chat(db_session: AsyncSession, *, initiator_user: User, recipient_user: User) -> Chat:
    # TODO: Make it an atomic transaction
    chat = Chat(chat_type=ChatType.DIRECT)
    chat.users.append(initiator_user)
    chat.users.append(recipient_user)
    db_session.add(chat)
    await db_session.flush()
    # make empty read statuses for both users last_read_message_id = 0
    initiator_read_status = ReadStatus(chat_id=chat.id, user_id=initiator_user.id, last_read_message_id=0)
    recipient_read_status = ReadStatus(chat_id=chat.id, user_id=recipient_user.id, last_read_message_id=0)
    db_session.add_all([initiator_read_status, recipient_read_status])
    await db_session.commit()

    return chat


async def get_direct_chat_by_users(
    db_session: AsyncSession, *, initiator_user: User, recipient_user: User
) -> Chat | None:
    query = select(Chat).where(
        and_(
            Chat.chat_type == ChatType.DIRECT, Chat.users.contains(initiator_user), Chat.users.contains(recipient_user)
        )
    )

    result = await db_session.execute(query)
    chat: Chat | None = result.scalar_one_or_none()

    return chat


async def get_chat_by_guid(db_session: AsyncSession, *, chat_guid: UUID) -> Chat | None:
    query = (
        select(Chat)
        .where(Chat.guid == chat_guid)
        .options(selectinload(Chat.messages), selectinload(Chat.users), selectinload(Chat.read_statuses))
    )
    result = await db_session.execute(query)
    chat: Chat | None = result.scalar_one_or_none()

    return chat


async def get_user_direct_chat_by_guid(
    db_session: AsyncSession, *, current_user: User, direct_chat_guid: UUID
) -> Chat | None:
    query = (
        select(Chat)
        .where(
            and_(
                Chat.is_active.is_(True),
                Chat.users.contains(current_user),
                Chat.guid == direct_chat_guid,
                Chat.chat_type == ChatType.DIRECT,
            )
        )
        .options(selectinload(Chat.users))
    )
    result = await db_session.execute(query)
    chat: Chat | None = result.scalar_one_or_none()

    return chat


async def get_user_by_guid(db_session: AsyncSession, *, user_guid: UUID) -> User | None:
    query = select(User).where(User.guid == user_guid)
    result = await db_session.execute(query)
    user: User | None = result.scalar_one_or_none()

    return user


async def get_user_direct_chats(db_session: AsyncSession, *, current_user: User) -> list[Chat]:
    query = (
        select(Chat)
        .where(
            and_(
                Chat.users.contains(current_user),
                Chat.is_active.is_(True),
                Chat.chat_type == ChatType.DIRECT,
            )
        )
        .options(selectinload(Chat.users), selectinload(Chat.read_statuses))
    )
    result = await db_session.execute(query)

    chats: list[Chat] = result.scalars().all()

    return chats


async def get_chat_messages(
    db_session: AsyncSession, *, user_id: int, chat: Chat, size: int
) -> tuple[list[Chat], bool, Message | None]:
    query = (
        select(Message)
        .where(and_(Message.chat_id == chat.id, Message.is_active.is_(True)))
        .order_by(Message.created_at.desc())
        .limit(size + 1)
        .options(selectinload(Message.user), selectinload(Message.chat))
    )
    result = await db_session.execute(query)
    messages: list[Message] = result.scalars().all()
    # check if there are more messages
    has_more_messages = len(messages) > size
    messages = messages[:size]

    # assuming only two read statuses
    for read_status in chat.read_statuses:
        if read_status.user_id == user_id:
            my_last_read_message_id = read_status.last_read_message_id

    last_read_message = await db_session.get(Message, my_last_read_message_id)
    get_message_schemas = [
        GetMessageSchema(
            message_guid=message.guid,
            content=message.content,
            created_at=message.created_at,
            chat_guid=message.chat.guid,
            user_guid=message.user.guid,
            is_read=message.id <= my_last_read_message_id,
        )
        for message in messages
    ]

    return get_message_schemas, has_more_messages, last_read_message


async def get_active_message_by_guid_and_chat(
    db_session: AsyncSession, *, chat_id: int, message_guid: UUID
) -> Message | None:
    query = select(Message).where(
        and_(Message.guid == message_guid, Message.is_active.is_(True), Message.chat_id == chat_id)
    )

    result = await db_session.execute(query)
    message: Message | None = result.scalar_one_or_none()

    return message


async def get_older_chat_messages(
    db_session: AsyncSession,
    *,
    chat: Chat,
    user_id: int,
    limit: int = 10,
    created_at: datetime,
) -> tuple[list[Message], bool]:
    query = (
        select(Message)
        .where(
            and_(
                Message.chat_id == chat.id,
                Message.is_active.is_(True),
                Message.created_at < created_at,
            )
        )
        .order_by(Message.created_at.desc())
        .limit(limit + 1)  # Fetch limit + 1 messages
        .options(selectinload(Message.user), selectinload(Message.chat))
    )

    result = await db_session.execute(query)
    older_messages: list[Message] = result.scalars().all()

    # Determine if there are more messages
    has_more_messages = len(older_messages) > limit
    older_messages = older_messages[:limit]

    # assuming only two read statuses
    for read_status in chat.read_statuses:
        if read_status.user_id == user_id:
            my_last_read_message_id = read_status.last_read_message_id
        else:
            other_last_read_message_id = read_status.last_read_message_id

    get_message_schemas = [
        GetMessageSchema(
            message_guid=message.guid,
            content=message.content,
            created_at=message.created_at,
            chat_guid=message.chat.guid,
            user_guid=message.user.guid,
            is_read=message.id <= other_last_read_message_id,
            is_new=message.id > my_last_read_message_id,
        )
        for message in older_messages
    ]

    # Return the first 'limit' messages and a flag indicating if there are more
    return get_message_schemas, has_more_messages


async def add_read_status_to_chat(db_session: AsyncSession, *, current_user: User, chat: Chat) -> tuple[bool, int]:
    has_new_messages: bool = False
    new_messages_count: int

    # assuming chat has two read statuses
    for read_status in chat.read_statuses:
        # own read status -> for new messages
        if read_status.user_id == current_user.id:
            own_last_read_message_id = read_status.last_read_message_id
    # get all user's active messages that have smaller last_read_message_id
    new_messages_query = select(func.count()).where(
        and_(
            Message.user_id != current_user.id,
            Message.id > own_last_read_message_id,
            Message.is_active.is_(True),
            Message.chat_id == chat.id,
        )
    )
    result = await db_session.execute(new_messages_query)
    new_messages_count: int = result.scalar_one_or_none()
    if new_messages_count:
        has_new_messages = True

    return GetDirectChatsSchema(
        chat_guid=chat.guid,
        chat_type=chat.chat_type,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        users=chat.users,
        has_new_messages=has_new_messages,
        new_messages_count=new_messages_count,
    )
