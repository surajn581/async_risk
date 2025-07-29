import contextvars
from contextlib import contextmanager
from copy import deepcopy

_env_context = contextvars.ContextVar("env", default={})

class Env:
    def __init__(self, **kwargs):
        self._new_values = kwargs
        self._token = None

    def __enter__(self):
        current_env = deepcopy(_env_context.get())
        current_env.update(self._new_values)
        self._token = _env_context.set(current_env)

    def __exit__(self, exc_type, exc_val, exc_tb):
        _env_context.reset(self._token)

    @classmethod
    def get(cls, key, default=None):
        return _env_context.get().get(key, default)

    def __getattr__(self, item):
        return self.get(item)