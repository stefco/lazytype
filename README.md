# lazytype

Write type hints, implement optional features, define `pydantic` models without
up-front import delays, and more without having to import slow modules; using a
`lazytype.LazyType`, you can wrap a slow-loading class so that its module
doesn't load until you instantiate it or run an actual type check.

# Installation

For users:

```bash
pip install lazytype
```

For developers, clone this repository, change to its directory, and run:

```bash
flit install --symlink
```

# Examples

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
