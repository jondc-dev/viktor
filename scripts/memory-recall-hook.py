#!/usr/bin/env python3
"""
Python importable module for gateway integration — Viktor pre-response memory recall.
Now includes Butler Brain response advisor guidance.

Example wiring in a gateway/handler:

    import sys, os
    sys.path.insert(0, os.path.expanduser("~/clawd/scripts"))
    from memory_recall_hook import process_text_message

    def handle_message(user_message, session_id=None):
        memory_context = process_text_message(user_message, session_id=session_id)
        if memory_context:
            system_prompt = memory_context + "\\n\\n" + base_system_prompt
        else:
            system_prompt = base_system_prompt
        # ... proceed with LLM call
"""

import sys
from pathlib import Path

# Resolve workspace root relative to this file: scripts/ -> parent -> workspace root
_WORKSPACE_ROOT = Path(__file__).parent.parent
_VECTOR_MEMORY_DIR = _WORKSPACE_ROOT / "vector-memory"
_SECOND_BRAIN_DIR = _WORKSPACE_ROOT / "second-brain"


def process_text_message(message: str, session_id: str = None, agent_id: str = "viktor") -> str:
    """
    Run pre-response memory recall + butler guidance for the given user message.

    Args:
        message:    The incoming user message text.
        session_id: Unused for Viktor (kept for interface compatibility).
        agent_id:   Unused; present for interface compatibility.

    Returns:
        A formatted context string to prepend to the system prompt,
        or an empty string if no relevant memories are found or on any error.
    """
    context_parts = []

    # 1. FAISS memory recall (existing behavior)
    try:
        vm_dir = str(_VECTOR_MEMORY_DIR)
        if vm_dir not in sys.path:
            sys.path.insert(0, vm_dir)

        from pre_response_recall import recall_for_message  # noqa: PLC0415

        memory_context = recall_for_message(message)
        if memory_context:
            context_parts.append(memory_context)
    except Exception:
        pass

    # 2. Butler Brain response advisor (NEW)
    try:
        sb_dir = str(_SECOND_BRAIN_DIR)
        if sb_dir not in sys.path:
            sys.path.insert(0, sb_dir)

        from response_advisor import advise_on_response  # noqa: PLC0415

        guidance = advise_on_response(message)
        if guidance:
            context_parts.append(guidance)
    except Exception:
        pass

    return "\n\n".join(context_parts)
