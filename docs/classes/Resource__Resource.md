# Resource

![Resource Diagram](../diagrams/Resource__Resource.dot.svg)

<a href="../../diagrams/Resource__Resource.dot.svg">Open interactive Resource diagram</a>

## Specializations of Resource

| Class | Description |
|-------|-------------|
| [Divisible Resource (Resource)](Resource__DivisibleResource.md) |  |
| [Non Divisible Resource (Resource)](Resource__NonDivisibleResource.md) |  |

## Formalization for Resource

| Property | Constraint |
|----------|------------|
| capacityInUse | exactly 1 owl::Thing |
| hasAllocation | all PlannedAllocation |
| hasAvailableCapacity | exactly 1 owl::Thing |
| hasCapacity | exactly 1 owl::Thing |
| participatesIn | min 1 owl::Thing |
| spatialLoc::asLocation | all spatialLoc::ocation |
| subClassOf | ResourceOntologyThing |

## Used by classes

| Class | Property |
|-------|----------|
| [Terminal Resource State (Resource)](Resource__TerminalResourceState.md) | hasResource |

