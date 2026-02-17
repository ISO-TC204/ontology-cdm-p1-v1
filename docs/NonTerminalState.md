![Draft for review only](/assets/img/draft_for_review.svg)

# NonTerminalState

![NonTerminalState Diagram](diagrams/NonTerminalState.dot.svg)

<a href="diagrams/NonTerminalState.dot.svg">Open interactive NonTerminalState diagram</a>

## Specializations of NonTerminalState

| Class | Description |
|-------|-------------|
| [Conjunctive State](ConjunctiveState.md) |  |
| [Disjunctive State](DisjunctiveState.md) |  |

## Formalization for NonTerminalState

| Property | Constraint |
|----------|------------|
| disjointWith | TerminalState |
| hasDecomp | min 2 owl:Thing |
| hasSubstate | all State |
| subClassOf | State |

