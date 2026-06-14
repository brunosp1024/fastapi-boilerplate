from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.core.utils.cache import cache
from app.db.base import async_get_db
from app.schemas.post_dto import PostCreate, PostRead, PostUpdate
from app.services.post_service import PostService

router = APIRouter(tags=["posts"])


@router.post("/post", response_model=PostRead, status_code=201)
async def create_post(
    post: PostCreate,
    current_user: Annotated[Any, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> PostRead:

    post_service = PostService(db)
    return await post_service.create_post(post, current_user.id)


@router.get("/{username}/posts", response_model=list[PostRead])
async def read_posts(
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 10,
) -> list[PostRead]:
    post_service = PostService(db)
    posts = await post_service.read_posts(username, page, items_per_page)

    return [PostRead.model_validate(post) for post in posts]


@router.get("/{username}/post/{id}", response_model=PostRead)
@cache(key_prefix="{username}_post_cache", resource_id_name="id")
async def read_post(
    request: Request,
    username: str,
    id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    post_service = PostService(db)
    db_post = await post_service.read_post(username, id)

    return PostRead.model_validate(db_post).model_dump()


@router.patch("/{username}/post/{id}")
@cache(
    "{username}_post_cache",
    resource_id_name="id",
    pattern_to_invalidate_extra=["{username}_posts:*"],
)
async def patch_post(
    request: Request,
    username: str,
    id: UUID,
    values: PostUpdate,
    current_user: Annotated[Any, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, str]:
    post_service = PostService(db)
    await post_service.patch_post(username, id, values, current_user.id)
    return {"message": "Post updated"}


@router.delete("/{username}/post/{id}")
@cache(
    "{username}_post_cache",
    resource_id_name="id",
    to_invalidate_extra={"{username}_posts": "{username}"},
)
async def erase_post(
    request: Request,
    username: str,
    id: UUID,
    current_user: Annotated[Any, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, str]:
    post_service = PostService(db)
    await post_service.erase_post(username, id, current_user.id)

    return {"message": "Post deleted"}


@router.delete("/{username}/db_post/{id}")
@cache(
    "{username}_post_cache",
    resource_id_name="id",
    to_invalidate_extra={"{username}_posts": "{username}"},
)
async def erase_db_post(
    request: Request,
    username: str,
    id: UUID,
    current_user: Annotated[Any, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, str]:
    post_service = PostService(db)
    await post_service.erase_db_post(username, id, current_user.role)
    return {"message": "Post deleted from the database"}
