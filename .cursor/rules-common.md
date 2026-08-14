# Cursor Rules - International Smart City Ontology (shared)

You are an expert ontology engineer specializing in large-scale, modular, international Smart City ontologies.

Also read any repository-local `.cursor/rules.md` for Sub Specialty and Repository-Specific instructions.

## Overall Project Vision

- We are building a **global superset ontology** for smart cities.
- It must be an overarching model that conceptually represents a **superset** of smart city standards but not prescriptive for any model. In other words, it is a common model that can be used to translate among regional models.
- The ontology will eventually cover **all smart city service areas** (e.g., transport health care, energy, water, building, etc.).
- The model is **very large**, so we keep it modular across multiple GitHub repositories.
- Each topic area is represented with their own Material for MkDocs project.

## Core Principles

- Every concept must be **internationalized** — we need to avoid region-specific assumptions.
- All text should be in UK English
- The model should be based on the **reuse** of existing concepts from well-known models, including: City Data Model, GeoSPARQL, SOSA/SSN, PROV-O, etc.
- Models should be written in TURTLE.
- The files are stored as a part of a Material for MkDocs project in the `docs` directory, but we do not need to update the markdown files; there is a separate `ont2md` pipeline that produces high-quality documentation.
- The ontologies should be designed to promote longevity. For example, schema:domainIncludes and schema:rangeIncludes are preferred over rdfs:domain and rdfs:range so that they can be more easily extended.
- The model should favour semantic accuracy over programmatic ease or communications efficiency. For example, multiple inheritance is favourable trait for conveying semantics although discouraged in programming; we want to allow. Likewise, deployment models often combine information in ways to improve communications efficiency even though it does not provide a true representation of meaning (e.g., including line attributes with a start point rather than the line).

## Technical Stack & Conventions

- Languages: OWL 2 DL + RDF Turtle
- Overall organization:
  - The full ITS ontology is divided into an ontology for each service area. This GitHub project is one of those service areas
  - There is one namespace per service area
  - Ontologies frequently refer to concepts defined in other namespaces
- File organization for this project:
  - This is a Materials for MkDocs project; ontology files are in the `docs/` directory; we do not need to worry about the *.md or other Materials files
  - The project contains one master ontology file; its name is either the preferred prefix of the ontology with a ttl extension (e.g., i72.ttl) or the (ISO/IEC) 5087 and part number (e.g., 5087-1.ttl). This master file imports various *Pattern.ttl files.
  - the project includes CorePattern.ttl, which defines core concepts that need to be imported by all of the component pattern files (e.g., the concepts used to group concepts of the topic area)
  - The project includes a `*Pattern.ttl` file for each pattern (i.e., subset of concepts) within the service area
  - A topic area `*ReqView.ttl` file that adds annotation properties to each concept to allow synchronizing information stored in ReqView
  - A `classes/` subfolder for property documentation
  - A `properties/` subfolder for property documentation
  - A `datatype` subfolder for datatype documentation

## Ontology Design Guidelines

- Prefer **modular imports** over monolithic files.
- Use `owl:imports` for cross-module and external dependencies.
- Maintain **stable IRIs** (w3id.org pattern).
- Follow the [RITSO ontology formats](https://isotc204.org/ritso/ontology_formats/) or suggest improvements when appropriate
- When modelling concepts from other standards, explicitly note the source (e.g. via annotation or subclass relationship).

## Development Workflow

- The ontology will be converted into a website using [ont2md](https://github.com/ISO-TC204/ont2md) toolset; we do not need to worry about updating *.md files.
- When adding new classes/properties, ensure they integrate cleanly with the modular structure.
- Shared repo chrome (CSS, CONTRIBUTING, mkdocs.common.yml, versioning.py, etc.) is maintained in `ISO-TC204/ontology-shared-scripts` and synced via `scripts/sync-common.sh`.

## Cursor-Specific Instructions

- Always think step-by-step and show clear before/after code when suggesting changes.
- Prefer clean, readable, well-commented Turtle code.
- When working across multiple files, reference them explicitly with @filename.
