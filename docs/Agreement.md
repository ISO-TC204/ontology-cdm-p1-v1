![Draft for review only](/assets/img/draft_for_review.svg)

# Agreement

![Agreement Diagram](diagrams/Agreement.dot.svg)

<a href="diagrams/Agreement.dot.svg">Open interactive Agreement diagram</a>

## Specializations of Agreement

| Class | Description |
|-------|-------------|
| [Conjunctive Agreement](ConjunctiveAgreement.md) |  |
| [Disjunctive Agreement](DisjunctiveAgreement.md) |  |

## Formalization for Agreement

| Property | Constraint |
|----------|------------|
| establishedOn | all time:Instant |
| involvesAgent | min 2 owl:Thing |
| subClassOf | AgreementThing |
| validFor | all time:Interval |
| validIn | all Location |

