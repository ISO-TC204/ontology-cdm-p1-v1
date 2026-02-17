![Draft for review only](/assets/img/draft_for_review.svg)

# AtomicAgreement

![AtomicAgreement Diagram](diagrams/AtomicAgreement.dot.svg)

<a href="diagrams/AtomicAgreement.dot.svg">Open interactive AtomicAgreement diagram</a>

## Formalization for AtomicAgreement

| Property | Constraint |
|----------|------------|
| commitsToActivity | some Activity |
| disjointWith | ComplexAgreement |
| inverse hasClaim | all Agent |
| inverse hasDuty | all Agent |
| inverse hasNoClaim | all Agent |
| inverse hasPrivilege | all Agent |
| subClassOf | Agreement |

## Used by classes

| Class | Property |
|-------|----------|
| [Agent (SpatialLocPattern)](Agent.md) | hasClaim |
| [Agent (SpatialLocPattern)](Agent.md) | hasDuty |
| [Agent (SpatialLocPattern)](Agent.md) | hasNoClaim |
| [Agent (SpatialLocPattern)](Agent.md) | hasPrivilege |

