from pathlib import Path
import csv

# This helper regenerates the built-in 1000-row safe email dataset.


def main() -> None:
    source = Path("data/datasets/safe_emails.csv")
    if source.exists():
        print(f"Dataset already exists: {source}")
        return
    print("Dataset missing. Please restore safe_emails.csv from the project archive.")


if __name__ == "__main__":
    main()
