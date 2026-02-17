![Draft for review only](/assets/img/draft_for_review.svg)

# Manifestation

![Manifestation Diagram](diagrams/Manifestation.dot.svg)

<a href="diagrams/Manifestation.dot.svg">Open interactive Manifestation diagram</a>

## Specializations of Manifestation

| Class | Description |
|-------|-------------|
| [First Manifestation](FirstManifestation.md) |  |
| [Planned Allocation](PlannedAllocation.md) |  |

## Formalization for Manifestation

| Property | Constraint |
|----------|------------|
| existsAt | exactly 1 owl:Thing |
| hasFirstManifestation | exactly 1 owl:Thing |
| hasNextManifestation | max 1 owl:Thing |
| inverse hasNextManifestation | max 1 owl:Thing |
| subClassOf | ChangeThing |

## Used by classes

| Class | Property |
|-------|----------|
| [Manifestation State](ManifestationState.md) | satisfiedBy |

