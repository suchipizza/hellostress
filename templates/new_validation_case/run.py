from pathlib import Path


def main() -> None:
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    raise SystemExit("TODO: implement the validation command and comparison logic.")


if __name__ == "__main__":
    main()
