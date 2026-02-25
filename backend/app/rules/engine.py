"""
Email rules engine for Regia.
Evaluates user-defined rules against incoming emails for auto-labeling,
classification, folder routing, and other automated actions.
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional

from app.database import Database

logger = logging.getLogger("regia.rules")


# Supported condition fields
CONDITION_FIELDS = {
    "sender_email": "Sender email address",
    "sender_name": "Sender display name",
    "subject": "Email subject line",
    "body": "Email body text",
    "has_attachments": "Has attachments (true/false)",
    "attachment_name": "Attachment filename",
    "recipient": "Recipient email address",
}

# Supported operators
OPERATORS = {
    "contains": lambda val, target: target.lower() in val.lower(),
    "not_contains": lambda val, target: target.lower() not in val.lower(),
    "equals": lambda val, target: val.lower() == target.lower(),
    "not_equals": lambda val, target: val.lower() != target.lower(),
    "starts_with": lambda val, target: val.lower().startswith(target.lower()),
    "ends_with": lambda val, target: val.lower().endswith(target.lower()),
    "matches_regex": lambda val, target: bool(re.search(target, val, re.IGNORECASE)),
    "is_true": lambda val, target: str(val).lower() in ("1", "true", "yes"),
    "is_false": lambda val, target: str(val).lower() in ("0", "false", "no", ""),
}

# Supported actions
ACTION_TYPES = {
    "label": "Set classification label",
    "category": "Set document category",
    "tag": "Add a tag to the email",
    "priority": "Set priority (low, normal, high)",
    "move_to_folder": "Move to specific storage subfolder",
    "skip_processing": "Skip LLM processing",
    "auto_archive": "Auto-archive (mark as completed)",
    "flag": "Flag for manual review",
}


class EmailRulesEngine:
    """Evaluates email rules and applies matching actions."""

    def __init__(self, db: Database):
        self.db = db
        self._rules_cache: Optional[List[Dict]] = None
        self._cache_valid = False

    def invalidate_cache(self):
        """Invalidate the rules cache (call after CRUD operations)."""
        self._cache_valid = False
        self._rules_cache = None

    def get_rules(self) -> List[Dict]:
        """Get all rules, sorted by priority (highest first)."""
        if self._cache_valid and self._rules_cache is not None:
            return self._rules_cache

        rows = self.db.execute(
            "SELECT * FROM email_rules ORDER BY priority DESC, id ASC"
        )
        rules = []
        for row in rows:
            rule = dict(row)
            try:
                rule["conditions"] = json.loads(rule["conditions"]) if rule["conditions"] else []
                rule["actions"] = json.loads(rule["actions"]) if rule["actions"] else []
            except json.JSONDecodeError:
                rule["conditions"] = []
                rule["actions"] = []
            rules.append(rule)

        self._rules_cache = rules
        self._cache_valid = True
        return rules

    def create_rule(self, name: str, conditions: List[Dict], actions: List[Dict],
                    priority: int = 0, enabled: bool = True) -> int:
        """Create a new email rule. Returns the rule ID."""
        rule_id = self.db.execute_insert(
            """INSERT INTO email_rules (name, enabled, priority, conditions, actions)
               VALUES (?, ?, ?, ?, ?)""",
            (name, 1 if enabled else 0, priority,
             json.dumps(conditions), json.dumps(actions)),
        )
        self.invalidate_cache()
        logger.info(f"Created rule '{name}' (id={rule_id})")
        return rule_id

    def update_rule(self, rule_id: int, **kwargs) -> bool:
        """Update an existing rule."""
        updates = []
        params = []
        for key in ("name", "enabled", "priority"):
            if key in kwargs:
                updates.append(f"{key} = ?")
                params.append(kwargs[key])
        for key in ("conditions", "actions"):
            if key in kwargs:
                updates.append(f"{key} = ?")
                params.append(json.dumps(kwargs[key]))

        if not updates:
            return False

        updates.append("updated_at = datetime('now')")
        params.append(rule_id)

        self.db.execute(
            f"UPDATE email_rules SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        self.invalidate_cache()
        return True

    def delete_rule(self, rule_id: int) -> bool:
        """Delete an email rule."""
        self.db.execute("DELETE FROM email_rules WHERE id = ?", (rule_id,))
        self.invalidate_cache()
        return True

    def evaluate(self, email_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Evaluate all enabled rules against an email.
        Returns a list of actions to apply.
        
        email_data should contain:
            sender_email, sender_name, subject, body, has_attachments,
            attachment_names (list), recipient
        """
        rules = self.get_rules()
        all_actions = []

        for rule in rules:
            if not rule.get("enabled"):
                continue

            if self._matches(rule["conditions"], email_data):
                all_actions.extend(rule["actions"])
                # Increment match count
                self.db.execute(
                    "UPDATE email_rules SET match_count = match_count + 1 WHERE id = ?",
                    (rule["id"],),
                )
                logger.debug(f"Rule '{rule['name']}' matched email from {email_data.get('sender_email')}")

        return all_actions

    def _matches(self, conditions: List[Dict], email_data: Dict[str, Any]) -> bool:
        """Check if all conditions match the email data (AND logic)."""
        if not conditions:
            return False  # No conditions = never match

        for condition in conditions:
            field = condition.get("field", "")
            operator = condition.get("operator", "contains")
            target = condition.get("value", "")

            # Get the field value from email data
            if field == "attachment_name":
                # Check against all attachment names
                names = email_data.get("attachment_names", [])
                field_value = " ".join(names)
            elif field == "has_attachments":
                field_value = str(email_data.get("has_attachments", False))
            else:
                field_value = str(email_data.get(field, ""))

            # Apply operator
            op_func = OPERATORS.get(operator)
            if not op_func:
                logger.warning(f"Unknown operator: {operator}")
                return False

            if not op_func(field_value, target):
                return False  # AND logic — all must match

        return True

    def apply_actions(self, email_id: int, actions: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Apply rule actions to an email in the database.
        Returns summary of applied actions.
        """
        applied = {"labels": [], "categories": [], "tags": [], "flags": []}

        for action in actions:
            action_type = action.get("action", "")
            value = action.get("value", "")

            if action_type == "label":
                self.db.execute(
                    "UPDATE emails SET classification = ? WHERE id = ?",
                    (value, email_id),
                )
                applied["labels"].append(value)

            elif action_type == "category":
                # Apply to all documents of this email
                self.db.execute(
                    "UPDATE documents SET category = ? WHERE email_id = ?",
                    (value, email_id),
                )
                applied["categories"].append(value)

            elif action_type == "tag":
                # Store tags in classification field (append)
                rows = self.db.execute(
                    "SELECT classification FROM emails WHERE id = ?", (email_id,)
                )
                current = rows[0]["classification"] if rows else ""
                tags = set(current.split(",")) if current else set()
                tags.add(value)
                self.db.execute(
                    "UPDATE emails SET classification = ? WHERE id = ?",
                    (",".join(t for t in tags if t), email_id),
                )
                applied["tags"].append(value)

            elif action_type == "auto_archive":
                self.db.execute(
                    "UPDATE emails SET status = 'completed' WHERE id = ?",
                    (email_id,),
                )
                applied["flags"].append("archived")

            elif action_type == "flag":
                self.db.execute(
                    "UPDATE emails SET status = 'flagged' WHERE id = ?",
                    (email_id,),
                )
                applied["flags"].append("flagged")

            elif action_type == "priority":
                # Store in classification as prefix
                applied["flags"].append(f"priority:{value}")

        return applied


# === Default Rules (created on first run) ===

DEFAULT_RULES = [
    {
        "name": "Invoices from common providers",
        "priority": 10,
        "conditions": [
            {"field": "subject", "operator": "matches_regex", "value": r"invoice|factura|rechnung|billing|payment"}
        ],
        "actions": [
            {"action": "label", "value": "invoice"},
            {"action": "category", "value": "financial"},
        ],
    },
    {
        "name": "Receipts and confirmations",
        "priority": 8,
        "conditions": [
            {"field": "subject", "operator": "matches_regex", "value": r"receipt|order confirm|purchase confirm|your order"}
        ],
        "actions": [
            {"action": "label", "value": "receipt"},
            {"action": "category", "value": "financial"},
        ],
    },
    {
        "name": "Shipping and delivery",
        "priority": 7,
        "conditions": [
            {"field": "subject", "operator": "matches_regex", "value": r"shipped|tracking|delivery|dispatch|your package"}
        ],
        "actions": [
            {"action": "label", "value": "shipping"},
            {"action": "category", "value": "logistics"},
        ],
    },
    {
        "name": "Contracts and agreements",
        "priority": 9,
        "conditions": [
            {"field": "subject", "operator": "matches_regex", "value": r"contract|agreement|terms|sign|docusign|NDA"}
        ],
        "actions": [
            {"action": "label", "value": "contract"},
            {"action": "category", "value": "legal"},
        ],
    },
    {
        "name": "Newsletters and marketing",
        "priority": 3,
        "conditions": [
            {"field": "subject", "operator": "matches_regex", "value": r"unsubscribe|newsletter|weekly digest|monthly update"}
        ],
        "actions": [
            {"action": "label", "value": "newsletter"},
            {"action": "category", "value": "marketing"},
        ],
    },
]


def seed_default_rules(db: Database):
    """Create default rules if none exist."""
    rows = db.execute("SELECT COUNT(*) as c FROM email_rules")
    if rows[0]["c"] > 0:
        return  # Rules already exist

    engine = EmailRulesEngine(db)
    for rule in DEFAULT_RULES:
        engine.create_rule(
            name=rule["name"],
            conditions=rule["conditions"],
            actions=rule["actions"],
            priority=rule["priority"],
        )
    logger.info(f"Seeded {len(DEFAULT_RULES)} default email rules")
