"""Response models for MCP inspection endpoints."""

from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ToolPublic(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    title: str | None = None
    description: str | None = None
    input_schema: dict[str, object] | None = Field(
        default=None,
        serialization_alias="inputSchema",
        validation_alias=AliasChoices("inputSchema", "input_schema"),
    )


class ToolsListResponse(BaseModel):
    tools: list[ToolPublic]


class ResourcePublic(BaseModel):
    model_config = ConfigDict(extra="ignore")

    uri: str
    name: str | None = None
    title: str | None = None
    description: str | None = None
    mime_type: str | None = Field(
        default=None,
        serialization_alias="mimeType",
        validation_alias="mimeType",
    )
    size: int | None = None


class ResourcesListResponse(BaseModel):
    resources: list[ResourcePublic]


class ResourceTemplatePublic(BaseModel):
    model_config = ConfigDict(extra="ignore")

    uri_template: str = Field(
        serialization_alias="uriTemplate",
        validation_alias="uriTemplate",
    )
    name: str | None = None
    title: str | None = None
    description: str | None = None
    mime_type: str | None = Field(
        default=None,
        serialization_alias="mimeType",
        validation_alias="mimeType",
    )


class ResourceTemplatesListResponse(BaseModel):
    resource_templates: list[ResourceTemplatePublic]


class PromptArgumentPublic(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    description: str | None = None
    required: bool | None = None


class PromptPublic(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    title: str | None = None
    description: str | None = None
    arguments: list[PromptArgumentPublic] | None = None


class PromptsListResponse(BaseModel):
    prompts: list[PromptPublic]


class ResourceContentBlockPublic(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["text", "blob"]
    mime_type: str | None = Field(
        default=None,
        serialization_alias="mimeType",
        validation_alias="mimeType",
    )
    text: str | None = None
    blob: str | None = None


class ResourceReadResponse(BaseModel):
    uri: str
    contents: list[ResourceContentBlockPublic]
