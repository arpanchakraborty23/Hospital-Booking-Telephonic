import json
import logging
import os
import time
from typing import Optional, Type, TypeVar

import redis as redis_lib
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import SQLModel, Session, select
from sqlalchemy import create_engine

from src.monitoring import observe_db, observe_redis

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
        self._table_name = model.__tablename__ if hasattr(model, '__tablename__') else model.__name__

    def connect(self):
        if self.engine is None:
            self.engine = SQLModelValidation.validate(self.database_url)
        return self.engine

    def create(self, **kwargs):
        _start = time.perf_counter()
        self.connect()
        obj = self.model(**kwargs)
        with Session(self.engine) as session:
            session.add(obj)
            session.commit()
            session.refresh(obj)
        observe_db("create", self._table_name, time.perf_counter() - _start)
        return obj

    def get(self, id):
        _start = time.perf_counter()
        self.connect()
        with Session(self.engine) as session:
            result = session.get(self.model, id)
        observe_db("get", self._table_name, time.perf_counter() - _start)
        return result

    def get_all(self):
        _start = time.perf_counter()
        self.connect()
        with Session(self.engine) as session:
            result = session.exec(select(self.model)).all()
        observe_db("read", self._table_name, time.perf_counter() - _start)
        return result

    def filter(self, *conditions):
        _start = time.perf_counter()
        self.connect()
        with Session(self.engine) as session:
            stmt = select(self.model).where(*conditions)
            result = session.exec(stmt).all()
        observe_db("read", self._table_name, time.perf_counter() - _start)
        return result

    def first(self, *conditions):
        _start = time.perf_counter()
        self.connect()
        with Session(self.engine) as session:
            stmt = select(self.model).where(*conditions)
            result = session.exec(stmt).first()
        observe_db("read", self._table_name, time.perf_counter() - _start)
        return result

    def update(self, id, **kwargs):
        _start = time.perf_counter()
        self.connect()
        with Session(self.engine) as session:
            obj = session.get(self.model, id)
            if obj is None:
                observe_db("update", self._table_name, time.perf_counter() - _start)
                return None
            for key, value in kwargs.items():
                setattr(obj, key, value)
            session.add(obj)
            session.commit()
            session.refresh(obj)
        observe_db("update", self._table_name, time.perf_counter() - _start)
        return obj

    def delete(self, id):
        _start = time.perf_counter()
        self.connect()
        with Session(self.engine) as session:
            obj = session.get(self.model, id)
            if obj is None:
                observe_db("delete", self._table_name, time.perf_counter() - _start)
                return False
            session.delete(obj)
            session.commit()
        observe_db("delete", self._table_name, time.perf_counter() - _start)
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
        _start = time.perf_counter()
        self.connect()
        self.client.set(key, json.dumps(data))
        if ttl is not None:
            self.client.expire(key, ttl)
        observe_redis("set", time.perf_counter() - _start)

    def get_json(self, key: str) -> Optional[dict]:
        _start = time.perf_counter()
        self.connect()
        data = self.client.get(key)
        if data is not None:
            observe_redis("get", time.perf_counter() - _start)
            return json.loads(data)
        observe_redis("get", time.perf_counter() - _start)
        return None

    def append_to_array(self, key: str, array_field: str, item: dict, ttl: Optional[int] = None) -> None:
        _start = time.perf_counter()
        self.connect()
        data = self.get_json(key)
        if data is None:
            data = {}
        if array_field not in data:
            data[array_field] = []
        data[array_field].append(item)
        self.set_json(key, data, ttl)
        observe_redis("append", time.perf_counter() - _start)

    def delete(self, key: str) -> None:
        _start = time.perf_counter()
        self.connect()
        self.client.delete(key)
        observe_redis("delete", time.perf_counter() - _start)

    def disconnect(self) -> None:
        if self.client is not None:
            self.client.close()
            self._initialized = False
            self.client = None
            logger.info("Disconnected from Redis")
