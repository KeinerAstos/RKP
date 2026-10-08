"""Cola acotada y estado publicable para consultas Helix lentas."""

from __future__ import annotations

import queue
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

TTL_SECONDS = 120
MAX_CACHED_OLTS = 32
MAX_PENDING_OLTS = 32
MAX_TERMINAL_STATES = 32
MAX_BATCH_OLTS = 3
ERROR_RETRY_SECONDS = 30


@dataclass
class JobState:
    olt: str
    job_id: str
    generation: int
    estado: str
    creado_en: float
    alcance: str = "todos_los_puertos_olt"
    iniciado_at: float | None = None
    finalizado_at: float | None = None
    iniciado_en: str | None = None
    finalizado_en: str | None = None
    consultado_en: str | None = None
    casos_por_puerto: dict[str, list[dict[str, Any]]] | None = None
    error_codigo: str | None = None
    error: str | None = None
    retry_at: float = 0.0
    revision: int = 0


class HelixWorker:
    """Un único hilo Oracle por proceso y un límite explícito de OLT en espera."""

    def __init__(
        self,
        query: Callable[[str, Callable[[Callable[[], None] | None], None]], tuple[dict[str, list[dict[str, Any]]], str]],
        *,
        ttl_seconds: int = TTL_SECONDS,
        max_pending: int = MAX_PENDING_OLTS,
        max_cache: int = MAX_CACHED_OLTS,
        retry_seconds: int = ERROR_RETRY_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._query = query
        self._ttl_seconds = max(0, ttl_seconds)
        self._max_cache = max(1, max_cache)
        self._retry_seconds = max(0, retry_seconds)
        self._clock = clock
        self._queue: queue.Queue[tuple[str, str, int]] = queue.Queue(maxsize=max(1, max_pending))
        self._states: OrderedDict[str, JobState] = OrderedDict()
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._accepting = False
        self._stopping = threading.Event()
        self._active_cancel: Callable[[], None] | None = None
        self._active_olt: str | None = None
        self._generation = 0
        self._reserved_pending = 0

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                self._accepting = True
                return
            self._stopping.clear()
            self._accepting = True
            self._thread = threading.Thread(
                target=self._run,
                name="helix-oracle-worker",
                daemon=True,
            )
            self._thread.start()

    def stop(self, join_seconds: float = 2.0) -> None:
        cancel: Callable[[], None] | None
        with self._lock:
            self._accepting = False
            self._stopping.set()
            while True:
                try:
                    self._queue.get_nowait()
                    self._queue.task_done()
                except queue.Empty:
                    break
            self._reserved_pending = 0
            cancel = self._active_cancel
            thread = self._thread
        if cancel:
            try:
                cancel()
            except Exception:
                pass
        if thread and thread.is_alive():
            thread.join(timeout=max(0.0, join_seconds))

    def _evict_terminal_locked(self) -> None:
        terminal = [olt for olt, item in self._states.items() if item.estado in {"listo", "error"}]
        while len(terminal) > self._max_cache:
            victim = terminal.pop(0)
            self._states.pop(victim, None)

    def _schedule_locked(self, olt: str, previous: JobState | None) -> JobState:
        if not self._accepting:
            return JobState(
                olt=olt, job_id="", generation=0, estado="error", creado_en=self._clock(),
                error_codigo="WORKER_STOPPED", error="La consulta Helix no está disponible temporalmente",
            )
        if self._reserved_pending >= self._queue.maxsize:
            return JobState(
                olt=olt, job_id="", generation=self._generation + 1, estado="error", creado_en=self._clock(),
                error_codigo="QUEUE_FULL", error="Hay demasiadas consultas Helix pendientes; reintente en la próxima actualización",
            )
        self._evict_terminal_locked()
        generation = self._generation + 1
        job_id = uuid.uuid4().hex
        try:
            self._queue.put_nowait((olt, job_id, generation))
        except queue.Full:
            return JobState(
                olt=olt, job_id="", generation=generation, estado="error", creado_en=self._clock(),
                error_codigo="QUEUE_FULL", error="Hay demasiadas consultas Helix pendientes; reintente en la próxima actualización",
            )
        self._reserved_pending += 1
        self._generation = generation
        state = JobState(
            olt=olt,
            job_id=job_id,
            generation=generation,
            estado="actualizando",
            creado_en=self._clock(),
            iniciado_en=None,
            finalizado_en=None,
            consultado_en=previous.consultado_en if previous else None,
            casos_por_puerto=None,
            revision=(previous.revision + 1) if previous else 1,
        )
        self._states[olt] = state
        self._states.move_to_end(olt)
        return state

    def _state_locked(self, olt: str) -> JobState | None:
        state = self._states.get(olt)
        if state:
            self._states.move_to_end(olt)
        return state

    def submit(self, olt: str, ports: list[str]) -> dict[str, Any]:
        now = self._clock()
        with self._lock:
            state = self._state_locked(olt)
            if state and state.estado == "actualizando":
                return self._snapshot_locked(state, ports)
            if state and state.estado == "listo" and state.finalizado_at is not None:
                if now - state.finalizado_at < self._ttl_seconds:
                    return self._snapshot_locked(state, ports)
            if state and state.estado == "error" and now < state.retry_at:
                return self._snapshot_locked(state, ports)
            state = self._schedule_locked(olt, state)
            if state.estado == "error":
                # Queue rejection isn't persisted as a false terminal result.
                return self._snapshot_locked(state, ports)
            return self._snapshot_locked(state, ports)

    def read(self, olt: str, ports: list[str]) -> dict[str, Any]:
        with self._lock:
            state = self._state_locked(olt)
            if not state:
                return {
                    "olt": olt, "estado": "sin_solicitud", "consultado_en": None,
                    "puertos": {port: {"estado": "sin_solicitud", "casos": None} for port in ports},
                }
            if state.estado == "listo" and state.finalizado_at is not None:
                if self._clock() - state.finalizado_at >= self._ttl_seconds:
                    return {
                        "olt": olt, "estado": "expirado", "consultado_en": state.consultado_en,
                        "puertos": {port: {"estado": "expirado", "casos": None} for port in ports},
                    }
            return self._snapshot_locked(state, ports)

    def _snapshot_locked(self, state: JobState, ports: list[str]) -> dict[str, Any]:
        if state.estado == "listo":
            port_results = {
                port: {"estado": "listo", "casos": list((state.casos_por_puerto or {}).get(port, []))}
                for port in ports
            }
        elif state.estado == "error":
            port_results = {
                port: {"estado": "error", "casos": None,
                       "error": {"codigo": state.error_codigo, "mensaje": state.error}}
                for port in ports
            }
        else:
            port_results = {
                port: {"estado": "actualizando", "casos": None}
                for port in ports
            }
        result: dict[str, Any] = {
            "olt": state.olt,
            "estado": state.estado,
            "job_id": state.job_id or None,
            "generacion": state.generation,
            "revision": state.revision,
            "alcance": state.alcance,
            "iniciado_en": state.iniciado_en,
            "finalizado_en": state.finalizado_en,
            "consultado_en": state.consultado_en,
            "puertos": port_results,
        }
        if state.estado == "error":
            result["error"] = {"codigo": state.error_codigo, "mensaje": state.error}
        return result

    def _run(self) -> None:
        while not self._stopping.is_set():
            try:
                first = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            batch = [first]
            for _ in range(MAX_BATCH_OLTS - 1):
                try:
                    batch.append(self._queue.get_nowait())
                except queue.Empty:
                    break
            for job in batch:
                try:
                    if self._stopping.is_set():
                        continue
                    self._execute(job)
                finally:
                    self._queue.task_done()

    def _execute(self, job: tuple[str, str, int]) -> None:
        olt, job_id, generation = job
        with self._lock:
            state = self._states.get(olt)
            if not state or state.job_id != job_id or state.generation != generation:
                return
            state.iniciado_at = self._clock()
            state.iniciado_en = datetime.now(timezone.utc).isoformat(timespec="seconds")
            self._active_olt = olt
            self._reserved_pending = max(0, self._reserved_pending - 1)

        def register_cancel(cancel: Callable[[], None] | None) -> None:
            cancel_now = False
            with self._lock:
                if self._active_olt == olt:
                    self._active_cancel = cancel
                    cancel_now = self._stopping.is_set() and cancel is not None
            if cancel_now and cancel:
                try:
                    cancel()
                except Exception:
                    pass

        try:
            result, consulted_at = self._query(olt, register_cancel)
            if self._stopping.is_set():
                return
            with self._lock:
                current = self._states.get(olt)
                if current and current.job_id == job_id and current.generation == generation:
                    current.estado = "listo"
                    current.casos_por_puerto = result
                    current.consultado_en = consulted_at
                    current.finalizado_at = self._clock()
                    current.finalizado_en = datetime.now(timezone.utc).isoformat(timespec="seconds")
                    current.error = None
                    current.error_codigo = None
                    current.retry_at = 0.0
                    current.revision += 1
                    self._states.move_to_end(olt)
        except Exception:
            with self._lock:
                current = self._states.get(olt)
                if current and current.job_id == job_id and current.generation == generation:
                    current.estado = "error"
                    current.casos_por_puerto = None
                    current.finalizado_at = self._clock()
                    current.finalizado_en = datetime.now(timezone.utc).isoformat(timespec="seconds")
                    current.error_codigo = "QUERY_FAILED"
                    current.error = "No se pudo consultar Oracle Helix; se reintentará más tarde"
                    current.retry_at = self._clock() + self._retry_seconds
                    current.revision += 1
                    self._states.move_to_end(olt)
        finally:
            with self._lock:
                if self._active_olt == olt:
                    self._active_cancel = None
                    self._active_olt = None
            self._trim_terminal_states()

    def _trim_terminal_states(self) -> None:
        with self._lock:
            terminal = [olt for olt, state in self._states.items() if state.estado in {"listo", "error"}]
            while len(terminal) > self._max_cache:
                victim = terminal.pop(0)
                self._states.pop(victim, None)


_worker: HelixWorker | None = None
_worker_lock = threading.Lock()


def start_worker(query: Callable[[str, Callable[[Callable[[], None] | None], None]], tuple[dict[str, list[dict[str, Any]]], str]], **options: Any) -> HelixWorker:
    global _worker
    with _worker_lock:
        if _worker is not None:
            _worker.stop()
        _worker = HelixWorker(query, **options)
        _worker.start()
        return _worker


def stop_worker() -> None:
    global _worker
    with _worker_lock:
        worker = _worker
        _worker = None
    if worker:
        worker.stop()


def get_worker() -> HelixWorker | None:
    return _worker
