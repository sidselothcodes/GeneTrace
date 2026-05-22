import os
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@db:5432/genetrace",
)

Base = declarative_base()


class QueryRecord(Base):
    __tablename__ = "query_records"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(64), nullable=False, index=True)
    brief = Column(Text, nullable=False)
    eval_score = Column(Float, nullable=False, default=0.0)
    clinvar_hits = Column(Integer, nullable=False, default=0)
    pubmed_hits = Column(Integer, nullable=False, default=0)
    uniprot_hits = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


engine = create_async_engine(DATABASE_URL, echo=False, future=True, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


async def save_query(
    session: AsyncSession,
    *,
    query: str,
    brief: str,
    eval_score: float,
    clinvar_hits: int,
    pubmed_hits: int,
    uniprot_hits: int,
) -> QueryRecord:
    record = QueryRecord(
        query=query,
        brief=brief,
        eval_score=eval_score,
        clinvar_hits=clinvar_hits,
        pubmed_hits=pubmed_hits,
        uniprot_hits=uniprot_hits,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def recent_queries(session: AsyncSession, limit: int = 20) -> list[QueryRecord]:
    stmt = select(QueryRecord).order_by(QueryRecord.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())
