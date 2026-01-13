import sys
from pathlib import Path

FILENAME = Path(__file__).parent / "redditbabes.txt"


def load_subreddits() -> list[str]:
    try:
        with FILENAME.open("r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []


def save_subreddits(subreddits: list[str]) -> None:
    with FILENAME.open("w", encoding="utf-8") as f:
        f.write("\n".join(subreddits))


def list_subreddits() -> None:
    subs = load_subreddits()
    if not subs:
        print("Aucun subreddit enregistré.")
    else:
        for i, sub in enumerate(subs, 1):
            print(f"{i}. {sub}")


def add_subreddit(name: str) -> None:
    subs = load_subreddits()
    if name in subs:
        print(f"{name} est déjà dans la liste.")
        return
    subs.append(name)
    save_subreddits(subs)
    print(f"{name} ajouté.")


def remove_subreddit(name: str) -> None:
    subs = load_subreddits()
    if name not in subs:
        print(f"{name} n’est pas dans la liste.")
        return
    subs = [s for s in subs if s != name]
    save_subreddits(subs)
    print(f"{name} supprimé.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: reddit [list|add|remove] [args...]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "list":
        list_subreddits()
    elif cmd == "add" and len(sys.argv) > 2:
        add_subreddit(sys.argv[2])
    elif cmd in ("remove", "rm") and len(sys.argv) > 2:
        remove_subreddit(sys.argv[2])
    else:
        print("Commande inconnue.")
