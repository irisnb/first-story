"""Event Log Service - manages the append-only event log.

This service implements the event-log-service spec:
- Append events to JSONL file
- Idempotency checking
- Batch boundary support
- Read events by sequence
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from ..models import SystemEvent


class EventLogService:
    """Service for managing the append-only event log."""

    def __init__(self, events_dir: Path):
        """Initialize the event log service.

        Args:
            events_dir: Directory containing event log files
        """
        self.events_dir = events_dir
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = events_dir / "00001.jsonl"

        # In-memory index: idempotency_key -> seq
        self._idempotency_index: dict[str, int] = {}
        # Track the highest seq
        self._next_seq: int = 1

        # Build index on startup
        self._build_idempotency_index()

    def _build_idempotency_index(self) -> None:
        """Build the in-memory idempotency index by scanning the log file."""
        if not self.log_file.exists():
            return

        max_seq = 0
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    event_data = json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Malformed JSON at line {line_num}: {e}") from e

                idempotency_key = event_data.get("idempotency_key")
                seq = event_data.get("seq", 0)
                if idempotency_key and seq:
                    self._idempotency_index[idempotency_key] = seq
                    max_seq = max(max_seq, seq)

        self._next_seq = max_seq + 1

    def _assign_seq(self) -> int:
        """Assign a new monotonically increasing sequence number."""
        seq = self._next_seq
        self._next_seq += 1
        return seq

    def _check_idempotency(self, idempotency_key: str) -> Optional[int]:
        """Check if an event with the given idempotency key exists.

        Args:
            idempotency_key: The deduplication key to check

        Returns:
            The existing seq if found, None otherwise
        """
        return self._idempotency_index.get(idempotency_key)

    def append_event(
        self,
        event_id: str,
        idempotency_key: str,
        event_type: str,
        payload: dict,
        base_state_version: int = 0,
        actor: str = "user",
        batch_id: Optional[str] = None,
        schema_version: str = "1.0",
    ) -> tuple[int, bool]:
        """Append a new event to the log.

        Args:
            event_id: Globally unique event identity
            idempotency_key: Stable deduplication key
            event_type: Type of the event
            payload: Event payload
            base_state_version: State version observed when proposing
            actor: Origin of the event
            batch_id: Optional batch identifier
            schema_version: Schema version

        Returns:
            Tuple of (seq, was_new) where was_new is True if event was appended,
            False if it was a duplicate
        """
        # Check idempotency
        existing_seq = self._check_idempotency(idempotency_key)
        if existing_seq is not None:
            return existing_seq, False

        # Assign new seq
        seq = self._assign_seq()

        # Create event
        event = {
            "event_id": event_id,
            "idempotency_key": idempotency_key,
            "seq": seq,
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "schema_version": schema_version,
            "payload": payload,
            "base_state_version": base_state_version,
            "actor": actor,
        }
        if batch_id:
            event["batch_id"] = batch_id

        # Append to file
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

        # Update index
        self._idempotency_index[idempotency_key] = seq

        return seq, True

    def read_events(
        self,
        from_seq: Optional[int] = None,
        to_seq: Optional[int] = None,
    ) -> Iterator[SystemEvent]:
        """Read events from the log in seq order.

        Args:
            from_seq: Start from this seq (inclusive), None for beginning
            to_seq: End at this seq (inclusive), None for all

        Yields:
            SystemEvent objects in ascending seq order

        Raises:
            ValueError: If JSON is malformed or event data is invalid
        """
        if not self.log_file.exists():
            return

        with open(self.log_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    event_data = json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Malformed JSON at line {line_num}: {e}") from e

                seq = event_data.get("seq", 0)

                # Filter by seq range
                if from_seq is not None and seq < from_seq:
                    continue
                if to_seq is not None and seq > to_seq:
                    continue

                try:
                    yield SystemEvent(**event_data)
                except Exception as e:
                    raise ValueError(f"Invalid event data at line {line_num}: {e}") from e

    def get_events_by_batch(self, batch_id: str) -> list[SystemEvent]:
        """Get all events with the given batch_id.

        Args:
            batch_id: The batch identifier

        Returns:
            List of events in the batch
        """
        events = []
        for event in self.read_events():
            if event.batch_id == batch_id:
                events.append(event)
        return events

    def get_event_count(self) -> int:
        """Get the total number of events in the log."""
        return self._next_seq - 1

    def get_max_seq(self) -> int:
        """Get the maximum seq in the log."""
        return self._next_seq - 1
