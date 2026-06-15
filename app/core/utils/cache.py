import functools
import json
import re
from collections.abc import AsyncGenerator, Callable
from typing import Any, cast

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from redis.asyncio import ConnectionPool, Redis

from ..exceptions.cache_exceptions import (
    CacheIdentificationInferenceError,
    InvalidRequestError,
    MissingClientError,
)

pool: ConnectionPool | None = None
client: Redis | None = None


def _infer_resource_id(
    kwargs: dict[str, Any], resource_id_type: type | tuple[type, ...]
) -> int | str:
    """
    Returns the resource ID from kwargs according to the expected type.
    If resource_id_type is int, looks for an int argument with 'id' in its name.
    If str, returns the first argument of type str.
    Raises CacheIdentificationInferenceError if not found.
    """
    resource_id: int | str | None = None
    for arg_name, arg_value in kwargs.items():
        if isinstance(arg_value, resource_id_type):
            if (resource_id_type is int) and ("id" in arg_name):
                resource_id = cast(int, arg_value)

            elif resource_id_type is str:
                resource_id = cast(str, arg_value)

    if resource_id is None:
        raise CacheIdentificationInferenceError

    return resource_id


def _extract_data_inside_brackets(input_string: str) -> list[str]:
    """
    Returns a list of strings found between curly brackets in input_string.
    """
    data_inside_brackets = re.findall(r"{(.*?)}", input_string)
    return data_inside_brackets


def _construct_data_dict(
    data_inside_brackets: list[str], kwargs: dict[str, Any]
) -> dict[str, Any]:
    """
    Builds a dict with keys found between curly brackets and their values from kwargs.
    """
    data_dict = {}
    for key in data_inside_brackets:
        data_dict[key] = kwargs[key]
    return data_dict


def _format_prefix(prefix: str, kwargs: dict[str, Any]) -> str:
    """
    Formats the prefix by replacing curly-braced keys with values from kwargs.
    """
    data_inside_brackets = _extract_data_inside_brackets(prefix)
    data_dict = _construct_data_dict(data_inside_brackets, kwargs)
    formatted_prefix = prefix.format(**data_dict)
    return formatted_prefix


def _format_extra_data(
    to_invalidate_extra: dict[str, str], kwargs: dict[str, Any]
) -> dict[str, Any]:
    """
    Formats extra data for cache invalidation using kwargs.
    """
    formatted_extra = {}
    for prefix, id_template in to_invalidate_extra.items():
        formatted_prefix = _format_prefix(prefix, kwargs)
        id = _extract_data_inside_brackets(id_template)[0]
        formatted_extra[formatted_prefix] = kwargs[id]

    return formatted_extra


async def _delete_keys_by_pattern(pattern: str) -> None:
    """
    Deletes all Redis keys matching the given pattern using SCAN and bulk delete.
    Pattern can include wildcards (e.g., 'user:*').
    """
    if client is None:
        return

    cursor = 0
    while True:
        cursor, keys = await client.scan(cursor, match=pattern, count=100)
        if keys:
            await client.delete(*keys)
        if cursor == 0:
            break


def cache(
    key_prefix: str,
    resource_id_name: Any = None,
    expiration: int = 3600,
    resource_id_type: type | tuple[type, ...] = int,
    to_invalidate_extra: dict[str, Any] | None = None,
    pattern_to_invalidate_extra: list[str] | None = None,
) -> Callable:
    """
    Decorator for caching FastAPI endpoint results in Redis.

    Args:
        key_prefix (str): Prefix for the cache key.
        resource_id_name (Any, optional): Name of the resource ID argument. If not provided, inferred automatically.
        expiration (int, optional): Cache expiration in seconds. Default is 3600.
        resource_id_type (type or tuple, optional): Expected type of the resource ID. Default is int.
        to_invalidate_extra (dict, optional): Extra cache keys to invalidate on non-GET requests.
        pattern_to_invalidate_extra (list, optional): Patterns for bulk cache invalidation.

    Returns:
        Callable: Decorator for FastAPI endpoints.

    Example:
        @app.get("/sample/{resource_id}")
        @cache(key_prefix="sample_data", expiration=3600, resource_id_type=int)
        async def sample_endpoint(request: Request, resource_id: int):
            return {"data": "your_data"}

    Advanced Example:
        @app.put("/items/{item_id}")
        @cache(
            key_prefix="item_data",
            resource_id_name="item_id",
            to_invalidate_extra={"user_items": "{user_id}"},
            pattern_to_invalidate_extra=["user_*_items:*"]
        )
        async def update_item(request: Request, item_id: int, data: dict, user_id: int):
            return {"status": "updated"}
    """

    def wrapper(func: Callable) -> Callable:
        @functools.wraps(func)
        async def inner(request: Request, *args: Any, **kwargs: Any) -> Any:
            if client is None:
                raise MissingClientError

            if resource_id_name:
                resource_id = kwargs[resource_id_name]
            else:
                resource_id = _infer_resource_id(
                    kwargs=kwargs, resource_id_type=resource_id_type
                )

            formatted_key_prefix = _format_prefix(key_prefix, kwargs)
            cache_key = f"{formatted_key_prefix}:{resource_id}"
            if request.method == "GET":
                if (
                    to_invalidate_extra is not None
                    or pattern_to_invalidate_extra is not None
                ):
                    raise InvalidRequestError

                cached_data = await client.get(cache_key)
                if cached_data:
                    cached_text = (
                        cached_data.decode()
                        if isinstance(cached_data, bytes)
                        else cached_data
                    )
                    return json.loads(cached_text)

            result = await func(request, *args, **kwargs)

            if request.method == "GET":
                serializable_data = jsonable_encoder(result)
                serialized_data = json.dumps(serializable_data)

                await client.set(cache_key, serialized_data)
                await client.expire(cache_key, expiration)

                return json.loads(serialized_data)

            else:
                await client.delete(cache_key)
                if to_invalidate_extra is not None:
                    formatted_extra = _format_extra_data(to_invalidate_extra, kwargs)
                    for prefix, id in formatted_extra.items():
                        extra_cache_key = f"{prefix}:{id}"
                        await client.delete(extra_cache_key)

                if pattern_to_invalidate_extra is not None:
                    for pattern in pattern_to_invalidate_extra:
                        formatted_pattern = _format_prefix(pattern, kwargs)
                        await _delete_keys_by_pattern(formatted_pattern + "*")

            return result

        return inner

    return wrapper


async def async_get_redis() -> AsyncGenerator[Redis, None]:
    """Get a Redis client from the pool for each request."""
    client = Redis(connection_pool=pool)
    try:
        yield client
    finally:
        await client.aclose()
