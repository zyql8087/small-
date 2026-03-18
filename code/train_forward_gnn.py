from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main():
    runpy.run_path(str(ROOT / "train_forward_gnn.py"), run_name="__main__")


if __name__ == "__main__":
    main()
