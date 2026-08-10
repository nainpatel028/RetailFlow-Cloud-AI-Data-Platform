# RF-001 — Define MVP Data Model

**Status:** In Review

## Business problem

RetailFlow leadership cannot answer basic operational questions (daily
revenue, order completion/cancellation, payment-failure rate, top
customers, incoming-data reliability) without manual data pulls. Before any
pipeline is built, the data model those questions depend on must be
explicitly defined and agreed.

## Scope

Define the three-table MVP model: `customers`, `orders`, `payments`.

### Grains

- `customers` — one row per customer
- `orders` — one row per order
- `payments` — one row per payment *attempt* (not per order — an order may
  have multiple payment attempts)

### Keys

- `customers.customer_id` — primary key
- `orders.order_id` — primary key; `orders.customer_id` — foreign key to
  `customers.customer_id`
- `payments.payment_id` — primary key; `payments.order_id` — foreign key to
  `orders.order_id`

### Relationships

- One `customers` row → many `orders` rows
- One `orders` row → many `payments` rows

Full column-level contract: [docs/data_contracts.md](../data_contracts.md).
Business questions this model must support:
[docs/business_requirements.md](../business_requirements.md).

These keys and relationships describe the **intended** model. The raw
source data is deliberately dirty (see
[docs/data_contracts.md](../data_contracts.md)) and contains a small,
documented rate of rows that violate them on purpose — duplicate or missing
primary keys, orphaned foreign keys. Enforcing these constraints is the
Silver layer's job, not the generator's.

## Acceptance criteria

- [ ] `docs/business_requirements.md` documents the business problem, the
      five business questions, and the data model summary
- [ ] `docs/data_contracts.md` documents all three tables' columns, types,
      nullability, domains, and keys, consistent with this ticket
- [ ] Grains and relationships above are reflected identically in both
      documents (no contradictions)
- [ ] The relationship is explicitly one-to-many in both directions
      (`customers` → `orders`, `orders` → `payments`), with payments
      allowing multiple rows per order
- [ ] No table, column, or domain value is introduced elsewhere in the repo
      (generator, tests, config) that isn't defined here first

## Out of scope for this ticket

Implementation of ingestion, storage, or transformation — see RF-002 and
later tickets.
