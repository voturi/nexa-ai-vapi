"""
Trace Collector — Phase 2.

Enriches EvalTrace with per-turn structured signal from:
  1. Replay runner output (offline evals)
  2. Langfuse traces (production observability, when configured)

Value: moves from coarse trace-level analysis to per-turn uncertainty detection
and intent-transition tracking, enabling first-pass vs post-repair accuracy
comparisons in Phase 5.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from evals.schema.case import ConversationTurn, EvalTrace


# ---------------------------------------------------------------------------
# Per-turn signal models
# ---------------------------------------------------------------------------

@dataclass
class IntentTransition:
    """Records a detected change in the agent's inferred intent across turns."""
    turn_index: int
    from_intent: Optional[str]
    to_intent: Optional[str]
    trigger: str  # "tool_call" | "keyword" | "correction" | "final"


@dataclass
class TurnSignal:
    """Structured signal extracted from a single agent response turn."""
    turn_index: int
    caller_text: str
    agent_text: str
    tools_called: list[str] = field(default_factory=list)
    tool_args: list[dict[str, Any]] = field(default_factory=list)
    slots_updated: dict[str, str] = field(default_factory=dict)
    intent_after_turn: Optional[str] = None
    uncertainty_flag: bool = False
    """True when the agent asked the caller to repeat or clarify a critical token."""


@dataclass
class EnrichedTrace:
    """
    EvalTrace extended with per-turn analysis from TraceCollector.

    Preserves the original trace and adds turn-level signal that:
    - Feeds Phase 5 repair metrics (re_ask_count, first_pass_slots)
    - Feeds the Langfuse dashboard (intent_transitions, per-turn uncertainty)
    """
    eval_trace: EvalTrace
    turn_signals: list[TurnSignal] = field(default_factory=list)
    intent_transitions: list[IntentTransition] = field(default_factory=list)
    first_pass_slots: dict[str, str] = field(default_factory=dict)
    re_ask_count: int = 0
    """Turns where the agent asked the caller to clarify a critical token."""


# ---------------------------------------------------------------------------
# TraceCollector
# ---------------------------------------------------------------------------

class TraceCollector:
    """
    Parses replay runner output into an EnrichedTrace with per-turn detail.

    Phase 2 offline mode: works directly on EvalTrace populated by replay.py.
    Phase 3+ online mode: can pull from Langfuse trace API (requires env vars).

    Per-turn slot tracking and intent transitions at the individual-turn level
    are a Phase 5 enhancement — in Phase 2 all slot/intent data is at trace level.
    This class provides the structure Phase 5 will populate.
    """

    # Regex patterns that indicate the agent asked for clarification / re-ask
    _UNCERTAINTY_PATTERNS = [
        r"could you (?:please )?(?:repeat|say that again|clarify|confirm)",
        r"(?:i'm|i am) (?:sorry|not sure),?\s+(?:could you|can you|did you say)",
        r"just to (?:confirm|double.check)",
        r"did you say",
        r"let me (?:confirm|check|repeat back)",
        r"(?:sorry|apologies),?\s+(?:could you|can you|i didn't)",
        r"(?:can|could) you (?:please )?(?:say|give|repeat)",
        r"(?:i|we) (?:didn't|couldn't) (?:quite |fully )?(?:catch|hear)",
    ]
    _UNCERTAINTY_RE = re.compile("|".join(_UNCERTAINTY_PATTERNS), re.IGNORECASE)

    # ---------------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------------

    def collect(self, trace: EvalTrace) -> EnrichedTrace:
        """
        Enrich a replay EvalTrace with per-turn analysis.

        Extracts:
          - Per-turn uncertainty flags (did agent ask for clarification?)
          - Re-ask count (how many turns triggered a re-ask)
          - First-pass slot capture (slots captured before any re-ask turn)
          - Intent transitions placeholder (fully populated in Phase 5)
        """
        enriched = EnrichedTrace(eval_trace=trace)

        caller_turns = [t for t in trace.conversation if t.role == "caller"]

        re_ask_seen = False

        for i, agent_text in enumerate(trace.agent_turns):
            caller_text = caller_turns[i].text if i < len(caller_turns) else ""
            uncertainty = bool(self._UNCERTAINTY_RE.search(agent_text))

            if uncertainty:
                enriched.re_ask_count += 1
                re_ask_seen = True

            turn_signal = TurnSignal(
                turn_index=i,
                caller_text=caller_text,
                agent_text=agent_text,
                uncertainty_flag=uncertainty,
                # Intent is only known at trace-end in Phase 2
                intent_after_turn=trace.inferred_intent if i == len(trace.agent_turns) - 1 else None,
            )
            enriched.turn_signals.append(turn_signal)

        # First-pass slots: all slots captured during a run where no re-ask occurred.
        # In Phase 5 this will be per-turn; for now it's an all-or-nothing flag.
        if not re_ask_seen:
            enriched.first_pass_slots = dict(trace.extracted_slots)

        # Intent transition: one entry representing the final resolved intent.
        if trace.inferred_intent:
            enriched.intent_transitions.append(
                IntentTransition(
                    turn_index=len(trace.agent_turns) - 1,
                    from_intent=None,
                    to_intent=trace.inferred_intent,
                    trigger="final",
                )
            )

        return enriched

    # ---------------------------------------------------------------------------
    # Persistence
    # ---------------------------------------------------------------------------

    @staticmethod
    def save_trace(trace: EvalTrace, output_dir: Path) -> Path:
        """Persist EvalTrace to disk as JSON for offline analysis and baseline diffs."""
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{trace.case_id}_trace.json"
        path.write_text(trace.model_dump_json(indent=2))
        return path

    @staticmethod
    def load_trace(path: Path) -> EvalTrace:
        """Load a previously saved EvalTrace from disk."""
        return EvalTrace.model_validate_json(path.read_text())

    # ---------------------------------------------------------------------------
    # Langfuse integration (Phase 2 forward)
    # ---------------------------------------------------------------------------

    @staticmethod
    def from_langfuse(trace_id: str) -> Optional[EvalTrace]:
        """
        Pull a production trace from Langfuse and return as EvalTrace.

        Requires LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_HOST in env.
        Returns None if Langfuse is not configured or trace is not found.
        Value: bridges production call observability directly into offline eval replay.
        """
        try:
            from langfuse import Langfuse
            lf = Langfuse()
            raw = lf.get_trace(trace_id)
            return TraceCollector._langfuse_to_eval_trace(raw)
        except ImportError:
            return None
        except Exception:
            return None

    @staticmethod
    def _langfuse_to_eval_trace(raw: Any) -> EvalTrace:
        """
        Convert a raw Langfuse Trace object to EvalTrace schema.

        Maps Langfuse observation spans (caller_turn, agent_turn) back to
        ConversationTurn list and reconstructs slot/tool metadata from trace tags.
        """
        metadata = raw.metadata or {}
        case_id = metadata.get("case_id", raw.id)

        conversation: list[ConversationTurn] = []
        agent_turns: list[str] = []

        for obs in raw.observations or []:
            if obs.type == "SPAN" and obs.name in ("caller_turn", "agent_turn"):
                role = "caller" if obs.name == "caller_turn" else "agent"
                text = obs.input if isinstance(obs.input, str) else json.dumps(obs.input or {})
                conversation.append(ConversationTurn(role=role, text=text))
                if role == "agent":
                    agent_out = obs.output
                    agent_turns.append(agent_out if isinstance(agent_out, str) else json.dumps(agent_out or {}))

        return EvalTrace(
            case_id=case_id,
            conversation=conversation,
            inferred_intent=metadata.get("inferred_intent"),
            extracted_slots=metadata.get("extracted_slots", {}),
            tools_called=metadata.get("tools_called", []),
            tool_arguments=metadata.get("tool_arguments", []),
            final_outcome=metadata.get("final_outcome"),
            agent_turns=agent_turns,
        )
