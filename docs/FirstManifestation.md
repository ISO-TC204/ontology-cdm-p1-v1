![Draft for review only](/assets/img/draft_for_review.svg)

# FirstManifestation

![FirstManifestation Diagram](diagrams/FirstManifestation.dot.svg)

<a href="diagrams/FirstManifestation.dot.svg">Open interactive FirstManifestation diagram</a>

## Formalization for FirstManifestation

| Property | Constraint |
|----------|------------|
| hasLatestManifestation | exactly 1 owl:Thing |
| precedesManifestation | all Manifestation and not FirstManifestation |
| subClassOf | Manifestation |

