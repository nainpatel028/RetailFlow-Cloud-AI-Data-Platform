# Business Requirements

## Business context

RetailFlow is a fictional mid-size Canadian retailer selling through online,
mobile, and in-store channels. Leadership needs regular, trustworthy answers
to a small set of operational questions, currently unavailable without
manual data pulls.

## Business questions

1. **What is our daily revenue?** — sum of order amounts by day, likely
   scoped to completed orders.
2. **How many orders are completed vs. cancelled?** — order counts by
   `order_status`, over time and by channel.
3. **What is our payment-failure rate, and why?** — share of payment
   attempts with `payment_status = failed`, broken down by `failure_reason`.
4. **Who are our highest-value customers?** — customers ranked by total
   completed order value.
5. **How reliable is our incoming data?** — count and rate of data-quality
   issues found in each ingestion run (missing fields, invalid domains,
   orphaned foreign keys, out-of-order timestamps).

These questions drive the Gold-layer aggregates (planned) and the Power BI
dashboard scope (see [power_bi_scope.md](power_bi_scope.md)).

## Data model

Three entities, related as follows:

```
customers (1) ───< orders (1) ───< payments
```

- One **customer** can have many **orders**.
- One **order** can have many **payment attempts** (e.g., a failed attempt
  followed by a successful retry).

### `customers`

- **Grain:** one row per customer
- **Primary key:** `customer_id`

### `orders`

- **Grain:** one row per order
- **Primary key:** `order_id`
- **Foreign key:** `customer_id` → `customers.customer_id`

### `payments`

- **Grain:** one row per payment attempt
- **Primary key:** `payment_id`
- **Foreign key:** `order_id` → `orders.order_id`

Full column-level definitions, types, and allowed values are in
[data_contracts.md](data_contracts.md).

## Non-goals

See [PROJECT_SCOPE.md](../PROJECT_SCOPE.md) for what this project explicitly
excludes (real data, production deployment, autonomous agent writes,
streaming, enterprise SLAs).
