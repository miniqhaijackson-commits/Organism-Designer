import contextlib
from weakref import WeakValueDictionary
import logging
from typing import Callable


class ResourceManager:
    """Manage system resources and prevent memory leaks (minimal)."""

    def __init__(self):
        self._resources = WeakValueDictionary()
        self._cleanup_tasks = []

    @contextlib.contextmanager
    def managed_resource(self, resource_id: str, factory_func: Callable, *args, **kwargs):
        """Context manager for automatic resource cleanup."""
        resource = factory_func(*args, **kwargs)
        self._resources[resource_id] = resource

        try:
            yield resource
        finally:
            try:
                if hasattr(resource, 'close'):
                    resource.close()
                elif hasattr(resource, 'cleanup'):
                    resource.cleanup()
            except Exception as e:
                logging.error(f"Error cleaning resource {resource_id}: {e}")

            if resource_id in self._resources:
                try:
                    del self._resources[resource_id]
                except Exception:
                    pass

    def register_cleanup(self, cleanup_func: Callable, *args, **kwargs):
        """Register cleanup functions for shutdown."""
        self._cleanup_tasks.append((cleanup_func, args, kwargs))

    def cleanup_all(self):
        """Execute all cleanup tasks."""
        for cleanup_func, args, kwargs in reversed(self._cleanup_tasks):
            try:
                cleanup_func(*args, **kwargs)
            except Exception as e:
                logging.error(f"Cleanup error: {e}")
