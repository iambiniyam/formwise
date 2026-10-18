# Publishing

The GitHub release already contains a wheel. Registry publishing is a one-time account setup.

## PyPI

1. Create the `formwise` project on PyPI.
2. Add a trusted publisher with owner `iambiniyam`, repository `formwise`, workflow `publish.yml`, environment `pypi`.
3. Add the GitHub variable `PUBLISH_PYPI=true`.
4. Run the `publish` workflow manually, or publish a new release.

## Direct install

```bash
pip install https://github.com/iambiniyam/formwise/releases/download/v0.1.9/formwise-0.1.9-py3-none-any.whl
```
