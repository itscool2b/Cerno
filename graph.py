import json
from chroma import get_all_file_metadata


def build_repo_map(directory=None):
    """Build a compact text map of the repo: file paths + all function/class signatures.

    Output format:
        src/auth/oauth.py
          class OAuthProvider(BaseProvider)
            def authenticate(request: Request) -> Token
        src/models/user.py
          class User(BaseModel)
            def has_permission(perm: str) -> bool
    """
    all_metadata = get_all_file_metadata()
    if not all_metadata:
        return ""

    # Filter by directory if specified
    if directory:
        all_metadata = [m for m in all_metadata if m["path"].startswith(directory)]

    # Sort by path for consistent output
    all_metadata.sort(key=lambda m: m["path"])

    lines = []
    for file_meta in all_metadata:
        path = file_meta["path"]
        defs_raw = file_meta.get("definitions", "[]")
        if isinstance(defs_raw, str):
            defs = json.loads(defs_raw)
        else:
            defs = defs_raw

        if not defs:
            continue

        lines.append(path)
        for d in defs:
            sig = d.get("signature", d.get("name", ""))
            if not sig:
                continue
            lines.append(f"  {sig}")

    return "\n".join(lines)


def get_dependency_context(chunk_metadata):
    """Given a chunk's calls list and name, resolve call signatures.

    Returns:
        {
            "calls": ["def bar(x: int) -> str", ...],
            "called_by": ["def main() -> None", ...]
        }
    """
    calls_raw = chunk_metadata.get("calls", "[]")
    if isinstance(calls_raw, str):
        calls = json.loads(calls_raw)
    else:
        calls = calls_raw or []

    chunk_name = chunk_metadata.get("name", "")

    all_metadata = get_all_file_metadata()
    if not all_metadata:
        return {"calls": [], "called_by": []}

    # Build lookup: name -> signature, and name -> list of callers
    sig_lookup = {}
    callers_of = {}  # name -> list of signatures that call it

    for file_meta in all_metadata:
        defs_raw = file_meta.get("definitions", "[]")
        if isinstance(defs_raw, str):
            defs = json.loads(defs_raw)
        else:
            defs = defs_raw

        for d in defs:
            name = d.get("name", "")
            sig = d.get("signature", "")
            if name:
                sig_lookup[name] = sig

            # Track who calls what
            d_calls_raw = d.get("calls", "[]")
            if isinstance(d_calls_raw, str):
                d_calls = json.loads(d_calls_raw)
            else:
                d_calls = d_calls_raw or []

            for called in d_calls:
                # Strip dotted prefix (e.g. "os.path.join" -> "join")
                short = called.rsplit(".", 1)[-1] if "." in called else called
                if short not in callers_of:
                    callers_of[short] = []
                callers_of[short].append(sig)

    # Resolve: signatures of functions this chunk calls
    call_sigs = []
    for called in calls:
        short = called.rsplit(".", 1)[-1] if "." in called else called
        if short in sig_lookup:
            call_sigs.append(sig_lookup[short])

    # Resolve: signatures of functions that call this chunk
    called_by_sigs = []
    if chunk_name and chunk_name in callers_of:
        called_by_sigs = callers_of[chunk_name]

    return {"calls": call_sigs, "called_by": called_by_sigs}
