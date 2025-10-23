import functools
import logging
from collections.abc import Callable
from typing import Any, Union

import redis
from flask import Flask
from redis import RedisError
from redis.cache import CacheConfig
from redis.cluster import ClusterNode, RedisCluster
from redis.connection import Connection, SSLConnection
from redis.sentinel import Sentinel

from app.configs import config

logger = logging.getLogger(__name__)


class RedisClientWrapper:
    """
    A wrapper class for the Redis client that addresses the issue where the global
    `redis_client` variable cannot be updated when a new Redis instance is returned
    by Sentinel.

    This class allows for deferred initialization of the Redis client, enabling the
    client to be re-initialized with a new instance when necessary. This is particularly
    useful in scenarios where the Redis instance may change dynamically, such as during
    a failover in a Sentinel-managed Redis setup.

    Attributes:
        _client (redis.Redis): The actual Redis client instance. It remains None until
                               initialized with the `initialize` method.

    Methods:
        initialize(client): Initializes the Redis client if it hasn't been initialized already.
        __getattr__(item): Delegates attribute access to the Redis client, raising an error
                           if the client is not initialized.
    """

    def __init__(self):
        self._client = None

    def initialize(self, client):
        if self._client is None:
            self._client = client

    def __getattr__(self, item):
        if self._client is None:
            raise RuntimeError("Redis client is not initialized. Call init_app first.")
        return getattr(self._client, item)


redis_client = RedisClientWrapper()


def init_app(app: Flask):
    global redis_client
    connection_class: type[Union[Connection, SSLConnection]] = Connection
    if config.REDIS_USE_SSL:
        connection_class = SSLConnection
    resp_protocol = config.REDIS_SERIALIZATION_PROTOCOL
    if config.REDIS_ENABLE_CLIENT_SIDE_CACHE:
        if resp_protocol >= 3:
            clientside_cache_config = CacheConfig()
        else:
            logger.warning("Client side cache is only supported in RESP3, disabling cache")
            clientside_cache_config = None
    else:
        clientside_cache_config = None

    redis_params: dict[str, Any] = {
        "username": config.REDIS_USERNAME,
        "password": config.REDIS_PASSWORD or None,  # Temporary fix for empty password
        "db": config.REDIS_DB,
        "encoding": "utf-8",
        "encoding_errors": "strict",
        "decode_responses": False,
        "protocol": resp_protocol,
        "cache_config": clientside_cache_config,
    }

    if config.REDIS_USE_SENTINEL:
        assert config.REDIS_SENTINELS is not None, "REDIS_SENTINELS must be set when REDIS_USE_SENTINEL is True"
        sentinel_hosts = [
            (node.split(":")[0], int(node.split(":")[1])) for node in config.REDIS_SENTINELS.split(",")
        ]
        sentinel = Sentinel(
            sentinel_hosts,
            sentinel_kwargs={
                "socket_timeout": config.REDIS_SENTINEL_SOCKET_TIMEOUT,
                "username": config.REDIS_SENTINEL_USERNAME,
                "password": config.REDIS_SENTINEL_PASSWORD,
            },
        )
        master = sentinel.master_for(config.REDIS_SENTINEL_SERVICE_NAME, **redis_params)
        redis_client.initialize(master)
    elif config.REDIS_USE_CLUSTERS:
        assert config.REDIS_CLUSTERS is not None, "REDIS_CLUSTERS must be set when REDIS_USE_CLUSTERS is True"
        nodes = [
            ClusterNode(host=node.split(":")[0], port=int(node.split(":")[1]))
            for node in config.REDIS_CLUSTERS.split(",")
        ]
        redis_client.initialize(
            RedisCluster(
                startup_nodes=nodes,
                password=config.REDIS_CLUSTERS_PASSWORD,
                protocol=resp_protocol,
                cache_config=clientside_cache_config,
            )
        )
    else:
        redis_params.update(
            {
                "host": config.REDIS_HOST,
                "port": config.REDIS_PORT,
                "connection_class": connection_class,
                "protocol": resp_protocol,
                "cache_config": clientside_cache_config,
            }
        )
        pool = redis.ConnectionPool(**redis_params)
        redis_client.initialize(redis.Redis(connection_pool=pool))

    app.extensions["redis"] = redis_client


def redis_fallback(default_return: Any = None):
    """
    decorator to handle Redis operation exceptions and return a default value when Redis is unavailable.

    Args:
        default_return: The value to return when a Redis operation fails. Defaults to None.
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except RedisError as e:
                logger.warning("Redis operation failed in %s: %s", func.__name__, str(e), exc_info=True)
                return default_return

        return wrapper

    return decorator
