# -*- coding: utf-8 -*-
"""
Supabase Postgres에 seed_water_leisure.sql 전체 실행(한 번에 여러 문).

  pip install "psycopg[binary]"
  PowerShell:
    $env:DATABASE_URL = "postgresql://postgres.[프로젝트]:[비밀번호]@aws-0-....pooler.supabase.com:6543/postgres"
    python tools/run_seed.py

DATABASE_URL: Supabase → Project Settings → Database → Connection string (URI)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "supabase" / "seed_water_leisure.sql"


def main() -> None:
    url = (os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DATABASE_URL") or "").strip()
    if not url:
        print(
            "DATABASE_URL(또는 SUPABASE_DATABASE_URL)이 없습니다.\n"
            "Supabase → Settings → Database → Connection string 에서 URI를 복사한 뒤,\n"
            "PowerShell: $env:DATABASE_URL='postgresql://...'\n"
            "python tools/run_seed.py",
            file=sys.stderr,
        )
        sys.exit(1)
    if not SEED.is_file():
        print("seed 파일 없음:", SEED, file=sys.stderr)
        sys.exit(1)

    try:
        import psycopg
    except ImportError:
        print('pip install "psycopg[binary]" 후 다시 실행하세요.', file=sys.stderr)
        sys.exit(1)

    sql = SEED.read_text(encoding="utf-8")
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(sql)
    print("OK:", SEED.name, "실행 완료")


if __name__ == "__main__":
    main()
