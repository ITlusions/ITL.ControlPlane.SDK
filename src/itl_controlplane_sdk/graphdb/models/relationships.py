"""
Graph Relationship type for ITL ControlPlane SDK.

Relationships represent connections between nodes in the resource graph.
"""
from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime
import uuid

from .enums import RelationshipType


@dataclass
class GraphRelationship:
    """Relationship between two graph nodes."""
    id: str
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    properties: Dict[str, Any] = field(default_factory=dict)
    created_time: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
