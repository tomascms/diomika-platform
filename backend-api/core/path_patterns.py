"""Path pattern matchers — shared across middleware and rate_limit."""


def is_admin_or_system_path(path: str) -> bool:
    """Check if path is admin or system endpoint."""
    return path.startswith("/admin") or path.startswith("/system")


def is_public_catalog_path(path: str) -> bool:
    """Check if path is a public catalogue endpoint (GET only)."""
    return (
        path == "/categorias"
        or path.startswith("/categorias/")
        or path == "/catalogo/meta"
        or (path.startswith("/catalogo/") and "/admin/" not in path)
    )
