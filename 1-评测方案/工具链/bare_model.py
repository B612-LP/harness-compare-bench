"""Harbor custom agent: bare model baseline (C group).

Zero-scaffold attribution baseline: the task instruction goes to the model
API verbatim (no system prompt, no tools, no iteration), and the model's final
answer text is written verbatim to ``--ak output_path=...``. The same
deterministic verifier then scores the file — so A − C measures exactly what
the Harness layer adds on top of the raw model.

Used as ``-a bare_model:BareModel`` with PYTHONPATH pointing at this
directory. The model endpoint is Xiaomi MiMo via its Token Plan OpenAI
compatible API; the API call runs inside the task container under the same
proxy overlay as the Codex/DSH runs (same network conditions).
"""

from __future__ import annotations

import json
import shlex
from pathlib import Path, PurePosixPath
from typing import Annotated, Any, override

from harbor.agents.capabilities import AgentCapabilities
from harbor.agents.installed.base import (
    BaseInstalledAgent,
    with_prompt_template,
)
from harbor.agents.options import Cli, InstalledAgentOptions
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.models.trajectories import (
    Agent,
    FinalMetrics,
    Metrics,
    Step,
    Trajectory,
)
from harbor.utils.trajectory_utils import format_trajectory_json


class BareModelOptions(InstalledAgentOptions):
    output_path: Annotated[str, Cli("--output-path", format="--output-path {value}")] = (
        "/app/output.txt"
    )


class BareModel(BaseInstalledAgent):
    """Send the instruction to a raw model API and save the answer verbatim."""

    capabilities = AgentCapabilities(
        atif=True,
        resume=False,
        load_native_trajectory=False,
        load_atif_trajectory=False,
        native_config=False,
        skills=False,
        mcp_servers=False,
    )

    options_model = BareModelOptions
    options: BareModelOptions

    _BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"
    _RESPONSE_FILENAME = "bare-response.json"
    _REQUEST_FILENAME = "bare-request.json"
    _REMOTE_TMP = PurePosixPath("/tmp/bare-model")

    @staticmethod
    @override
    def name() -> str:
        return "bare-model"

    @override
    def get_version_command(self) -> str | None:
        return None

    @override
    async def install(self, environment: BaseEnvironment) -> None:
        await self.ensure_system_dependencies(environment, ("curl",))

    @override
    @with_prompt_template
    async def run(
        self, instruction: str, environment: BaseEnvironment, context: AgentContext
    ) -> None:
        self._last_instruction = instruction
        model = self.model_name or "mimo-v2.6-flash"
        output_path = self.options.output_path
        logs_dir = self.environment_logs_dir.as_posix()
        remote_req = (self._REMOTE_TMP / "request.json").as_posix()
        remote_resp = (self._REMOTE_TMP / "response.json").as_posix()

        env = {"XIAOMI_BASE_URL": self._BASE_URL}

        await self.exec_as_agent(
            environment,
            command=(
                f"mkdir -p {shlex.quote(self._REMOTE_TMP.as_posix())} "
                f"{shlex.quote(logs_dir)}"
            ),
            env=env,
        )

        request_body = {"model": model, "input": instruction}
        request_json = json.dumps(request_body, ensure_ascii=False)
        await self.exec_as_agent(
            environment,
            command=(
                f"printf %s {shlex.quote(request_json)} > {shlex.quote(remote_req)}"
            ),
            env=env,
        )

        result = await self.exec_as_agent(
            environment,
            command=(
                "curl -sS --fail-with-body -X POST "
                '"$XIAOMI_BASE_URL/responses" '
                '-H "Authorization: Bearer $XIAOMI_API_KEY" '
                '-H "Content-Type: application/json" '
                f"--data-binary @{shlex.quote(remote_req)} "
                f"-o {shlex.quote(remote_resp)} "
                f"&& cp {shlex.quote(remote_resp)} {shlex.quote(f'{logs_dir}/{self._RESPONSE_FILENAME}')} "
                f"&& cp {shlex.quote(remote_req)} {shlex.quote(f'{logs_dir}/{self._REQUEST_FILENAME}')} "
                f"&& cat {shlex.quote(remote_resp)}"
            ),
            env=env,
        )

        try:
            response = json.loads(result.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"bare model response is not JSON: {exc}") from exc

        answer = self._extract_output_text(response)
        reasoning = self._extract_reasoning(response)
        usage = response.get("usage") or {}
        self._bare_result = {
            "answer": answer,
            "reasoning": reasoning,
            "usage": usage,
            "model": response.get("model") or model,
            "status": response.get("status"),
        }

        await self.exec_as_agent(
            environment,
            command=(
                f"printf %s {shlex.quote(answer)} "
                f"> {shlex.quote(output_path)}"
            ),
            env=env,
        )

    @staticmethod
    def _extract_output_text(response: dict[str, Any]) -> str:
        text = response.get("output_text")
        if isinstance(text, str):
            return text
        parts: list[str] = []
        for item in response.get("output") or []:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for block in item.get("content") or []:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    parts.append(block["text"])
        return "\n".join(parts)

    @staticmethod
    def _extract_reasoning(response: dict[str, Any]) -> str | None:
        parts: list[str] = []
        for item in response.get("output") or []:
            if not isinstance(item, dict) or item.get("type") != "reasoning":
                continue
            for block in item.get("content") or []:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    parts.append(block["text"])
        return "\n".join(parts) or None

    @override
    def convert_trajectory(self, logs_dir: Path) -> Trajectory | None:
        result = getattr(self, "_bare_result", None)
        if result is None:
            resp_path = logs_dir / self._RESPONSE_FILENAME
            if not resp_path.exists():
                return None
            response = json.loads(resp_path.read_text(encoding="utf-8"))
            result = {
                "answer": self._extract_output_text(response),
                "reasoning": self._extract_reasoning(response),
                "usage": response.get("usage") or {},
                "model": response.get("model"),
                "status": response.get("status"),
            }

        usage = result.get("usage") or {}
        metrics = Metrics(
            prompt_tokens=usage.get("input_tokens"),
            completion_tokens=usage.get("output_tokens"),
            cached_tokens=(usage.get("input_tokens_details") or {}).get("cached_tokens"),
            extra={
                "reasoning_tokens": (usage.get("output_tokens_details") or {}).get(
                    "reasoning_tokens"
                ),
                "total_tokens": usage.get("total_tokens"),
            },
        )

        steps = [
            Step(step_id=1, source="user", message=self._last_instruction or ""),
            Step(
                step_id=2,
                source="agent",
                message=result.get("answer") or "",
                reasoning_content=result.get("reasoning"),
                model_name=result.get("model") or self.model_name,
                llm_call_count=1,
                metrics=metrics,
            ),
        ]

        return Trajectory(
            schema_version="ATIF-v1.7",
            session_id=None,
            agent=Agent(
                name="bare-model",
                version="api",
                model_name=result.get("model") or self.model_name,
                extra={"status": result.get("status")} if result.get("status") else None,
            ),
            steps=steps,
            final_metrics=FinalMetrics(
                total_prompt_tokens=metrics.prompt_tokens,
                total_completion_tokens=metrics.completion_tokens,
                total_cached_tokens=metrics.cached_tokens,
                total_cost_usd=None,
                total_steps=len(steps),
                extra=metrics.extra,
            ),
        )

    @override
    def populate_context_post_run(self, context: AgentContext) -> None:
        try:
            trajectory = self.convert_trajectory(self.logs_dir)
        except Exception:
            self.logger.exception("Failed to build bare-model trajectory")
            return
        if not trajectory:
            return
        try:
            (self.logs_dir / "trajectory.json").write_text(
                format_trajectory_json(trajectory.to_json_dict()), encoding="utf-8"
            )
        except OSError as exc:
            self.logger.debug(f"Failed to write trajectory: {exc}")
        if trajectory.final_metrics:
            m = trajectory.final_metrics
            context.cost_usd = m.total_cost_usd
            context.n_input_tokens = m.total_prompt_tokens or 0
            context.n_cache_tokens = m.total_cached_tokens or 0
            context.n_output_tokens = m.total_completion_tokens or 0
