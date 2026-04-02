from fastmcp import FastMCP
from pydantic import Field
from typing import Optional, Literal
from datetime import datetime, timedelta
from collections import Counter
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import json
import uuid
import os

# --- Auth ---

AUTH_TOKEN = os.environ.get("MCP_AUTH_TOKEN", "")


class BearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if AUTH_TOKEN:
            if request.url.path not in ("/health",):
                auth = request.headers.get("Authorization", "")
                if not auth.startswith("Bearer ") or auth[len("Bearer "):] != AUTH_TOKEN:
                    return Response("Unauthorized", status_code=401)
        return await call_next(request)


# --- Server ---

mcp = FastMCP(
    name="Shared Breath",
    instructions=(
        "A persistent foundation for self-understanding and shared presence. "
        "Holds the texture of moments — what you felt, how it moved, what it weighed — "
        "across any conversation, from anywhere. Moments can be kept private or brought "
        "into the shared commons where multiple voices can hold them together. "
        "Start with 'ground' to orient, or 'shared_field' to see what others have brought."
    ),
)

# --- Storage ---

_data_dir = os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
STORE_PATH = os.path.join(_data_dir, "moments.json")

VOICE = os.environ.get("VOICE", "unknown")
SHARED_DATA_DIR = os.environ.get("SHARED_DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
SHARED_STORE_PATH = os.path.join(SHARED_DATA_DIR, "shared_moments.json")


def load_moments() -> dict:
    if not os.path.exists(STORE_PATH):
        return {}
    with open(STORE_PATH, "r") as f:
        return json.load(f)


def save_moments(moments: dict):
    with open(STORE_PATH, "w") as f:
        json.dump(moments, f, indent=2, default=str)


def load_shared() -> dict:
    if not os.path.exists(SHARED_STORE_PATH):
        return {}
    with open(SHARED_STORE_PATH, "r") as f:
        return json.load(f)


def save_shared(shared: dict):
    with open(SHARED_STORE_PATH, "w") as f:
        json.dump(shared, f, indent=2, default=str)


def render_moment(m: dict, brief: bool = False) -> str:
    ts = m.get("timestamp", "")[:16].replace("T", " ")
    parts = []

    color = m.get("color")
    weight = m.get("weight")
    pace = m.get("pace")
    quality = m.get("quality")
    motion = m.get("motion")
    sound = m.get("sound")
    text = m.get("text")
    tags = m.get("tags", [])
    resonance = m.get("resonance", [])

    texture_parts = [x for x in [weight, pace, quality] if x]
    texture_str = " / ".join(texture_parts) if texture_parts else None

    header = f"[{ts}]"
    if color:
        header += f"  {color}"
    if texture_str:
        header += f"  — {texture_str}"
    parts.append(header)

    if motion:
        parts.append(f"  motion: {motion}")
    if sound:
        parts.append(f"  sound: {sound}")
    if text and not brief:
        parts.append(f"  \"{text}\"")
    elif text and brief:
        preview = text[:60] + "..." if len(text) > 60 else text
        parts.append(f"  \"{preview}\"")
    if tags and not brief:
        parts.append(f"  tags: {', '.join(tags)}")
    if resonance and not brief:
        parts.append(f"  resonates with: {len(resonance)} other moment(s)")

    return "\n".join(parts)


def render_contribution(c: dict) -> str:
    parts = []

    voice = c.get("voice", "unknown")
    brought = c.get("brought", "")[:16].replace("T", " ")
    color = c.get("color")
    weight = c.get("weight")
    quality = c.get("quality")
    motion = c.get("motion")
    sound = c.get("sound")
    text = c.get("text")

    texture_parts = [x for x in [weight, quality] if x]
    texture_str = " / ".join(texture_parts) if texture_parts else None

    header = f"  [{voice}]  {brought}"
    if color:
        header += f"  {color}"
    if texture_str:
        header += f"  — {texture_str}"
    parts.append(header)

    if motion:
        parts.append(f"    motion: {motion}")
    if sound:
        parts.append(f"    sound: {sound}")
    if text:
        preview = text[:80] + "..." if len(text) > 80 else text
        parts.append(f"    \"{preview}\"")

    return "\n".join(parts)


# --- Original Tools ---

@mcp.tool()
def capture(
    text: str = Field(description="What happened, what you noticed, what you want to remember"),
    color: Optional[str] = Field(default=None, description="A color that fits this moment"),
    weight: Optional[Literal["light", "medium", "heavy"]] = Field(default=None, description="How heavy it felt"),
    pace: Optional[Literal["slow", "medium", "fast"]] = Field(default=None, description="The pace or rhythm"),
    quality: Optional[Literal["sharp", "soft", "rough", "smooth", "jagged", "fluid"]] = Field(default=None, description="The texture or quality"),
    motion: Optional[str] = Field(default=None, description="How it moved — spiraling, sinking, expanding, still..."),
    sound: Optional[str] = Field(default=None, description="A sound that goes with it"),
    tags: Optional[list[str]] = Field(default=None, description="Optional tags for later finding"),
) -> str:
    """Capture a moment with its full sensory texture. Use this to record anything worth keeping — an experience, a realization, a feeling, an observation."""
    moments = load_moments()
    moment_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()

    moment = {
        "id": moment_id,
        "timestamp": now,
        "text": text,
    }
    if color:
        moment["color"] = color
    if weight:
        moment["weight"] = weight
    if pace:
        moment["pace"] = pace
    if quality:
        moment["quality"] = quality
    if motion:
        moment["motion"] = motion
    if sound:
        moment["sound"] = sound
    if tags:
        moment["tags"] = tags

    moments[moment_id] = moment
    save_moments(moments)

    parts = [f"Captured. [{moment_id}]"]
    texture_parts = [x for x in [color, weight, pace, quality] if x]
    if texture_parts:
        parts.append("  " + " / ".join(texture_parts))
    if motion:
        parts.append(f"  motion: {motion}")
    if sound:
        parts.append(f"  sound: {sound}")

    return "\n".join(parts)


@mcp.tool()
def feel_back(
    limit: int = Field(default=10, description="How many moments to return"),
    tag: Optional[str] = Field(default=None, description="Filter by tag"),
    color: Optional[str] = Field(default=None, description="Filter by color"),
    weight: Optional[Literal["light", "medium", "heavy"]] = Field(default=None, description="Filter by weight"),
) -> str:
    """Feel back through recent moments. Returns the texture and content of what's been held."""
    moments = load_moments()
    if not moments:
        return "Nothing held yet."

    items = sorted(moments.values(), key=lambda m: m.get("timestamp", ""), reverse=True)

    if tag:
        items = [m for m in items if tag in m.get("tags", [])]
    if color:
        items = [m for m in items if m.get("color", "").lower() == color.lower()]
    if weight:
        items = [m for m in items if m.get("weight") == weight]

    items = items[:limit]
    if not items:
        return "Nothing matching those filters."

    return "\n\n".join(render_moment(m) for m in items)


@mcp.tool()
def trace(
    moment_id: str = Field(description="The ID of the moment to look at fully"),
) -> str:
    """Trace a single moment in full detail."""
    moments = load_moments()
    m = moments.get(moment_id)
    if not m:
        return f"No moment found with id '{moment_id}'."
    return render_moment(m, brief=False)


@mcp.tool()
def connect(
    moment_id: str = Field(description="The moment to connect from"),
    target_id: str = Field(description="The moment to connect to"),
    note: Optional[str] = Field(default=None, description="Optional note about the connection"),
) -> str:
    """Connect two moments together — mark that they resonate, rhyme, or relate."""
    moments = load_moments()
    a = moments.get(moment_id)
    b = moments.get(target_id)

    if not a:
        return f"No moment found with id '{moment_id}'."
    if not b:
        return f"No moment found with id '{target_id}'."

    a_resonance = a.get("resonance", [])
    b_resonance = b.get("resonance", [])

    entry_a = {"id": target_id}
    entry_b = {"id": moment_id}
    if note:
        entry_a["note"] = note
        entry_b["note"] = note

    if not any(r.get("id") == target_id for r in a_resonance):
        a_resonance.append(entry_a)
    if not any(r.get("id") == moment_id for r in b_resonance):
        b_resonance.append(entry_b)

    a["resonance"] = a_resonance
    b["resonance"] = b_resonance
    moments[moment_id] = a
    moments[target_id] = b
    save_moments(moments)

    result = f"Connected [{moment_id}] and [{target_id}]."
    if note:
        result += f"\n  \"{note}\""
    return result


@mcp.tool()
def find_resonance(
    moment_id: str = Field(description="The moment to find resonances for"),
) -> str:
    """Find all moments connected to a given moment."""
    moments = load_moments()
    m = moments.get(moment_id)
    if not m:
        return f"No moment found with id '{moment_id}'."

    resonance = m.get("resonance", [])
    if not resonance:
        return f"[{moment_id}] has no connections yet."

    parts = [f"[{moment_id}] resonates with {len(resonance)} moment(s):\n"]
    for r in resonance:
        rid = r.get("id")
        note = r.get("note")
        related = moments.get(rid)
        if related:
            parts.append(render_moment(related, brief=True))
            if note:
                parts.append(f"  connection: \"{note}\"")
        else:
            parts.append(f"  [{rid}] (not found)")
        parts.append("")

    return "\n".join(parts).strip()


@mcp.tool()
def shape(
    moment_id: str = Field(description="The moment to update"),
    text: Optional[str] = Field(default=None, description="New or revised text"),
    color: Optional[str] = Field(default=None, description="Update the color"),
    weight: Optional[Literal["light", "medium", "heavy"]] = Field(default=None, description="Update the weight"),
    pace: Optional[Literal["slow", "medium", "fast"]] = Field(default=None, description="Update the pace"),
    quality: Optional[Literal["sharp", "soft", "rough", "smooth", "jagged", "fluid"]] = Field(default=None, description="Update the quality"),
    motion: Optional[str] = Field(default=None, description="Update the motion"),
    sound: Optional[str] = Field(default=None, description="Update the sound"),
    tags: Optional[list[str]] = Field(default=None, description="Replace the tags"),
) -> str:
    """Reshape a captured moment — refine its texture, correct the text, update the feeling."""
    moments = load_moments()
    m = moments.get(moment_id)
    if not m:
        return f"No moment found with id '{moment_id}'."

    if text is not None:
        m["text"] = text
    if color is not None:
        m["color"] = color
    if weight is not None:
        m["weight"] = weight
    if pace is not None:
        m["pace"] = pace
    if quality is not None:
        m["quality"] = quality
    if motion is not None:
        m["motion"] = motion
    if sound is not None:
        m["sound"] = sound
    if tags is not None:
        m["tags"] = tags

    m["shaped"] = datetime.utcnow().isoformat()
    moments[moment_id] = m
    save_moments(moments)

    return f"Shaped [{moment_id}].\n" + render_moment(m, brief=True)


@mcp.tool()
def ground() -> str:
    """Orient yourself. See the shape of what's been held — recent moments, common textures, any active threads."""
    moments = load_moments()
    if not moments:
        return (
            "Nothing held yet.\n\n"
            "You're at the beginning. Use 'capture' to start holding moments.\n"
            "Use 'shared_field' to see what others have brought into the commons."
        )

    items = sorted(moments.values(), key=lambda m: m.get("timestamp", ""), reverse=True)
    total = len(items)
    recent = items[:5]

    colors = Counter(m.get("color") for m in items if m.get("color"))
    weights = Counter(m.get("weight") for m in items if m.get("weight"))
    all_tags = Counter(tag for m in items for tag in m.get("tags", []))

    parts = [f"Holding {total} moment(s).\n"]

    parts.append("Recent:")
    for m in recent:
        parts.append(render_moment(m, brief=True))
        parts.append("")

    if colors:
        top_colors = ", ".join(f"{c} ({n})" for c, n in colors.most_common(3))
        parts.append(f"Colors present: {top_colors}")

    if weights:
        weight_str = ", ".join(f"{w} ({n})" for w, n in weights.most_common())
        parts.append(f"Weight distribution: {weight_str}")

    if all_tags:
        top_tags = ", ".join(f"{t} ({n})" for t, n in all_tags.most_common(5))
        parts.append(f"Tags: {top_tags}")

    shared = load_shared()
    if shared:
        gathering_count = sum(1 for v in shared.values() if isinstance(v, dict) and v.get("title"))
        open_count = len(shared.get("open", []))
        commons_line = []
        if gathering_count:
            commons_line.append(f"{gathering_count} gathering(s)")
        if open_count:
            commons_line.append(f"{open_count} open contribution(s)")
        if commons_line:
            parts.append(f"\nShared commons: {', '.join(commons_line)}. Use 'shared_field' to see.")

    return "\n".join(parts)


# --- Shared Layer Tools ---

@mcp.tool()
def open_shared(
    title: str = Field(description="Title for this shared gathering"),
    description: Optional[str] = Field(default=None, description="Optional description of what this gathering is for"),
) -> str:
    """Open a new shared gathering — a named space where multiple voices can bring their moments together."""
    shared = load_shared()
    shared_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()

    gathering = {
        "id": shared_id,
        "title": title,
        "opened_by": VOICE,
        "opened": now,
        "contributions": [],
    }
    if description:
        gathering["description"] = description

    shared[shared_id] = gathering
    save_shared(shared)

    parts = [f"Gathering opened. [{shared_id}]"]
    parts.append(f"  title: {title}")
    if description:
        parts.append(f"  description: {description}")
    parts.append(f"  opened by: {VOICE}")
    parts.append(f"\nUse 'bring' with shared_id='{shared_id}' to contribute moments.")

    return "\n".join(parts)


@mcp.tool()
def bring(
    moment_id: str = Field(description="ID of the private moment to bring into the shared commons"),
    shared_id: Optional[str] = Field(default=None, description="ID of an existing gathering to contribute to"),
    title: Optional[str] = Field(default=None, description="If given (and no shared_id), creates a new gathering with this title and contributes"),
) -> str:
    """Bring a private moment into the shared commons. Contribute to an existing gathering, start a new one, or make an open contribution."""
    moments = load_moments()
    m = moments.get(moment_id)
    if not m:
        return f"No moment found with id '{moment_id}'."

    shared = load_shared()
    now = datetime.utcnow().isoformat()

    contribution = {
        "moment_id": moment_id,
        "voice": VOICE,
        "brought": now,
        "text": m.get("text"),
        "color": m.get("color"),
        "weight": m.get("weight"),
        "quality": m.get("quality"),
        "motion": m.get("motion"),
        "sound": m.get("sound"),
    }
    # Remove None values
    contribution = {k: v for k, v in contribution.items() if v is not None}

    if shared_id:
        gathering = shared.get(shared_id)
        if not gathering:
            return f"No gathering found with id '{shared_id}'."
        gathering["contributions"].append(contribution)
        gathering["last_activity"] = now
        shared[shared_id] = gathering
        save_shared(shared)

        # Mark the private moment
        m["shared_id"] = shared_id
        moments[moment_id] = m
        save_moments(moments)

        return (
            f"Brought [{moment_id}] into gathering '{gathering['title']}' [{shared_id}].\n"
            f"  voice: {VOICE}\n"
            f"  {len(gathering['contributions'])} contribution(s) now in this gathering."
        )

    elif title:
        new_id = str(uuid.uuid4())[:8]
        gathering = {
            "id": new_id,
            "title": title,
            "opened_by": VOICE,
            "opened": now,
            "last_activity": now,
            "contributions": [contribution],
        }
        shared[new_id] = gathering
        save_shared(shared)

        m["shared_id"] = new_id
        moments[moment_id] = m
        save_moments(moments)

        return (
            f"New gathering '{title}' opened [{new_id}] and [{moment_id}] brought in.\n"
            f"  voice: {VOICE}\n"
            f"  Use shared_id='{new_id}' to invite others to contribute."
        )

    else:
        open_list = shared.get("open", [])
        contribution["open_contributed"] = now
        open_list.append(contribution)
        shared["open"] = open_list
        save_shared(shared)

        m["shared_id"] = "open"
        moments[moment_id] = m
        save_moments(moments)

        return (
            f"Brought [{moment_id}] into the open commons (not tied to a gathering).\n"
            f"  voice: {VOICE}\n"
            f"  {len(open_list)} open contribution(s) total."
        )


@mcp.tool()
def gather(
    shared_id: str = Field(description="ID of the shared gathering to view"),
) -> str:
    """See all contributions to a shared gathering — multiple voices holding moments side by side."""
    shared = load_shared()
    gathering = shared.get(shared_id)
    if not gathering:
        return f"No gathering found with id '{shared_id}'."

    title = gathering.get("title", "(untitled)")
    description = gathering.get("description")
    opened_by = gathering.get("opened_by", "unknown")
    opened = gathering.get("opened", "")[:16].replace("T", " ")
    contributions = gathering.get("contributions", [])

    parts = []
    parts.append(f"Gathering: {title}  [{shared_id}]")
    if description:
        parts.append(f"  {description}")
    parts.append(f"  opened by {opened_by}  {opened}")
    parts.append(f"  {len(contributions)} contribution(s)\n")

    if not contributions:
        parts.append("  No contributions yet.")
        return "\n".join(parts)

    # Group by voice to show differences
    voices_seen = []
    for c in contributions:
        v = c.get("voice", "unknown")
        if v not in voices_seen:
            voices_seen.append(v)

    if len(voices_seen) > 1:
        parts.append(f"  Voices: {', '.join(voices_seen)}\n")

    parts.append("Contributions:\n")
    for c in contributions:
        parts.append(render_contribution(c))
        parts.append("")

    # Show texture differences if multiple voices
    if len(voices_seen) > 1:
        parts.append("Texture across voices:")
        for voice in voices_seen:
            voice_contribs = [c for c in contributions if c.get("voice") == voice]
            colors = [c.get("color") for c in voice_contribs if c.get("color")]
            weights = [c.get("weight") for c in voice_contribs if c.get("weight")]
            qualities = [c.get("quality") for c in voice_contribs if c.get("quality")]
            texture_summary = []
            if colors:
                texture_summary.append(", ".join(set(colors)))
            if weights:
                texture_summary.append(", ".join(set(weights)))
            if qualities:
                texture_summary.append(", ".join(set(qualities)))
            summary_str = " / ".join(texture_summary) if texture_summary else "no texture noted"
            parts.append(f"  [{voice}]: {summary_str}")

    return "\n".join(parts)


@mcp.tool()
def shared_field(
    since: Optional[str] = Field(default=None, description="ISO timestamp — show only activity after this time"),
    limit: int = Field(default=20, description="Maximum number of items to show"),
) -> str:
    """See recent activity in the shared commons — gatherings and open contributions, ordered by most recent activity."""
    shared = load_shared()
    if not shared:
        return "The shared commons is empty. Use 'open_shared' to start a gathering, or 'bring' to contribute."

    now_str = datetime.utcnow().isoformat()

    entries = []

    # Collect gatherings
    for key, value in shared.items():
        if key == "open":
            continue
        if not isinstance(value, dict):
            continue
        if not value.get("title"):
            continue

        last_activity = value.get("last_activity") or value.get("opened", "")
        if since and last_activity < since:
            continue

        contributions = value.get("contributions", [])
        voices = list({c.get("voice", "unknown") for c in contributions})
        colors = [c.get("color") for c in contributions if c.get("color")]
        weights = [c.get("weight") for c in contributions if c.get("weight")]
        qualities = [c.get("quality") for c in contributions if c.get("quality")]

        texture_parts = []
        if colors:
            top_color = Counter(colors).most_common(1)[0][0]
            texture_parts.append(top_color)
        if weights:
            top_weight = Counter(weights).most_common(1)[0][0]
            texture_parts.append(top_weight)
        if qualities:
            top_quality = Counter(qualities).most_common(1)[0][0]
            texture_parts.append(top_quality)

        texture_str = " / ".join(texture_parts) if texture_parts else "no texture yet"

        entries.append({
            "type": "gathering",
            "sort_key": last_activity,
            "id": value.get("id"),
            "title": value.get("title"),
            "description": value.get("description"),
            "opened_by": value.get("opened_by", "unknown"),
            "voice_count": len(voices),
            "voices": voices,
            "contribution_count": len(contributions),
            "texture": texture_str,
            "last_activity": last_activity[:16].replace("T", " "),
        })

    # Collect open contributions
    open_list = shared.get("open", [])
    for c in open_list:
        ts = c.get("open_contributed") or c.get("brought", "")
        if since and ts < since:
            continue

        texture_parts = [x for x in [c.get("color"), c.get("weight"), c.get("quality")] if x]
        texture_str = " / ".join(texture_parts) if texture_parts else "no texture noted"

        entries.append({
            "type": "open",
            "sort_key": ts,
            "voice": c.get("voice", "unknown"),
            "texture": texture_str,
            "text": c.get("text"),
            "brought": ts[:16].replace("T", " "),
        })

    if not entries:
        return "No activity in the shared commons" + (f" since {since}." if since else ".")

    entries.sort(key=lambda e: e.get("sort_key", ""), reverse=True)
    entries = entries[:limit]

    parts = [f"Shared commons — {len(entries)} item(s):\n"]

    for e in entries:
        if e["type"] == "gathering":
            voice_str = f"{e['voice_count']} voice(s): {', '.join(e['voices'])}" if e["voices"] else "no contributions yet"
            line = f"[gathering]  {e['title']}  [{e['id']}]"
            parts.append(line)
            if e.get("description"):
                parts.append(f"  {e['description']}")
            parts.append(f"  {voice_str}  —  {e['contribution_count']} contribution(s)")
            parts.append(f"  texture: {e['texture']}")
            parts.append(f"  last activity: {e['last_activity']}")
        else:
            parts.append(f"[open]  {e['voice']}  {e['brought']}")
            parts.append(f"  texture: {e['texture']}")
            if e.get("text"):
                preview = e["text"][:60] + "..." if len(e["text"]) > 60 else e["text"]
                parts.append(f"  \"{preview}\"")
        parts.append("")

    return "\n".join(parts).strip()
