"""
Service Container - Simple Dependency Injection container.

This module provides a lightweight DI container for managing application
dependencies and promoting loose coupling.
"""

from typing import Any, Callable, Dict, Optional, Type, TypeVar
from threading import Lock
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceContainer:
    """
    Simple Dependency Injection container.

    Supports:
    - Singleton registration (single instance reused)
    - Transient registration (new instance each time)
    - Factory registration (custom creation logic)
    - Interface to implementation mapping
    """

    def __init__(self):
        """Initialize the service container."""
        self._singletons: Dict[Type, Any] = {}
        self._transients: Dict[Type, Callable] = {}
        self._factories: Dict[Type, Callable] = {}
        self._lock = Lock()

    def register_singleton(self, service_type: Type[T], instance: T) -> None:
        """
        Register a singleton instance.

        The same instance will be returned for all resolutions.

        Args:
            service_type: The type/interface to register
            instance: The instance to return
        """
        with self._lock:
            self._singletons[service_type] = instance
            logger.debug(f"Registered singleton: {service_type.__name__}")

    def register_transient(self, service_type: Type[T],
                          implementation: Type[T]) -> None:
        """
        Register a transient service.

        A new instance will be created for each resolution.

        Args:
            service_type: The type/interface to register
            implementation: The concrete type to instantiate
        """
        with self._lock:
            self._transients[service_type] = implementation
            logger.debug(f"Registered transient: {service_type.__name__} -> "
                        f"{implementation.__name__}")

    def register_factory(self, service_type: Type[T],
                        factory: Callable[[], T]) -> None:
        """
        Register a factory function for creating instances.

        Args:
            service_type: The type/interface to register
            factory: Function that creates and returns an instance
        """
        with self._lock:
            self._factories[service_type] = factory
            logger.debug(f"Registered factory for: {service_type.__name__}")

    def resolve(self, service_type: Type[T]) -> T:
        """
        Resolve a service instance.

        Args:
            service_type: The type to resolve

        Returns:
            Instance of the requested type

        Raises:
            KeyError: If the service type is not registered
        """
        with self._lock:
            # Check singletons first
            if service_type in self._singletons:
                return self._singletons[service_type]

            # Check factories
            if service_type in self._factories:
                factory = self._factories[service_type]
                instance = factory()
                logger.debug(f"Created instance via factory: {service_type.__name__}")
                return instance

            # Check transients
            if service_type in self._transients:
                implementation = self._transients[service_type]
                instance = implementation()
                logger.debug(f"Created transient instance: {service_type.__name__}")
                return instance

        raise KeyError(f"Service not registered: {service_type.__name__}")

    def try_resolve(self, service_type: Type[T]) -> Optional[T]:
        """
        Try to resolve a service, returning None if not found.

        Args:
            service_type: The type to resolve

        Returns:
            Instance of the requested type, or None if not registered
        """
        try:
            return self.resolve(service_type)
        except KeyError:
            return None

    def is_registered(self, service_type: Type) -> bool:
        """
        Check if a service type is registered.

        Args:
            service_type: The type to check

        Returns:
            bool: True if registered, False otherwise
        """
        with self._lock:
            return (service_type in self._singletons or
                   service_type in self._transients or
                   service_type in self._factories)

    def unregister(self, service_type: Type) -> None:
        """
        Unregister a service type.

        Args:
            service_type: The type to unregister
        """
        with self._lock:
            self._singletons.pop(service_type, None)
            self._transients.pop(service_type, None)
            self._factories.pop(service_type, None)
            logger.debug(f"Unregistered service: {service_type.__name__}")

    def clear(self) -> None:
        """Clear all registered services."""
        with self._lock:
            self._singletons.clear()
            self._transients.clear()
            self._factories.clear()
            logger.debug("Cleared all registered services")


# Global service container instance
_container = None


def get_container() -> ServiceContainer:
    """
    Get the global service container instance.

    Returns:
        ServiceContainer: The global container
    """
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container


def reset_container() -> None:
    """Reset the global container (useful for testing)."""
    global _container
    if _container:
        _container.clear()
    _container = None


# Convenience functions
def register_singleton(service_type: Type[T], instance: T) -> None:
    """Register a singleton in the global container."""
    get_container().register_singleton(service_type, instance)


def register_transient(service_type: Type[T], implementation: Type[T]) -> None:
    """Register a transient in the global container."""
    get_container().register_transient(service_type, implementation)


def register_factory(service_type: Type[T], factory: Callable[[], T]) -> None:
    """Register a factory in the global container."""
    get_container().register_factory(service_type, factory)


def resolve(service_type: Type[T]) -> T:
    """Resolve a service from the global container."""
    return get_container().resolve(service_type)


def try_resolve(service_type: Type[T]) -> Optional[T]:
    """Try to resolve a service from the global container."""
    return get_container().try_resolve(service_type)
