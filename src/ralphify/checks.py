import warnings
from dataclasses import dataclass
from pathlib import Path

from ralphify._frontmatter import find_run_script, parse_frontmatter
from ralphify._output import truncate_output
from ralphify._runner import run_command


@dataclass
class Check:
    name: str
    path: Path
    command: str | None
    script: Path | None
    timeout: int = 60
    enabled: bool = True
    failure_instruction: str = ""


@dataclass
class CheckResult:
    check: Check
    passed: bool
    exit_code: int
    output: str
    timed_out: bool = False


def discover_checks(root: Path = Path(".")) -> list[Check]:
    """Discover checks in root/.ralph/checks/ directories."""
    checks_dir = root / ".ralph" / "checks"
    if not checks_dir.is_dir():
        return []

    checks = []
    for entry in sorted(checks_dir.iterdir()):
        if not entry.is_dir():
            continue

        check_md = entry / "CHECK.md"
        if not check_md.exists():
            continue

        text = check_md.read_text()
        frontmatter, body = parse_frontmatter(text)

        script = find_run_script(entry)
        command = frontmatter.get("command")

        if not script and not command:
            warnings.warn(f"Check '{entry.name}' has neither a run.* script nor a command — skipping")
            continue

        checks.append(
            Check(
                name=entry.name,
                path=entry,
                command=command,
                script=script,
                timeout=frontmatter.get("timeout", 60),
                enabled=frontmatter.get("enabled", True),
                failure_instruction=body,
            )
        )

    return checks


def run_check(check: Check, project_root: Path) -> CheckResult:
    """Run a single check and return the result."""
    r = run_command(
        script=check.script,
        command=check.command,
        cwd=project_root,
        timeout=check.timeout,
    )
    return CheckResult(
        check=check,
        passed=r.success,
        exit_code=r.exit_code,
        output=r.output,
        timed_out=r.timed_out,
    )


def run_all_checks(checks: list[Check], project_root: Path) -> list[CheckResult]:
    """Run all checks and return results."""
    return [run_check(check, project_root) for check in checks]


def format_check_failures(results: list[CheckResult]) -> str:
    """Format check failures as markdown for injection into the next prompt.

    Returns empty string if all checks passed.
    """
    failures = [r for r in results if not r.passed]
    if not failures:
        return ""

    parts = ["## Check Failures\n"]
    parts.append("The following checks failed after the last iteration. Fix these issues:\n")

    for r in failures:
        parts.append(f"### {r.check.name}")
        if r.timed_out:
            parts.append(f"**Timed out** after {r.check.timeout}s")
        else:
            parts.append(f"**Exit code:** {r.exit_code}")

        output = truncate_output(r.output)

        if output.strip():
            parts.append(f"\n```\n{output.strip()}\n```\n")

        if r.check.failure_instruction:
            parts.append(r.check.failure_instruction)
            parts.append("")

    return "\n".join(parts)
