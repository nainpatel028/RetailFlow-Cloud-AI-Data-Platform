"""Tests for scripts/generate_data.py Parquet output.

Correctness tests run against a small temporary fixture profile (built from
the real config/data_generation.yml with row counts shrunk down) so the
suite stays fast and never triggers a full portfolio-scale generation. A
second set of tests validates the real project-scale manifests under
data/incoming/ if they have already been generated, skipping cleanly
otherwise — see docs/tickets and README.md for how to generate them.
"""

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = REPO_ROOT / "scripts" / "generate_data.py"
REAL_CONFIG_PATH = REPO_ROOT / "config" / "data_generation.yml"
REAL_OUTPUT_ROOT = REPO_ROOT / "data" / "incoming"

CUSTOMER_COLUMNS = ["customer_id", "full_name", "email", "province", "signup_date", "customer_status"]
ORDER_COLUMNS = ["order_id", "customer_id", "order_timestamp", "order_status", "sales_channel", "order_amount", "currency"]
PAYMENT_COLUMNS = ["payment_id", "order_id", "payment_timestamp", "payment_method", "payment_status", "payment_amount", "currency", "failure_reason"]

PROVINCES = {"AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"}
ORDER_STATUS = {"pending", "completed", "cancelled"}
PAYMENT_STATUS = {"pending", "successful", "failed"}

REQUIRED_CUSTOMER_ISSUES = {
    "DUPLICATE_CUSTOMER_ID", "NULL_OR_BLANK_CUSTOMER_ID", "BLANK_EMAIL", "MALFORMED_EMAIL",
    "INVALID_PROVINCE_CODE", "INVALID_CUSTOMER_STATUS", "INVALID_SIGNUP_DATE", "FUTURE_SIGNUP_DATE",
    "WHITESPACE_PADDING", "MIXED_CASING",
}
REQUIRED_ORDER_ISSUES = {
    "DUPLICATE_ORDER_ID", "NULL_OR_BLANK_ORDER_ID", "ORPHAN_CUSTOMER_ID", "MISSING_CUSTOMER_ID",
    "INVALID_ORDER_TIMESTAMP", "FUTURE_ORDER_TIMESTAMP", "NONNUMERIC_ORDER_AMOUNT", "NEGATIVE_ORDER_AMOUNT",
    "BLANK_ORDER_AMOUNT", "INVALID_ORDER_STATUS", "INVALID_SALES_CHANNEL", "WHITESPACE_PADDING",
    "INVALID_CURRENCY",
}
REQUIRED_PAYMENT_ISSUES = {
    "DUPLICATE_PAYMENT_ID", "NULL_OR_BLANK_PAYMENT_ID", "ORPHAN_ORDER_ID", "MISSING_ORDER_ID",
    "INVALID_PAYMENT_TIMESTAMP", "PAYMENT_BEFORE_ORDER", "NONNUMERIC_PAYMENT_AMOUNT", "NEGATIVE_PAYMENT_AMOUNT",
    "BLANK_PAYMENT_AMOUNT", "AMOUNT_MISMATCH", "INVALID_PAYMENT_METHOD", "INVALID_PAYMENT_STATUS",
    "INVALID_CURRENCY", "FAILED_MISSING_REASON", "SUCCESSFUL_WITH_REASON",
}

# Small enough to run in seconds; large enough that even the rarest
# configured issue rate (0.1%) is expected to produce several rows.
FIXTURE_ROW_COUNTS = {"customers": 6000, "orders": 6000, "payments": 7000}
FIXTURE_ROWS_PER_FILE = {"customers": 3000, "orders": 3000, "payments": 3500}

REAL_EXPECTED_COUNTS = {
    "development": {"customers": 10000, "orders": 100000, "payments": 130000},
    "portfolio": {"customers": 100000, "orders": 1000000, "payments": 1300000},
}


def _load_real_config() -> dict:
    with REAL_CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _build_fixture_config(tmp_path: Path) -> Path:
    config = copy.deepcopy(_load_real_config())
    config["profiles"] = {
        "development": {
            "row_counts": FIXTURE_ROW_COUNTS,
            "rows_per_file": FIXTURE_ROWS_PER_FILE,
        }
    }
    config_path = tmp_path / "fixture_config.yml"
    with config_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config, f)
    return config_path


def _run_generator(config_path: Path, output_root: Path, profile: str = "development", extra_args=None):
    args = [
        sys.executable, str(GENERATOR),
        "--profile", profile,
        "--config", str(config_path),
        "--output-root", str(output_root),
    ]
    if extra_args:
        args.extend(extra_args)
    return subprocess.run(args, cwd=REPO_ROOT, capture_output=True, text=True)


def _read_dataset(profile_dir: Path, name: str, columns: list[str]):
    files = sorted((profile_dir / name).glob("*.parquet"))
    frames = [pd.read_parquet(f) for f in files]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=columns)
    return df, files


@pytest.fixture(scope="module")
def fixture_dir(tmp_path_factory):
    base = tmp_path_factory.mktemp("retailflow_fixture")
    config_path = _build_fixture_config(base)
    output_root = base / "incoming"
    result = _run_generator(config_path, output_root)
    assert result.returncode == 0, result.stderr
    return {"config_path": config_path, "output_root": output_root, "profile_dir": output_root / "development"}


# --------------------------------------------------------------------------
# Schema / structure
# --------------------------------------------------------------------------

def test_schema_and_column_order(fixture_dir):
    profile_dir = fixture_dir["profile_dir"]
    for name, columns in (("customers", CUSTOMER_COLUMNS), ("orders", ORDER_COLUMNS), ("payments", PAYMENT_COLUMNS)):
        df, files = _read_dataset(profile_dir, name, columns)
        assert list(df.columns) == columns
        for f in files:
            schema = pq.read_schema(f)
            assert schema.names == columns
            for field in schema:
                assert field.type == pa.string(), f"{f}:{field.name} is {field.type}, expected string"


def test_parquet_files_readable(fixture_dir):
    profile_dir = fixture_dir["profile_dir"]
    for name, columns in (("customers", CUSTOMER_COLUMNS), ("orders", ORDER_COLUMNS), ("payments", PAYMENT_COLUMNS)):
        _, files = _read_dataset(profile_dir, name, columns)
        assert len(files) > 0
        for f in files:
            table = pq.read_table(f)
            assert table.num_columns == len(columns)


def test_row_counts_match_config(fixture_dir):
    profile_dir = fixture_dir["profile_dir"]
    for name, expected in FIXTURE_ROW_COUNTS.items():
        columns = {"customers": CUSTOMER_COLUMNS, "orders": ORDER_COLUMNS, "payments": PAYMENT_COLUMNS}[name]
        df, _ = _read_dataset(profile_dir, name, columns)
        assert len(df) == expected


def test_snappy_compression(fixture_dir):
    profile_dir = fixture_dir["profile_dir"]
    for name, columns in (("customers", CUSTOMER_COLUMNS), ("orders", ORDER_COLUMNS), ("payments", PAYMENT_COLUMNS)):
        _, files = _read_dataset(profile_dir, name, columns)
        for f in files:
            meta = pq.ParquetFile(f).metadata
            for rg in range(meta.num_row_groups):
                row_group = meta.row_group(rg)
                for col in range(row_group.num_columns):
                    assert row_group.column(col).compression.upper() == "SNAPPY"


def test_expected_part_file_counts(fixture_dir):
    manifest = json.loads((fixture_dir["profile_dir"] / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["datasets"]["customers"]["file_count"] == 2
    assert manifest["datasets"]["orders"]["file_count"] == 2
    assert manifest["datasets"]["payments"]["file_count"] == 2


def test_no_csv_files_generated(fixture_dir):
    assert list(fixture_dir["output_root"].rglob("*.csv")) == []


def test_no_csv_files_in_real_project_data():
    if not REAL_OUTPUT_ROOT.exists():
        pytest.skip("data/incoming has not been generated yet")
    assert list(REAL_OUTPUT_ROOT.rglob("*.csv")) == []


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------

def test_manifest_hashes_match_files(fixture_dir):
    profile_dir = fixture_dir["profile_dir"]
    manifest = json.loads((profile_dir / "manifest.json").read_text(encoding="utf-8"))
    for dataset in manifest["datasets"].values():
        for file_info in dataset["files"]:
            digest = hashlib.sha256((profile_dir / file_info["path"]).read_bytes()).hexdigest()
            assert digest == file_info["sha256"]


def test_manifest_has_no_generation_timestamp(fixture_dir):
    manifest = json.loads((fixture_dir["profile_dir"] / "manifest.json").read_text(encoding="utf-8"))
    assert "generated_at" not in manifest
    assert manifest["seed"] == 42
    assert manifest["compression"] == "snappy"


def test_manifest_raw_types_are_string(fixture_dir):
    manifest = json.loads((fixture_dir["profile_dir"] / "manifest.json").read_text(encoding="utf-8"))
    for dataset in manifest["datasets"].values():
        assert set(dataset["raw_types"].values()) == {"string"}


# --------------------------------------------------------------------------
# Data-quality issue injection
# --------------------------------------------------------------------------

def test_all_customer_issues_present_and_counted(fixture_dir):
    manifest = json.loads((fixture_dir["profile_dir"] / "manifest.json").read_text(encoding="utf-8"))
    issues = {i["code"]: i for i in manifest["issues"]["customers"]}
    assert REQUIRED_CUSTOMER_ISSUES.issubset(issues.keys())
    for code in REQUIRED_CUSTOMER_ISSUES:
        assert issues[code]["affected_row_count"] > 0, code


def test_all_order_issues_present_and_counted(fixture_dir):
    manifest = json.loads((fixture_dir["profile_dir"] / "manifest.json").read_text(encoding="utf-8"))
    issues = {i["code"]: i for i in manifest["issues"]["orders"]}
    assert REQUIRED_ORDER_ISSUES.issubset(issues.keys())
    for code in REQUIRED_ORDER_ISSUES:
        assert issues[code]["affected_row_count"] > 0, code


def test_all_payment_issues_present_and_counted(fixture_dir):
    manifest = json.loads((fixture_dir["profile_dir"] / "manifest.json").read_text(encoding="utf-8"))
    issues = {i["code"]: i for i in manifest["issues"]["payments"]}
    assert REQUIRED_PAYMENT_ISSUES.issubset(issues.keys())
    for code in REQUIRED_PAYMENT_ISSUES:
        assert issues[code]["affected_row_count"] > 0, code


def test_issue_counts_do_not_exceed_configured_rate(fixture_dir):
    manifest = json.loads((fixture_dir["profile_dir"] / "manifest.json").read_text(encoding="utf-8"))
    row_counts = {name: d["row_count"] for name, d in manifest["datasets"].items()}
    for dataset_name in ("customers", "orders", "payments"):
        n = row_counts[dataset_name]
        for issue in manifest["issues"][dataset_name]:
            expected = issue["configured_rate"] * n
            tolerance = max(expected * 0.75, 10)
            assert issue["affected_row_count"] <= expected + tolerance, issue


def test_raw_invalid_values_preserved(fixture_dir):
    profile_dir = fixture_dir["profile_dir"]
    orders_df, _ = _read_dataset(profile_dir, "orders", ORDER_COLUMNS)
    payments_df, _ = _read_dataset(profile_dir, "payments", PAYMENT_COLUMNS)
    config = _load_real_config()

    invalid_order_amounts = set(config["invalid_values"]["order_amount"])
    assert set(orders_df["order_amount"]) & invalid_order_amounts

    assert (orders_df["customer_id"] == "").any() or orders_df["customer_id"].isnull().any()
    assert (payments_df["order_id"] == "ORD-ORPHAN").any()
    assert (orders_df["customer_id"] == "CUST-ORPHAN").any()


def test_majority_of_rows_remain_valid(fixture_dir):
    profile_dir = fixture_dir["profile_dir"]
    customers_df, _ = _read_dataset(profile_dir, "customers", CUSTOMER_COLUMNS)
    orders_df, _ = _read_dataset(profile_dir, "orders", ORDER_COLUMNS)
    payments_df, _ = _read_dataset(profile_dir, "payments", PAYMENT_COLUMNS)

    assert customers_df["province"].isin(PROVINCES).mean() > 0.9
    assert orders_df["order_status"].isin(ORDER_STATUS).mean() > 0.9
    valid_amounts = pd.to_numeric(orders_df["order_amount"], errors="coerce")
    assert (valid_amounts.notna() & (valid_amounts >= 0)).mean() > 0.9
    assert payments_df["payment_status"].isin(PAYMENT_STATUS).mean() > 0.9


# --------------------------------------------------------------------------
# CLI behavior
# --------------------------------------------------------------------------

def test_overwrite_protection_and_force(tmp_path_factory):
    base = tmp_path_factory.mktemp("retailflow_overwrite")
    config_path = _build_fixture_config(base)
    output_root = base / "incoming"

    first = _run_generator(config_path, output_root)
    assert first.returncode == 0, first.stderr

    blocked = _run_generator(config_path, output_root)
    assert blocked.returncode != 0
    assert "overwrite" in (blocked.stdout + blocked.stderr).lower()

    forced = _run_generator(config_path, output_root, extra_args=["--force"])
    assert forced.returncode == 0, forced.stderr


def test_deterministic_regeneration(tmp_path_factory):
    base = tmp_path_factory.mktemp("retailflow_determinism")
    config_path = _build_fixture_config(base)
    output_root = base / "incoming"

    result_a = _run_generator(config_path, output_root)
    assert result_a.returncode == 0, result_a.stderr
    manifest_a = json.loads((output_root / "development" / "manifest.json").read_text(encoding="utf-8"))

    result_b = _run_generator(config_path, output_root, extra_args=["--force"])
    assert result_b.returncode == 0, result_b.stderr
    manifest_b = json.loads((output_root / "development" / "manifest.json").read_text(encoding="utf-8"))

    def file_hashes(manifest):
        return {
            (name, f["path"]): f["sha256"]
            for name, d in manifest["datasets"].items() for f in d["files"]
        }

    assert file_hashes(manifest_a) == file_hashes(manifest_b)
    assert manifest_a["issues"] == manifest_b["issues"]


# --------------------------------------------------------------------------
# Real project-scale manifests (skip cleanly if not yet generated)
# --------------------------------------------------------------------------

@pytest.mark.parametrize("profile_name", ["development", "portfolio"])
def test_real_profile_row_counts(profile_name):
    manifest_path = REAL_OUTPUT_ROOT / profile_name / "manifest.json"
    if not manifest_path.exists():
        pytest.skip(f"{profile_name} profile not generated at {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for dataset_name, expected_count in REAL_EXPECTED_COUNTS[profile_name].items():
        assert manifest["datasets"][dataset_name]["row_count"] == expected_count


@pytest.mark.parametrize("profile_name", ["development", "portfolio"])
def test_real_profile_manifest_hashes(profile_name):
    profile_dir = REAL_OUTPUT_ROOT / profile_name
    manifest_path = profile_dir / "manifest.json"
    if not manifest_path.exists():
        pytest.skip(f"{profile_name} profile not generated at {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for dataset in manifest["datasets"].values():
        for file_info in dataset["files"]:
            digest = hashlib.sha256((profile_dir / file_info["path"]).read_bytes()).hexdigest()
            assert digest == file_info["sha256"]
