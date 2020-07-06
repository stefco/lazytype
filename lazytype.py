"Read-only type wrappers for typing; module loading deferred till __init__."

__version__ = 0.1.0

import importlib
from typing import Union


class LazyTypeMeta(type):

    def __getitem__(self, wraps: str):
        return type('Lazy'+wraps.split('.')[-1], (self,), {'_wraps': wraps,
                                                           '_instance': None})

    def __instancecheck__(self, obj):
        return isinstance(obj, self._load_wraps())

    @classmethod
    def __subclasscheck__(self, obj):
        return issubclass(obj, self._load_wraps())


class LazyType(metaclass=LazyTypeMeta):
    _wraps: Union[str, type]
    _instance: str

    @classmethod
    def _load_wraps(cls):
        if isinstance(cls._wraps, str):
            *modname, sub = cls._wraps.split(".")
            cls._wraps = vars(importlib.import_module(".".join(modname)))[sub]
        return cls._wraps

    def __init__(self, *args, **kwargs):
        self._instance = self._load_wraps()(*args, **kwargs)

    def __getitem__(self, key):
        return self._instance[key]

    def __setitem__(self, key, value):
        self._instance[key] = value

    def __delitem__(self, key):
        del self._instance[key]

    def __getattr__(self, key):
        return getattr(self._instance, key)

    def __dir__(self):
        return sorted(set(super().__dir__()).union(self._instance.__dir__()))
