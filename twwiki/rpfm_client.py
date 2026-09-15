"""Minimal WebSocket client for rpfm_server.

Wire format (from RPFM's server docs, docs/server/ws-protocol.md):

    send:    {"id": <int>, "data": "<Command>"}                 # no arguments
             {"id": <int>, "data": {"<Command>": <arg>}}         # one argument
             {"id": <int>, "data": {"<Command>": [a, b, ...]}}   # several
    receive: {"id": <int>, "data": "<Response>"}  or  {"id": <int>, "data": {"<Response>": <payload>}}

Commands and responses are serde externally-tagged enums, which is why a
no-argument command is a bare string rather than {"Command": null}.

On connect the server pushes {"id": 0, "data": {"SessionConnected": <id>}}.
Failures come back as {"Error": "<message>"}. Before closing, send
"ClientDisconnecting" so the server drops the session immediately instead of
holding it for its 5-minute reconnect grace period.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

import websockets

log = logging.getLogger(__name__)

# --- Command surface -------------------------------------------------------
# Command names from docs/server/ws-commands.md, verified against
# rpfm_server 5.0.6.
CMD = {
    # [game_key, rebuild_dependencies]
    #   -> {CompressionFormatDependenciesInfo: [CompressionFormat, DependenciesInfo | null]}
    # Per session: loads that game's schema and dependency cache.
    "select_game": "SetGameSelected",
    # no args -> {Bool: bool}. There is no schema-version command.
    "schema_loaded": "IsSchemaLoaded",
    # [pack_key, path, DataSource] -> {DBRFileInfo: [DB, RFileInfo]}
    #   or {LocRFileInfo: [Loc, RFileInfo]}. With DataSource "GameFiles" the
    #   pack_key is unused and the file comes from the dependency cache.
    "decode": "DecodePackedFile",
    # Definition -> {VecField: [Field, ...]} in the order row cells use.
    "fields_processed": "FieldsProcessed",
}


class RpfmError(RuntimeError):
    pass


@dataclass
class RpfmClient:
    url: str = "ws://127.0.0.1:45127/ws"
    timeout_s: float = 120.0
    session_id: int | None = None
    _ws: Any = field(default=None, repr=False)
    _next_id: int = field(default=1, repr=False)

    async def __aenter__(self) -> "RpfmClient":
        # Decoded tables can be many MB, so lift the default frame-size limit.
        self._ws = await websockets.connect(self.url, max_size=None)
        greeting = await self._recv()
        if _variant(greeting) != "SessionConnected":
            await self._ws.close()
            raise RpfmError(f"expected SessionConnected, got: {greeting}")
        self.session_id = _payload(greeting)
        log.info("connected: session %s", self.session_id)
        return self

    async def __aexit__(self, *exc) -> None:
        if self._ws is None:
            return
        try:
            # The server does not reply to this one.
            await self._send("ClientDisconnecting")
        except websockets.ConnectionClosed:
            pass
        await self._ws.close()

    async def _recv(self) -> dict:
        raw = await asyncio.wait_for(self._ws.recv(), timeout=self.timeout_s)
        return json.loads(raw)

    async def _send(self, data: Any) -> int:
        msg_id = self._next_id
        self._next_id += 1
        await self._ws.send(json.dumps({"id": msg_id, "data": data}))
        return msg_id

    async def call(self, command: str, args: Any = None) -> Any:
        """Send one command, return the payload of its response.

        Pass `args` as a list for multi-argument commands. Raises RpfmError on
        an Error response.
        """
        msg_id = await self._send(command if args is None else {command: args})

        while True:
            msg = await self._recv()
            if msg.get("id") != msg_id:
                log.debug("ignoring out-of-band message: %s", _variant(msg))
                continue
            if _variant(msg) == "Error":
                raise RpfmError(f"{command} failed: {_payload(msg)}")
            return _payload(msg)

    async def probe(self, requests: list[tuple[str, Any]]) -> dict[str, Any]:
        """Send each (command, args) pair and record whatever comes back.

        Used to map the server surface. Errors are captured, not raised --
        an error response still tells you the command exists and what shape
        of argument it wanted.
        """
        results: dict[str, Any] = {}
        for command, args in requests:
            label = command if args is None else f"{command} {json.dumps(args)}"
            try:
                results[label] = await self.call(command, args)
            except RpfmError as e:
                results[label] = {"_error": str(e)}
            except asyncio.TimeoutError:
                results[label] = {"_error": f"no response in {self.timeout_s}s"}
        return results


def _variant(msg: dict) -> str | None:
    data = msg.get("data")
    if isinstance(data, dict) and len(data) == 1:
        return next(iter(data))
    if isinstance(data, str):
        return data
    return None


def _payload(msg: dict) -> Any:
    data = msg.get("data")
    if isinstance(data, dict) and len(data) == 1:
        return next(iter(data.values()))
    return data
