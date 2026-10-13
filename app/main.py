from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.auth import router as auth_router
from app.routes.bookmarks import router as bookmarks_router
from app.routes.comments import router as comments_router
from app.routes.likes import router as likes_router
from app.routes.notifications import router as notifications_router
from app.routes.posts import router as posts_router
from app.routes.social import router as social_router
from app.utils.useful_apis import router as useful_apis_router

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5173/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(posts_router)
app.include_router(social_router)
app.include_router(comments_router)
app.include_router(likes_router)
app.include_router(bookmarks_router)
app.include_router(notifications_router)
app.include_router(useful_apis_router)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/version")
def read_version():
    return {"version": "1.0.0"}


@app.get("/health/db")
async def check_database(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"database": "ok"}