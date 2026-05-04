from pathlib import Path
import shutil


def copy_dataset(src: str, dst_dir: str = "data/datasets") -> str:
    dst_path = Path(dst_dir)
    dst_path.mkdir(parents=True, exist_ok=True)
    src_path = Path(src)
    final_path = dst_path / src_path.name
    shutil.copy2(src_path, final_path)
    return str(final_path)


if __name__ == "__main__":
    import sys
    for item in sys.argv[1:]:
        print(copy_dataset(item))
