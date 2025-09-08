from functools import wraps
from typing import NamedTuple, Callable, Any
import asyncio

def outputs(**types: Any):
    """
    Decorator that:
    1. Dynamically creates a NamedTuple with given fields.
    2. Ensures the function returns either a dict or that NamedTuple.
    3. Updates __annotations__ so static analyzers see correct return type.
    """
    OutTuple = NamedTuple("Outputs", [(name, typ) for name, typ in types.items()])

    def decorator(func: Callable[..., Any]) -> Callable[..., OutTuple]:

        if not asyncio.iscoroutinefunction(func):
            @wraps(func)
            def _wrapper(*args, **kwargs) -> OutTuple:
                result = func(*args, **kwargs)
                if isinstance(result, list):
                    if len(result)!= len(types):
                        raise TypeError(f"Expected {func.__name__} outputs to be like {types}, got {[type(res) for res in result]}")
                    return OutTuple(**dict(zip(types.keys(), result)))
                if isinstance(result, dict):
                    try:
                        return OutTuple(**result)
                    except TypeError as e:
                        raise TypeError(
                            f"Output dict keys mismatch. "
                            f"Expected {list(types.keys())}, got {list(result.keys())}"
                        ) from e
                elif isinstance(result, OutTuple):
                    return result
                elif len(types)==1 and isinstance(result, list(types.values())[0]):
                    name = list(types.keys())[0]
                    return OutTuple(**{name:result})
                else:
                    raise TypeError(
                        f"Expected {func.__name__} to return dict or {OutTuple}, got {type(result)}"
                    )
        else:
            
            @wraps(func)
            async def _wrapper(*args, **kwargs) -> OutTuple:
                result = await func(*args, **kwargs)
                if isinstance(result, list):
                    if len(result)!= len(types):
                        raise TypeError(f"Expected {func.__name__} outputs to be like {types}, got {[type(res) for res in result]}")
                    return OutTuple(**dict(zip(types.keys(), result)))
                if isinstance(result, dict):
                    try:
                        return OutTuple(**result)
                    except TypeError as e:
                        raise TypeError(
                            f"Output dict keys mismatch. "
                            f"Expected {list(types.keys())}, got {list(result.keys())}"
                        ) from e
                elif isinstance(result, OutTuple):
                    return result
                elif len(types)==1 and isinstance(result, list(types.values())[0]):
                    name = list(types.keys())[0]
                    return OutTuple(**{name:result})
                else:
                    raise TypeError(
                        f"Expected {func.__name__} to return dict or {OutTuple}, got {type(result)}"
                    )

        # Update return type annotation dynamically
        _wrapper.__annotations__["return"] = OutTuple
        return _wrapper

    return decorator