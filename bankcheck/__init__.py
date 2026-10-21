from importlib.metadata import PackageNotFoundError, version

# The version is defined once, in pyproject.toml
try:
    __version__ = version("bankcheck")
except PackageNotFoundError:  # running from source without installing
    __version__ = "0.0.0+unknown"
