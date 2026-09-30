# FORGE Specification Testing & Stress Testing

Experiment 026

## Objective

Systematically test FORGE against increasingly complex and increasingly
large specifications.

## Testing Dimensions

- Specification complexity
- Planning behavior
- Generation correctness
- Relationship and foreign-key correctness
- Constraint enforcement
- Semantic generation
- Memory utilization
- Generation throughput
- Artifact generation
- Checkpoint and restart behavior
- Scalability limits

## Baseline

The current production specification is the reference model.

Baseline characteristics:

- 21 entities
- 26 relationships
- 30 foreign keys
- 6 constraints

## Stress Strategy

Stress specifications should preserve the semantic structure of the
production model unless a specific experiment intentionally changes it.

Initial progression:

1. Baseline production specification
2. Stress V1-B: approximately 3M rows
3. Stress V1-C: approximately 5M rows
4. Stress V1-D: approximately 9M rows

## Evidence

Each benchmark should persist:

- Exact specification used
- Benchmark configuration
- Execution metrics
- Per-entity measurements
- Success/failure status
- Errors, when applicable

Results must be reproducible from the saved specification and benchmark
configuration.
