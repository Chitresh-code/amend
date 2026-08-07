# 0001: Agent runtime capabilities

Status: Accepted
Date: 2026-08-07

## Context

Agent SDKs like Strands offer a broad surface: memory, sessions, context management, structured output, streaming, an autonomous agent loop, state, hooks, conversation management, interrupts, plugins. Not all of it fits Amend. This records which of those capabilities Amend uses, which it deliberately does not, and why, so the choice reads as a decision rather than an omission.

The governing constraint throughout is [ARCHITECTURE.md §2](../ARCHITECTURE.md#2-why-the-pipeline-is-not-a-graph-execution-framework) and PRD principle 4.1 (evidence before generation): retrieval, graph expansion, temporal validation, supersession resolution, and citation validation stay deterministic Python. Nothing below is allowed to move that logic into a model call.

## Decisions

### Memory (long-term, cross-session)

**Not implemented.** A persistent memory of facts the model "remembers" across sessions is in tension with evidence-before-generation: an answer should trace to retrieved evidence for *this* query, not to a remembered belief that may be stale. Revisit only if a concrete need appears (for example, a caller's default regulator focus), and scope it to preferences, not regulatory facts.

### Sessions and conversation management

**Implemented.** Follow-up questions ("what about NBFCs specifically?") are an expected usage pattern for a research tool, and answering them needs the prior turn's resolved intent and evidence, not just raw chat text. A `conversation_id` groups a sequence of turns; each turn is a full, independent pipeline run (§25) that also receives prior turns as context. See [docs/DATA_MODEL.md](../DATA_MODEL.md) for `conversations`/`conversation_turns`, and PRD §71.

### Context management

**Bounded window, not summarization, for MVP.** Each turn passes the last N turns (configurable, small default) verbatim into query understanding. Building a summarization step for older turns is deferred until real conversations show the window is actually insufficient; there is no evidence yet that it will be.

### Structured output

**Used, for query understanding only.** `Agent.structured_output(QueryIntent, prompt)` produces the typed intent/entities/concepts/`as_of_date` object directly (verified against the Strands API, not inferred). This removes a whole class of "the model almost returned valid JSON" parsing failures. Answer generation does not use structured output beyond the citation object shape already specified in PRD §31; its main output is prose plus citations, not a rigid schema.

### Streaming

**Progress events only, not token-by-token answer streaming.** PRD §32's citation validation gate can reject a generated answer and trigger regeneration. Streaming the answer-generation agent's tokens directly to the client would show text the system might immediately discard, which contradicts the validation gate's purpose. Instead: an SSE variant of the query endpoint streams pipeline stage transitions (retrieving evidence, expanding lineage, validating citations, ...) for perceived responsiveness, and emits the answer only once, after validation passes, alongside the existing synchronous `POST /v1/query`. `agent.stream_async()` is the mechanism if per-token streaming is revisited later, but that is not this decision.

### Agent loop (autonomous tool-calling)

**Not used.** Already decided in [ARCHITECTURE.md §2](../ARCHITECTURE.md#2-why-the-pipeline-is-not-a-graph-execution-framework): retrieval/graph/validation ordering is deterministic Python, not left to the model to sequence via tool calls. Restated here because it is the most consequential "no" among these capabilities, not because it changed.

### State

**Two separate state objects, not one.** `PipelineState` (ARCHITECTURE §2) is per-turn and ephemeral. Persisted conversation state (`conversations`/`conversation_turns`) is a different lifetime and a different concern. Conflating them would make the deterministic pipeline harder to unit test in isolation (CODING_STANDARDS.md testing rules assume `PipelineState` can be constructed directly, with no database).

### Hooks

**Used, for telemetry only.** Strands' `HookProvider` (`BeforeInvocationEvent`, `AfterInvocationEvent`, confirmed to exist in the SDK) populates query telemetry (PRD §52: provider/model identity, token usage, latency) without threading observability calls through every pipeline stage. The exact hook event set available should be confirmed against the installed `strands-agents` version at implementation time; only the two events above are confirmed here.

### Interrupts and interventions

**Client-initiated cancellation, not human-approval gates.** There is no autonomous, side-effecting tool use on the query path (§ Agent loop, above), so there is nothing for a human to approve mid-flight. What does matter: a caller who disconnects mid-request is paying for an in-flight model call with their own BYOK credential (PRD §70) that nobody will read the result of. Request cancellation (FastAPI/Starlette disconnect detection) should propagate into the pipeline's async calls and cancel them, not just stop reading the response.

### Plugins

**Not given to the answer-generation agent.** Tool/plugin access for that agent reintroduces the agent-loop problem above. The viable direction is the reverse: exposing Amend's own query capability as an MCP tool (Strands has native MCP support) so other agents can call it. This is a post-MVP extension point, noted here so it is not rediscovered as a surprise, not something built now.

## Consequences

- New tables: `conversations`, `conversation_turns` (DATA_MODEL.md).
- `POST /v1/query` gains an optional `conversation_id` (PRD §71); an SSE variant is additive.
- `app/agents/` gains hook-based telemetry wiring, distinct from pipeline logic.
- No change to the deterministic pipeline's control flow: this ADR reinforces §2's decision rather than revisiting it.
