"Type wrappers for typing; module loading deferred till __init__."

__version__ = "0.1.0"

import importlib
from textwrap import indent


class _Validator:

    def __init__(self, key):
        self.key, *self.extras = key if isinstance(key, tuple) else (key,)
        for extra in self.extras:
            x, args = ((extra.start, (extra.stop, extra.step))
                        if isinstance(extra, slice) else (extra, ()))
            try:
                getattr(self, x)(*args)
            except AttributeError:
                raise TypeError("Invalid spec: %s"%extra)

    def strict(self, check, _=None):
        *mod, clsname = self.key.split('.')
        modname = '.'.join(mod)
        if importlib.util.find_spec(modname) is None:
            raise ImportError("Strict check for module %s availability failed"
                              % modname)


class LazyTypeMeta(type):

    def __getitem__(self, wraps: str):
        wraps = _Validator(wraps).key
        return type('Lazy'+wraps.split('.')[-1], (self,), {'_wraps': wraps,
                                                           '_instance': None})

    def __instancecheck__(self, obj):
        return isinstance(obj, self._load_wraps())

    def __subclasscheck__(self, obj):
        return issubclass(obj, self._load_wraps())


class LazyType(metaclass=LazyTypeMeta):
    """
    Get a wrapper class for the qualified name; module loading is deferred
    until instantiation, which has the same interface as the wrapped object.
    Attributes and subscripting refer to the wrapped class, except for the
    special attributes ``_wraps`` (the wrapped class) and ``_instance`` (the
    actual instance of the wrapped class). Note that setting attributes affects
    the lazy wrapper, not the wrapped class; indexing passes directly through
    to the wrapped instance, however.

    Examples
    --------
    The interface is the same as the wrapped object:

    >>> a = LazyType['numpy.ndarray']((3, 2))
    >>> a
    <Lazy array([[-1.49166815e-154, -2.68679856e+154],
                 [ 1.48219694e-323,  0.00000000e+000],
                 [ 0.00000000e+000,  4.17201348e-309]])>
    >>> a._instance
    array([[-2.00000000e+000,  2.32036240e+077],
           [ 1.48219694e-323,  0.00000000e+000],
           [ 0.00000000e+000,  4.17201348e-309]])
    >>> a[:] = 0
    >>> a
    array([[0., 0.],
           [0., 0.],
           [0., 0.]])
    >>> a.dtype
    dtype('float64')
    >>> isinstance(a._instance, type(a))
    True

    etc.
    """
    _wraps: type
    _instance: object

    @classmethod
    def _load_wraps(cls):
        if isinstance(cls._wraps, str):
            *modname, sub = cls._wraps.split(".")
            cls._wraps = vars(importlib.import_module(".".join(modname)))[sub]
        return cls._wraps

    def __init__(self, *args, **kwargs):
        self._instance = self._load_wraps()(*args, **kwargs)

    def __str__(self):
        return '<Lazy %s>'%indent(str(self._instance), ' '*6)[6:]

    def __repr__(self):
        return '<Lazy %s>'%indent(repr(self._instance), ' '*6)[6:]

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
