from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_current_user
from app.db.base import async_get_db
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.schemas.auth_dto import RefreshTokenRequest, TokenResponse
from app.schemas.user_dto import UserCreateDTO, UserResponse
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    user_data: UserCreateDTO, db: Annotated[AsyncSession, Depends(async_get_db)]
):
    """Register a new user."""
    user_service = UserService(db)
    try:
        user = await user_service.create_user(user_data)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/token", response_model=TokenResponse)
async def login(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """Login and get access token."""
    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    refresh_token = await AuthService.create_refresh_token(user.id, db)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",  # nosec
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    request: RefreshTokenRequest, db: Annotated[AsyncSession, Depends(async_get_db)]
):
    """Refresh access token using refresh token."""
    refresh_token_repo = RefreshTokenRepository(db)
    stored_token = await refresh_token_repo.get_by_token(request.refresh_token)

    if not stored_token or stored_token.revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    if stored_token.expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired"
        )

    user_service = UserService(db)
    user = await user_service.get_user_by_id(stored_token.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    new_access_token = create_access_token(data={"sub": user.email, "role": user.role})
    new_refresh_token = await AuthService.create_refresh_token(user.id, db)

    # Revoke old refresh token
    await refresh_token_repo.revoke(request.refresh_token)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",  # nosec
    )
