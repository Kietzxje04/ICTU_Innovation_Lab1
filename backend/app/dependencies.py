from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from .agent_service import AgentService
from .database import get_session
from .services import ActionService, AssessmentService, ResolutionService


@lru_cache(maxsize=1)
def get_agent_service() -> AgentService:
    return AgentService()


def get_assessment_service(
    session: Session = Depends(get_session),
    agent: AgentService = Depends(get_agent_service),
) -> AssessmentService:
    return AssessmentService(session, agent)


def get_resolution_service(
    session: Session = Depends(get_session),
    assessments: AssessmentService = Depends(get_assessment_service),
) -> ResolutionService:
    return ResolutionService(session, assessments)


def get_action_service(
    session: Session = Depends(get_session),
    resolution: ResolutionService = Depends(get_resolution_service),
) -> ActionService:
    return ActionService(session, resolution)
