"""Deliver review feedback to the Codex session that opened this server."""
import os
from pathlib import Path
import shutil
import subprocess


def queue_feedback(folder, data, event_type):
    thread = os.environ.get("CODEX_THREAD_ID")
    if not thread:
        return False  # Other agents still consume the review through `wait`.
    executable = shutil.which("codex")
    if not executable:
        raise RuntimeError("Codex CLI indisponível. Suas notas continuam salvas.")
    command = [executable]
    if Path(executable).suffix.lower() in (".cmd", ".ps1", ".bat"):
        # Avoid passing user text through a Windows command shell.
        launcher = Path(executable).parent / "node_modules/@openai/codex/bin/codex.js"
        node = shutil.which("node")
        if not node or not launcher.is_file():
            raise RuntimeError("Não foi possível localizar o executável do Codex.")
        command = [node, str(launcher)]
    notes = [c for c in data["comments"] if c["stage"] == data["stage"]
             and c["round"] == data["round"] and not c.get("queued")]
    message = (f"Feedback enviado pela revisão Cooked neste chat. Ação: {event_type}.\n"
               f"Projeto: {Path(folder).resolve()}\n"
               f"Etapa: {data['stage']}, versão: {data['round']}.\n"
               "Leia review.json e os anexos locais para aplicar o feedback e atualizar a revisão.\n")
    message += "\n".join(f"Nota #{c['id']} em {c['t']:.2f}s: {c['text']}" for c in notes)
    try:
        result = subprocess.run(command + ["queue", "--thread", thread, "--message", message],
                                capture_output=True, text=True, encoding="utf-8", timeout=8,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Não foi possível confirmar o envio ao Codex. As notas foram preservadas.") from exc
    if result.returncode:
        raise RuntimeError("O Codex recusou o envio. Suas notas continuam salvas nesta revisão.")
    return True
