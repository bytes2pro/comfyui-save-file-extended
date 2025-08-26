from __future__ import annotations

import functools
import inspect
import traceback
from typing import Any, Callable

SENSITIVE_KEYS = {
    "api_key",
    "access_key",
    "secret_key",
    "client_secret",
    "authorization",
    "token",
    "access_token",
    "refresh_token",
}


def _sanitize(value: Any) -> Any:
    try:
        if isinstance(value, dict):
            return {k: ("***" if str(k).lower() in SENSITIVE_KEYS else _sanitize(v)) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return type(value)(_sanitize(v) for v in value)
        if isinstance(value, str) and len(value) > 128:
            return value[:125] + "..."
        return value
    except Exception:
        return "<unserializable>"


def log_exceptions(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Wrap a function (sync or async) to print exceptions with flush, then re-raise.
    Does minimal argument sanitization to avoid leaking secrets.
    """

    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                try:
                    func_name = f"{func.__module__}.{func.__qualname__}"
                    safe_kwargs = {k: ("***" if k.lower() in SENSITIVE_KEYS else _sanitize(v)) for k, v in kwargs.items()}
                    safe_args = [_sanitize(a) for a in args]
                    print(f"[ERROR] {func_name} failed | args={safe_args} kwargs={safe_kwargs}: {e}", flush=True)
                    tb = traceback.format_exc()
                    print(tb, flush=True)
                finally:
                    pass
                raise

        return async_wrapper

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            try:
                func_name = f"{func.__module__}.{func.__qualname__}"
                safe_kwargs = {k: ("***" if k.lower() in SENSITIVE_KEYS else _sanitize(v)) for k, v in kwargs.items()}
                safe_args = [_sanitize(a) for a in args]
                print(f"[ERROR] {func_name} failed | args={safe_args} kwargs={safe_kwargs}: {e}", flush=True)
                tb = traceback.format_exc()
                print(tb, flush=True)
            finally:
                pass
            raise

    return wrapper


