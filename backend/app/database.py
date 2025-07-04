from prisma import Prisma
import asyncio
from typing import Optional

# Global Prisma client instance
prisma_client: Optional[Prisma] = None

async def get_prisma() -> Prisma:
    """Get the global Prisma client instance."""
    global prisma_client
    if prisma_client is None:
        prisma_client = Prisma()
        await prisma_client.connect()
    return prisma_client

async def disconnect_prisma():
    """Disconnect the Prisma client."""
    global prisma_client
    if prisma_client is not None:
        await prisma_client.disconnect()
        prisma_client = None

# Dependency for FastAPI
async def get_db():
    """FastAPI dependency to get database connection."""
    return await get_prisma()