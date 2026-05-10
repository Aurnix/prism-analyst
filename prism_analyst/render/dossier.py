"""Full dossier markdown renderer."""

from __future__ import annotations

from ..models import Dossier


def render_dossier(dossier: Dossier) -> str:
    lines: list[str] = []

    lines.append(f"# Intelligence Dossier: {dossier.account_slug}")
    lines.append("")
    lines.append(f"*Generated: {dossier.generated_at.strftime('%Y-%m-%d %H:%M')} UTC*")
    lines.append(f"*Model: {dossier.model} | Prompt: {dossier.prompt_version}*")
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, section in enumerate(dossier.sections, 1):
        lines.append(f"## {i}. {section.title}")
        lines.append("")
        if section.content:
            lines.append(section.content)
        else:
            lines.append("*No data available for this section.*")
        lines.append("")

    return "\n".join(lines)
