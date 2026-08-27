# MyClaw project structure

```text
config/     configuration, permissions, tool registry, logging
core/       live view, scheduler, workflow engine
llm/        model routing and providers
memory/     conversation and long-term memory
src/        Telegram agent, parser, approvals, recovery
tools/      macOS automation and integrations
ui/         local dashboard
scripts/    diagnostics, service helpers, readiness checks
deploy/     LaunchAgent and deployment assets
tests/      manual/integration test scripts
docs/       audit, operations, and architecture notes
data/       runtime state (ignored; contains secrets/tokens)
logs/       runtime logs (ignored)
```

The root `run_telegram_bot.py` is intentionally retained as the stable
LaunchAgent entrypoint. Runtime-generated files and Python caches are excluded
from the source tree; old generated artifacts are kept under `archive/`.
