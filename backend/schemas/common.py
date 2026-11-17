"""NETVIGIE — Schémas communs."""
from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, description="Numéro de page (1-indexé)")
    page_size: int = Field(20, ge=1, le=200, description="Taille de page (max 200)")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    services: dict


class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None