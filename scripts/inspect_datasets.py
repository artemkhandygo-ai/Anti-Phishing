from pathlib import Path
import pandas as pd


def main() -> None:
    dataset_dir = Path("data/datasets")
    for path in sorted(dataset_dir.glob("*.csv")):
        try:
            if path.name.lower() == "spam.csv":
                df = pd.read_csv(path, encoding="latin1")
            else:
                df = pd.read_csv(path)
            print("=" * 80)
            print(path.name)
            print(f"rows: {len(df)}")
            print(f"columns: {list(df.columns)}")
            print("head:")
            print(df.head(2).to_string(index=False, max_colwidth=60))
        except Exception as exc:
            print("=" * 80)
            print(path.name)
            print(f"ERROR: {exc}")


if __name__ == "__main__":
    main()
