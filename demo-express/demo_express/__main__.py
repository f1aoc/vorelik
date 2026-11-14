"""Lancement : python -m demo_express → interface sur http://127.0.0.1:8777, ouverte dans le navigateur."""

from __future__ import annotations

import argparse
import os
import threading
import webbrowser

import uvicorn

from demo_express.reglages import Reglages, dossier_par_defaut
from demo_express.web import creer_app

PORT = 8777


def main() -> None:
    parser = argparse.ArgumentParser(prog="demo-express", description="Démo Express : maquettes de sites à partir des fiches Google.")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--sans-navigateur", action="store_true", help="ne pas ouvrir le navigateur")
    args = parser.parse_args()
    app = creer_app(Reglages(dossier_par_defaut()))
    if not args.sans_navigateur and not os.environ.get("DEMO_SANS_NAVIGATEUR"):
        threading.Timer(1.0, webbrowser.open, args=(f"http://127.0.0.1:{args.port}/",)).start()
    # Uniquement sur cet ordinateur : jamais accessible depuis le réseau
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
