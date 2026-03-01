fmt:
    just --fmt --unstable

repl:
    PYTHONPATH=src/arbitui uv run --with pydantic python

[working-directory('src')]
run-server:
    uv run uvicorn arbitui.server:app --timeout-graceful-shutdown 0

[working-directory('src')]
console-tui:
    uv run textual console -x DEBUG

[working-directory('src')]
app:
    uv run -m arbitui.app

[working-directory('src')]
app-dev:
    uv run textual -m run --dev arbitui.dev

main-app:
  PYTHONPATH=src uv run -m arbitui.app

main-db:
  PYTHONPATH=src uv run -m arbitui.db

main-proc:
  PYTHONPATH=src uv run -m arbitui.processes

ws-client:
    websocat ws://localhost:8000/ws

tui-gif:
    vhs demo.tape

socket:
  socat - UNIX-CONNECT:/tmp/rates-scope.sock
