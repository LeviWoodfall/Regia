"""
Email rules API routes for Regia.
CRUD operations for email auto-labeling and processing rules.
"""

from fastapi import APIRouter, HTTPException, Request
from typing import List, Dict, Any
from pydantic import BaseModel

router = APIRouter(prefix="/api/rules", tags=["rules"])


class RuleCreate(BaseModel):
    name: str
    conditions: List[Dict[str, str]]
    actions: List[Dict[str, str]]
    priority: int = 0
    enabled: bool = True


class RuleUpdate(BaseModel):
    name: str = None
    conditions: List[Dict[str, str]] = None
    actions: List[Dict[str, str]] = None
    priority: int = None
    enabled: bool = None


def _get_engine(request: Request):
    from app.main import app_state
    return app_state.get("rules_engine")


@router.get("")
async def list_rules(request: Request):
    """List all email rules."""
    engine = _get_engine(request)
    if not engine:
        return {"rules": []}
    rules = engine.get_rules()
    return {"rules": rules}


@router.post("")
async def create_rule(data: RuleCreate, request: Request):
    """Create a new email rule."""
    engine = _get_engine(request)
    if not engine:
        raise HTTPException(503, "Rules engine not initialized")

    rule_id = engine.create_rule(
        name=data.name,
        conditions=data.conditions,
        actions=data.actions,
        priority=data.priority,
        enabled=data.enabled,
    )
    return {"rule_id": rule_id, "message": "Rule created"}


@router.put("/{rule_id}")
async def update_rule(rule_id: int, data: RuleUpdate, request: Request):
    """Update an existing email rule."""
    engine = _get_engine(request)
    if not engine:
        raise HTTPException(503, "Rules engine not initialized")

    kwargs = {}
    if data.name is not None:
        kwargs["name"] = data.name
    if data.conditions is not None:
        kwargs["conditions"] = data.conditions
    if data.actions is not None:
        kwargs["actions"] = data.actions
    if data.priority is not None:
        kwargs["priority"] = data.priority
    if data.enabled is not None:
        kwargs["enabled"] = 1 if data.enabled else 0

    success = engine.update_rule(rule_id, **kwargs)
    if not success:
        raise HTTPException(400, "No updates provided")
    return {"message": "Rule updated"}


@router.delete("/{rule_id}")
async def delete_rule(rule_id: int, request: Request):
    """Delete an email rule."""
    engine = _get_engine(request)
    if not engine:
        raise HTTPException(503, "Rules engine not initialized")

    engine.delete_rule(rule_id)
    return {"message": "Rule deleted"}


@router.get("/fields")
async def list_fields():
    """List available condition fields and operators."""
    from app.rules.engine import CONDITION_FIELDS, OPERATORS, ACTION_TYPES
    return {
        "fields": [{"id": k, "label": v} for k, v in CONDITION_FIELDS.items()],
        "operators": list(OPERATORS.keys()),
        "action_types": [{"id": k, "label": v} for k, v in ACTION_TYPES.items()],
    }


@router.post("/test")
async def test_rules(request: Request):
    """Test rules against a sample email (for debugging)."""
    engine = _get_engine(request)
    if not engine:
        raise HTTPException(503, "Rules engine not initialized")

    body = await request.json()
    actions = engine.evaluate(body)
    return {"matched_actions": actions}
