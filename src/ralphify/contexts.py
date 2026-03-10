import re
from dataclasses import dataclass
from pathlib import Path

from ralphify._frontmatter import find_run_script, parse_frontmatter
from ralphify._output import truncate_output
from ralphify._runner import run_command
from ralphify.resolver import resolve_placeholders


@dataclass
class Context:
    name: str
    path: Path
    command: str | None = None
    script: Path | None = None
    timeout: int = 30
    enabled: bool = True
    static_content: str = ""


@dataclass
class ContextResult:
    context: Context
    output: str
    success: bool
    timed_out: bool = False


_NAMED_PATTERN = re.compile(r"\{\{\s*contexts\.([a-zA-Z0-9_-]+)\s*\}\}")
_BULK_PATTERN = re.compile(r"\{\{\s*contexts\s*\}\}")


def discover_contexts(root: Path = Path(".")) -> list[Context]:
    """Discover contexts in root/.ralph/contexts/ directories."""
    contexts_dir = root / ".ralph" / "contexts"
    if not contexts_dir.is_dir():
        return []

    contexts = []
    for entry in sorted(contexts_dir.iterdir()):
        if not entry.is_dir():
            continue

        context_md = entry / "CONTEXT.md"
        if not context_md.exists():
            continue

        text = context_md.read_text()
        frontmatter, body = parse_frontmatter(text)

        script = find_run_script(entry)

        contexts.append(
            Context(
                name=entry.name,
                path=entry,
                command=frontmatter.get("command"),
                script=script,
                timeout=frontmatter.get("timeout", 30),
                enabled=frontmatter.get("enabled", True),
                static_content=body,
            )
        )

    return contexts


def run_context(context: Context, project_root: Path) -> ContextResult:
    """Run a single context command and return the result."""
    if not context.script and not context.command:
        # Static-only context, no command to run
        return ContextResult(context=context, output="", success=True)

    r = run_command(
        script=context.script,
        command=context.command,
        cwd=project_root,
        timeout=context.timeout,
    )
    return ContextResult(
        context=context,
        output=r.output,
        success=r.success,
        timed_out=r.timed_out,
    )


def run_all_contexts(contexts: list[Context], project_root: Path) -> list[ContextResult]:
    """Run all contexts and return results."""
    return [run_context(ctx, project_root) for ctx in contexts]


def _render_context(result: ContextResult) -> str:
    """Render a single context result into text for prompt injection."""
    parts = []

    if result.context.static_content:
        parts.append(result.context.static_content)

    output = truncate_output(result.output)

    if output.strip():
        parts.append(output.strip())

    return "\n".join(parts)


def resolve_contexts(prompt: str, results: list[ContextResult]) -> str:
    """Replace context placeholders in a prompt string.

    - {{ contexts.<name> }} → specific context content
    - {{ contexts }} → all enabled contexts not already placed
    - If no placeholders found → append all at end
    """
    available: dict[str, str] = {}
    for r in results:
        if not r.context.enabled:
            continue
        rendered = _render_context(r)
        if rendered:
            available[r.context.name] = rendered

    return resolve_placeholders(prompt, available, _NAMED_PATTERN, _BULK_PATTERN)
