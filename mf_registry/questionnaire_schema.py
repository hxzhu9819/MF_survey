from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


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
}


@dataclass(frozen=True)
class QuestionnaireBundle:
    body: dict[str, Any]
    source_path: Path
    yaml_text: str
    sha256: str

    @property
    def questionnaire_id(self) -> str:
        return str(self.body["questionnaire"]["id"])

    @property
    def version(self) -> str:
        return str(self.body["questionnaire"]["version"])

    @property
    def title(self) -> str:
        return str(self.body["questionnaire"]["title"])

    @property
    def consent_version(self) -> str:
        return str(self.body["questionnaire"]["consent_version"])

    @property
    def questions(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for module in sorted(self.body.get("modules", []), key=lambda item: item.get("order", 0)):
            for question in module.get("questions", []):
                items.append(question)
        return items


def load_questionnaire(path: str | Path) -> QuestionnaireBundle:
    source_path = Path(path)
    yaml_text = source_path.read_text(encoding="utf-8")
    body = yaml.safe_load(yaml_text)
    validate_questionnaire(body)
    return QuestionnaireBundle(
        body=body,
        source_path=source_path,
        yaml_text=yaml_text,
        sha256=hashlib.sha256(yaml_text.encode("utf-8")).hexdigest(),
    )


def validate_questionnaire(body: dict[str, Any]) -> None:
    if not isinstance(body, dict):
        raise ValueError("Questionnaire YAML must parse to an object.")

    questionnaire = body.get("questionnaire")
    if not isinstance(questionnaire, dict):
        raise ValueError("Missing questionnaire metadata.")

    for key in ("id", "version", "title", "consent_version"):
        if not questionnaire.get(key):
            raise ValueError(f"Missing questionnaire.{key}.")

    modules = body.get("modules")
    if not isinstance(modules, list) or not modules:
        raise ValueError("Questionnaire must contain at least one module.")

    question_ids: set[str] = set()
    export_names: set[str] = set()
    for module in modules:
        if not module.get("id") or not module.get("title"):
            raise ValueError("Every module needs id and title.")
        questions = module.get("questions")
        if not isinstance(questions, list):
            raise ValueError(f"Module {module.get('id')} needs questions list.")
        for question in questions:
            validate_question(question)
            question_id = question["id"]
            export_name = question["export_name"]
            if question_id in question_ids:
                raise ValueError(f"Duplicate question id: {question_id}")
            if export_name in export_names:
                raise ValueError(f"Duplicate export_name: {export_name}")
            question_ids.add(question_id)
            export_names.add(export_name)


def validate_question(question: dict[str, Any]) -> None:
    for key in ("id", "export_name", "type", "label"):
        if not question.get(key):
            raise ValueError(f"Question missing {key}: {question}")

    question_type = question["type"]
    if question_type not in SUPPORTED_TYPES:
        raise ValueError(f"Unsupported question type {question_type} for {question['id']}.")

    if question_type in {"single_select", "multiselect"}:
        options = question.get("options")
        if not isinstance(options, list) or not options:
            raise ValueError(f"{question['id']} needs options.")
        for option in options:
            if not isinstance(option, dict) or "value" not in option or "label" not in option:
                raise ValueError(f"{question['id']} has invalid option: {option}")
