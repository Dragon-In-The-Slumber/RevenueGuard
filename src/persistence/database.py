from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.config import settings
from src.persistence.models import Base

import urllib.parse as urlparse

db_url = settings.database_url
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

parsed = urlparse.urlparse(db_url)
query_params = urlparse.parse_qs(parsed.query)

if "sslmode" in query_params:
    query_params["ssl"] = query_params.pop("sslmode")

query_params.pop("channel_binding", None)

new_query = urlparse.urlencode(query_params, doseq=True)
db_url = parsed._replace(query=new_query).geturl()

engine = create_async_engine(db_url, echo=True)

async_session = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    async with engine.begin() as conn:
        # Create tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with async_session() as session:
        yield session
