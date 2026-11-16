"""FastAPI SSE Gateway application for RepoPilot execution and live streaming."""

from __future__ import annotations

import asyncio
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from repopilot.agents.graph import create_migration_graph
from repopilot.agents.state import MigrationPhase, MigrationState
from repopilot.mcp.tools_file import apply_unified_diff
from repopilot.server.event_broadcaster import EventBroadcaster
from repopilot.server.models import (
    ApprovalRequest,
    HealthResponse,
    MigrationCreateRequest,
    MigrationSummaryResponse,
)


def create_app(
    broadcaster: EventBroadcaster | None = None,
    graph_factory: Any | None = None,
) -> FastAPI:
    """Application factory for the RepoPilot API Gateway."""
    app = FastAPI(
        title="RepoPilot API Gateway",
        description="Real-time control plane and SSE event streaming for autonomous codebase migrations.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    start_time = time.time()
    events = broadcaster or EventBroadcaster()
    tasks: dict[str, MigrationState] = {}
    compile_graph = graph_factory or create_migration_graph

    app.state.tasks = tasks
    app.state.events = events

    async def _execute_migration_task(
        task_id: str, repo_path: str, recipe: str, max_retries: int
    ) -> None:
        """Background coroutine driving the LangGraph state machine and streaming events."""
        await events.publish(
            task_id=task_id,
            event_type="migration:started",
            data={"task_id": task_id, "phase": MigrationPhase.INITIALIZE.value, "recipe": recipe},
        )

        try:
            graph = compile_graph()
            config = {"configurable": {"thread_id": f"thread_{task_id}"}}

            initial_state = {
                "task_id": task_id,
                "repo_path": repo_path,
                "recipe": recipe,
                "phase": MigrationPhase.INITIALIZE,
                "max_retries": max_retries,
            }

            # Run in worker thread to prevent blocking the async event loop
            loop = asyncio.get_running_loop()
            final_dict = await loop.run_in_executor(
                None, lambda: graph.invoke(initial_state, config=config)
            )

            # Reconstruct updated MigrationState model
            final_state = MigrationState.model_validate(final_dict)
            tasks[task_id] = final_state

            await events.publish(
                task_id=task_id,
                event_type="migration:state_update",
                data={
                    "task_id": task_id,
                    "phase": final_state.phase.value,
                    "retry_count": final_state.retry_count,
                    "patches_count": len(final_state.patches),
                    "is_terminal": final_state.is_terminal,
                    "error_message": final_state.error_message,
                },
            )

        except Exception as exc:
            failed_state = MigrationState(
                task_id=task_id,
                repo_path=repo_path,
                recipe=recipe,
                phase=MigrationPhase.FAILED,
                error_message=str(exc),
                is_terminal=True,
            )
            tasks[task_id] = failed_state
            await events.publish(
                task_id=task_id,
                event_type="migration:error",
                data={
                    "task_id": task_id,
                    "phase": MigrationPhase.FAILED.value,
                    "error_message": str(exc),
                    "is_terminal": True,
                },
            )

    @app.get("/health", response_model=HealthResponse)
    def health_check() -> HealthResponse:
        return HealthResponse(
            status="ok",
            version="0.1.0",
            uptime_seconds=round(time.time() - start_time, 2),
        )

    @app.post(
        "/api/v1/migrations",
        response_model=MigrationSummaryResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_migration(
        request: MigrationCreateRequest,
        background_tasks: BackgroundTasks,
    ) -> MigrationSummaryResponse:
        repo = Path(request.repo_path).resolve()
        if not repo.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target repository path does not exist: {request.repo_path}",
            )

        task_id = uuid.uuid4().hex[:12]
        init_state = MigrationState(
            task_id=task_id,
            repo_path=str(repo),
            recipe=request.recipe,
            phase=MigrationPhase.INITIALIZE,
            max_retries=request.max_retries,
        )
        tasks[task_id] = init_state

        background_tasks.add_task(
            _execute_migration_task,
            task_id=task_id,
            repo_path=str(repo),
            recipe=request.recipe,
            max_retries=request.max_retries,
        )

        return MigrationSummaryResponse(
            task_id=task_id,
            phase=init_state.phase.value,
            is_terminal=False,
            retry_count=0,
            patches_count=0,
            affected_files=[],
        )

    @app.get("/api/v1/migrations/{task_id}", response_model=dict[str, Any])
    def get_migration(task_id: str) -> dict[str, Any]:
        if task_id not in tasks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Task not found: {task_id}"
            )
        return tasks[task_id].model_dump()

    @app.get("/api/v1/migrations/{task_id}/stream")
    async def stream_migration_events(task_id: str) -> EventSourceResponse:
        if task_id not in tasks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Task not found: {task_id}"
            )
        return EventSourceResponse(events.subscribe(task_id))

    @app.post("/api/v1/migrations/{task_id}/approve", response_model=dict[str, Any])
    async def approve_migration(task_id: str, payload: ApprovalRequest) -> dict[str, Any]:
        if task_id not in tasks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Task not found: {task_id}"
            )

        state = tasks[task_id]
        if not payload.approved:
            updated = state.model_copy(
                update={
                    "phase": MigrationPhase.FAILED,
                    "error_message": f"Rejected by operator: {payload.comment or 'No comment'}",
                }
            )
            tasks[task_id] = updated
            await events.publish(
                task_id=task_id,
                event_type="migration:rejected",
                data={"task_id": task_id, "operator": payload.operator},
            )
            return {"status": "rejected", "task_id": task_id}

        # Apply synthesized patches to repository disk
        applied_files: list[str] = []
        for patch in state.patches:
            apply_res = await asyncio.to_thread(
                apply_unified_diff,
                state.repo_path,
                patch.file_path,
                patch.diff_text,
            )
            if apply_res.is_err:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to land approved patch on {patch.file_path}: {apply_res.unwrap_err().message}",
                )
            applied_files.append(patch.file_path)

        updated = state.model_copy(update={"phase": MigrationPhase.VERIFIED, "is_terminal": True})
        tasks[task_id] = updated
        await events.publish(
            task_id=task_id,
            event_type="migration:landed",
            data={"task_id": task_id, "applied_files": applied_files, "operator": payload.operator},
        )
        return {"status": "landed", "task_id": task_id, "applied_files": applied_files}

    return app


app = create_app()
