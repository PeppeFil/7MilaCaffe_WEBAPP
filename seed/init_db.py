import argparse
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import create_app
from app.extensions import db
from seed.seed_demo import esegui_seed


def main():
    parser = argparse.ArgumentParser(description="Inizializza il database dell'app")
    parser.add_argument("--reset", action="store_true", help="Esegue drop e recreate di tutte le tabelle")
    parser.add_argument("--seed", action="store_true", help="Carica dati demo")
    args = parser.parse_args()

    app = create_app("development")
    with app.app_context():
        if args.reset:
            db.drop_all()
        db.create_all()
        print("Database inizializzato.")
        if args.seed:
            esegui_seed(reset=False)
            print("Dati demo caricati.")


if __name__ == "__main__":
    main()
