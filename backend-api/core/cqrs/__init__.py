"""CQRS (Command Query Responsibility Segregation) pattern implementation."""
from __future__ import annotations

import logging
from enum import Enum
from typing import TypeVar, Generic, Optional, Any, Callable, List
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("diomika-api")

T = TypeVar("T")
R = TypeVar("R")


class CommandType(Enum):
    """Types of commands."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BULK_CREATE = "bulk_create"
    BULK_UPDATE = "bulk_update"
    BULK_DELETE = "bulk_delete"


@dataclass
class Command(ABC, Generic[R]):
    """Base command that modifies state."""
    command_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    @abstractmethod
    def execute(self) -> R:
        """Execute the command and return result."""
        pass


@dataclass
class Query(ABC, Generic[R]):
    """Base query for reading data."""
    query_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    @abstractmethod
    def execute(self) -> R:
        """Execute the query and return result."""
        pass


class CommandHandler(ABC, Generic[T, R]):
    """Base handler for commands."""

    @abstractmethod
    async def handle(self, command: T) -> R:
        """Handle the command and return result."""
        pass


class QueryHandler(ABC, Generic[T, R]):
    """Base handler for queries."""

    @abstractmethod
    async def handle(self, query: T) -> R:
        """Handle the query and return result."""
        pass


class CommandBus:
    """Command bus for routing and executing commands."""

    def __init__(self):
        self.handlers: dict[type, CommandHandler] = {}
        self.middleware: List[Callable] = []

    def register_handler(self, command_type: type, handler: CommandHandler):
        """Register a command handler."""
        self.handlers[command_type] = handler
        logger.info(f"Registered handler for {command_type.__name__}")

    def add_middleware(self, middleware: Callable):
        """Add middleware to command pipeline."""
        self.middleware.append(middleware)

    async def execute(self, command: Command) -> Any:
        """Execute a command."""
        handler = self.handlers.get(type(command))
        if not handler:
            raise ValueError(f"No handler registered for {type(command).__name__}")

        # Apply middleware
        for middleware in self.middleware:
            command = await middleware(command)

        # Execute handler
        try:
            logger.info(f"Executing command {type(command).__name__} (ID: {command.command_id})")
            result = await handler.handle(command)
            logger.info(f"Command {command.command_id} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Command {command.command_id} failed: {str(e)}")
            raise


class QueryBus:
    """Query bus for routing and executing queries."""

    def __init__(self):
        self.handlers: dict[type, QueryHandler] = {}
        self.middleware: List[Callable] = []
        self.cache: dict[str, tuple[Any, datetime]] = {}
        self.cache_ttl: int = 300  # 5 minutes

    def register_handler(self, query_type: type, handler: QueryHandler):
        """Register a query handler."""
        self.handlers[query_type] = handler
        logger.info(f"Registered handler for {query_type.__name__}")

    def add_middleware(self, middleware: Callable):
        """Add middleware to query pipeline."""
        self.middleware.append(middleware)

    async def execute(self, query: Query, use_cache: bool = True) -> Any:
        """Execute a query with optional caching."""
        # Check cache
        if use_cache:
            cached_result, cached_time = self.cache.get(query.query_id, (None, None))
            if cached_result is not None:
                age = (datetime.utcnow() - cached_time).total_seconds()
                if age < self.cache_ttl:
                    logger.debug(f"Query {query.query_id} served from cache")
                    return cached_result

        handler = self.handlers.get(type(query))
        if not handler:
            raise ValueError(f"No handler registered for {type(query).__name__}")

        # Apply middleware
        for middleware in self.middleware:
            query = await middleware(query)

        # Execute handler
        try:
            logger.info(f"Executing query {type(query).__name__} (ID: {query.query_id})")
            result = await handler.handle(query)

            # Cache result
            if use_cache:
                self.cache[query.query_id] = (result, datetime.utcnow())

            logger.info(f"Query {query.query_id} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Query {query.query_id} failed: {str(e)}")
            raise

    def invalidate_cache(self, query_id: Optional[str] = None):
        """Invalidate cache for a specific query or all cache."""
        if query_id:
            self.cache.pop(query_id, None)
            logger.debug(f"Invalidated cache for query {query_id}")
        else:
            self.cache.clear()
            logger.debug("Invalidated entire query cache")


class CommandAuditLogger:
    """Log all commands for audit trail."""

    def __init__(self):
        self.command_log: List[dict] = []

    async def log_command(self, command: Command, result: Any, error: Optional[Exception] = None):
        """Log command execution."""
        entry = {
            "command_id": command.command_id,
            "command_type": type(command).__name__,
            "timestamp": command.timestamp.isoformat(),
            "user_id": command.user_id,
            "result_type": type(result).__name__ if result else None,
            "error": str(error) if error else None,
            "metadata": command.metadata,
        }
        self.command_log.append(entry)
        logger.info(f"Logged command execution: {entry}")

    def get_command_history(self, user_id: Optional[str] = None, limit: int = 100) -> List[dict]:
        """Get command history."""
        if user_id:
            return [e for e in self.command_log if e["user_id"] == user_id][:limit]
        return self.command_log[-limit:]


class EventStore:
    """Store events generated by commands."""

    def __init__(self):
        self.events: List[dict] = []

    def append_event(
        self,
        event_type: str,
        aggregate_id: str,
        aggregate_type: str,
        data: dict,
        user_id: Optional[str] = None,
    ):
        """Append event to store."""
        event = {
            "event_type": event_type,
            "aggregate_id": aggregate_id,
            "aggregate_type": aggregate_type,
            "data": data,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.events.append(event)
        logger.info(f"Appended event: {event_type} for {aggregate_type}#{aggregate_id}")

    def get_events(
        self,
        aggregate_id: Optional[str] = None,
        aggregate_type: Optional[str] = None,
    ) -> List[dict]:
        """Get events, optionally filtered."""
        events = self.events
        if aggregate_id:
            events = [e for e in events if e["aggregate_id"] == aggregate_id]
        if aggregate_type:
            events = [e for e in events if e["aggregate_type"] == aggregate_type]
        return events

    def rebuild_aggregate(self, aggregate_id: str, aggregate_type: str) -> dict:
        """Rebuild aggregate state from events."""
        events = self.get_events(aggregate_id, aggregate_type)
        state: dict[str, Any] = {"id": aggregate_id, "type": aggregate_type}

        for event in events:
            # Apply event to state (simplified logic)
            state.update(event["data"])

        return state


# Global bus instances
_command_bus: Optional[CommandBus] = None
_query_bus: Optional[QueryBus] = None
_command_audit: Optional[CommandAuditLogger] = None
_event_store: Optional[EventStore] = None


def get_command_bus() -> CommandBus:
    """Get global command bus."""
    global _command_bus
    if _command_bus is None:
        _command_bus = CommandBus()
    return _command_bus


def get_query_bus() -> QueryBus:
    """Get global query bus."""
    global _query_bus
    if _query_bus is None:
        _query_bus = QueryBus()
    return _query_bus


def get_command_audit() -> CommandAuditLogger:
    """Get global command audit logger."""
    global _command_audit
    if _command_audit is None:
        _command_audit = CommandAuditLogger()
    return _command_audit


def get_event_store() -> EventStore:
    """Get global event store."""
    global _event_store
    if _event_store is None:
        _event_store = EventStore()
    return _event_store
