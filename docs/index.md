# ontology-cdm-p1

## Activity Ontology

Ontology to capture concepts related to activities.

This ontology consists of the following patterns:


The ontology also contains the following classes that are not assigned to any pattern:

- [Activity (Activity)](classes/Activity__Activity.md)
- [Activity Ontology Thing (Activity)](classes/Activity__ActivityOntologyThing.md)
- [Activity Status (Activity)](classes/Activity__ActivityStatus.md)
- [Conjunctive State (Activity)](classes/Activity__ConjunctiveState.md)
- [Disjunctive State (Activity)](classes/Activity__DisjunctiveState.md)
- [Manifestation State (Activity)](classes/Activity__ManifestationState.md)
- [Non Terminal State (Activity)](classes/Activity__NonTerminalState.md)
- [State (Activity)](classes/Activity__State.md)
- [State Status (Activity)](classes/Activity__StateStatus.md)
- [Terminal State (Activity)](classes/Activity__TerminalState.md)

The formal definition of these patterns is available in [OWL Syntax](Activity.owl).

## Agent Pattern

An Agent is defined in the context of an Activity that it affects or is affected by, or their role within an Organization.  An Agent can be a Person, Organization, Software or Mechanical device.

This ontology consists of the following patterns:


The ontology also contains the following classes that are not assigned to any pattern:

- [Agent (Agent)](classes/Agent__Agent.md)
- [Agent Ontology Thing (Agent)](classes/Agent__AgentOntologyThing.md)

The formal definition of these patterns is available in [OWL Syntax](Agent.owl).

## Agreement Pattern

An agreement exists between 2 or more agents. It is established at some point in time and it may be considered valid only in some Location and/or for some interval in time. An agreement may be defined at varying levels of detail, this is supported with the introduction of the ComplexAgreement and AtomicAgreement class. A complex agreement may be decomposed into sub-agreements, whereas an atomic agreement cannot. Similar to the approach taken for the representation of activities, a complex agreement may be decomposed into disjunctive or conjunctive sub-agreements. This allows for the representation of both types of agreement composition. At their most simple level, the AtomicAgreement describes a commitment to some activity; this is captured with the commitsToActivity property.  Finally, agreements involve some specification of rights or commitments of the involved parties. This is represented as a relationship between the involved Agent and a particular activity. The precise nature of the relationship indicates the type of agreement. The possible relationships are defined according to the elements of the primary rules of the Hohfeldian analytical system, (and their opposites): claim and privilege.

This ontology consists of the following patterns:


The ontology also contains the following classes that are not assigned to any pattern:

- [Agent (Agreement)](classes/Agreement__Agent.md)
- [Agreement (Agreement)](classes/Agreement__Agreement.md)
- [Agreement Ontology Thing (Agreement)](classes/Agreement__AgreementOntologyThing.md)
- [Atomic Agreement](classes/Agreement__Atomic Agreement.md)
- [Complex Agreement](classes/Agreement__Complex Agreement.md)
- [Conjunctive Agreement (Agreement)](classes/Agreement__ConjunctiveAgreement.md)
- [Disjunctive Agreement (Agreement)](classes/Agreement__DisjunctiveAgreement.md)

The formal definition of these patterns is available in [OWL Syntax](Agreement.owl).

## City Units of Measure

Annotation property introduced for organization purposes, to identify annotation properties defined in the Units of Measure Ontology.

This ontology consists of the following patterns:


The ontology also contains the following classes that are not assigned to any pattern:

- [acceleration](classes/CityUnits__acceleration.md)
- [acceleration unit](classes/CityUnits__acceleration unit.md)
- [amount of money](classes/CityUnits__amount of money.md)
- [area](classes/CityUnits__area.md)
- [area unit](classes/CityUnits__area unit.md)
- [Capacity (CityUnits)](classes/CityUnits__Capacity.md)
- [Capacity Rate (CityUnits)](classes/CityUnits__CapacityRate.md)
- [Capacity Size (CityUnits)](classes/CityUnits__CapacitySize.md)
- [Cardinality Measure (CityUnits)](classes/CityUnits__CardinalityMeasure.md)
- [Cardinality Unit Per Time (CityUnits)](classes/CityUnits__CardinalityUnitPerTime.md)
- [City Units Thing (CityUnits)](classes/CityUnits__CityUnitsThing.md)
- [duration](classes/CityUnits__duration.md)
- [function](classes/CityUnits__function.md)
- [Geo_Position_unit (CityUnits)](classes/CityUnits__Geo_Position_unit.md)
- [length](classes/CityUnits__length.md)
- [length unit](classes/CityUnits__length unit.md)
- [mass](classes/CityUnits__mass.md)
- [mass unit](classes/CityUnits__mass unit.md)
- [Monetary Value (CityUnits)](classes/CityUnits__MonetaryValue.md)
- [ratio](classes/CityUnits__ratio.md)
- [speed](classes/CityUnits__speed.md)
- [speed unit](classes/CityUnits__speed unit.md)
- [time unit](classes/CityUnits__time unit.md)
- [Value Of Money (CityUnits)](classes/CityUnits__ValueOfMoney.md)
- [volume](classes/CityUnits__volume.md)
- [volume unit](classes/CityUnits__volume unit.md)

The formal definition of these patterns is available in [OWL Syntax](CityUnits.owl).

## Generic Properties

Ontology to define generic properties used throughout the ISO 5087 series.

This ontology consists of the following patterns:


The formal definition of these patterns is available in [OWL Syntax](GenericProperties.owl).

## iCity Change Ontology

Many of the concepts identified in the urban system ontologies are subject to change. For example, a Vehicle will have one location at one time, and another location at a later time; it may have only one passenger at one time, and four passengers at a later time. Similarly, many attributes of Persons, Households, and even Transportation Networks are subject to change. An approach to representing changing properties, or fluents, that leverages the 4-dimensionalist perspective was proposed by (Welty, Fikes, and Makarios, 2006). We adopt a similar approach, based on a re-interpretation by Krieger (2008) requiring the division of classes that are subject to change into two parts: invariant and variant parts of the concept; we refer to these as TimeVaryingConcept and Manifestation classes, respectively. By distinguishing between these class types and recognizing the properties that are (and aren't) subject to change, the ontology supports the capture of both the static and dynamic aspects of a particular entity. 

This ontology consists of the following patterns:


The ontology also contains the following classes that are not assigned to any pattern:

- [Change Ontology Thing (Change)](classes/Change__ChangeOntologyThing.md)
- [First Manifestation (Change)](classes/Change__FirstManifestation.md)
- [Manifestation (Change)](classes/Change__Manifestation.md)

The formal definition of these patterns is available in [OWL Syntax](Change.owl).

## iCity Resource Ontology

This ontology provides a generic representation of resources that contain core properties generic across all transportation uses. We take the view presented in the TOVE model (Fadel, Fox, and Gruninger, 1994) that "...being a resource is not an innate property of an object but a property that is derived from the role the object plays with respect to an activity". The definition of  a resource is dependent on its participation in an activity occurrence, so the Resource ontology is in fact an extension of the Activity ontology. In this sense, Resources are a class of manifestations, so that rather than have a specialized Resource-perdurant (PD) class, a Resource is a manifestation of some other perdurant class in the ontology. For example, an instance of a Vehicle that is a manifestation of some VehiclePD may also be an instance of a resource, whereas some other instance of a Vehicle that is some later manifestation of the same VehiclePD may not be a Resource, or it may be a different Resource. 
		

This ontology consists of the following patterns:


The ontology also contains the following classes that are not assigned to any pattern:

- [Consume State (Resource)](classes/Resource__ConsumeState.md)
- [Divisible Resource (Resource)](classes/Resource__DivisibleResource.md)
- [Non Divisible Resource (Resource)](classes/Resource__NonDivisibleResource.md)
- [Planned Allocation (Resource)](classes/Resource__PlannedAllocation.md)
- [Produce State (Resource)](classes/Resource__ProduceState.md)
- [Release State (Resource)](classes/Resource__ReleaseState.md)
- [Resource (Resource)](classes/Resource__Resource.md)
- [Resource Ontology Thing (Resource)](classes/Resource__ResourceOntologyThing.md)
- [Terminal Resource State (Resource)](classes/Resource__TerminalResourceState.md)
- [Use State (Resource)](classes/Resource__UseState.md)

The formal definition of these patterns is available in [OWL Syntax](Resource.owl).

## ISO 5087-1 Provenance Pattern

Ontology to capture concepts related to provenance.

This ontology consists of the following patterns:


The ontology also contains the following classes that are not assigned to any pattern:

- [Activity (Prov)](classes/Prov__Activity.md)
- [Agent (Prov)](classes/Prov__Agent.md)
- [Prov Ontology Thing (Prov)](classes/Prov__ProvOntologyThing.md)

The formal definition of these patterns is available in [OWL Syntax](Prov.owl).

## Mereology Ontology

Ontology to capture concepts related to parthood.
The Mereology Ontology extends beyond classical mereology to cover parthood, but also component-hood and containment.

This ontology consists of the following patterns:


The formal definition of these patterns is available in [OWL Syntax](Mereology.owl).

## Organization Structure Pattern

An Organization “represents a collection of people organized together into a community or other social, commercial or political structure. The group has some common purpose or reason for existence which goes beyond the set of people belonging to it. An organization may itself be able to act as an agent.” In this document we include only concepts and properties that focus on the structure of the organization.

This ontology consists of the following patterns:


The ontology also contains the following classes that are not assigned to any pattern:

- [Organization (OrganizationStructure)](classes/OrganizationStructure__Organization.md)
- [Organization Structure Ontology Thing (OrganizationStructure)](classes/OrganizationStructure__OrganizationStructureOntologyThing.md)

The formal definition of these patterns is available in [OWL Syntax](OrganizationStructure.owl).

## Recurring Event Ontology

Ontology to capture concepts related to a calendar. 
Reuses the RecurringEvents ontology.
Beyond the representation of individual timepoints and time intervals, there is often a requirement to reference concepts from a calendar. These calendar concepts provide means of describing some reoccurring events in time, it is important to note that calendar concepts are distinct from the temporal objects that may be characterized with these concepts. In fact, calendar concepts, such as a day of the week, or a month implicitly refer to a class of time objects. 
Here, we define calendar concepts specific to the Gregorian calendar. If required, concepts from other sorts of calendars could be included here as well. These calendar concepts are required to capture properties such as hours of operation, transit schedules, parking policies, and so on.

This ontology consists of the following patterns:


The ontology also contains the following classes that are not assigned to any pattern:

- [Daily Recurring Event (RecurringEvent)](classes/RecurringEvent__DailyRecurringEvent.md)
- [Exception Day (RecurringEvent)](classes/RecurringEvent__ExceptionDay.md)
- [Monthly Recurring Event (RecurringEvent)](classes/RecurringEvent__MonthlyRecurringEvent.md)
- [Recurring Event (RecurringEvent)](classes/RecurringEvent__RecurringEvent.md)
- [Recurring Event Thing (RecurringEvent)](classes/RecurringEvent__RecurringEventThing.md)
- [Weekly Recurring Event (RecurringEvent)](classes/RecurringEvent__WeeklyRecurringEvent.md)
- [Yearly Recurring Event (RecurringEvent)](classes/RecurringEvent__YearlyRecurringEvent.md)

The formal definition of these patterns is available in [OWL Syntax](RecurringEvent.owl).

## Spatial Location Ontology

To capture generic spatial features we require concepts of location, but also concepts of geometry in order to describe shapes that are more complex than a single point in space. To achieve this, we combine an ontology of longitude and latitude, with simple spatial and geometry ontologies.

This ontology was created to organize the reuse of the geoSPARQL vocabulary in the iCity ontology.

This ontology consists of the following patterns:


The ontology also contains the following classes that are not assigned to any pattern:

- [Location (SpatialLoc)](classes/SpatialLoc__Location.md)
- [Spatial Loc Ontology Thing (SpatialLoc)](classes/SpatialLoc__SpatialLocOntologyThing.md)

The formal definition of these patterns is available in [OWL Syntax](SpatialLoc.owl).

## Time Pattern

Ontology to capture concepts related to time. Reuses the owl-time ontology.

This ontology consists of the following patterns:


The ontology also contains the following classes that are not assigned to any pattern:

- [Time Ontology Thing (Time)](classes/Time__TimeOntologyThing.md)

The formal definition of these patterns is available in [OWL Syntax](Time.owl).

