# Publishing KSB

## CI

Every push/PR to `main` runs `.github/workflows/ci.yml` (pytest on Python 3.10–3.13 + CLI smoke).

## GitHub Release → PyPI

`.github/workflows/publish.yml` builds a wheel/sdist and uploads to PyPI when you publish a GitHub Release.

### One-time: PyPI Trusted Publisher

1. Create a free account at [pypi.org](https://pypi.org/account/register/).
2. Enable 2FA.
3. Go to **Publishing → Add a new pending publisher**:
   - **PyPI project name:** `ksb`
   - **Owner:** `semihbalan`
   - **Repository:** `ksb`
   - **Workflow name:** `publish.yml`
   - **Environment name:** `pypi`
4. On GitHub: **Settings → Environments → New environment → `pypi`** (optional protection rules).
5. Create a GitHub Release (tag `v0.2.0`, etc.) — the workflow publishes automatically.

### Manual build (local)

```bash
pip install -e ".[dev]"
python -m build
twine check dist/*
# twine upload dist/*   # needs API token
```

### Bump version

Edit `version` in:
- `pyproject.toml`
- `src/ksb/__init__.py`

Then tag and release:

```bash
git tag v0.2.1
git push origin v0.2.1
gh release create v0.2.1 --generate-notes
```
