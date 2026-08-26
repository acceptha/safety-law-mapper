"""Pydantic models mirroring schemas/*.schema.json."""

from __future__ import annotations

import datetime
from enum import Enum

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# Plain str with pattern check (not HttpUrl): keeps Korean URLs byte-identical
# so YAML -> model -> dict round-trips losslessly.
Url = Annotated[str, Field(pattern=r"^https?://")]


class LawType(str, Enum):
    ACT = "act"
    DECREE = "decree"
    RULE = "rule"
    NOTICE = "notice"


class WorkCategory(str, Enum):
    HOT_WORK = "hot-work"
    CONFINED_SPACE = "confined-space"
    WORK_AT_HEIGHT = "work-at-height"
    LIFTING = "lifting"
    EXCAVATION = "excavation"
    ELECTRICAL = "electrical"
    CHEMICAL_HANDLING = "chemical-handling"
    MACHINERY = "machinery"
    DEMOLITION = "demolition"
    TRANSPORT = "transport"


class ObligationType(str, Enum):
    GENERAL = "general"
    APPOINTMENT = "appointment"
    MEASUREMENT = "measurement"
    EDUCATION = "education"
    REPORT = "report"
    PERMIT = "permit"
    INSPECTION = "inspection"
    PROVISION = "provision"


class ObligationSubject(str, Enum):
    EMPLOYER = "employer"
    PRINCIPAL_CONTRACTOR = "principal-contractor"
    SUPERVISOR = "supervisor"
    WORKER = "worker"
    OWNER = "owner"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Law(_StrictModel):
    law_id: str
    name_ko: str
    name_short: str | None = None
    type: LawType
    administered_by: str
    source_url: Url


class Article(_StrictModel):
    article_ref: str
    article_title: str | None = None
    obligation_type: ObligationType
    obligation_subject: ObligationSubject | None = None
    summary_ko: str
    valid_from: datetime.date
    valid_until: datetime.date | None = None
    source_url: Url


class ApplicableLaw(_StrictModel):
    law_id: str
    articles: list[Article]


class WorkType(_StrictModel):
    name_ko: str
    category: WorkCategory
    keywords: list[str]


class Conditions(_StrictModel):
    min_employees: int | None = None
    max_employees: int | None = None
    substances: list[str] = Field(default_factory=list)
    equipment: list[str] = Field(default_factory=list)


class Reference(_StrictModel):
    title: str
    url: Url


class Mapping(_StrictModel):
    mapping_id: str
    work_type: WorkType
    conditions: Conditions = Field(default_factory=Conditions)
    applicable_laws: list[ApplicableLaw]
    references: list[Reference] = Field(default_factory=list)
    last_verified: datetime.date | None = None
    verified_by: str | None = None
