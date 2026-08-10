# Data Contracts

These contracts define the three MVP raw source datasets produced by
`scripts/generate_data.py` into `data/incoming/<profile>/<dataset>/`. This
data is generated, not manually edited — see
[docs/tickets/RF-001_define_mvp_data_model.md](tickets/RF-001_define_mvp_data_model.md).

## Raw source data, on purpose

**This data is intentionally dirty.** It models what a real retail source
system export typically looks like — not a clean, production-ready dataset.
A configured, deterministic (seed 42) fraction of rows in every dataset
carry realistic problems: duplicate or missing identifiers, invalid dates,
non-numeric or negative amounts, orphaned foreign keys, inconsistent casing,
and more. **The majority of rows in every dataset are valid** so that
useful analytics remain possible even before cleaning.

The generator does **not** clean, standardize, cast, repair, deduplicate,
reject, or quarantine anything — that is explicitly the job of the future
Silver layer, using `TRY_CAST` / `TRY_TO_*`-style logic. Bronze is expected
to preserve these raw values exactly as generated.

To make that possible, **every column in every raw Parquet file is stored
as a string (Arrow/Parquet `utf8`)** — including amounts, dates, and
timestamps — so that invalid values (`"BAD_AMOUNT"`, `"not-a-date"`, a
blank identifier, an unsupported status code) can be preserved rather than
rejected at write time. The table below documents both the **raw type**
(what's actually in the Parquet file today) and the **logical type** (what
Silver is expected to cast each column to).

## Profiles

| Profile       | Purpose                              | customers | orders    | payments  |
|---------------|----------------------------------------|-----------|-----------|-----------|
| `development` | Fast local iteration                    | 10,000    | 100,000   | 130,000   |
| `portfolio`   | Snowflake / cloud-scale demonstrations  | 100,000   | 1,000,000 | 1,300,000 |

Both profiles use the same seed (42) and the same issue rates; only volume
differs. Each profile is written as one or more Snappy-compressed Parquet
part files per dataset (`part-00000.parquet`, `part-00001.parquet`, ...) so
that multi-file ingestion (e.g. Snowflake `COPY INTO` over a stage) can be
practiced even in the `development` profile. A `manifest.json` alongside
each profile records row counts, file hashes, expected columns, raw types,
and every injected issue code with its configured rate and actual affected
row count.

## Conventions

- File format: Apache Parquet, Snappy compression, all columns `string`
- Encoding: UTF-8
- Valid dates: ISO-8601 (`YYYY-MM-DD`); valid timestamps: ISO-8601 with `T`
  separator, UTC (`YYYY-MM-DDTHH:MM:SSZ`) — invalid rows may not conform
- Valid monetary values: decimal string, two places, no currency symbol —
  invalid rows may not conform
- Valid currency: `CAD` — invalid rows may not conform

## `customers`

Grain: one row per customer. Primary key: `customer_id`.

| Column             | Raw type | Logical type (post-Silver) | Business meaning |
|---------------------|----------|-------------------------------|-------------------|
| `customer_id`       | string   | string, primary key           | Customer identifier, `CUST-######` when valid |
| `full_name`         | string   | string                         | Customer's display name |
| `email`             | string   | string                         | Contact email |
| `province`          | string   | string, one of the Canadian province/territory codes | Customer's province/territory |
| `signup_date`       | string   | date                           | Date the customer registered |
| `customer_status`   | string   | string, `active` or `inactive` | Whether the customer is currently active |

## `orders`

Grain: one row per order. Primary key: `order_id`. Foreign key: `customer_id` → `customers.customer_id`.

| Column            | Raw type | Logical type (post-Silver) | Business meaning |
|-------------------|----------|--------------------------------|-------------------|
| `order_id`        | string   | string, primary key            | Order identifier, `ORD-#######` when valid |
| `customer_id`     | string   | string, foreign key             | Purchasing customer |
| `order_timestamp` | string   | timestamp                       | When the order was placed |
| `order_status`    | string   | string, `pending`/`completed`/`cancelled` | Order lifecycle state |
| `sales_channel`   | string   | string, `online`/`mobile`/`store` | Channel the order was placed through |
| `order_amount`    | string   | decimal(10,2), >= 0             | Total order value |
| `currency`        | string   | string, `CAD`                   | Currency of `order_amount` |

## `payments`

Grain: one row per payment attempt. Primary key: `payment_id`. Foreign key: `order_id` → `orders.order_id`.

| Column              | Raw type | Logical type (post-Silver) | Business meaning |
|---------------------|----------|--------------------------------|-------------------|
| `payment_id`        | string   | string, primary key            | Payment attempt identifier, `PAY-#######` when valid |
| `order_id`          | string   | string, foreign key             | Order this attempt is for |
| `payment_timestamp` | string   | timestamp, >= order timestamp   | When the attempt occurred |
| `payment_method`    | string   | string, `credit_card`/`debit_card`/`digital_wallet`/`gift_card` | Method used |
| `payment_status`    | string   | string, `pending`/`successful`/`failed` | Outcome of the attempt |
| `payment_amount`    | string   | decimal(10,2), >= 0, reconciles with order amount | Amount attempted |
| `currency`          | string   | string, `CAD`                   | Currency of `payment_amount` |
| `failure_reason`    | string   | string, nullable                | Reason code; expected non-blank only when `payment_status = failed` |

## Domains (valid values)

**`customer_status`**: `active`, `inactive`

**`order_status`**: `pending`, `completed`, `cancelled`

**`sales_channel`**: `online`, `mobile`, `store`

**`payment_method`**: `credit_card`, `debit_card`, `digital_wallet`, `gift_card`

**`payment_status`**: `pending`, `successful`, `failed`

**`currency`**: `CAD`

**Canadian province/territory codes**: `AB`, `BC`, `MB`, `NB`, `NL`, `NS`,
`NT`, `NU`, `ON`, `PE`, `QC`, `SK`, `YT`

## Relationships

- One `customers` row can relate to many `orders` rows — when the FK is
  valid; some rows deliberately violate this (see below).
- One `orders` row can relate to many `payments` rows (multiple payment
  attempts per order) — when the FK is valid.

## Injected data-quality issues

Issue rates are configured in `config/data_generation.yml` under
`issue_rates` (generally 0.1%–2% per issue, deterministic for seed 42).
Issues that target the same column are mutually exclusive, so a given row
is affected by at most one issue per column. Actual affected-row counts are
recorded per run in each profile's `manifest.json`, alongside each issue's
configured rate — exact counts follow from the seed and row count, not a
fixed number.

### `customers` (10 issue codes)

| Code | Column | Description |
|------|--------|--------------|
| `DUPLICATE_CUSTOMER_ID` | `customer_id` | Row's ID is overwritten to match another existing row's ID |
| `NULL_OR_BLANK_CUSTOMER_ID` | `customer_id` | ID is null or an empty string |
| `BLANK_EMAIL` | `email` | Empty string |
| `MALFORMED_EMAIL` | `email` | `@` replaced, producing an unparseable address |
| `INVALID_PROVINCE_CODE` | `province` | Value outside the valid province/territory domain |
| `INVALID_CUSTOMER_STATUS` | `customer_status` | Value outside the valid status domain |
| `INVALID_SIGNUP_DATE` | `signup_date` | Malformed / non-ISO-8601 date string |
| `FUTURE_SIGNUP_DATE` | `signup_date` | Well-formed date after `as_of_date` |
| `WHITESPACE_PADDING` | `full_name` | Leading/trailing whitespace added |
| `MIXED_CASING` | `full_name` | Casing swapped (e.g. `jOHN sMITH`) |

### `orders` (13 issue codes)

| Code | Column | Description |
|------|--------|--------------|
| `DUPLICATE_ORDER_ID` | `order_id` | Row's ID overwritten to match another existing row's ID |
| `NULL_OR_BLANK_ORDER_ID` | `order_id` | ID is null or an empty string |
| `ORPHAN_CUSTOMER_ID` | `customer_id` | Set to the sentinel `CUST-ORPHAN`, which never exists in `customers` |
| `MISSING_CUSTOMER_ID` | `customer_id` | Null or an empty string |
| `INVALID_ORDER_TIMESTAMP` | `order_timestamp` | Malformed / non-ISO-8601 timestamp string |
| `FUTURE_ORDER_TIMESTAMP` | `order_timestamp` | Well-formed timestamp after `as_of_date` |
| `NONNUMERIC_ORDER_AMOUNT` | `order_amount` | Non-numeric string (e.g. `BAD_AMOUNT`, `N/A`) |
| `NEGATIVE_ORDER_AMOUNT` | `order_amount` | Numeric but negative |
| `BLANK_ORDER_AMOUNT` | `order_amount` | Empty string |
| `INVALID_ORDER_STATUS` | `order_status` | Value outside the valid status domain |
| `INVALID_SALES_CHANNEL` | `sales_channel` | Value outside the valid channel domain |
| `WHITESPACE_PADDING` | `sales_channel` | Leading/trailing whitespace added |
| `INVALID_CURRENCY` | `currency` | Value other than `CAD` |

### `payments` (15 issue codes)

| Code | Column | Description |
|------|--------|--------------|
| `DUPLICATE_PAYMENT_ID` | `payment_id` | Row's ID overwritten to match another existing row's ID |
| `NULL_OR_BLANK_PAYMENT_ID` | `payment_id` | ID is null or an empty string |
| `ORPHAN_ORDER_ID` | `order_id` | Set to the sentinel `ORD-ORPHAN`, which never exists in `orders` |
| `MISSING_ORDER_ID` | `order_id` | Null or an empty string |
| `INVALID_PAYMENT_TIMESTAMP` | `payment_timestamp` | Malformed / non-ISO-8601 timestamp string |
| `PAYMENT_BEFORE_ORDER` | `payment_timestamp` | Well-formed timestamp that precedes the linked order's timestamp |
| `NONNUMERIC_PAYMENT_AMOUNT` | `payment_amount` | Non-numeric string |
| `NEGATIVE_PAYMENT_AMOUNT` | `payment_amount` | Numeric but negative |
| `BLANK_PAYMENT_AMOUNT` | `payment_amount` | Empty string |
| `AMOUNT_MISMATCH` | `payment_amount` | Numeric and positive, but does not reconcile with the linked order's amount |
| `INVALID_PAYMENT_METHOD` | `payment_method` | Value outside the valid method domain |
| `INVALID_PAYMENT_STATUS` | `payment_status` | Value outside the valid status domain |
| `INVALID_CURRENCY` | `currency` | Value other than `CAD` |
| `FAILED_MISSING_REASON` | `failure_reason` | `payment_status = failed` but `failure_reason` is blank (rate applies within failed payments) |
| `SUCCESSFUL_WITH_REASON` | `failure_reason` | `payment_status = successful` but `failure_reason` is populated (rate applies within successful payments) |

## Manifest structure

Each profile's `manifest.json` includes: profile name, seed, as-of date,
Parquet compression, and per dataset — row count, part-file count, relative
file paths with SHA-256 hashes, expected column order, and raw types — plus
per dataset the full list of injected issues with code, target column,
configured rate, and actual affected row count. It does not include a
generation timestamp (regenerating with the same seed reproduces identical
files and hashes).
