"""
CLI script for seeding the ControlPlane database.

Usage:
    python -m itl_controlplane_sdk.cli.seed all
    python -m itl_controlplane_sdk.cli.seed tenants
    python -m itl_controlplane_sdk.cli.seed locations
    python -m itl_controlplane_sdk.cli.seed management-groups
    python -m itl_controlplane_sdk.cli.seed subscriptions
    python -m itl_controlplane_sdk.cli.seed policies
    python -m itl_controlplane_sdk.cli.seed --help

Environment:
    DATABASE_URL: PostgreSQL connection string (default: postgresql+asyncpg://controlplane:controlplane@localhost:5432/controlplane)
"""

import asyncio
import logging
import sys
from typing import Optional
import uuid

import click
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from itl_controlplane_sdk.core.models.base.constants import DEFAULT_TENANT
from itl_controlplane_sdk.core.services.seed import (
    SeedService,
    DEFAULT_TENANT_UUID,
    seed_default_tenant,
    seed_locations,
    seed_default_management_groups,
    seed_default_policies,
    seed_default_subscriptions,
    seed_default_resource_groups,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default database URL
DEFAULT_DATABASE_URL = (
    "postgresql+asyncpg://controlplane:controlplane@localhost:5432/controlplane"
)


async def get_session(database_url: str) -> AsyncSession:
    """Create and return an async database session."""
    engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        return session


@click.group()
@click.option(
    "--database-url",
    envvar="DATABASE_URL",
    default=DEFAULT_DATABASE_URL,
    help="PostgreSQL connection string",
)
@click.option(
    "--tenant-id",
    default=DEFAULT_TENANT_UUID,
    help=f"Tenant ID to seed (default: {DEFAULT_TENANT_UUID})",
)
@click.pass_context
def cli(ctx, database_url: str, tenant_id: str):
    """Seed ControlPlane database with initial data."""
    ctx.ensure_object(dict)
    ctx.obj["database_url"] = database_url
    ctx.obj["tenant_id"] = tenant_id
    logger.info(f"Using database: {database_url}")
    logger.info(f"Using tenant: {tenant_id}")


@cli.command()
@click.pass_context
def all(ctx):
    """Seed all default data."""
    database_url = ctx.obj["database_url"]
    tenant_id = ctx.obj["tenant_id"]

    async def _seed():
        engine = create_async_engine(database_url, echo=False, future=True)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            results = await SeedService.seed_all(session, tenant_id)
            return results

    try:
        results = asyncio.run(_seed())
        click.echo("\n✓ All seeding completed successfully:")
        for category, result in results.items():
            click.echo(f"  {category}: {result}")
        sys.exit(0)
    except Exception as e:
        click.echo(f"✗ Seeding failed: {str(e)}", err=True)
        logger.exception("Seeding error")
        sys.exit(1)


@cli.command()
@click.pass_context
def tenants(ctx):
    """Seed default tenant."""
    database_url = ctx.obj["database_url"]

    async def _seed():
        engine = create_async_engine(database_url, echo=False, future=True)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            result = await SeedService.seed_default_tenant(session)
            return result

    try:
        result = asyncio.run(_seed())
        click.echo(f"✓ Tenants seeded: {result}")
        sys.exit(0)
    except Exception as e:
        click.echo(f"✗ Tenant seeding failed: {str(e)}", err=True)
        logger.exception("Seeding error")
        sys.exit(1)


@cli.command()
@click.pass_context
def locations(ctx):
    """Seed default locations."""
    database_url = ctx.obj["database_url"]

    async def _seed():
        engine = create_async_engine(database_url, echo=False, future=True)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            result = await SeedService.seed_locations(session)
            return result

    try:
        result = asyncio.run(_seed())
        click.echo(f"✓ Locations seeded: {result}")
        sys.exit(0)
    except Exception as e:
        click.echo(f"✗ Location seeding failed: {str(e)}", err=True)
        logger.exception("Seeding error")
        sys.exit(1)


@cli.command("management-groups")
@click.pass_context
def management_groups(ctx):
    """Seed default management groups."""
    database_url = ctx.obj["database_url"]
    tenant_id = ctx.obj["tenant_id"]

    async def _seed():
        engine = create_async_engine(database_url, echo=False, future=True)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            result = await SeedService.seed_default_management_groups(session, tenant_id)
            return result

    try:
        result = asyncio.run(_seed())
        click.echo(f"✓ Management groups seeded: {result}")
        sys.exit(0)
    except Exception as e:
        click.echo(f"✗ Management group seeding failed: {str(e)}", err=True)
        logger.exception("Seeding error")
        sys.exit(1)


@cli.command()
@click.pass_context
def policies(ctx):
    """Seed default policies."""
    database_url = ctx.obj["database_url"]
    tenant_id = ctx.obj["tenant_id"]

    async def _seed():
        engine = create_async_engine(database_url, echo=False, future=True)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            result = await SeedService.seed_default_policies(session, tenant_id)
            return result

    try:
        result = asyncio.run(_seed())
        click.echo(f"✓ Policies seeded: {result}")
        sys.exit(0)
    except Exception as e:
        click.echo(f"✗ Policy seeding failed: {str(e)}", err=True)
        logger.exception("Seeding error")
        sys.exit(1)


@cli.command()
@click.pass_context
def subscriptions(ctx):
    """Seed default ITLusions subscriptions."""
    database_url = ctx.obj["database_url"]
    tenant_id = ctx.obj["tenant_id"]

    async def _seed():
        engine = create_async_engine(database_url, echo=False, future=True)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            result = await SeedService.seed_default_subscriptions(session, tenant_id)
            return result

    try:
        result = asyncio.run(_seed())
        click.echo(f"✓ Subscriptions seeded: {result}")
        sys.exit(0)
    except Exception as e:
        click.echo(f"✗ Subscription seeding failed: {str(e)}", err=True)
        logger.exception("Seeding error")
        sys.exit(1)


@cli.command("resource-groups")
@click.pass_context
def resource_groups(ctx):
    """Seed default resource groups."""
    database_url = ctx.obj["database_url"]
    tenant_id = ctx.obj["tenant_id"]

    async def _seed():
        engine = create_async_engine(database_url, echo=False, future=True)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            result = await SeedService.seed_default_resource_groups(session, tenant_id)
            return result

    try:
        result = asyncio.run(_seed())
        click.echo(f"✓ Resource groups seeded: {result}")
        sys.exit(0)
    except Exception as e:
        click.echo(f"✗ Resource group seeding failed: {str(e)}", err=True)
        logger.exception("Seeding error")
        sys.exit(1)


@cli.command("audit-events")
@click.pass_context
def audit_events(ctx):
    """Seed audit events for existing resources."""
    database_url = ctx.obj["database_url"]
    tenant_id = ctx.obj["tenant_id"]

    async def _seed():
        engine = create_async_engine(database_url, echo=False, future=True)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            result = await SeedService.seed_audit_events(session, tenant_id)
            return result

    try:
        result = asyncio.run(_seed())
        click.echo(f"✓ Audit events seeded: {result}")
        sys.exit(0)
    except Exception as e:
        click.echo(f"✗ Audit event seeding failed: {str(e)}", err=True)
        logger.exception("Seeding error")
        sys.exit(1)


if __name__ == "__main__":
    cli(obj={})
