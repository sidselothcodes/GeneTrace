from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.fetcher import fetch_all
from app.agents.synthesizer import compute_eval_score, synthesize
from app.database import QueryRecord, get_session, recent_queries, save_query
from app.models.schemas import HistoryItem, SourceResult, TraceRequest, TraceResponse

router = APIRouter()


@router.post("/trace", response_model=TraceResponse)
async def trace(req: TraceRequest, session: AsyncSession = Depends(get_session)) -> TraceResponse:
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="query must not be empty")

    sources = await fetch_all(query)
    brief = await synthesize(query, sources)
    score = compute_eval_score(brief, sources)

    by_src = {s["source"]: s for s in sources}
    record = await save_query(
        session,
        query=query,
        brief=brief,
        eval_score=score,
        clinvar_hits=by_src.get("clinvar", {}).get("hits", 0),
        pubmed_hits=by_src.get("pubmed", {}).get("hits", 0),
        uniprot_hits=by_src.get("uniprot", {}).get("hits", 0),
    )

    return TraceResponse(
        query=query,
        brief=brief,
        eval_score=score,
        sources=[SourceResult(**s) for s in sources],
        created_at=record.created_at or datetime.now(timezone.utc),
    )


@router.get("/history", response_model=list[HistoryItem])
async def history(session: AsyncSession = Depends(get_session)) -> list[HistoryItem]:
    records = await recent_queries(session, limit=20)
    return [HistoryItem.model_validate(r) for r in records]


@router.delete("/history/{record_id}")
async def delete_history_item(
    record_id: int, session: AsyncSession = Depends(get_session)
) -> dict[str, int | str]:
    record = await session.get(QueryRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="history item not found")
    await session.delete(record)
    await session.commit()
    return {"status": "deleted", "id": record_id}
