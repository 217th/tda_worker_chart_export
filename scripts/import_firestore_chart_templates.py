#!/usr/bin/env python3
"""Import chart templates into Firestore.

Usage example:
  python3 scripts/import_firestore_chart_templates.py \
    --project kb-agent-479608 \
    --database tda-db \
    --collection chart_templates \
    --dir docs-worker-chart-export/chart-templates

Notes:
- Expects JSON files in --dir, each file name (without .json) is used as document id.
- Uses default application credentials (gcloud auth / Cloud Shell). No creds embedded.
- Safe to commit: no project-specific secrets inside.
"""
import argparse
import json
from pathlib import Path
from typing import Any

from google.cloud import firestore


def load_templates(dir_path: Path) -> dict[str, dict[str, Any]]:
    data: dict[str, dict[str, Any]] = {}
    for path in dir_path.glob("*.json"):
        doc_id = path.stem
        with path.open("r", encoding="utf-8") as f:
            data[doc_id] = json.load(f)
    if not data:
        raise SystemExit(f"No JSON files found in {dir_path}")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Import chart templates into Firestore")
    parser.add_argument("--project", required=True)
    parser.add_argument("--database", default="(default)")
    parser.add_argument("--collection", default="chart_templates")
    parser.add_argument("--dir", required=True, help="Directory with template JSON files")
    args = parser.parse_args()

    dir_path = Path(args.dir)
    templates = load_templates(dir_path)

    client = firestore.Client(project=args.project, database=args.database)
    batch = client.batch()
    for doc_id, payload in templates.items():
        ref = client.collection(args.collection).document(doc_id)
        batch.set(ref, payload)
    batch.commit()
    print(f"Imported {len(templates)} templates into {args.collection} (project={args.project}, db={args.database})")


if __name__ == "__main__":
    main()
