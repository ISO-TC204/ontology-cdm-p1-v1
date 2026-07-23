# Information technology - City data model - Part 1: Foundation level concepts - Recurring Event Pattern

This ontology specifies the foundation-level concepts related to the recurring event pattern of the city data model.

This pattern imports the following files:

- [https://w3id.org/citydata/part1/v1/ActivityPattern](https://w3id.org/citydata/part1/v1/ActivityPattern)
- [https://w3id.org/citydata/part1/v1/GenericPropertiesPattern](https://w3id.org/citydata/part1/v1/GenericPropertiesPattern)

This pattern consists of the following classes:

- [Daily Recurring Event](DailyRecurringEvent.md)
- [Exception Day](ExceptionDay.md)
- [Monthly Recurring Event](MonthlyRecurringEvent.md)
- [Recurring Event](RecurringEvent.md)
- [Recurring Event Thing](RecurringEventThing.md)
- [Weekly Recurring Event](WeeklyRecurringEvent.md)
- [Yearly Recurring Event](YearlyRecurringEvent.md)
This module defines the following properties:

- [beginsRecurringState](../properties/beginsRecurringState.md)
- [beginsRecurringTime](../properties/beginsRecurringTime.md)
- [endDayOfWeek](../properties/endDayOfWeek.md)
- [endMonth](../properties/endMonth.md)
- [endsRecurringState](../properties/endsRecurringState.md)
- [endsRecurringTime](../properties/endsRecurringTime.md)
- [endTime](../properties/endTime.md)
- [hasDayOfWeek](../properties/hasDayOfWeek.md)
- [hasMonth](../properties/hasMonth.md)
- [hasOccurrence](../properties/hasOccurrence.md)
- [hasSubRecurringEvent](../properties/hasSubRecurringEvent.md)
- [onDateTimeDescription](../properties/onDateTimeDescription.md)
- [RecurringEventDataProperty](../properties/RecurringEventDataProperty.md)
- [RecurringEventObjectProperty](../properties/RecurringEventObjectProperty.md)
- [recursAddition](../properties/recursAddition.md)
- [recursExcept](../properties/recursExcept.md)
- [startTime](../properties/startTime.md)


The formal definition of this pattern is available in TURTLE Syntax in two files, the [core semantics](../RecurringEventPattern.ttl) and the SHACL [restrictions](../RecurringEventSHACL.ttl).
