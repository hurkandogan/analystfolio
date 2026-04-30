from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# 1. Create Engine
engine = create_async_engine(settings.DATABASE_URL, echo=False)

# 2. Session Factory
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

# 3. Base Class for ORM Models
class Base(DeclarativeBase):
    pass

# 4. Dependency Injection
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session