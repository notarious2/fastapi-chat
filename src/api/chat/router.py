from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi_pagination import Page, paginate
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.chat.schemas import CreateDirectChatSchema, DisplayDirectChatSchema, GetChatsSchema, MessageSchema
from src.api.chat.services import (
    create_bob_emily_chat,
    get_bob_emily_chat,
    get_chat_by_guid,
    get_user_by_guid,
    get_user_chats,
    send_message_to_chat,
)
from src.database import get_async_session
from src.dependencies import get_current_user
from src.models import Chat, User

# from fastapi_pagination.ext.sqlalchemy import paginate

chat_router = APIRouter(tags=["Chat Management"])


@chat_router.post("/chat/direct/", summary="Get or create a direct chat", response_model=DisplayDirectChatSchema)
async def get_or_create_bob_emily_chat(
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

    # return chat if already exists
    chat: Chat | None = await get_bob_emily_chat(db_session, initiator_user=current_user, recipient_user=recipient_user)

    if not chat:
        chat: Chat = await create_bob_emily_chat(db_session, initiator_user=current_user, recipient_user=recipient_user)

    return chat


@chat_router.post("/chat/{chat_guid}/message/", summary="Send a message")  #
async def send_message(
    chat_guid: UUID,
    content: Annotated[str, Body(max_length=5000, embed=True)],
    db_session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    chat: Chat | None = await get_chat_by_guid(db_session, chat_guid=chat_guid)

    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat with provided guid is not found")

    await send_message_to_chat(db_session, content=content, user_id=current_user.id, chat_id=chat.id)

    return "Message has been sent"


@chat_router.get(
    "/chat/{chat_guid}/messages/", summary="Get user's chat messages", response_model=Page[MessageSchema]
)  #
async def get_user_messages_in_chat(
    chat_guid: UUID,
    db_session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    chat: Chat | None = await get_chat_by_guid(db_session, chat_guid=chat_guid)

    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat with provided guid does not exist")

    if current_user not in chat.users:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You don't have access to this chat")

    # TODO: standard paginate/chat.messages fetches all messages, probably should messages separately
    return paginate(chat.messages)


@chat_router.get("/chats/", summary="Get user's chats", response_model=list[GetChatsSchema])  #
async def get_user_chats_view(
    db_session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    chats: list[Chat] = await get_user_chats(db_session, current_user=current_user)

    return chats
