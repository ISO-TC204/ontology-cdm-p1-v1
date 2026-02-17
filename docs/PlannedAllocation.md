![Draft for review only](/assets/img/draft_for_review.svg)

# PlannedAllocation

![PlannedAllocation Diagram](diagrams/PlannedAllocation.dot.svg)

<a href="diagrams/PlannedAllocation.dot.svg">Open interactive PlannedAllocation diagram</a>

## Formalization for PlannedAllocation

| Property | Constraint |
|----------|------------|
| forResource | exactly 1 owl:Thing |
| hasQuantity | exactly 1 owl:Thing |
| inverse hasAllocation | exactly 1 owl:Thing |
| subClassOf | Manifestation |
| subClassOf | ResourceThing |
| time:hasTime | exactly 1 owl:Thing |

## Used by classes

| Class | Property |
|-------|----------|
| [Resource](Resource.md) | hasAllocation |
| [Terminal Resource State](TerminalResourceState.md) | hasAllocation |

