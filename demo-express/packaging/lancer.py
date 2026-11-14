"""Point d'entrée de l'application installée (PyInstaller).

Double-clic : une petite fenêtre « Démo Express » s'ouvre (pas de console noire). Elle démarre l'interface sur
http://127.0.0.1:8777/, ouvre le navigateur, et arrête tout quand on clique sur « Quitter » ou qu'on la ferme.
Le navigateur intégré (images et PDF des maquettes) n'est téléchargé qu'au premier export.

Variables utiles (tests, dépannage) : DEMO_SANS_NAVIGATEUR=1 (ne pas ouvrir le navigateur),
DEMO_SANS_FENETRE=1 (serveur seul), DEMO_DONNEES (dossier de données).
"""

from __future__ import annotations

import os
import queue
import sys
import threading
import urllib.request
import webbrowser
from pathlib import Path

from demo_express.langue import _
from demo_express.reglages import Reglages, dossier_par_defaut

NOM = "Démo Express"
AUTEUR = "VORELIK"
PORT = 8777
ADRESSE = f"http://127.0.0.1:{PORT}/"
ACCENT, ACCENT_FONCE, FOND, ENCRE, GRIS = "#6d5bef", "#5546d1", "#f5f7fc", "#0f1733", "#5b6480"


def ressource(nom: str) -> Path:
    """Fichier livré dans l'application (icône…)."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / nom


def rediriger_sorties() -> None:
    """Application sans console (Windows) : les messages vont dans <données>/console.log."""
    if sys.stdout is None or sys.stderr is None:
        dossier = dossier_par_defaut()
        dossier.mkdir(parents=True, exist_ok=True)
        fichier = open(dossier / "console.log", "w", encoding="utf-8", buffering=1)  # noqa: SIM115
        sys.stdout = sys.stdout or fichier
        sys.stderr = sys.stderr or fichier


def deja_lance() -> bool:
    """Vrai si Démo Express répond déjà sur le port (application ouverte deux fois)."""
    try:
        with urllib.request.urlopen(ADRESSE + "licence", timeout=2) as r:
            return NOM.encode() in r.read(20000)
    except OSError:
        return False


def creer_serveur():
    import uvicorn

    from demo_express.web import creer_app

    app = creer_app(Reglages(dossier_par_defaut()))  # applique aussi la langue choisie dans les Réglages
    serveur = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning", log_config=None))
    serveur.install_signal_handlers = lambda: None  # tourne dans un fil secondaire
    return serveur


def ouvrir_navigateur() -> None:
    if not os.environ.get("DEMO_SANS_NAVIGATEUR"):
        webbrowser.open(ADRESSE)


class Fenetre:
    def __init__(self, tk):
        from tkinter import ttk

        self.racine = tk.Tk()
        self.racine.title(f"{NOM} by {AUTEUR}")
        self.racine.configure(bg=FOND)
        self.racine.resizable(False, False)
        try:
            self.icone = tk.PhotoImage(file=str(ressource("icone.png")))
            self.racine.iconphoto(True, self.icone)
        except (tk.TclError, OSError):
            pass
        cadre = tk.Frame(self.racine, bg=FOND, padx=28, pady=22)
        cadre.pack()
        titre = tk.Frame(cadre, bg=FOND)
        titre.pack(anchor="w")
        tk.Label(titre, text=NOM, bg=FOND, fg=ENCRE, font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(titre, text=f"by {AUTEUR}", bg=FOND, fg=GRIS, font=("Segoe UI", 10)).pack(side="left", padx=(8, 0), pady=(6, 0))
        tk.Label(cadre, text=_("Le futur site de votre prospect, en deux minutes"), bg=FOND, fg=GRIS,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 14))
        self.etat = tk.Label(cadre, text=_("Démarrage…"), bg=FOND, fg=ENCRE, font=("Segoe UI", 11), justify="left", wraplength=420)
        self.etat.pack(anchor="w")
        self.barre = ttk.Progressbar(cadre, mode="indeterminate", length=420)
        self.barre.pack(anchor="w", pady=(10, 14))
        boutons = tk.Frame(cadre, bg=FOND)
        boutons.pack(anchor="w", fill="x")
        self.ouvrir = tk.Button(boutons, text=_("Ouvrir l'interface"), command=ouvrir_navigateur, state="disabled",
                                bg=ACCENT, fg="white", activebackground=ACCENT_FONCE, activeforeground="white",
                                relief="flat", padx=16, pady=6, font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.ouvrir.pack(side="left")
        tk.Button(boutons, text=_("Quitter"), command=self.quitter, relief="flat", padx=16, pady=6,
                  font=("Segoe UI", 10), cursor="hand2").pack(side="left", padx=(10, 0))
        tk.Label(cadre, text=_("Gardez cette fenêtre ouverte (vous pouvez la réduire) : la fermer arrête l'application."),
                 bg=FOND, fg=GRIS, font=("Segoe UI", 9), wraplength=420, justify="left").pack(anchor="w", pady=(14, 0))
        self.racine.protocol("WM_DELETE_WINDOW", self.quitter)
        self.serveur = None
        self.messages: queue.Queue = queue.Queue()

    # Seul le fil principal touche à la fenêtre (Tk n'est pas sûr entre fils, notamment sur Mac) :
    # le fil de démarrage dépose des messages, relevés toutes les 100 ms.
    def afficher(self, texte: str, occupe: bool) -> None:
        print(texte, flush=True)
        self.messages.put(("etat", texte, occupe))

    def _relever(self) -> None:
        while True:
            try:
                genre, *valeurs = self.messages.get_nowait()
            except queue.Empty:
                break
            if genre == "pret":
                self.ouvrir.configure(state="normal")
                continue
            texte, occupe = valeurs
            self.etat.configure(text=texte)
            if occupe:
                self.barre.start(12)
            else:
                self.barre.stop()
                self.barre.pack_forget()
        self.racine.after(100, self._relever)

    def demarrer(self) -> None:
        self.racine.after(100, self._relever)
        threading.Thread(target=self._preparer, daemon=True).start()
        self.racine.mainloop()

    def _preparer(self) -> None:
        self.afficher(_("Démarrage de l'interface…"), True)
        try:
            self.serveur = creer_serveur()
        except Exception as e:  # noqa: BLE001 — affiché à l'utilisateur
            self.afficher(_("⚠ Impossible de démarrer : {erreur}").format(erreur=e), False)
            return
        threading.Thread(target=self.serveur.run, daemon=True).start()
        for _essai in range(300):
            if self.serveur.started or self.serveur.should_exit:
                break
            threading.Event().wait(0.1)
        if not self.serveur.started:
            self.afficher(_("⚠ Le port {port} est déjà utilisé par un autre programme. Fermez-le, puis relancez.").format(port=PORT), False)
            return
        self.afficher(_("L'application est prête : {adresse}").format(adresse=ADRESSE), False)
        self.messages.put(("pret",))
        ouvrir_navigateur()

    def quitter(self) -> None:
        if self.serveur is not None:
            self.serveur.should_exit = True
        self.racine.destroy()


def sans_fenetre() -> int:
    """Serveur seul, au premier plan (pas d'affichage graphique disponible, ou DEMO_SANS_FENETRE)."""
    serveur = creer_serveur()
    threading.Timer(1.5, ouvrir_navigateur).start()
    print(f"{NOM} : {ADRESSE}", flush=True)
    serveur.run()
    return 0


def fermer_ecran_de_demarrage() -> None:
    if "_PYI_SPLASH_IPC" not in os.environ:  # écran présent seulement dans l'exécutable Windows
        return
    try:
        import pyi_splash

        pyi_splash.close()
    except Exception:  # noqa: BLE001 — l'écran de démarrage n'est qu'un confort
        pass


def main() -> int:
    rediriger_sorties()
    fermer_ecran_de_demarrage()
    if deja_lance():
        ouvrir_navigateur()
        return 0
    Reglages(dossier_par_defaut())  # langue enregistrée, pour cette fenêtre aussi
    if os.environ.get("DEMO_SANS_FENETRE"):
        return sans_fenetre()
    try:
        import tkinter as tk

        fenetre = Fenetre(tk)
    except Exception:  # noqa: BLE001 — pas d'affichage graphique : on sert quand même l'interface
        return sans_fenetre()
    fenetre.demarrer()
    return 0


if __name__ == "__main__":
    sys.exit(main())
