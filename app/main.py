from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.auth import router as auth_router

app = FastAPI()
app.include_router(auth_router)

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