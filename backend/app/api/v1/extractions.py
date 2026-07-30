from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import BaseModel, Field

from dataforge.backend.app.core.deps import (
    get_current_user,
    get_db,
    verify_project_access,
)
from dataforge.backend.app.extraction.ai_extractor import AIExtractor
from dataforge.backend.app.models.result import (
    ExtractionResult as ExtractionResultModel,
)

router = APIRouter()


class ExtractRequest(BaseModel):
    content: str = Field(..., description="The web content to extract from")
    url: Optional[str] = None
    title: Optional[str] = None
    schema: Optional[dict] = None
    prompt_template: Optional[str] = None
    fields: Optional[list[dict]] = None
    model: Optional[str] = None
    temperature: Optional[float] = None


class ExtractResponse(BaseModel):
    success: bool
    data: Any = None
    error: Optional[str] = None
    processing_time_ms: Optional[int] = None
    model_used: Optional[str] = None
    tokens_used: int = 0
    confidence_score: Optional[float] = None


class ClassifyRequest(BaseModel):
    content: str
    categories: list[str]
    url: Optional[str] = None


@router.post("/extract", response_model=ExtractResponse)
async def extract_data(
    request: ExtractRequest,
    current_user: dict = Depends(get_current_user),
) -> Any:
    extractor = AIExtractor()
    result = await extractor.extract(
        content=request.content,
        schema=request.schema,
        prompt_template=request.prompt_template,
        fields=request.fields,
        url=request.url,
        title=request.title,
        model=request.model,
        temperature=request.temperature,
    )
    return result


@router.post("/classify")
async def classify_content(
    request: ClassifyRequest,
    current_user: dict = Depends(get_current_user),
) -> Any:
    extractor = AIExtractor()
    result = await extractor.classify(
        content=request.content,
        categories=request.categories,
        url=request.url,
    )
    return result


@router.post("/extract-contacts")
async def extract_contacts(
    content: str,
    current_user: dict = Depends(get_current_user),
) -> Any:
    extractor = AIExtractor()
    return await extractor.extract_contacts(content)


@router.post("/extract-table")
async def extract_table(
    content: str,
    table_selector: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
) -> Any:
    extractor = AIExtractor()
    return await extractor.extract_table(content, table_selector)


@router.get("/results/{result_id}")
async def get_extraction_result(
    result_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(
        select(ExtractionResultModel).where(ExtractionResultModel.id == result_id)
    )
    extraction = result.scalar_one_or_none()
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction result not found")
    if extraction.project_id:
        await verify_project_access(extraction.project_id, current_user["sub"], db)

    return {
        "id": extraction.id,
        "job_id": extraction.job_id,
        "extracted_data": extraction.extracted_data,
        "structured_output": extraction.structured_output,
        "confidence_score": extraction.confidence_score,
        "llm_provider": extraction.llm_provider,
        "llm_model": extraction.llm_model,
        "tokens_total": extraction.tokens_total,
        "cost_usd": extraction.cost_usd,
        "success": extraction.success,
        "processing_time_ms": extraction.processing_time_ms,
        "created_at": extraction.created_at,
    }
