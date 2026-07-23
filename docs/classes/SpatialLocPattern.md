# Information technology - City data model - Part 1: Foundation level concepts - Spatial Location Pattern

This ontology specifies the foundation-level concepts related to the spatial location pattern of the city data model.

This pattern imports the following files:

- [http://www.opengis.net/ont/geosparql#](http://www.opengis.net/ont/geosparql#)
- [https://w3id.org/citydata/part1/v1/MereologyPattern](https://w3id.org/citydata/part1/v1/MereologyPattern)

This pattern consists of the following classes:

- [Location](Location.md)
- [Spatial Loc Thing](SpatialLocThing.md)
This module defines the following properties:

- [associatedLocation](../properties/associatedLocation.md)
- [hasLocation](../properties/hasLocation.md)
- [hasSerialization](../properties/hasSerialization.md)
- [LocationDataProperty](../properties/LocationDataProperty.md)
- [LocationObjectProperty](../properties/LocationObjectProperty.md)
- [nonTangentialProperPart](../properties/nonTangentialProperPart.md)
- [tangentialProperPart](../properties/tangentialProperPart.md)


The formal definition of this pattern is available in TURTLE Syntax in two files, the [core semantics](../SpatialLocPattern.ttl) and the SHACL [restrictions](../SpatialLocSHACL.ttl).
