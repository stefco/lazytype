# lazytype

Write type hints, implement optional features, define `pydantic` models without
up-front import delays, and more without having to import slow modules; using a
`lazytype.LazyType`, you can wrap a slow-loading class so that its module
doesn't load until you instantiate it or run an actual type check.

[Pydantic](https://pydantic-docs.helpmanual.io/) models are also supported
through the `LazyField` interface, though you don't need to have Pydantic
installed to use `LazyType`s.

# Installation

For users:

```bash
pip install lazytype
```

Optionally make sure `pydantic` is installed with the `pydantic` option (if you
plan to use `LazyField`s):

```bash
pip install lazytype[pydantic]
```

For developers, clone this repository, change to its directory, and run:

```bash
flit install --symlink
```

# Examples

## Regular `LazyTypes`

The interface is the same as the wrapped object:

```python
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
```

You can optionally require that a check run for the module availability at
definition time:

```python
# this works if you have "numpy" installed
>>> LazyArray = LazyType['numpy.ndarray', 'strict':True]
lazytype.Lazyndarray

# this doesn't (unless you have a package called "numpay"...)
>>> LazyArray = LazyType['numpay.ndarray', 'strict':True]
ImportError: Strict check for module numpay availability failed
```

## `pydantic` Fields with `LazyField`s

You can also use `LazyType`s with Pydantic models to specify data types and
validators. This requires some extra methods provided by the `LazyField` class;
you can specify any [built-in Pydantic
field-type](https://pydantic-docs.helpmanual.io/usage/types/) to use for schema
validation, followed by the arguments you would use to create a new
`LazyType`. This allows you to map an existing field-type to a custom,
slow-loading field-type that can trivially accept the same input arguments, all
without loading the wrapped class's module until your model is instantiated.

Create a lazy-loading field for `astropy.time.Time` using the built-in
`datetime` string validator:

```python
>>> from datetime import datetime
>>> LazyField[datetime, 'astropy.time.Time', 'strict':True]
lazytype.LazyFieldTime
```

Actually use the field in a `pydantic` model:

```python
>>> from pydantic import BaseModel
>>> class LazyTest(BaseModel):
...     foo: str
...     time: LazyField[datetime, 'astropy.time.Time', 'strict':True]
```

See the JSON schema of the resulting model:

```python
>>> LazyTest.schema()
{'title': 'LazyTest',
 'type': 'object',
 'properties': {'foo': {'title': 'Foo', 'type': 'string'},
  'time': {'title': 'Time', 'type': 'string', 'format': 'date-time'}},
 'required': ['foo', 'time']}
```

Actually instantiate something, forcing `astropy.time.Time` to load:

```python
>>> t = LazyTest(foo='bar', time='2019-11-29 13:40:29.197')
>>> t.time
<Lazy <Time object: scale='utc' format='iso' value=2019-11-29 13:40:29.197>>
>>> t.time.gps
1259070047.197
```

Provide additional schema annotations, e.g. providing an example input
value:

```python
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
```
