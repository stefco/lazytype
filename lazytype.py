"Wrappers for typing & pydantic models; module loading deferred till __init__."

__version__ = "0.2.1"

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
    registry = {}

    def __getitem__(self, wraps: str):
        wraps = _Validator(wraps).key
        if wraps not in self.__class__.registry:
            self.__class__.registry[wraps] = \
                type('Lazy'+wraps.split('.')[-1], (self,),
                     {'_wraps': wraps, '_instance': None})
        return self.__class__.registry[wraps]

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


class LazyFieldMeta(LazyTypeMeta):
    registry = {}

    def __getitem__(self, wraps: tuple):
        if not isinstance(wraps, tuple):
            raise IndexError("Must provide [schematype[:schema_base], "
                             "*lazy_type_args]")
        st, lazytype, *lazyextras = wraps
        t, s, e = ((st.start, st.stop, st.step)
                   if isinstance(st, slice) else (st, None, None))
        key = (t, (tuple(i) if isinstance(i, dict) else i for i in (s, e)),
               lazytype)
        if key not in self.__class__.registry:
            if s is None:
                from pydantic import BaseModel

                class GetAnno(BaseModel):
                    foo: t
                s = GetAnno.schema()['properties']['foo']
                s.pop('title', None)  # title not actually 'foo', of course
            if e is not None:
                s.update(e)
            field = LazyTypeMeta.__getitem__(self, (lazytype, *lazyextras))
            self.__class__.registry[key] = \
                type('LazyField'+lazytype.split('.')[-1], (field,),
                     {'__base_schema__': s})
        return self.__class__.registry[key]


class LazyField(LazyType, metaclass=LazyFieldMeta):
    """
    Make a ``pydantic`` field with the ``LazyField`` subscript interface. Just
    like ``LazyType``, but it starts with a type annotation for the pydantic
    model's JSON schema.

    Examples
    --------
    Create a lazy-loading field for ``astropy.time.Time`` using the built-in
    ``datetime`` string validator:
    >>> from datetime import datetime
    >>> LazyField[datetime, 'astropy.time.Time', 'strict':True]
    lazytype.LazyFieldTime

    Actually use the field in a ``pydantic`` model:
    >>> from pydantic import BaseModel
    >>> class LazyTest(BaseModel):
    ...     foo: str
    ...     time: LazyField[datetime, 'astropy.time.Time', 'strict':True]

    See the JSON schema of the resulting model:
    >>> LazyTest.schema()
    {'title': 'LazyTest',
     'type': 'object',
     'properties': {'foo': {'title': 'Foo', 'type': 'string'},
      'time': {'title': 'Time', 'type': 'string', 'format': 'date-time'}},
     'required': ['foo', 'time']}

    Actually instantiate something, forcing ``astropy.time.Time`` to load:
    >>> t = LazyTest(foo='bar', time='2019-11-29 13:40:29.197')
    >>> t.time
    <Lazy <Time object: scale='utc' format='iso' value=2019-11-29 13:40:29.197>>
    >>> t.time.gps
    1259070047.197

    Provide additional schema annotations, e.g. providing an example input
    value:
    >>> class LazyTest(BaseModel):
    ...     foo: str
    ...     time: LazyField[str::{'example': '2019-11-29 13:40:29.197'},
    ...                     'astropy.time.Time', 'strict':True]
    >>> LazyTest.schema()
    {'title': 'LazyTest',
     'type': 'object',
     'properties': {'foo': {'title': 'Foo', 'type': 'string'},
      'time': {'title': 'Time',
       'type': 'string',
       'example': '2019-11-29 13:40:29.197'}},
     'required': ['foo', 'time']}
    """

    @classmethod
    def __get_validators__(cls):
        yield lambda v: cls(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(cls.__base_schema__)
