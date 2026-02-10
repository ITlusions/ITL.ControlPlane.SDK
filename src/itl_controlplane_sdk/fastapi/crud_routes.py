"""
CRUD Route Factory for resource providers.

Generates standard POST / GET-list / GET-one / DELETE endpoints for a
resource type, eliminating the ~60 lines of boilerplate that every
simple resource router repeats.

For resources that need custom logic (e.g. subscriptions with UUID
generation, or resource groups with subscription scoping), write your
own router and skip this factory.

Example::

    from itl_controlplane_sdk.fastapi.crud_routes import create_crud_routes
    from itl_controlplane_sdk.core import CreateLocationRequest, LocationResponse

    create_crud_routes(
        app=app,
        provider=provider,
        resource_type="locations",
        request_model=CreateLocationRequest,
        response_model=LocationResponse,
        tag="Locations",
    )
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional, Type

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)


def create_crud_routes(
    app: FastAPI,
    provider: Any,
    resource_type: str,
    request_model: Type[BaseModel],
    response_model: Type[BaseModel],
    *,
    tag: Optional[str] = None,
    path_prefix: str = "",
    type_label: Optional[str] = None,
) -> None:
    """
    Register standard CRUD routes (POST, GET-list, GET-one, DELETE) for
    a resource type on a FastAPI app.

    Args:
        app: The FastAPI application.
        provider: A resource provider instance with ``create_or_update_resource``,
            ``list_resources``, ``get_resource``, and ``delete_resource`` methods.
        resource_type: Internal resource type name (e.g. "locations").
        request_model: Pydantic model for POST request body.
        response_model: Pydantic model for single-resource responses.
        tag: OpenAPI tag (defaults to capitalized ``resource_type``).
        path_prefix: Optional URL prefix (e.g. "/subscriptions/{sub_id}").
        type_label: Display label for the resource type (defaults to
            ``resource_type``). Used in error messages and log output.
    """
    tag = tag or resource_type.capitalize()
    type_label = type_label or resource_type
    base_path = f"{path_prefix}/{resource_type}"

    # We need to use a closure to capture the request_model as a proper
    # type annotation for FastAPI's dependency injection.
    def _make_create(req_model, res_model):
        async def _create(request: req_model) -> res_model:  # type: ignore[valid-type]
            try:
                response = await provider.create_or_update_resource(request)
                return {
                    "id": response.id,
                    "name": response.name,
                    "type": type_label,
                    "properties": getattr(request, "body", None) or {},
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.error("Error creating %s: %s", type_label, e)
                raise HTTPException(status_code=500, detail=str(e))
        _create.__name__ = f"create_{resource_type}"
        _create.__qualname__ = f"create_{resource_type}"
        return _create

    app.post(
        base_path,
        response_model=response_model,
        summary=f"Create {tag}",
        tags=[tag],
    )(_make_create(request_model, response_model))

    @app.get(
        base_path,
        summary=f"List {tag}",
        tags=[tag],
    )
    async def list_resources():
        try:
            response = await provider.list_resources(resource_type)
            resources = [
                {
                    "id": r.id,
                    "name": r.name,
                    "type": type_label,
                    "properties": r.properties or {},
                }
                for r in response.value
            ]
            return {"resources": resources, "count": len(resources)}
        except Exception as e:
            logger.error("Error listing %s: %s", type_label, e)
            raise HTTPException(status_code=500, detail=str(e))

    list_resources.__name__ = f"list_{resource_type}"
    list_resources.__qualname__ = f"list_{resource_type}"

    @app.get(
        f"{base_path}/{{resource_name}}",
        response_model=response_model,
        summary=f"Get {tag}",
        tags=[tag],
    )
    async def get_resource(resource_name: str):
        try:
            response = await provider.get_resource(resource_type, resource_name)
            if response.properties and response.properties.get("error"):
                raise HTTPException(
                    status_code=404, detail=response.properties["error"]
                )
            return response
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error getting %s: %s", type_label, e)
            raise HTTPException(status_code=500, detail=str(e))

    get_resource.__name__ = f"get_{resource_type}_item"
    get_resource.__qualname__ = f"get_{resource_type}_item"

    @app.delete(
        f"{base_path}/{{resource_name}}",
        summary=f"Delete {tag}",
        tags=[tag],
    )
    async def delete_resource(resource_name: str):
        try:
            response = await provider.delete_resource(resource_type, resource_name)
            if response.properties and response.properties.get("error"):
                raise HTTPException(
                    status_code=404, detail=response.properties["error"]
                )
            return {
                "message": f"{tag} {resource_name} deleted successfully",
                "resource_id": response.id,
                "deleted_at": datetime.now(timezone.utc).isoformat(),
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error deleting %s: %s", type_label, e)
            raise HTTPException(status_code=500, detail=str(e))

    delete_resource.__name__ = f"delete_{resource_type}_item"
    delete_resource.__qualname__ = f"delete_{resource_type}_item"
