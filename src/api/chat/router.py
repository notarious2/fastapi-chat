import json
from typing import Annotated
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.chat.schemas import (
    CreateDirectChatSchema,
    DisplayDirectChatSchema,
    GetDirectChatsSchema,
    GetMessagesSchema,
    GetOldMessagesSchema,
)
from src.api.chat.services import (
    add_read_status_to_chat,
    create_direct_chat,
    get_active_message_by_guid_and_chat,
    get_chat_by_guid,
    get_chat_messages,
    get_direct_chat_by_users,
    get_older_chat_messages,
    get_user_by_guid,
    get_user_direct_chat_by_guid,
    get_user_direct_chats,
)
from src.config import settings
from src.database import get_async_session
from src.dependencies import get_cache, get_current_user
from src.models import Chat, Message, User

chat_router = APIRouter(tags=["Chat Management"])


# TODO: not used, do I need it?
@chat_router.get("/chat/direct/{direct_chat_guid}/", summary="Get a direct chat")
async def get_direct_chat_view(
    direct_chat_guid: UUID,
    db_session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
    cache: aioredis.Redis = Depends(get_cache),
):
    cache_key = f"get_direct_chat_{direct_chat_guid}"

    # return cached direct chat if key exists
    if cached_direct_chat := await cache.get(cache_key):
        return json.loads(cached_direct_chat)

    chat: Chat | None = await get_user_direct_chat_by_guid(
        db_session, current_user=current_user, direct_chat_guid=direct_chat_guid
    )

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Direct chat with provided guid does not exist"
        )

    response = DisplayDirectChatSchema.model_validate(chat, from_attributes=True)

    # Store the chat in the cache with a TTL
    await cache.set(cache_key, response.model_dump_json(), ex=settings.REDIS_CACHE_EXPIRATION_SECONDS)

    return response


@chat_router.post("/chat/direct/", summary="Create a direct chat", response_model=DisplayDirectChatSchema)
async def create_direct_chat_view(
    bob_emily_chat_schema: CreateDirectChatSchema,
    db_session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    # check if another user (recipient) exists
    recipient_user_guid = bob_emily_chat_schema.recipient_user_guid
    recipient_user: User | None = await get_user_by_guid(db_session, user_guid=recipient_user_guid)

    # TODO: must check that recipient user is not the same as initiator
    if not recipient_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="There is no recipient user with provided guid"
        )

    # check if chat already exists
    if await get_direct_chat_by_users(db_session, current_user=current_user, recipient_user=recipient_user):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Chat already exists")

    # Check if the data is already in the cache
    chat: Chat = await create_direct_chat(db_session, initiator_user=current_user, recipient_user=recipient_user)

    return chat


# applies to both direct and group chats
# TODO: Find all path where to nullify the keys
@chat_router.get("/chat/{chat_guid}/messages/", summary="Get user's chat messages")
async def get_user_messages_in_chat(
    chat_guid: UUID,
    size: Annotated[int | None, Query(gt=0, lt=200)] = 20,
    db_session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
    cache: aioredis.Redis = Depends(get_cache),
):
    cache_key = f"messages_{size}_{chat_guid}"

    # return cached chat messages if key exists
    if cached_chat_messages := await cache.get(cache_key):
        print("cache used")
        return json.loads(cached_chat_messages)

    chat: Chat | None = await get_chat_by_guid(db_session, chat_guid=chat_guid)

    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat with provided guid does not exist")

    if current_user not in chat.users:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You don't have access to this chat")

    messages, has_more_messages, last_read_message = await get_chat_messages(
        db_session, user_id=current_user.id, chat=chat, size=size
    )
    response = GetMessagesSchema(
        messages=messages,
        has_more_messages=has_more_messages,
    )
    if last_read_message:
        response.last_read_message = last_read_message

    # Store the chat in the cache with a TTL
    await cache.set(cache_key, response.model_dump_json(), ex=settings.REDIS_CACHE_EXPIRATION_SECONDS)

    return response


# TODO: when to clear the cache?
@chat_router.get("/chats/direct/", summary="Get user's direct chats", response_model=list[GetDirectChatsSchema])
async def get_user_chats_view(
    db_session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    chats: list[Chat] = await get_user_direct_chats(db_session, current_user=current_user)

    return [await add_read_status_to_chat(db_session, current_user=current_user, chat=chat) for chat in chats]


@chat_router.get(
    "/chat/{chat_guid}/messages/old/{message_guid}/",
    summary="Get user's historical chat messages",
)
async def get_older_messages(
    chat_guid: UUID,
    message_guid: UUID,
    limit: Annotated[int | None, Query(gt=0, lt=200)] = 10,
    db_session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    chat: Chat | None = await get_chat_by_guid(db_session, chat_guid=chat_guid)

    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat with provided guid is not found")

    if current_user not in chat.users:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You don't have access to this chat")

    message: Message | None = await get_active_message_by_guid_and_chat(
        db_session, chat_id=chat.id, message_guid=message_guid
    )

    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message with provided guid is not found")

    old_messages, has_more_messages = await get_older_chat_messages(
        db_session, chat=chat, user_id=current_user.id, created_at=message.created_at, limit=limit
    )
    return GetOldMessagesSchema(messages=old_messages, has_more_messages=has_more_messages)
