import logging
from typing import Any, Optional

import asyncpg
from dotenv import load_dotenv

from src.constants.config import NeonConfig

logger = logging.getLogger(__name__)
load_dotenv()


class NeonPool:
    _pool: Optional[asyncpg.Pool] = None

    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        if cls._pool is None:
            dsn = NeonConfig.database_url
            if not dsn:
                raise RuntimeError("NEON_DATABASE_URL is not set")
            cls._pool = await asyncpg.create_pool(
                dsn=dsn,
                min_size=1,
                max_size=5,
            )
            logger.info("Neon pool created")
        return cls._pool

    @classmethod
    async def close(cls):
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
            logger.info("Neon pool closed")


class NeonServices:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        self.pool = await NeonPool.get_pool()
        async with self.pool.acquire() as conn:
            await conn.execute("SELECT 1")
        logger.info("Neon connection verified")
        return self.pool

    async def disconnect(self):
        await NeonPool.close()

    async def create(self, table: str, data: dict) -> dict:
        if not self.pool:
            self.pool = await NeonPool.get_pool()
        columns = ", ".join(data.keys())
        placeholders = ", ".join(f"${i+1}" for i in range(len(data)))
        values = list(data.values())
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING *",
                *values,
            )
            return dict(row)

    async def read(self, table: str, where: Optional[dict] = None, order_by: Optional[str] = None, limit: Optional[int] = None) -> list[dict]:
        if not self.pool:
            self.pool = await NeonPool.get_pool()
        query = f"SELECT * FROM {table}"
        params: list[Any] = []
        if where:
            conditions = " AND ".join(
                f"{k} = ${i+1}" for i, k in enumerate(where.keys())
            )
            query += f" WHERE {conditions}"
            params = list(where.values())
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit:
            query += f" LIMIT {limit}"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    async def read_one(self, table: str, where: dict) -> Optional[dict]:
        if not self.pool:
            self.pool = await NeonPool.get_pool()
        conditions = " AND ".join(
            f"{k} = ${i+1}" for i, k in enumerate(where.keys())
        )
        params = list(where.values())
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT * FROM {table} WHERE {conditions} LIMIT 1",
                *params,
            )
            return dict(row) if row else None

    async def update(self, table: str, where: dict, data: dict) -> Optional[dict]:
        if not self.pool:
            self.pool = await NeonPool.get_pool()
        set_clause = ", ".join(
            f"{k} = ${i+1}" for i, k in enumerate(data.keys())
        )
        where_clause = " AND ".join(
            f"{k} = ${len(data) + i + 1}" for i, k in enumerate(where.keys())
        )
        params = list(data.values()) + list(where.values())
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"UPDATE {table} SET {set_clause} WHERE {where_clause} RETURNING *",
                *params,
            )
            return dict(row) if row else None

    async def delete(self, table: str, where: dict) -> Optional[dict]:
        if not self.pool:
            self.pool = await NeonPool.get_pool()
        conditions = " AND ".join(
            f"{k} = ${i+1}" for i, k in enumerate(where.keys())
        )
        params = list(where.values())
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"DELETE FROM {table} WHERE {conditions} RETURNING *",
                *params,
            )
            return dict(row) if row else None

    async def fetch(self, query: str, *args: Any) -> list[dict]:
        if not self.pool:
            self.pool = await NeonPool.get_pool()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(r) for r in rows]

    async def fetch_one(self, query: str, *args: Any) -> Optional[dict]:
        if not self.pool:
            self.pool = await NeonPool.get_pool()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def execute(self, query: str, *args: Any) -> str:
        if not self.pool:
            self.pool = await NeonPool.get_pool()
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
