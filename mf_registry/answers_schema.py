from typing import Any, Literal
import logging
from pydantic import BaseModel, create_model, ValidationError
from mf_registry.questionnaire_schema import QuestionnaireSchema, AnswerStatus

class Region(BaseModel):
    province: str | None = None
    city: str | None = None

class MisdiagnosisEvent(BaseModel):
    visit_month: str | None = None
    care_region: Region | None = None
    hospital_level: str | None = None
    misdiagnosis: str | None = None
    misdiagnosis_other: str | None = None

_model_cache = {}

def build_answers_model(schema: QuestionnaireSchema) -> type[BaseModel]:
    cache_key = f"{schema.questionnaire.id}_{schema.questionnaire.version}"
    if cache_key in _model_cache:
        return _model_cache[cache_key]
        
    fields = {}
    for mod in schema.modules:
        for q in mod.questions:
            if q.type in ["info_text", "subsection"]:
                continue
                
            py_type = Any
            if q.type in ["text", "textarea", "single_select", "month", "date"]:
                py_type = str | None
            elif q.type in ["year", "integer", "slider_nrs_0_10", "body_area_percent"]:
                py_type = int | None
            elif q.type == "decimal":
                py_type = float | None
            elif q.type == "boolean":
                py_type = bool | None
            elif q.type == "multiselect":
                py_type = list[str | int | float] | None
            elif q.type == "repeatable_misdiagnosis":
                py_type = list[MisdiagnosisEvent] | None
            elif q.type == "region_select":
                py_type = Region | None
            
            # Using union with Literal to allow explicit skipping
            fields[q.id] = (py_type | Literal[AnswerStatus.SKIPPED.value], None)
            
    model = create_model('DynamicAnswersModel', **fields)
    _model_cache[cache_key] = model
    return model

def validate_answers(schema: QuestionnaireSchema, answers: dict[str, Any]) -> dict[str, Any]:
    Model = build_answers_model(schema)
    try:
        validated = Model.model_validate(answers)
        return validated.model_dump()
    except ValidationError as e:
        logging.error(f"Pydantic validation failed for answers: {e}")
        # Fallback: return raw answers so we don't lose patient data in production
        return answers
