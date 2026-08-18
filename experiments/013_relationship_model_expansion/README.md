# Experiment 013: Relationship Model Expansion

**Status:** Planned  
**Experiment Type:** Relationship / Structural  
**FORGE Area:** Relationship Generation  
**Objective:** Determine whether a generic relationship model can represent and generate multiple relationship topologies while maintaining referential integrity.

---

## 1. Research Question

Can a generic synthetic data generator represent different entity relationship topologies such as `1:1`, `1:N`, `N:1`, `N:M`, optional relationships, and multiple foreign keys without introducing relationship-specific generation logic?

The experiment will determine whether relationships can be represented as metadata and then interpreted by the generator to create structurally valid related datasets.

---

## 2. Hypothesis

A generic relationship model should be able to represent multiple relationship topologies independently of the individual entity definitions.

The generator should be able to:

- Generate parent entities before dependent entities where required.
- Maintain referential integrity.
- Support one-to-one relationships.
- Support one-to-many relationships.
- Support many-to-one relationships.
- Support many-to-many relationships through an associative entity.
- Support optional relationships.
- Support multiple foreign keys between the same or different entities.
- Validate each relationship independently.

The hypothesis will be considered supported if all declared relationship types can be generated and validated using the same generic relationship model.

The hypothesis will be rejected if relationship types require fundamentally different relationship representations or if relationship-specific generation logic must be embedded into individual entities.

---

## 3. Scope

This experiment will expand the relationship model established in Experiments 004, 005, and 006.

The experiment will use a small set of domain-neutral entities to demonstrate different relationship topologies.

### Included

- `1:1` relationships
- `1:N` relationships
- `N:1` relationships
- `N:M` relationships
- Optional relationships
- Multiple foreign keys
- Associative entities
- Referential integrity validation
- Relationship-level validation
- Relationship metadata
- Deterministic generation
- Generated relationship statistics

### Excluded

- Composite keys
- Parent-dependent distributions
- Conditional relationships
- Cross-field constraints
- Statistical correlation between related entities
- Real production data
- Machine Learning
- Deep Learning
- Large Language Models
- Domain-specific SAP, ERP, PLM or MES logic
- Complex temporal relationships

These capabilities may be explored in later experiments.

---

## 4. Initial Dataset / Entity

The experiment will use several generic entities so that different relationship topologies can be demonstrated without introducing domain-specific behavior.

### Entities

`CUSTOMER`

`PROFILE`

`PRODUCT`

`ORDER`

`ORDER_ITEM`

`SHIPMENT`

### Fields

| Entity | Field | Type | Semantic / Behavior |
|---|---|---|---|
| CUSTOMER | CUSTOMER_ID | identifier | Unique customer identity |
| PROFILE | PROFILE_ID | identifier | Unique profile identity |
| PROFILE | CUSTOMER_ID | identifier | Reference to CUSTOMER |
| PRODUCT | PRODUCT_ID | identifier | Unique product identity |
| ORDER | ORDER_ID | identifier | Unique order identity |
| ORDER | CUSTOMER_ID | identifier | Reference to CUSTOMER |
| ORDER | BILL_TO_CUSTOMER_ID | identifier | Optional customer reference |
| ORDER_ITEM | ORDER_ITEM_ID | identifier | Unique order item identity |
| ORDER_ITEM | ORDER_ID | identifier | Reference to ORDER |
| ORDER_ITEM | PRODUCT_ID | identifier | Reference to PRODUCT |
| SHIPMENT | SHIPMENT_ID | identifier | Unique shipment identity |
| SHIPMENT | ORDER_ID | identifier | Reference to ORDER |

The entities are intentionally generic.

---

## 5. Relationship Model

The experiment will represent relationships separately from entity definitions.

Example:

```json
{
  "parent_entity": "CUSTOMER",
  "parent_field": "CUSTOMER_ID",
  "child_entity": "ORDER",
  "child_field": "CUSTOMER_ID",
  "cardinality": "1:N"
}
````

The relationship itself should describe:

* Parent entity
* Parent field
* Child entity
* Child field
* Cardinality
* Optionality where applicable

The entity generator should not need to know whether a field is a foreign key until relationship generation is applied.

---

## 6. Relationship Topologies

The experiment will test the following relationship types.

### 6.1 One-to-One

Example:

```text
CUSTOMER
    1
    │
    │
    1
PROFILE
```

Each customer should have at most one profile.

Each profile should belong to exactly one customer.

Expected behavior:

```text
CUSTOMER.CUSTOMER_ID
        ↓
PROFILE.CUSTOMER_ID
```

The generator must prevent multiple profiles from being assigned to the same customer.

---

### 6.2 One-to-Many

Example:

```text
CUSTOMER
    1
    │
    │
    N
ORDER
```

A customer may have multiple orders.

Each order must reference one valid customer.

This extends the relationship model already established in Experiment 004.

---

### 6.3 Many-to-One

Many child records reference a smaller set of parent records.

Example:

```text
ORDER_ITEM
    N
    │
    │
    1
ORDER
```

Multiple order items may belong to the same order.

This is structurally equivalent to the child perspective of a `1:N` relationship, but the experiment will explicitly verify that the relationship model can represent the direction without requiring a separate relationship implementation.

---

### 6.4 Many-to-Many

A direct foreign key is insufficient for a many-to-many relationship.

The experiment will therefore use an associative entity.

Example:

```text
ORDER
   1
   │
   N
ORDER_ITEM
   N
   │
   1
PRODUCT
```

This allows:

```text
ORDER A → PRODUCT 1
ORDER A → PRODUCT 2
ORDER B → PRODUCT 1
ORDER B → PRODUCT 3
```

The relationship model should therefore be able to represent the two relationships independently:

```text
ORDER
    ↓
ORDER_ITEM
    ↓
PRODUCT
```

The experiment will determine whether this is sufficient to represent the many-to-many topology generically.

---

### 6.5 Optional Relationship

Some orders may have a secondary customer reference.

Example:

```text
ORDER.BILL_TO_CUSTOMER_ID
```

The field may contain:

```text
valid CUSTOMER_ID
```

or:

```text
NULL
```

The relationship metadata should identify the relationship as optional.

The generator should produce both valid references and permitted null references without producing invalid non-null references.

---

### 6.6 Multiple Foreign Keys

An entity may reference the same parent entity through more than one field.

Example:

```text
ORDER
 ├── CUSTOMER_ID
 └── BILL_TO_CUSTOMER_ID
          │
          ▼
       CUSTOMER
```

The two relationships should be independently represented.

The generator should not assume that an entity can have only one relationship to another entity.

---

## 7. Experiment Configuration

Relationship metadata will be defined separately from entity metadata.

Example:

```json
{
  "relationships": [
    {
      "id": "R001",
      "parent_entity": "CUSTOMER",
      "parent_field": "CUSTOMER_ID",
      "child_entity": "PROFILE",
      "child_field": "CUSTOMER_ID",
      "cardinality": "1:1",
      "optional": false
    },
    {
      "id": "R002",
      "parent_entity": "CUSTOMER",
      "parent_field": "CUSTOMER_ID",
      "child_entity": "ORDER",
      "child_field": "CUSTOMER_ID",
      "cardinality": "1:N",
      "optional": false
    }
  ]
}
```

The relationship definition should remain independent of the field's generation strategy.

Conceptually:

```text
Entity Definition
       │
       └── Fields

Relationship Definition
       │
       ├── Parent
       ├── Child
       ├── Cardinality
       └── Optionality
```

---