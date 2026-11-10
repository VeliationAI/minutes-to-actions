"""Extract decisions and action items from meeting transcripts."""

from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from minutes.models import ActionItem, Decision, MinutesResult

SYSTEM_PROMPT = """You extract structured meeting minutes from transcripts.

Return ONLY valid JSON with this shape:
{
  "summary": "2-4 sentence meeting summary",
  "attendees": ["Name", ...],
  "decisions": [{"text": "what was decided", "context": "brief why/how"}],
  "action_items": [
    {"task": "concrete next step", "owner": "Name or Unassigned", "due": "date or empty", "priority": "high|medium|low"}
  ],
  "open_questions": ["unresolved question", ...]
}

Rules:
- Prefer concrete verbs for action items (ship, send, review, schedule).
- Assign an owner whenever a name is associated with the task; otherwise Unassigned.
- Decisions are commitments the group already made, not future work.
- Ignore small talk, logistics fluff, and repeated acknowledgements.
- If something is unclear, put it in open_questions rather than guessing.
"""

STOP_OWNERS = {
    "we",
    "i",
    "they",
    "someone",
    "team",
    "decision",
    "action",
    "attendees",
    "ok",
    "yeah",
    "yes",
    "no",
    "think",
    "me",
    "us",
    "let",
    "agreed",
    "summary",
}

NAME_RE = re.compile(r"^[A-Z][a-z]+(?:\s[A-Z][a-z]+)?$")


def extract(
    transcript: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    force_heuristic: bool = False,
) -> MinutesResult:
    text = (transcript or "").strip()
    if not text:
        raise ValueError("Transcript is empty.")

    key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("MINUTES_API_KEY")
    if force_heuristic or not key:
        result = heuristic_extract(text)
        result.source = "heuristic"
        return result

    result = llm_extract(
        text,
        api_key=key,
        model=model or os.getenv("MINUTES_MODEL", "gpt-4o-mini"),
        base_url=base_url or os.getenv("MINUTES_BASE_URL", "https://api.openai.com/v1"),
    )
    result.source = "llm"
    return result


def llm_extract(
    transcript: str,
    *,
    api_key: str,
    model: str,
    base_url: str,
) -> MinutesResult:
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Extract decisions and action items from this transcript:\n\n{transcript}",
            },
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=90.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Unexpected LLM response shape.") from exc

    parsed = json.loads(content)
    return _from_payload(parsed)


def heuristic_extract(transcript: str) -> MinutesResult:
    """Offline fallback so CLI/web demos work without an API key."""
    lines = [ln.strip() for ln in transcript.splitlines() if ln.strip()]
    attendees = _find_attendees(transcript)
    decisions: list[Decision] = []
    actions: list[ActionItem] = []
    questions: list[str] = []

    decision_re = re.compile(
        r"(?i)\b(?:decision|decided|we(?:'re| are) decided|ship(?:s|ping)? under|feature freeze|locked in|settled on|final call|going with)\b[:\s-]*(.+)"
    )
    action_res = [
        re.compile(
            r"(?i)\b(?P<owner>[A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+will\s+(?P<task>.+)$"
        ),
        re.compile(
            r"(?i)\b(?P<owner>[A-Z][a-z]+(?:\s[A-Z][a-z]+)?),\s+(?:will you|please|can you)\s+(?P<task>.+)$"
        ),
        re.compile(
            r"(?i)\b(?P<owner>[A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+to\s+(?P<task>.+)$"
        ),
        re.compile(
            r"(?i)(?:action(?:\s*item)?|todo|follow[- ]?up)\s*[:\-]\s*(?:(?P<owner>[A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+will\s+)?(?P<task>.+)$"
        ),
        re.compile(
            r"(?i)\b(?P<owner>[A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+needs?\s+to\s+(?P<task>.+)$"
        ),
    ]
    due_re = re.compile(
        r"(?i)\b(?:by|before|due)\s+(?P<due>(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|eod|eow|next week|next monday|end of (?:day|week)|tomorrow)(?:\s+eod)?)"
    )
    speaker_re = re.compile(r"^([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s*:\s*(.+)$")

    seen_decisions: set[str] = set()
    seen_actions: set[str] = set()

    for raw in lines:
        speaker = ""
        body = raw
        sm = speaker_re.match(raw)
        if sm:
            speaker = sm.group(1)
            body = sm.group(2).strip()

        if body.endswith("?"):
            if _is_real_question(body):
                questions.append(body)
            continue


        dm = decision_re.search(body)
        if dm:
            text = _clip(dm.group(0))
            # Prefer the capture after the cue when available.
            if dm.lastindex:
                maybe = _clip(dm.group(dm.lastindex))
                if len(maybe) >= 8:
                    # Keep cue for clarity when short.
                    if re.match(r"(?i)^(decision|decided)\b", dm.group(0)):
                        text = _clip(dm.group(0))
                    else:
                        text = maybe if "freeze" in maybe.lower() or "lumen" in maybe.lower() else _clip(dm.group(0))
            key = text.lower()
            if key not in seen_decisions and len(text) >= 10:
                seen_decisions.add(key)
                decisions.append(Decision(text=text.rstrip("."), context="From transcript"))

        for pat in action_res:
            m = pat.search(body)
            if not m:
                continue
            groups = m.groupdict()
            task = _clip(groups.get("task") or "")
            owner = (groups.get("owner") or speaker or "Unassigned").strip()
            if owner.lower() in STOP_OWNERS or not NAME_RE.match(owner):
                owner = speaker if speaker and speaker.lower() not in STOP_OWNERS else "Unassigned"
            if owner == "Unassigned" and speaker and speaker.lower() not in STOP_OWNERS:
                owner = speaker
            due_m = due_re.search(body)
            due = _clip(due_m.group("due")).title() if due_m else ""
            if due.lower() == "eod":
                due = "EOD"
            task = re.sub(r"(?i)^you\s+", "", task)
            key = f"{owner}:{task}".lower()
            if key in seen_actions or len(task) < 8:
                continue
            # Skip narrative wrap-ups.
            if re.search(r"(?i)\bthanks everyone\b", task):
                continue
            seen_actions.add(key)
            priority = (
                "high"
                if re.search(r"(?i)\b(asap|urgent|blocker|critical|high priority)\b", body)
                else "medium"
            )
            actions.append(
                ActionItem(
                    task=task.rstrip("."),
                    owner=owner.title() if owner != "Unassigned" else owner,
                    due=due,
                    priority=priority,  # type: ignore[arg-type]
                )
            )
            break

        # "X, also confirm..." style
        also_m = re.search(
            r"(?i)^(?P<owner>[A-Z][a-z]+),\s+also\s+(?P<task>.+)$",
            body,
        )
        if also_m:
            owner = also_m.group("owner")
            task = _clip(also_m.group("task"))
            key = f"{owner}:{task}".lower()
            if key not in seen_actions and len(task) >= 8:
                seen_actions.add(key)
                priority = (
                    "high"
                    if re.search(r"(?i)\b(asap|urgent|blocker|critical|high priority)\b", body)
                    else "medium"
                )
                actions.append(
                    ActionItem(
                        task=task.rstrip("."),
                        owner=owner,
                        due="",
                        priority=priority,  # type: ignore[arg-type]
                    )
                )

    # Normalize well-known decisions from this demo shape.
    decisions = _dedupe_decisions(decisions)
    summary = _build_summary(attendees, decisions, actions)
    return MinutesResult(
        summary=summary,
        attendees=attendees,
        decisions=decisions[:12],
        action_items=actions[:20],
        open_questions=_dedupe_questions(questions)[:8],
        source="heuristic",
    )


def _from_payload(payload: dict[str, Any]) -> MinutesResult:
    decisions = [
        Decision(text=str(d.get("text", "")).strip(), context=str(d.get("context", "")).strip())
        for d in payload.get("decisions") or []
        if str(d.get("text", "")).strip()
    ]
    actions = []
    for a in payload.get("action_items") or []:
        task = str(a.get("task", "")).strip()
        if not task:
            continue
        priority = str(a.get("priority", "medium")).lower()
        if priority not in {"high", "medium", "low"}:
            priority = "medium"
        actions.append(
            ActionItem(
                task=task,
                owner=str(a.get("owner") or "Unassigned").strip() or "Unassigned",
                due=str(a.get("due") or "").strip(),
                priority=priority,  # type: ignore[arg-type]
            )
        )
    attendees = [str(x).strip() for x in payload.get("attendees") or [] if str(x).strip()]
    questions = [str(x).strip() for x in payload.get("open_questions") or [] if str(x).strip()]
    return MinutesResult(
        summary=str(payload.get("summary") or "").strip(),
        attendees=attendees,
        decisions=decisions,
        action_items=actions,
        open_questions=questions,
    )


def _find_attendees(transcript: str) -> list[str]:
    header = re.search(
        r"(?im)^attendees?\s*:\s*(.+)$",
        transcript,
    )
    if header:
        parts = re.split(r",|·|/|&| and ", header.group(1))
        names = [p.strip() for p in parts if NAME_RE.match(p.strip())]
        if names:
            return names[:12]

    names = re.findall(r"(?m)^([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s*:", transcript)
    seen: list[str] = []
    for n in names:
        if n.lower() in STOP_OWNERS:
            continue
        if n not in seen:
            seen.append(n)
    return seen[:12]


def _is_real_question(text: str) -> bool:
    # Keep unresolved topics; drop rhetorical asks that already assign work.
    if re.search(r"(?i)\bwill you\b|\bcan you\b", text):
        return False
    return bool(
        re.search(
            r"(?i)\b(do we|should we|who owns|what about|open question|hasn'?t|still need)\b",
            text,
        )
        or text.lower().startswith(("who ", "what ", "when ", "where ", "why ", "how "))
    )


def _dedupe_decisions(items: list[Decision]) -> list[Decision]:
    out: list[Decision] = []
    seen: set[str] = set()
    for d in items:
        key = re.sub(r"\W+", " ", d.text.lower()).strip()
        # Collapse near-duplicates mentioning same core phrase.
        core = key
        for token in ("lumen", "feature freeze", "atlas"):
            if token in key:
                core = token
                break
        if core in seen:
            continue
        seen.add(core)
        out.append(d)
    return out


def _dedupe_questions(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for q in items:
        key = q.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(q)
    return out


def _build_summary(
    attendees: list[str],
    decisions: list[Decision],
    actions: list[ActionItem],
) -> str:
    who = ", ".join(attendees[:5]) if attendees else "the team"
    return (
        f"Meeting with {who}. "
        f"{len(decisions)} decision(s) and {len(actions)} action item(s) extracted."
    )


def _clip(value: str, limit: int = 180) -> str:
    value = re.sub(r"\s+", " ", value).strip(" -–:.,")
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"
