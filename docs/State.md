![Draft for review only](/assets/img/draft_for_review.svg)

# State

![State Diagram](diagrams/State.dot.svg)

<a href="diagrams/State.dot.svg">Open interactive State diagram</a>

## Specializations of State

| Class | Description |
|-------|-------------|
| [Conjunctive State](ConjunctiveState.md) |  |
| [Consume State](ConsumeState.md) |  |
| [Disjunctive State](DisjunctiveState.md) |  |
| [Manifestation State](ManifestationState.md) |  |
| [Non Terminal State](NonTerminalState.md) |  |
| [Produce State](ProduceState.md) |  |
| [Release State](ReleaseState.md) |  |
| [Terminal Resource State](TerminalResourceState.md) |  |
| [Terminal State](TerminalState.md) |  |
| [Use State](UseState.md) |  |

## Formalization for State

| Property | Constraint |
|----------|------------|
| achievedAt | all time:TemporalEntity |
| enablesActivity | all Activity |
| hasStatus | exactly 1 owl:Thing |
| inverse causesState | all Activity |
| inverse hasEffect | all Activity |
| preconditionOf | all Activity |
| scheduledFor | max 1 owl:Thing |
| subClassOf | ActivityThing |

## Used by classes

| Class | Property |
|-------|----------|
| [Activity](Activity.md) | hasPrecondition |
| [Activity](Activity.md) | enabledByState |
| [Activity](Activity.md) | hasEffect |
| [Activity](Activity.md) | causesState |
| [Non Terminal State](NonTerminalState.md) | hasSubstate |
| [Recurring Event](RecurringEvent.md) | beginsRecurringState |
| [Recurring Event](RecurringEvent.md) | endsRecurringState |

