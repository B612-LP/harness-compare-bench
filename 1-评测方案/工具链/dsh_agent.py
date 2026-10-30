"""Harbor custom agent adapter for the DeepSeek Harness CLI (`dsh`).

Used as ``-a dsh_agent:Dsh`` with PYTHONPATH pointing at this directory.

Design notes (2026-10-16, validated against the dsh-proto smoke run):
- dsh 0.2.0-rc.2 requires Node >= 24: its bin.js entry guard is
  ``if (import.meta.main)``, which is silently undefined on Node 22 — the CLI
  then exits 0 printing nothing. Install pins Node 24.
- Model/provider routing is config-layer only: headless has no per-run --model.
  ``--ak config=</path/cordis.patch.yml>`` uploads the patch to
  ``$DSH_HOME/profiles/headless/cordis.patch.yml`` (the profile user layer).
- ``--json`` emits the documented run-event vocabulary (session / status /
  thinking / text / tool_call / tool_result / error / final) which this adapter
  converts to ATIF v1.7. The answer stream is kept as-is in ``dsh.txt``.
- Permissions: DSH_PERMISSION_MODE=danger-full-access mirrors Codex's
  ``--dangerously-bypass-approvals-and-sandbox`` for unattended batch parity.
"""

from __future__ import annotations

import json
import shlex
from pathlib import Path, PurePosixPath
from typing import Any, override

from harbor.agents.capabilities import AgentCapabilities
from harbor.agents.installed.base import (
    BaseInstalledAgent,
    with_prompt_template,
)
from harbor.agents.options import InstalledAgentOptions
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.models.trajectories import (
    Agent,
    FinalMetrics,
    Metrics,
    Observation,
    ObservationResult,
    Step,
    ToolCall,
    Trajectory,
)
from harbor.utils.trajectory_utils import format_trajectory_json


class Dsh(BaseInstalledAgent):
    """Run tasks with the DeepSeek Harness CLI (dsh headless)."""

    capabilities = AgentCapabilities(
        atif=True,
        resume=False,
        load_native_trajectory=False,
        load_atif_trajectory=False,
        native_config=True,
        skills=False,
        mcp_servers=False,
    )

    _OUTPUT_FILENAME = "dsh.txt"
    _STDERR_FILENAME = "dsh-stderr.txt"
    _REMOTE_DSH_HOME = PurePosixPath("/tmp/dsh-home")
    _PATCH_REMOTE_PATH = PurePosixPath("/tmp/dsh-home/profiles/headless/cordis.patch.yml")

    _INSTALL_CHECK_COMMAND = (
        "if [ -s ~/.nvm/nvm.sh ]; then . ~/.nvm/nvm.sh; fi; "
        "command -v dsh >/dev/null 2>&1"
    )
    _INSTALL_VERSION_COMMAND = (
        "if [ -s ~/.nvm/nvm.sh ]; then . ~/.nvm/nvm.sh; fi; dsh --version"
    )

    # Without this declaration Harbor silently drops --ak kwargs (version/config).
    options_model = InstalledAgentOptions
    options: InstalledAgentOptions

    @staticmethod
    @override
    def name() -> str:
        return "dsh"

    @property
    def _trajectory_path(self) -> Path:
        return self.logs_dir / "trajectory.json"

    @override
    def get_version_command(self) -> str | None:
        return self._INSTALL_VERSION_COMMAND

    @override
    def parse_version(self, stdout: str) -> str:
        for line in stdout.strip().splitlines():
            line = line.strip()
            if line:
                return line
        return stdout.strip()

    @override
    async def install(self, environment: BaseEnvironment) -> None:
        if await self._installed_dsh_satisfies_version(environment):
            self.logger.debug("dsh is already available at the requested version")
            return

        await self.ensure_system_dependencies(
            environment, ("curl", "bash", "nodejs", "npm")
        )
        version_spec = f"@{self._version}" if self._version else "@latest"
        await self.exec_as_agent(
            environment,
            command=(
                "set -euo pipefail; "
                # Node 24 is a hard requirement (import.meta.main entry guard).
                "curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | bash &&"
                '  export NVM_DIR="$HOME/.nvm" &&'
                '  \\. "$NVM_DIR/nvm.sh" || true &&'
                "  command -v nvm &>/dev/null || { echo 'Error: NVM failed to load' >&2; exit 1; } &&"
                "  nvm install 24 && nvm alias default 24 && npm -v &&"
                f"  npm install -g @deepseek-ai/dsh{version_spec};"
                "dsh --version"
            ),
            env={"NVM_NODEJS_ORG_MIRROR": "https://nodejs.org/dist"},
        )
        await self.exec_as_root(
            environment,
            command=(
                "for bin in node dsh; do"
                '  BIN_PATH="$(which "$bin" 2>/dev/null || true)";'
                '  if [ -n "$BIN_PATH" ] && [ "$BIN_PATH" != "/usr/local/bin/$bin" ]; then'
                '    ln -sf "$BIN_PATH" "/usr/local/bin/$bin";'
                "  fi;"
                " done"
            ),
        )

    async def _installed_dsh_satisfies_version(
        self, environment: BaseEnvironment
    ) -> bool:
        if self._version is None:
            result = await environment.exec(command=self._INSTALL_CHECK_COMMAND)
            return result.return_code == 0
        result = await environment.exec(command=self._INSTALL_VERSION_COMMAND)
        if result.return_code != 0:
            return False
        return self.parse_version(result.stdout or "") == self._version

    def _build_env(self) -> dict[str, str]:
        return {
            "DSH_HOME": self._REMOTE_DSH_HOME.as_posix(),
            # Parity with Codex's --dangerously-bypass-approvals-and-sandbox.
            "DSH_PERMISSION_MODE": "danger-full-access",
        }

    def _upload_patch(self) -> str | None:
        """Render the shell fragment that installs the profile user layer."""
        config_source = self.config_source
        if config_source is None:
            return None
        if isinstance(config_source, dict):
            raise ValueError(
                "dsh adapter expects --ak config=</path/to/cordis.patch.yml>; "
                "inline JSON configs are not supported"
            )
        return config_source

    @override
    @with_prompt_template
    async def run(
        self, instruction: str, environment: BaseEnvironment, context: AgentContext
    ) -> None:
        self._last_instruction = instruction
        env = self._build_env()
        logs_dir = self.environment_logs_dir.as_posix()
        home = self._REMOTE_DSH_HOME.as_posix()

        await self.exec_as_agent(
            environment,
            command=(
                f"mkdir -p {shlex.quote(home)} {shlex.quote(logs_dir)} "
                f"{shlex.quote(self._PATCH_REMOTE_PATH.parent.as_posix())}"
            ),
            env=env,
        )

        patch_path = self._upload_patch()
        if patch_path is not None:
            content = Path(patch_path).read_text(encoding="utf-8")
            await self._upload_config_text(
                environment,
                content=content,
                remote_path=self._PATCH_REMOTE_PATH.as_posix(),
                filename="cordis.patch.yml",
            )

        try:
            await self.exec_as_agent(
                environment,
                command=(
                    "if [ -s ~/.nvm/nvm.sh ]; then . ~/.nvm/nvm.sh; fi; "
                    f"printf %s {shlex.quote(instruction)} | "
                    "dsh headless --json - "
                    f"2> {shlex.quote(f'{logs_dir}/{self._STDERR_FILENAME}')} | "
                    f"tee {shlex.quote(f'{logs_dir}/{self._OUTPUT_FILENAME}')}"
                ),
                env=env,
            )
        finally:
            try:
                await self.exec_as_agent(
                    environment,
                    command=(
                        f"mkdir -p {shlex.quote(logs_dir)}\n"
                        f'if [ -d "{home}/sessions" ]; then\n'
                        f"  rm -rf {shlex.quote(f'{logs_dir}/sessions')}\n"
                        f'  cp -R "{home}/sessions" {shlex.quote(f"{logs_dir}/sessions")}\n'
                        "fi"
                    ),
                    env=env,
                )
            except Exception:
                self.logger.debug("Failed to copy dsh session logs", exc_info=True)
            try:
                await self.exec_as_agent(
                    environment,
                    command=f"rm -rf {shlex.quote(home)}",
                    env=env,
                )
            except Exception:
                pass

    @override
    def convert_trajectory(self, logs_dir: Path) -> Trajectory | None:
        output_path = logs_dir / self._OUTPUT_FILENAME
        if not output_path.exists():
            return None

        events: list[dict[str, Any]] = []
        for line in output_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                # Diagnostics may leak into the stream; skip non-events.
                continue
        if not events:
            return None

        return self._events_to_trajectory(events)

    def _events_to_trajectory(self, events: list[dict[str, Any]]) -> Trajectory | None:
        session_id = None
        turn_reason = None
        agent_errors: list[str] = []
        final_text = None

        steps: list[Step] = []
        current: dict[str, Any] | None = None

        def flush_current() -> None:
            nonlocal current
            if current is None:
                return
            steps.append(self._step_from_accumulator(current, len(steps) + 1))
            current = None

        # Step 1 records the task text (the stream does not echo user turns).
        steps.append(
            Step(
                step_id=1,
                source="user",
                message=self._instruction_for_trajectory or "",
            )
        )

        for event in events:
            etype = event.get("type")
            if etype == "session":
                session_id = event.get("sessionId")
            elif etype == "status":
                phase = event.get("phase")
                if phase == "step_start":
                    flush_current()
                    current = {"reasoning": [], "text": [], "calls": [], "results": {}}
                elif phase == "step_end":
                    if current is None:
                        current = {"reasoning": [], "text": [], "calls": [], "results": {}}
                    current["usage"] = event.get("usage")
                    flush_current()
                elif phase == "turn_end":
                    reason = event.get("reason") or {}
                    turn_reason = reason.get("kind") if isinstance(reason, dict) else reason
            elif etype == "thinking":
                if current is None:
                    current = {"reasoning": [], "text": [], "calls": [], "results": {}}
                current["reasoning"].append(event.get("text") or "")
            elif etype == "text":
                if current is None:
                    current = {"reasoning": [], "text": [], "calls": [], "results": {}}
                current["text"].append(event.get("text") or "")
            elif etype == "tool_call":
                if current is None:
                    current = {"reasoning": [], "text": [], "calls": [], "results": {}}
                current["calls"].append(
                    {
                        "call_id": event.get("callId") or "",
                        "tool": event.get("tool") or "",
                        "input": event.get("input") or {},
                    }
                )
            elif etype == "tool_result":
                if current is None:
                    current = {"reasoning": [], "text": [], "calls": [], "results": {}}
                current["results"][event.get("callId") or ""] = {
                    "status": event.get("status"),
                    "result": event.get("result"),
                }
            elif etype == "error":
                agent_errors.append(event.get("message") or "")
            elif etype == "final":
                final_text = event.get("text")

        flush_current()

        if len(steps) <= 1:
            # No model steps: still expose the final answer if any.
            if final_text:
                steps.append(Step(step_id=2, source="agent", message=final_text))
            else:
                return None

        agent_extra: dict[str, Any] = {}
        if turn_reason:
            agent_extra["turn_end_reason"] = turn_reason
        if agent_errors:
            agent_extra["errors"] = agent_errors

        totals = {"prompt": 0, "completion": 0, "cached": 0, "total": 0}
        saw_usage = False
        for step in steps:
            if step.metrics:
                saw_usage = True
                totals["prompt"] += step.metrics.prompt_tokens or 0
                totals["completion"] += step.metrics.completion_tokens or 0
                totals["cached"] += step.metrics.cached_tokens or 0
                totals["total"] += (step.metrics.extra or {}).get("total_tokens") or 0

        final_metrics = FinalMetrics(
            total_prompt_tokens=totals["prompt"] if saw_usage else None,
            total_completion_tokens=totals["completion"] or None,
            total_cached_tokens=totals["cached"] or None,
            total_cost_usd=None,  # LiteLLM has no GLM pricing; filled offline.
            total_steps=len(steps),
            extra={"total_tokens": totals["total"]} if saw_usage else None,
        )

        return Trajectory(
            schema_version="ATIF-v1.7",
            session_id=session_id,
            agent=Agent(
                name="dsh",
                version=self._version or "unknown",
                model_name=self.model_name,
                extra=agent_extra or None,
            ),
            steps=steps,
            final_metrics=final_metrics,
        )

    @property
    def _instruction_for_trajectory(self) -> str | None:
        # The prompt template wrapper stores the rendered instruction here.
        return getattr(self, "_last_instruction", None)

    def _step_from_accumulator(self, acc: dict[str, Any], step_id: int) -> Step:
        tool_calls: list[ToolCall] = []
        results: list[ObservationResult] = []
        for call in acc.get("calls", []):
            call_id = call["call_id"]
            arguments = call.get("input")
            if not isinstance(arguments, dict):
                arguments = {"value": arguments}
            tool_calls.append(
                ToolCall(
                    tool_call_id=call_id,
                    function_name=call["tool"],
                    arguments=arguments,
                )
            )
            result = (acc.get("results") or {}).get(call_id)
            if result is not None:
                results.append(
                    ObservationResult(
                        source_call_id=call_id or None,
                        content=result.get("result"),
                    )
                )

        usage = acc.get("usage") or {}
        metrics = None
        if usage:
            metrics = Metrics(
                prompt_tokens=usage.get("inputTokens"),
                completion_tokens=usage.get("outputTokens"),
                cached_tokens=usage.get("cacheReadTokens"),
                extra={"total_tokens": usage.get("totalTokens")},
            )

        reasoning = "\n".join(x for x in acc.get("reasoning", []) if x) or None
        message = "\n\n".join(x for x in acc.get("text", []) if x) or None

        return Step(
            step_id=step_id,
            source="agent",
            message=message or "",
            reasoning_content=reasoning,
            model_name=self.model_name,
            llm_call_count=1,
            tool_calls=tool_calls or None,
            observation=Observation(results=results) if results else None,
            metrics=metrics,
        )

    @override
    def populate_context_post_run(self, context: AgentContext) -> None:
        try:
            trajectory = self.convert_trajectory(self.logs_dir)
        except Exception:
            self.logger.exception("Failed to convert dsh events to trajectory")
            return
        if not trajectory:
            self.logger.debug("No dsh trajectory produced")
            return

        try:
            self._trajectory_path.write_text(
                format_trajectory_json(trajectory.to_json_dict()), encoding="utf-8"
            )
        except OSError as exc:
            self.logger.debug(f"Failed to write trajectory file: {exc}")

        if trajectory.final_metrics:
            metrics = trajectory.final_metrics
            context.cost_usd = metrics.total_cost_usd
            context.n_input_tokens = metrics.total_prompt_tokens or 0
            context.n_cache_tokens = metrics.total_cached_tokens or 0
            context.n_output_tokens = metrics.total_completion_tokens or 0
