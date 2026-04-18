"""Pydantic request/response models for the web API."""

from __future__ import annotations

from pydantic import BaseModel


class TranscribeRequest(BaseModel):
    url: str
    provider: str | None = None
    language: str | None = None
    diarize: bool = False
    keep_media: bool = False
    output_format: str | None = None


class JobResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # pending, running, completed, failed
    events: list[dict]
    result: dict | None = None
    error: str | None = None


class ConfigUpdateRequest(BaseModel):
    provider: str | None = None
    language: str | None = None
    keep_media: bool | None = None
    output_format: str | None = None
    diarize: bool | None = None
    prompt_download: str | None = None
    local_file_media: str | None = None
    workspace_path: str | None = None
    local_model: str | None = None


class LocalSetupRequest(BaseModel):
    model: str


class ProviderTestRequest(BaseModel):
    name: str


class KeyUpdateRequest(BaseModel):
    provider_name: str
    api_key: str


class LanguageOption(BaseModel):
    code: str
    name: str


class ProviderLanguagesResponse(BaseModel):
    languages: list[LanguageOption]
    freeform: bool  # True for OpenRouter — the field accepts any text.
