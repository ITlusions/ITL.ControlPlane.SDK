"""
Base repository pattern for Analytics resources

Provides async CRUD operations for UUID-based analytics models.
"""

import logging
from abc import ABC
from typing import Generic, List, Optional, Type, TypeVar
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")

logger = logging.getLogger(__name__)


class BaseAnalyticsRepository(ABC, Generic[T]):
    """
    Base repository for analytics resources with UUID IDs.
    
    All analytics entities must have:
    - id: UUID (primary key)
    - subscription_id: str
    - resource_group: str
    - name: str
    
    Provides common CRUD operations and subscription-scoped queries.
    """

    def __init__(self, session: AsyncSession, model_class: Type[T]):
        """
        Initialize with async session and ORM model class.
        
        Args:
            session: SQLAlchemy AsyncSession
            model_class: ORM model class (e.g., Notebook, SparkCluster)
        """
        self.session = session
        self.model_class = model_class
        self.logger = logging.getLogger(f"{__name__}.{model_class.__name__}")

    async def create(self, data: dict) -> T:
        """
        Create and persist a new entity.
        
        Args:
            data: Dictionary of model fields
            
        Returns:
            Created entity instance
        """
        entity = self.model_class(**data)
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        self.logger.info(
            f"Created {self.model_class.__name__}",
            extra={
                "entity_id": str(entity.id),
                "subscription": getattr(entity, "subscription_id", None),
                "resource_group": getattr(entity, "resource_group", None),
                "name": getattr(entity, "name", None),
            }
        )
        return entity

    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """Get entity by UUID"""
        stmt = select(self.model_class).where(self.model_class.id == entity_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(
        self, subscription_id: str, resource_group: str, name: str
    ) -> Optional[T]:
        """Get entity by ARM path (subscription + resource_group + name)"""
        stmt = select(self.model_class).where(
            (self.model_class.subscription_id == subscription_id)
            & (self.model_class.resource_group == resource_group)
            & (self.model_class.name == name)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_subscription(
        self, subscription_id: str, resource_group: str
    ) -> List[T]:
        """List all entities in a resource group"""
        stmt = select(self.model_class).where(
            (self.model_class.subscription_id == subscription_id)
            & (self.model_class.resource_group == resource_group)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_owner(self, owner_id: str) -> List[T]:
        """List all entities owned by a user (requires owner_id field)"""
        if not hasattr(self.model_class, "owner_id"):
            raise NotImplementedError(
                f"{self.model_class.__name__} does not have owner_id field"
            )
        stmt = select(self.model_class).where(self.model_class.owner_id == owner_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update(self, entity_id: UUID, data: dict) -> Optional[T]:
        """
        Update entity with provided fields.
        
        Only updates fields that exist on the model.
        
        Args:
            entity_id: UUID of entity to update
            data: Dictionary of fields to update
            
        Returns:
            Updated entity or None if not found
        """
        entity = await self.get_by_id(entity_id)
        if not entity:
            return None

        for key, value in data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)

        await self.session.commit()
        await self.session.refresh(entity)
        self.logger.info(
            f"Updated {self.model_class.__name__}",
            extra={"entity_id": str(entity_id)}
        )
        return entity

    async def delete(self, entity_id: UUID) -> bool:
        """
        Delete entity by ID.
        
        Args:
            entity_id: UUID of entity to delete
            
        Returns:
            True if deleted, False if not found
        """
        entity = await self.get_by_id(entity_id)
        if not entity:
            return False

        await self.session.delete(entity)
        await self.session.commit()
        self.logger.info(
            f"Deleted {self.model_class.__name__}",
            extra={"entity_id": str(entity_id)}
        )
        return True
