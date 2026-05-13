from __future__ import annotations
from enum import Enum

class AnswerStatus(str, Enum):
    SKIPPED = '__prefer_not_to_answer__'

SKIPPED_ANSWER = AnswerStatus.SKIPPED.value



import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


SUPPORTED_TYPES = {
    "text",
    "textarea",
    "integer",
    "decimal",
    "date",
    "month",
    "year",
    "single_select",
    "multiselect",
    "boolean",
    "slider_nrs_0_10",
    "body_area_percent",
    "region_select",
    "repeatable_misdiagnosis",
    "info_text",
    "subsection",
}

class OptionSchema(BaseModel):
    value: str | int | float
    label: str

class QuestionSchema(BaseModel):
    id: str
    export_name: str | None = None
    type: str
    label: str
    description: str | None = None
    required: bool = True
    options: list[OptionSchema] | None = None
    min: float | None = None
    max: float | None = None
    allow_unknown: bool = False
    help: str | None = None
    checkbox_label: str | None = None
    anchors: dict[str, str] | None = None

    def model_post_init(self, __context):
        if not self.export_name and self.type not in {"info_text", "subsection"}:
            self.export_name = self.id
        if self.type not in SUPPORTED_TYPES:
            raise ValueError(f"Unsupported question type {self.type} for {self.id}.")
        if self.type in {"single_select", "multiselect"}:
            if not self.options:
                raise ValueError(f"{self.id} needs options.")

class ModuleSchema(BaseModel):
    id: str
    title: str
    description: str | None = None
    why_we_ask: str | None = None
    order: int = 0
    derived_view: str | None = None
    questions: list[QuestionSchema]

class QuestionnaireMetadataSchema(BaseModel):
    id: str
    version: str
    title: str
    description: str | None = None
    consent_version: str

class QuestionnaireSchema(BaseModel):
    questionnaire: QuestionnaireMetadataSchema
    modules: list[ModuleSchema]

@dataclass(frozen=True)
class QuestionnaireBundle:
    schema: QuestionnaireSchema
    source_path: Path
    yaml_text: str
    sha256: str

    @property
    def questionnaire_id(self) -> str:
        return self.schema.questionnaire.id

    @property
    def version(self) -> str:
        return self.schema.questionnaire.version

    @property
    def title(self) -> str:
        return self.schema.questionnaire.title

    @property
    def consent_version(self) -> str:
        return self.schema.questionnaire.consent_version

    @property
    def questions(self) -> list[QuestionSchema]:
        items: list[QuestionSchema] = []
        for module in sorted(self.schema.modules, key=lambda item: item.order):
            for question in module.questions:
                items.append(question)
        return items

def load_questionnaire(path: str | Path) -> QuestionnaireBundle:
    source_path = Path(path)
    yaml_text = source_path.read_text(encoding="utf-8")
    body = yaml.safe_load(yaml_text)
    
    schema = QuestionnaireSchema.model_validate(body)
    
    return QuestionnaireBundle(
        schema=schema,
        source_path=source_path,
        yaml_text=yaml_text,
        sha256=hashlib.sha256(yaml_text.encode("utf-8")).hexdigest(),
    )
