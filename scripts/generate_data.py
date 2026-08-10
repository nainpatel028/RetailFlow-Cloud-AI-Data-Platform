#!/usr/bin/env python3
"""Deterministic synthetic data generator for RetailFlow raw source data.

Models a realistically dirty source-system export, not a clean production
dataset: the majority of rows are valid, but a configured, deterministic
fraction of rows carry data-quality problems (bad amounts, invalid dates,
orphaned foreign keys, etc.) that a future Silver layer is responsible for
catching and cleaning. See docs/data_contracts.md.

Output is Parquet (Snappy-compressed), written as multiple deterministically
named part files per dataset, under two profiles:

- development: small enough for fast local iteration
- portfolio: large enough for Snowflake / cloud-scale demonstrations

Usage:
    python scripts/generate_data.py
    python scripts/generate_data.py --profile development
    python scripts/generate_data.py --overwrite
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from faker import Faker

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "data_generation.yml"
OUTPUT_ROOT = REPO_ROOT / "data" / "incoming"

CUSTOMER_COLUMNS = [
    "customer_id", "full_name", "email", "province", "signup_date", "customer_status",
]
ORDER_COLUMNS = [
    "order_id", "customer_id", "order_timestamp", "order_status",
    "sales_channel", "order_amount", "currency",
]
PAYMENT_COLUMNS = [
    "payment_id", "order_id", "payment_timestamp", "payment_method",
    "payment_status", "payment_amount", "currency", "failure_reason",
]

ID_WIDTH = {"customer": 6, "order": 7, "payment": 7}
ORPHAN_CUSTOMER_ID = "CUST-ORPHAN"
ORPHAN_ORDER_ID = "ORD-ORPHAN"

DATE_FMT = "%Y-%m-%d"
TIMESTAMP_FMT = "%Y-%m-%dT%H:%M:%SZ"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# --------------------------------------------------------------------------
# RNG helpers
# --------------------------------------------------------------------------

def bernoulli_mask(rng: np.random.Generator, n: int, rate: float) -> np.ndarray:
    if rate <= 0:
        return np.zeros(n, dtype=bool)
    return rng.random(n) < rate


def exclusive_partition(rng: np.random.Generator, n: int, rate_map: dict) -> dict:
    """Assign each row to at most one issue code, proportional to rate_map.

    A single random draw per row keeps issues that target the same column
    from ever double-mutating a row, so manifest affected-row counts match
    the data exactly.
    """
    u = rng.random(n)
    masks = {}
    lo = 0.0
    for code, rate in rate_map.items():
        hi = lo + rate
        masks[code] = (u >= lo) & (u < hi)
        lo = hi
    return masks


def apply_null_or_blank(rng: np.random.Generator, values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    values = values.astype(object)
    idx = np.flatnonzero(mask)
    if len(idx) == 0:
        return values
    is_null = rng.random(len(idx)) < 0.5
    for pos, null_flag in zip(idx, is_null):
        values[pos] = None if null_flag else ""
    return values


def duplicate_within(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    values = values.astype(object).copy()
    idx = np.flatnonzero(mask)
    for i in idx:
        source = i - 1 if i > 0 else min(i + 1, len(values) - 1)
        values[i] = values[source]
    return values


def gen_ids(prefix: str, n: int, width: int) -> np.ndarray:
    numbers = np.arange(1, n + 1)
    padded = np.char.zfill(numbers.astype(str), width)
    return np.char.add(f"{prefix}-", padded).astype(object)


# --------------------------------------------------------------------------
# Base (pre-issue) generation
# --------------------------------------------------------------------------

def generate_customers_base(rng: np.random.Generator, faker: Faker, config: dict, n: int) -> pd.DataFrame:
    provinces = np.array(config["provinces"])
    statuses = np.array(config["domains"]["customer_status"])
    as_of = pd.Timestamp(config["as_of_date"])
    domains = ["example.com", "example.org", "example.net"]

    customer_id = gen_ids("CUST", n, ID_WIDTH["customer"])
    first_names = [faker.first_name() for _ in range(n)]
    last_names = [faker.last_name() for _ in range(n)]
    full_name = [f"{f} {l}" for f, l in zip(first_names, last_names)]
    email_domain = rng.choice(domains, size=n)
    email = [
        f"{re.sub(r'[^a-z0-9.]', '', f'{f}.{l}'.lower())}{i}@{d}"
        for i, (f, l, d) in enumerate(zip(first_names, last_names, email_domain), start=1)
    ]
    province = rng.choice(provinces, size=n)
    signup_offset_days = rng.integers(30, 1096, size=n)
    signup_date = (as_of - pd.to_timedelta(signup_offset_days, unit="D")).strftime(DATE_FMT)
    customer_status = rng.choice(statuses, size=n)

    return pd.DataFrame({
        "customer_id": customer_id,
        "full_name": pd.array(full_name, dtype=object),
        "email": pd.array(email, dtype=object),
        "province": province,
        "signup_date": np.asarray(signup_date, dtype=object),
        "customer_status": customer_status,
    })


def generate_orders_base(rng: np.random.Generator, config: dict, n: int, valid_customer_ids: np.ndarray):
    statuses = np.array(config["domains"]["order_status"])
    channels = np.array(config["domains"]["sales_channel"])
    as_of = pd.Timestamp(config["as_of_date"])
    currency = config["currency"]

    order_id = gen_ids("ORD", n, ID_WIDTH["order"])
    customer_id = rng.choice(valid_customer_ids, size=n)
    minutes_before = rng.integers(0, 180 * 24 * 60, size=n)
    order_dt = as_of - pd.to_timedelta(minutes_before, unit="m")
    order_timestamp = order_dt.strftime(TIMESTAMP_FMT)
    order_status = rng.choice(statuses, size=n)
    sales_channel = rng.choice(channels, size=n)
    order_amount_numeric = np.round(rng.uniform(10, 500, size=n), 2)
    order_amount = np.asarray([f"{v:.2f}" for v in order_amount_numeric], dtype=object)

    df = pd.DataFrame({
        "order_id": order_id,
        "customer_id": customer_id.astype(object),
        "order_timestamp": np.asarray(order_timestamp, dtype=object),
        "order_status": order_status,
        "sales_channel": sales_channel,
        "order_amount": order_amount,
        "currency": np.full(n, currency, dtype=object),
    })
    helpers = {"order_dt": order_dt, "order_amount_numeric": order_amount_numeric}
    return df, helpers


def generate_payments_base(rng: np.random.Generator, config: dict, n: int, orders_df: pd.DataFrame, order_helpers: dict):
    methods = np.array(config["domains"]["payment_method"])
    statuses = np.array(config["domains"]["payment_status"])
    failure_reasons = np.array(config["failure_reasons"])
    currency = config["currency"]

    order_ids = orders_df["order_id"].to_numpy(dtype=object)
    order_dt = order_helpers["order_dt"]
    order_amount_numeric = order_helpers["order_amount_numeric"]
    n_orders = len(order_ids)

    base_count = min(n, n_orders)
    base_idx = np.arange(base_count)
    extra_count = max(n - n_orders, 0)
    if extra_count > 0:
        extra_idx = rng.integers(0, n_orders, size=extra_count)
        assign_idx = np.concatenate([base_idx, extra_idx])
    else:
        assign_idx = base_idx

    payment_id = gen_ids("PAY", n, ID_WIDTH["payment"])
    assigned_order_id = order_ids[assign_idx]
    assigned_order_dt = order_dt[assign_idx]
    assigned_order_amount = order_amount_numeric[assign_idx]

    delay_minutes = rng.integers(0, 2 * 24 * 60, size=n)
    payment_dt = assigned_order_dt + pd.to_timedelta(delay_minutes, unit="m")
    payment_timestamp = payment_dt.strftime(TIMESTAMP_FMT)

    payment_method = rng.choice(methods, size=n)
    payment_status = rng.choice(statuses, size=n)
    failure_choice = rng.choice(failure_reasons, size=n)
    failure_reason = np.where(payment_status == "failed", failure_choice, "")
    payment_amount = np.asarray([f"{v:.2f}" for v in assigned_order_amount], dtype=object)

    df = pd.DataFrame({
        "payment_id": payment_id,
        "order_id": assigned_order_id.astype(object),
        "payment_timestamp": np.asarray(payment_timestamp, dtype=object),
        "payment_method": payment_method,
        "payment_status": payment_status,
        "payment_amount": payment_amount,
        "currency": np.full(n, currency, dtype=object),
        "failure_reason": failure_reason.astype(object),
    })
    helpers = {"order_dt_assigned": assigned_order_dt, "order_amount_assigned": assigned_order_amount}
    return df, helpers


# --------------------------------------------------------------------------
# Issue injection
# --------------------------------------------------------------------------

def apply_customer_issues(rng: np.random.Generator, df: pd.DataFrame, config: dict):
    rates = config["issue_rates"]["customers"]
    invalid = config["invalid_values"]
    n = len(df)
    issues = []

    def record(code, column, mask):
        issues.append({
            "code": code, "column": column,
            "configured_rate": rates[code], "affected_row_count": int(mask.sum()),
        })

    id_masks = exclusive_partition(rng, n, {
        "DUPLICATE_CUSTOMER_ID": rates["DUPLICATE_CUSTOMER_ID"],
        "NULL_OR_BLANK_CUSTOMER_ID": rates["NULL_OR_BLANK_CUSTOMER_ID"],
    })
    ids = duplicate_within(df["customer_id"].to_numpy(dtype=object), id_masks["DUPLICATE_CUSTOMER_ID"])
    ids = apply_null_or_blank(rng, ids, id_masks["NULL_OR_BLANK_CUSTOMER_ID"])
    df["customer_id"] = ids
    record("DUPLICATE_CUSTOMER_ID", "customer_id", id_masks["DUPLICATE_CUSTOMER_ID"])
    record("NULL_OR_BLANK_CUSTOMER_ID", "customer_id", id_masks["NULL_OR_BLANK_CUSTOMER_ID"])

    email_masks = exclusive_partition(rng, n, {
        "BLANK_EMAIL": rates["BLANK_EMAIL"],
        "MALFORMED_EMAIL": rates["MALFORMED_EMAIL"],
    })
    emails = df["email"].to_numpy(dtype=object)
    emails[email_masks["BLANK_EMAIL"]] = ""
    idx = np.flatnonzero(email_masks["MALFORMED_EMAIL"])
    for i in idx:
        emails[i] = str(emails[i]).replace("@", "_at_")
    df["email"] = emails
    record("BLANK_EMAIL", "email", email_masks["BLANK_EMAIL"])
    record("MALFORMED_EMAIL", "email", email_masks["MALFORMED_EMAIL"])

    province_mask = bernoulli_mask(rng, n, rates["INVALID_PROVINCE_CODE"])
    provinces = df["province"].to_numpy(dtype=object)
    idx = np.flatnonzero(province_mask)
    provinces[idx] = rng.choice(invalid["province"], size=len(idx))
    df["province"] = provinces
    record("INVALID_PROVINCE_CODE", "province", province_mask)

    status_mask = bernoulli_mask(rng, n, rates["INVALID_CUSTOMER_STATUS"])
    statuses = df["customer_status"].to_numpy(dtype=object)
    idx = np.flatnonzero(status_mask)
    statuses[idx] = rng.choice(invalid["customer_status"], size=len(idx))
    df["customer_status"] = statuses
    record("INVALID_CUSTOMER_STATUS", "customer_status", status_mask)

    as_of = pd.Timestamp(config["as_of_date"])
    date_masks = exclusive_partition(rng, n, {
        "INVALID_SIGNUP_DATE": rates["INVALID_SIGNUP_DATE"],
        "FUTURE_SIGNUP_DATE": rates["FUTURE_SIGNUP_DATE"],
    })
    dates = df["signup_date"].to_numpy(dtype=object)
    idx = np.flatnonzero(date_masks["INVALID_SIGNUP_DATE"])
    dates[idx] = rng.choice(invalid["date"], size=len(idx))
    idx = np.flatnonzero(date_masks["FUTURE_SIGNUP_DATE"])
    if len(idx) > 0:
        offsets = rng.integers(1, 365, size=len(idx))
        future_dates = (as_of + pd.to_timedelta(offsets, unit="D")).strftime(DATE_FMT)
        dates[idx] = np.asarray(future_dates, dtype=object)
    df["signup_date"] = dates
    record("INVALID_SIGNUP_DATE", "signup_date", date_masks["INVALID_SIGNUP_DATE"])
    record("FUTURE_SIGNUP_DATE", "signup_date", date_masks["FUTURE_SIGNUP_DATE"])

    name_masks = exclusive_partition(rng, n, {
        "WHITESPACE_PADDING": rates["WHITESPACE_PADDING"],
        "MIXED_CASING": rates["MIXED_CASING"],
    })
    names = df["full_name"].to_numpy(dtype=object)
    idx = np.flatnonzero(name_masks["WHITESPACE_PADDING"])
    for i in idx:
        names[i] = f"  {names[i]}  "
    idx = np.flatnonzero(name_masks["MIXED_CASING"])
    for i in idx:
        names[i] = str(names[i]).swapcase()
    df["full_name"] = names
    record("WHITESPACE_PADDING", "full_name", name_masks["WHITESPACE_PADDING"])
    record("MIXED_CASING", "full_name", name_masks["MIXED_CASING"])

    return df, issues


def apply_order_issues(rng: np.random.Generator, df: pd.DataFrame, config: dict):
    rates = config["issue_rates"]["orders"]
    invalid = config["invalid_values"]
    n = len(df)
    issues = []

    def record(code, column, mask):
        issues.append({
            "code": code, "column": column,
            "configured_rate": rates[code], "affected_row_count": int(mask.sum()),
        })

    id_masks = exclusive_partition(rng, n, {
        "DUPLICATE_ORDER_ID": rates["DUPLICATE_ORDER_ID"],
        "NULL_OR_BLANK_ORDER_ID": rates["NULL_OR_BLANK_ORDER_ID"],
    })
    ids = duplicate_within(df["order_id"].to_numpy(dtype=object), id_masks["DUPLICATE_ORDER_ID"])
    ids = apply_null_or_blank(rng, ids, id_masks["NULL_OR_BLANK_ORDER_ID"])
    df["order_id"] = ids
    record("DUPLICATE_ORDER_ID", "order_id", id_masks["DUPLICATE_ORDER_ID"])
    record("NULL_OR_BLANK_ORDER_ID", "order_id", id_masks["NULL_OR_BLANK_ORDER_ID"])

    fk_masks = exclusive_partition(rng, n, {
        "ORPHAN_CUSTOMER_ID": rates["ORPHAN_CUSTOMER_ID"],
        "MISSING_CUSTOMER_ID": rates["MISSING_CUSTOMER_ID"],
    })
    cust_ids = df["customer_id"].to_numpy(dtype=object)
    cust_ids[fk_masks["ORPHAN_CUSTOMER_ID"]] = ORPHAN_CUSTOMER_ID
    cust_ids = apply_null_or_blank(rng, cust_ids, fk_masks["MISSING_CUSTOMER_ID"])
    df["customer_id"] = cust_ids
    record("ORPHAN_CUSTOMER_ID", "customer_id", fk_masks["ORPHAN_CUSTOMER_ID"])
    record("MISSING_CUSTOMER_ID", "customer_id", fk_masks["MISSING_CUSTOMER_ID"])

    as_of = pd.Timestamp(config["as_of_date"])
    ts_masks = exclusive_partition(rng, n, {
        "INVALID_ORDER_TIMESTAMP": rates["INVALID_ORDER_TIMESTAMP"],
        "FUTURE_ORDER_TIMESTAMP": rates["FUTURE_ORDER_TIMESTAMP"],
    })
    timestamps = df["order_timestamp"].to_numpy(dtype=object)
    idx = np.flatnonzero(ts_masks["INVALID_ORDER_TIMESTAMP"])
    timestamps[idx] = rng.choice(invalid["timestamp"], size=len(idx))
    idx = np.flatnonzero(ts_masks["FUTURE_ORDER_TIMESTAMP"])
    if len(idx) > 0:
        offsets = rng.integers(1, 365 * 24 * 60, size=len(idx))
        future_ts = (as_of + pd.to_timedelta(offsets, unit="m")).strftime(TIMESTAMP_FMT)
        timestamps[idx] = np.asarray(future_ts, dtype=object)
    df["order_timestamp"] = timestamps
    record("INVALID_ORDER_TIMESTAMP", "order_timestamp", ts_masks["INVALID_ORDER_TIMESTAMP"])
    record("FUTURE_ORDER_TIMESTAMP", "order_timestamp", ts_masks["FUTURE_ORDER_TIMESTAMP"])

    amount_masks = exclusive_partition(rng, n, {
        "NONNUMERIC_ORDER_AMOUNT": rates["NONNUMERIC_ORDER_AMOUNT"],
        "NEGATIVE_ORDER_AMOUNT": rates["NEGATIVE_ORDER_AMOUNT"],
        "BLANK_ORDER_AMOUNT": rates["BLANK_ORDER_AMOUNT"],
    })
    amounts = df["order_amount"].to_numpy(dtype=object)
    idx = np.flatnonzero(amount_masks["NONNUMERIC_ORDER_AMOUNT"])
    amounts[idx] = rng.choice(invalid["order_amount"], size=len(idx))
    idx = np.flatnonzero(amount_masks["NEGATIVE_ORDER_AMOUNT"])
    if len(idx) > 0:
        neg_values = -np.round(rng.uniform(5, 500, size=len(idx)), 2)
        amounts[idx] = np.asarray([f"{v:.2f}" for v in neg_values], dtype=object)
    amounts[amount_masks["BLANK_ORDER_AMOUNT"]] = ""
    df["order_amount"] = amounts
    record("NONNUMERIC_ORDER_AMOUNT", "order_amount", amount_masks["NONNUMERIC_ORDER_AMOUNT"])
    record("NEGATIVE_ORDER_AMOUNT", "order_amount", amount_masks["NEGATIVE_ORDER_AMOUNT"])
    record("BLANK_ORDER_AMOUNT", "order_amount", amount_masks["BLANK_ORDER_AMOUNT"])

    status_mask = bernoulli_mask(rng, n, rates["INVALID_ORDER_STATUS"])
    statuses = df["order_status"].to_numpy(dtype=object)
    idx = np.flatnonzero(status_mask)
    statuses[idx] = rng.choice(invalid["order_status"], size=len(idx))
    df["order_status"] = statuses
    record("INVALID_ORDER_STATUS", "order_status", status_mask)

    channel_masks = exclusive_partition(rng, n, {
        "INVALID_SALES_CHANNEL": rates["INVALID_SALES_CHANNEL"],
        "WHITESPACE_PADDING": rates["WHITESPACE_PADDING"],
    })
    channels = df["sales_channel"].to_numpy(dtype=object)
    idx = np.flatnonzero(channel_masks["INVALID_SALES_CHANNEL"])
    channels[idx] = rng.choice(invalid["sales_channel"], size=len(idx))
    idx = np.flatnonzero(channel_masks["WHITESPACE_PADDING"])
    for i in idx:
        channels[i] = f"  {channels[i]}  "
    df["sales_channel"] = channels
    record("INVALID_SALES_CHANNEL", "sales_channel", channel_masks["INVALID_SALES_CHANNEL"])
    record("WHITESPACE_PADDING", "sales_channel", channel_masks["WHITESPACE_PADDING"])

    currency_mask = bernoulli_mask(rng, n, rates["INVALID_CURRENCY"])
    currencies = df["currency"].to_numpy(dtype=object)
    idx = np.flatnonzero(currency_mask)
    currencies[idx] = rng.choice(invalid["currency"], size=len(idx))
    df["currency"] = currencies
    record("INVALID_CURRENCY", "currency", currency_mask)

    return df, issues


def apply_payment_issues(rng: np.random.Generator, df: pd.DataFrame, config: dict, payment_helpers: dict):
    rates = config["issue_rates"]["payments"]
    invalid = config["invalid_values"]
    n = len(df)
    issues = []

    def record(code, column, mask):
        issues.append({
            "code": code, "column": column,
            "configured_rate": rates[code], "affected_row_count": int(mask.sum()),
        })

    id_masks = exclusive_partition(rng, n, {
        "DUPLICATE_PAYMENT_ID": rates["DUPLICATE_PAYMENT_ID"],
        "NULL_OR_BLANK_PAYMENT_ID": rates["NULL_OR_BLANK_PAYMENT_ID"],
    })
    ids = duplicate_within(df["payment_id"].to_numpy(dtype=object), id_masks["DUPLICATE_PAYMENT_ID"])
    ids = apply_null_or_blank(rng, ids, id_masks["NULL_OR_BLANK_PAYMENT_ID"])
    df["payment_id"] = ids
    record("DUPLICATE_PAYMENT_ID", "payment_id", id_masks["DUPLICATE_PAYMENT_ID"])
    record("NULL_OR_BLANK_PAYMENT_ID", "payment_id", id_masks["NULL_OR_BLANK_PAYMENT_ID"])

    fk_masks = exclusive_partition(rng, n, {
        "ORPHAN_ORDER_ID": rates["ORPHAN_ORDER_ID"],
        "MISSING_ORDER_ID": rates["MISSING_ORDER_ID"],
    })
    order_ids = df["order_id"].to_numpy(dtype=object)
    order_ids[fk_masks["ORPHAN_ORDER_ID"]] = ORPHAN_ORDER_ID
    order_ids = apply_null_or_blank(rng, order_ids, fk_masks["MISSING_ORDER_ID"])
    df["order_id"] = order_ids
    record("ORPHAN_ORDER_ID", "order_id", fk_masks["ORPHAN_ORDER_ID"])
    record("MISSING_ORDER_ID", "order_id", fk_masks["MISSING_ORDER_ID"])

    ts_masks = exclusive_partition(rng, n, {
        "INVALID_PAYMENT_TIMESTAMP": rates["INVALID_PAYMENT_TIMESTAMP"],
        "PAYMENT_BEFORE_ORDER": rates["PAYMENT_BEFORE_ORDER"],
    })
    timestamps = df["payment_timestamp"].to_numpy(dtype=object)
    idx = np.flatnonzero(ts_masks["INVALID_PAYMENT_TIMESTAMP"])
    timestamps[idx] = rng.choice(invalid["timestamp"], size=len(idx))
    idx = np.flatnonzero(ts_masks["PAYMENT_BEFORE_ORDER"])
    if len(idx) > 0:
        order_dts = payment_helpers["order_dt_assigned"][idx]
        offsets_hours = rng.integers(1, 48, size=len(idx))
        before_dts = order_dts - pd.to_timedelta(offsets_hours, unit="h")
        timestamps[idx] = np.asarray(before_dts.strftime(TIMESTAMP_FMT), dtype=object)
    df["payment_timestamp"] = timestamps
    record("INVALID_PAYMENT_TIMESTAMP", "payment_timestamp", ts_masks["INVALID_PAYMENT_TIMESTAMP"])
    record("PAYMENT_BEFORE_ORDER", "payment_timestamp", ts_masks["PAYMENT_BEFORE_ORDER"])

    amount_masks = exclusive_partition(rng, n, {
        "NONNUMERIC_PAYMENT_AMOUNT": rates["NONNUMERIC_PAYMENT_AMOUNT"],
        "NEGATIVE_PAYMENT_AMOUNT": rates["NEGATIVE_PAYMENT_AMOUNT"],
        "BLANK_PAYMENT_AMOUNT": rates["BLANK_PAYMENT_AMOUNT"],
        "AMOUNT_MISMATCH": rates["AMOUNT_MISMATCH"],
    })
    amounts = df["payment_amount"].to_numpy(dtype=object)
    idx = np.flatnonzero(amount_masks["NONNUMERIC_PAYMENT_AMOUNT"])
    amounts[idx] = rng.choice(invalid["payment_amount"], size=len(idx))
    idx = np.flatnonzero(amount_masks["NEGATIVE_PAYMENT_AMOUNT"])
    if len(idx) > 0:
        neg_values = -np.round(rng.uniform(5, 500, size=len(idx)), 2)
        amounts[idx] = np.asarray([f"{v:.2f}" for v in neg_values], dtype=object)
    amounts[amount_masks["BLANK_PAYMENT_AMOUNT"]] = ""
    idx = np.flatnonzero(amount_masks["AMOUNT_MISMATCH"])
    if len(idx) > 0:
        true_amounts = payment_helpers["order_amount_assigned"][idx]
        deltas = rng.uniform(5, 50, size=len(idx)) * rng.choice([-1.0, 1.0], size=len(idx))
        mismatched = np.round(np.abs(true_amounts + deltas), 2)
        amounts[idx] = np.asarray([f"{v:.2f}" for v in mismatched], dtype=object)
    df["payment_amount"] = amounts
    record("NONNUMERIC_PAYMENT_AMOUNT", "payment_amount", amount_masks["NONNUMERIC_PAYMENT_AMOUNT"])
    record("NEGATIVE_PAYMENT_AMOUNT", "payment_amount", amount_masks["NEGATIVE_PAYMENT_AMOUNT"])
    record("BLANK_PAYMENT_AMOUNT", "payment_amount", amount_masks["BLANK_PAYMENT_AMOUNT"])
    record("AMOUNT_MISMATCH", "payment_amount", amount_masks["AMOUNT_MISMATCH"])

    method_mask = bernoulli_mask(rng, n, rates["INVALID_PAYMENT_METHOD"])
    methods = df["payment_method"].to_numpy(dtype=object)
    idx = np.flatnonzero(method_mask)
    methods[idx] = rng.choice(invalid["payment_method"], size=len(idx))
    df["payment_method"] = methods
    record("INVALID_PAYMENT_METHOD", "payment_method", method_mask)

    # Reason-consistency issues are scoped to the eligible status subset (rate
    # is "share of failed/successful payments", not "share of all payments"),
    # and are applied before INVALID_PAYMENT_STATUS so eligibility reflects
    # the true generated status rather than an already-corrupted one.
    statuses_current = df["payment_status"].to_numpy(dtype=object)
    reasons = df["failure_reason"].to_numpy(dtype=object)
    failed_eligible = statuses_current == "failed"
    successful_eligible = statuses_current == "successful"
    failed_missing_mask = failed_eligible & bernoulli_mask(rng, n, rates["FAILED_MISSING_REASON"])
    reasons[failed_missing_mask] = ""
    successful_with_mask = successful_eligible & bernoulli_mask(rng, n, rates["SUCCESSFUL_WITH_REASON"])
    idx = np.flatnonzero(successful_with_mask)
    reasons[idx] = rng.choice(config["failure_reasons"], size=len(idx))
    df["failure_reason"] = reasons
    record("FAILED_MISSING_REASON", "failure_reason", failed_missing_mask)
    record("SUCCESSFUL_WITH_REASON", "failure_reason", successful_with_mask)

    status_mask = bernoulli_mask(rng, n, rates["INVALID_PAYMENT_STATUS"])
    statuses = df["payment_status"].to_numpy(dtype=object)
    idx = np.flatnonzero(status_mask)
    statuses[idx] = rng.choice(invalid["payment_status"], size=len(idx))
    df["payment_status"] = statuses
    record("INVALID_PAYMENT_STATUS", "payment_status", status_mask)

    currency_mask = bernoulli_mask(rng, n, rates["INVALID_CURRENCY"])
    currencies = df["currency"].to_numpy(dtype=object)
    idx = np.flatnonzero(currency_mask)
    currencies[idx] = rng.choice(invalid["currency"], size=len(idx))
    df["currency"] = currencies
    record("INVALID_CURRENCY", "currency", currency_mask)

    return df, issues


# --------------------------------------------------------------------------
# Parquet writing
# --------------------------------------------------------------------------

def write_dataset_parquet(df: pd.DataFrame, columns: list[str], dataset_dir: Path, dataset_name: str,
                           rows_per_file: int, compression: str) -> list[dict]:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    n = len(df)
    schema = pa.schema([(col, pa.string()) for col in columns])
    file_records = []
    file_index = 0
    for start in range(0, max(n, 1), rows_per_file):
        end = min(start + rows_per_file, n)
        if start >= n:
            break
        chunk = df.iloc[start:end]
        arrays = [pa.array(chunk[col].to_numpy(dtype=object), type=pa.string()) for col in columns]
        table = pa.Table.from_arrays(arrays, schema=schema)
        filename = f"part-{file_index:05d}.parquet"
        path = dataset_dir / filename
        pq.write_table(table, path, compression=compression)
        file_records.append({
            "path": f"{dataset_name}/{filename}",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "row_count": end - start,
        })
        file_index += 1
    return file_records


# --------------------------------------------------------------------------
# Profile orchestration
# --------------------------------------------------------------------------

def generate_profile(profile_name: str, config: dict, output_root: Path) -> dict:
    seed = config["seed"]
    rng = np.random.default_rng(seed)
    faker = Faker()
    faker.seed_instance(seed)

    profile_cfg = config["profiles"][profile_name]
    counts = profile_cfg["row_counts"]
    rows_per_file = profile_cfg["rows_per_file"]

    customers_df = generate_customers_base(rng, faker, config, counts["customers"])
    valid_customer_ids = customers_df["customer_id"].to_numpy(dtype=object).copy()

    orders_df, order_helpers = generate_orders_base(rng, config, counts["orders"], valid_customer_ids)
    payments_df, payment_helpers = generate_payments_base(rng, config, counts["payments"], orders_df, order_helpers)

    customers_df, customer_issues = apply_customer_issues(rng, customers_df, config)
    orders_df, order_issues = apply_order_issues(rng, orders_df, config)
    payments_df, payment_issues = apply_payment_issues(rng, payments_df, config, payment_helpers)

    profile_dir = output_root / profile_name
    datasets_meta = {}
    for name, df, columns in (
        ("customers", customers_df, CUSTOMER_COLUMNS),
        ("orders", orders_df, ORDER_COLUMNS),
        ("payments", payments_df, PAYMENT_COLUMNS),
    ):
        files = write_dataset_parquet(
            df, columns, profile_dir / name, name, rows_per_file[name], config["parquet"]["compression"],
        )
        datasets_meta[name] = {
            "row_count": len(df),
            "file_count": len(files),
            "columns": columns,
            "raw_types": {col: "string" for col in columns},
            "files": files,
        }

    manifest = {
        "profile": profile_name,
        "seed": seed,
        "as_of_date": config["as_of_date"],
        "compression": config["parquet"]["compression"],
        "datasets": datasets_meta,
        "issues": {
            "customers": customer_issues,
            "orders": order_issues,
            "payments": payment_issues,
        },
    }
    manifest_path = profile_dir / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")

    return manifest


def existing_outputs(output_root: Path, profile_names: list[str]) -> list[Path]:
    existing = []
    for profile in profile_names:
        profile_dir = output_root / profile
        if profile_dir.exists():
            existing.extend(p for p in sorted(profile_dir.rglob("*")) if p.is_file())
    return existing


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--overwrite", "--force", action="store_true", dest="overwrite",
                         help="Overwrite existing generated files (regenerates from scratch).")
    parser.add_argument("--profile", choices=["development", "portfolio", "all"], default="all",
                         help="Which profile(s) to generate (default: all).")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH, help="Path to data_generation.yml.")
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT, help="Directory to write profiles into.")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    profile_names = ["development", "portfolio"] if args.profile == "all" else [args.profile]

    existing = existing_outputs(args.output_root, profile_names)
    if existing and not args.overwrite:
        print("Refusing to overwrite existing generated files:", file=sys.stderr)
        for path in existing[:20]:
            print(f"  {path}", file=sys.stderr)
        if len(existing) > 20:
            print(f"  ... and {len(existing) - 20} more", file=sys.stderr)
        print("Re-run with --overwrite (or --force) to regenerate.", file=sys.stderr)
        return 1

    if args.overwrite:
        for profile_name in profile_names:
            profile_dir = args.output_root / profile_name
            if profile_dir.exists():
                shutil.rmtree(profile_dir)

    for profile_name in profile_names:
        generate_profile(profile_name, config, args.output_root)
        print(f"Generated {profile_name} profile at {args.output_root / profile_name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
