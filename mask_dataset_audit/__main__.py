import argparse
import json
from pathlib import Path
import sys

from .audit import audit
from .report import render_html


def _integers(value):
    try:
        return [int(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use comma-separated integer IDs, e.g. 0,1,2") from error


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit PNG segmentation masks without changing them")
    parser.add_argument("root", type=Path)
    parser.add_argument("--labels", required=True, type=_integers)
    parser.add_argument("--ignore", default=[], type=_integers)
    parser.add_argument("--background", default=0, type=int)
    parser.add_argument("--splits", default="train,val,test")
    parser.add_argument("--out", required=True, type=Path, help="New report directory outside the dataset")
    args = parser.parse_args(argv)
    try:
        root, out = args.root.resolve(), args.out.resolve()
        if out == root or root in out.parents:
            raise ValueError("Report directory must be outside the dataset")
        if out.exists():
            raise ValueError("Report directory already exists; choose a new --out path")
        report = audit(root, labels=args.labels, ignore=args.ignore,
                       splits=args.splits.split(","), background=args.background)
        out.mkdir(parents=True, exist_ok=False)
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        (out / "report.html").write_text(render_html(report), encoding="utf-8")
        print(json.dumps({"summary": report["summary"], "report": str(out / "report.html")}, indent=2))
        return 1 if report["summary"]["errors"] else 0
    except (OSError, ValueError) as error:
        print(f"mask-dataset-audit: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
