import json
import logging
import os
from typing import Any, Optional, Type, TypeVar

import asyncpg
import redis as redis_lib
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import SQLModel, Session, select
from sqlalchemy import create_engine

from src.constants.config import NeonConfig

load_dotenv()


logger = logging.getLogger(__name__)

T = TypeVar("T", bound=SQLModel)


class SQLModelValidation:

    @staticmethod
    def validate(database_url: str):
        try:
            engine = create_engine(
                database_url,
                echo=False,
                pool_pre_ping=True,
            )

            with Session(engine) as session:
                session.exec(select(1))

            logger.info("Connected to PostgreSQL successfully.")

            return engine

        except SQLAlchemyError as e:
            logger.exception("Database connection failed.")
            raise e


class RedisValidation:

    @staticmethod
    def validate(redis_url: str) -> redis_lib.Redis:
        try:
            client = redis_lib.from_url(redis_url, decode_responses=True)
            client.ping()
            logger.info("Connected to Redis at %s", redis_url)
            return client
        except Exception as e:
            logger.error("Redis connection failed: %s", e)
            raise

class SQLModelServices:
    def __init__(self, database_url: str, model: Type[T]):
        self.database_url = database_url
        self.model = model
        self.engine = None

    def connect(self):
        if self.engine is None:
            self.engine = SQLModelValidation.validate(self.database_url)
        return self.engine

    def create(self, **kwargs):
        self.connect()
        obj = self.model(**kwargs)
        with Session(self.engine) as session:
            session.add(obj)
            session.commit()
            session.refresh(obj)
        return obj

    def get(self, id):
        self.connect()
        with Session(self.engine) as session:
            return session.get(self.model, id)

    def get_all(self):
        self.connect()
        with Session(self.engine) as session:
            return session.exec(select(self.model)).all()

    def filter(self, *conditions):
        self.connect()
        with Session(self.engine) as session:
            stmt = select(self.model).where(*conditions)
            return session.exec(stmt).all()

    def first(self, *conditions):
        self.connect()
        with Session(self.engine) as session:
            stmt = select(self.model).where(*conditions)
            return session.exec(stmt).first()

    def update(self, id, **kwargs):
        self.connect()
        with Session(self.engine) as session:
            obj = session.get(self.model, id)
            if obj is None:
                return None
            for key, value in kwargs.items():
                setattr(obj, key, value)
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return obj

    def delete(self, id):
        self.connect()
        with Session(self.engine) as session:
            obj = session.get(self.model, id)
            if obj is None:
                return False
            session.delete(obj)
            session.commit()
            return True

    def disconnect(self):
        if self.engine:
            self.engine.dispose()
            self.engine = None
            logger.info("Database connection closed.")


class RedisServices:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.client: Optional[redis_lib.Redis] = None
        self._initialized = False

    def connect(self) -> redis_lib.Redis:
        if not self._initialized:
            self.client = RedisValidation.validate(self.redis_url)
            self._initialized = True
        return self.client

    def set_json(self, key: str, data: dict, ttl: Optional[int] = None) -> None:
        self.connect()
        self.client.set(key, json.dumps(data))
        if ttl is not None:
            self.client.expire(key, ttl)

    def get_json(self, key: str) -> Optional[dict]:
        self.connect()
        data = self.client.get(key)
        if data is not None:
            return json.loads(data)
        return None

    def append_to_array(self, key: str, array_field: str, item: dict, ttl: Optional[int] = None) -> None:
        self.connect()
        data = self.get_json(key)
        if data is None:
            data = {}
        if array_field not in data:
            data[array_field] = []
        data[array_field].append(item)
        self.set_json(key, data, ttl)

    def delete(self, key: str) -> None:
        self.connect()
        self.client.delete(key)

    def disconnect(self) -> None:
        if self.client is not None:
            self.client.close()
            self._initialized = False
            self.client = None
            logger.info("Disconnected from Redis")
