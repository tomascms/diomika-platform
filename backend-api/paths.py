"""Caminhos partilhados do backend."""
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_ROOT.parent


def heartbeat_path(root: Path = BACKEND_ROOT) -> Path:
    """Onde o worker de email escreve a hora da última volta e o /health a lê. Em `data/`: é a única pasta (com `logs/`)
    em que o contentor, que corre sem root, pode escrever (I-1 da revisão final)."""
    return root / "data" / ".email_worker_heartbeat.json"

