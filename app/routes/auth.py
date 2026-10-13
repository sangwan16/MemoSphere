from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.auth.security import (
    create_access_token,
    create_email_verification_token,
    create_refresh_token,
    get_email_verification_claims,
    get_current_user,
    get_user_id_from_refresh_token,
    password_hash,
)
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import (
    EmailRequest,
    AccountPrivacyUpdate,
    CurrentUserResponse,
    MessageResponse,
    RefreshTokenRequest,
    SignupRequest,
    TokenResponse,
    UsernameUpdate,
    VerifyEmailRequest,
)
from app.utils.email import send_verification_email

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    email = str(payload.email).lower()
    username = payload.username.strip().lower()
    existing_user = await db.scalar(select(User).where(User.email == email))
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="Email is already registered")
    existing_username = await db.scalar(select(User).where(User.username == username))
    if existing_username is not None:
        raise HTTPException(status_code=409, detail="Username is already taken")

    user = User(
        email=email,
        username=username,
        hashed_password=password_hash.hash(payload.password),
        is_email_verified=False,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username is already registered.",
        ) from error
    await db.refresh(user)

    verification_token = create_email_verification_token(user.id, user.email)
    try:
        await send_verification_email(user.email, verification_token)
    except Exception as error:
        logger.exception("Could not send verification email to %s", user.email)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account created, but the verification email could not be sent. Try again later.",
        ) from error

    return MessageResponse(message="Check your email for a verification link.")


@router.post("/verify-email", response_model=TokenResponse)
async def verify_email(
    payload: VerifyEmailRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    try:
        user_id, email = get_email_verification_claims(payload.token)
    except (InvalidTokenError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link is invalid or expired.",
        ) from None

    user = await db.get(User, user_id)
    if user is None or user.email != email or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link is invalid or expired.",
        )
    if user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified. Please log in.",
        )

    user.is_email_verified = True
    await db.commit()
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    payload: EmailRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    email = str(payload.email).lower()
    user = await db.scalar(select(User).where(User.email == email))
    if user is not None and user.is_active and not user.is_email_verified:
        token = create_email_verification_token(user.id, user.email)
        try:
            await send_verification_email(user.email, token)
        except Exception:
            logger.exception("Could not resend verification email to %s", user.email)

    return MessageResponse(
        message="If the account needs verification, a new link has been sent."
    )


@router.post("/token")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    email = form_data.username.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not password_hash.verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in.",
        )
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh")
async def refresh_access_token(
    payload: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    try:
        user_id = get_user_id_from_refresh_token(payload.refresh_token)
    except (InvalidTokenError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = await db.get(User, user_id)
    if user is None or not user.is_active or not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@router.get("/me")
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        is_active=current_user.is_active,
        is_email_verified=current_user.is_email_verified,
        is_public=current_user.is_public,
    )


@router.patch("/me", response_model=CurrentUserResponse)
async def update_current_user(
    payload: UsernameUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CurrentUserResponse:
    username = payload.username.strip().lower()
    existing_username = await db.scalar(
        select(User).where(User.username == username, User.id != current_user.id)
    )
    if existing_username is not None:
        raise HTTPException(status_code=409, detail="Username is already taken")

    current_user.username = username
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Username is already taken") from error
    await db.refresh(current_user)
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        is_active=current_user.is_active,
        is_email_verified=current_user.is_email_verified,
        is_public=current_user.is_public,
    )


@router.patch("/me/privacy", response_model=CurrentUserResponse)
async def update_account_privacy(
    payload: AccountPrivacyUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CurrentUserResponse:
    current_user.is_public = payload.is_public
    await db.commit()
    await db.refresh(current_user)
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        is_active=current_user.is_active,
        is_email_verified=current_user.is_email_verified,
        is_public=current_user.is_public,
    )