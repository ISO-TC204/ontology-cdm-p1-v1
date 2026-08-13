#!/usr/bin/env python3
"""Convert CDM Part 1 OWL/XML modules to Protege/OWLAPI-style Turtle.

Pattern files keep OWL class definitions with *inline* restriction blank nodes.
Validation companions are emitted as *SHACL.ttl.

Layout matches Protege's Turtle export (section banners, ``### IRI`` markers,
aligned predicates, full IRIs for same-namespace terms) so diffs against
Protege saves are useful.

Usage:
  python scripts/owl_to_ttl.py              # convert from *.owl (if present)
  python scripts/owl_to_ttl.py --reformat   # re-serialize existing docs/*.ttl
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable

from rdflib import Graph, Literal, Namespace, URIRef, BNode
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD, DCTERMS

from protege_turtle import serialize_protege

DOCS = Path(__file__).resolve().parents[1] / "docs"
NS = Namespace("https://w3id.org/citydata/part1/v1/")
CC = Namespace("http://creativecommons.org/ns#")
VANN = Namespace("http://purl.org/vocab/vann/")
SH = Namespace("http://www.w3.org/ns/shacl#")
TIME = Namespace("http://www.w3.org/2006/time#")
PROV = Namespace("http://www.w3.org/ns/prov#")
ORG = Namespace("http://www.w3.org/ns/org#")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
I72 = Namespace("https://w3id.org/citydata/21972/v1/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")

# Source OWL filename -> (pattern ttl, shacl ttl, ontology local name)
MODULES: dict[str, tuple[str, str, str]] = {
    "Core.owl": ("CorePattern.ttl", "CoreSHACL.ttl", "CorePattern"),
    "ActivityPattern.owl": ("ActivityPattern.ttl", "ActivitySHACL.ttl", "ActivityPattern"),
    "AgentPattern.owl": ("AgentPattern.ttl", "AgentSHACL.ttl", "AgentPattern"),
    "AgreementPattern.owl": ("AgreementPattern.ttl", "AgreementSHACL.ttl", "AgreementPattern"),
    "ChangePattern.owl": ("ChangePattern.ttl", "ChangeSHACL.ttl", "ChangePattern"),
    "CityUnitsPattern.owl": ("CityUnitsPattern.ttl", "CityUnitsSHACL.ttl", "CityUnitsPattern"),
    "GenericPropertiesPattern.owl": (
        "GenericPropertiesPattern.ttl",
        "GenericPropertiesSHACL.ttl",
        "GenericPropertiesPattern",
    ),
    "MereologyPattern.owl": ("MereologyPattern.ttl", "MereologySHACL.ttl", "MereologyPattern"),
    "OrganizationStructurePattern.owl": (
        "OrganizationStructurePattern.ttl",
        "OrganizationStructureSHACL.ttl",
        "OrganizationStructurePattern",
    ),
    "RecurringEventPattern.owl": (
        "RecurringEventPattern.ttl",
        "RecurringEventSHACL.ttl",
        "RecurringEventPattern",
    ),
    "ResourcePattern.owl": ("ResourcePattern.ttl", "ResourceSHACL.ttl", "ResourcePattern"),
    "SpatialLocPattern.owl": ("SpatialLocPattern.ttl", "SpatialLocSHACL.ttl", "SpatialLocPattern"),
}

PREFIX_MAP: list[tuple[str, str]] = [
    ("", str(NS)),
    ("cdm1", str(NS)),  # explicit preferred prefix (RITSO / ont2md)
    ("cc", str(CC)),
    ("dcterms", str(DCTERMS)),
    ("owl", str(OWL)),
    ("rdf", str(RDF)),
    ("rdfs", str(RDFS)),
    ("sh", str(SH)),
    ("skos", str(SKOS)),
    ("vann", str(VANN)),
    ("xsd", str(XSD)),
    ("time", str(TIME)),
    ("prov", str(PROV)),
    ("org", str(ORG)),
    ("geo", str(GEO)),
    ("i72", str(I72)),
    ("foaf", str(FOAF)),
]

# Only always declare the default namespace. Other prefixes are added when their
# IRIs appear in the graph (owl:imports time:, geo: terms, etc.).
ALWAYS_DECLARE_PREFIXES = frozenset({""})


def ontology_iri(local: str) -> URIRef:
    """Ontology document IRI with no trailing slash (for ont2md module names)."""
    return URIRef(f"{NS}{local}")


def shacl_local_name(pattern_local: str) -> str:
    """SHACL ontology local name matching *SHACL.ttl (e.g. ActivityPattern → ActivitySHACL)."""
    if pattern_local.endswith("Pattern"):
        return pattern_local[: -len("Pattern")] + "SHACL"
    return f"{pattern_local}SHACL"


def shacl_iri(local: str) -> URIRef:
    """SHACL companion ontology IRI, e.g. :ActivitySHACL (not .../ActivityPattern/shacl)."""
    return URIRef(f"{NS}{shacl_local_name(local)}")


def _pn_local_ok(local: str) -> bool:
    """Turtle PN_LOCAL is restrictive; reject paths and empty fragments."""
    if local == "":
        return True  # bare prefix like time:
    # Allow simple names: letters, digits, _, -, .
    import re

    return re.fullmatch(r"[A-Za-z_][A-Za-z0-9_\-\.]*", local) is not None


def qname(term, prefixes: dict[str, str]) -> str:
    if isinstance(term, Literal):
        # Boolean literals without quotes
        if term.datatype == XSD.boolean:
            return "true" if str(term).lower() == "true" else "false"
        text = (
            str(term)
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\r\n", "\\n")
            .replace("\n", "\\n")
            .replace("\r", "\\n")
            .replace("\t", "\\t")
        )
        if term.datatype:
            return f'"{text}"^^{qname(term.datatype, prefixes)}'
        if term.language:
            return f'"{text}"@{term.language}'
        return f'"{text}"'
    if isinstance(term, BNode):
        return f"_:{term}"
    s = str(term)
    # Longest prefix match
    best = None
    for pfx, uri in prefixes.items():
        if s.startswith(uri):
            if best is None or len(uri) > len(best[1]):
                best = (pfx, uri)
    if best:
        pfx, uri = best
        local = s[len(uri) :]
        if _pn_local_ok(local):
            if pfx == "":
                return f":{local}" if local else ":"
            return f"{pfx}:{local}" if local else f"{pfx}:"
    return f"<{s}>"


def is_restriction(g: Graph, node) -> bool:
    return (node, RDF.type, OWL.Restriction) in g


def is_class_expr(g: Graph, node) -> bool:
    if isinstance(node, URIRef):
        return True
    if not isinstance(node, BNode):
        return False
    return (
        is_restriction(g, node)
        or (node, OWL.intersectionOf, None) in g
        or (node, OWL.unionOf, None) in g
        or (node, OWL.oneOf, None) in g
        or (node, OWL.complementOf, None) in g
        or (node, RDF.type, OWL.Class) in g
    )


def list_items(g: Graph, head) -> list:
    try:
        return list(Collection(g, head))
    except Exception:
        items = []
        cur = head
        while cur and cur != RDF.nil:
            first = g.value(cur, RDF.first)
            if first is not None:
                items.append(first)
            cur = g.value(cur, RDF.rest)
        return items


def transform_restriction(g: Graph, node: BNode) -> None:
    """Rewrite OWL restriction vocabulary toward RITSO style used in samples.

    - owl:someValuesFrom C -> owl:onClass C + owl:minQualifiedCardinality 1
    - owl:allValuesFrom C stays as allValuesFrom unless a cardinality is present,
      in which case it becomes owl:onClass C (qualified restriction form)
    - owl:onDataRange stays with qualified cardinality
    """
    has_card = any(
        g.value(node, p) is not None
        for p in (
            OWL.qualifiedCardinality,
            OWL.minQualifiedCardinality,
            OWL.maxQualifiedCardinality,
            OWL.cardinality,
            OWL.minCardinality,
            OWL.maxCardinality,
        )
    )

    avf = g.value(node, OWL.allValuesFrom)
    if avf is not None and has_card:
        # Qualified cardinality restrictions use onClass / onDataRange
        g.remove((node, OWL.allValuesFrom, avf))
        if (node, OWL.onClass, None) not in g and (node, OWL.onDataRange, None) not in g:
            if str(avf).startswith(str(XSD)):
                g.add((node, OWL.onDataRange, avf))
            else:
                g.add((node, OWL.onClass, avf))

    svf = g.value(node, OWL.someValuesFrom)
    if svf is not None:
        g.remove((node, OWL.someValuesFrom, svf))
        if (node, OWL.onClass, None) not in g and (node, OWL.onDataRange, None) not in g:
            if str(svf).startswith(str(XSD)):
                g.add((node, OWL.onDataRange, svf))
            else:
                g.add((node, OWL.onClass, svf))
        if (
            (node, OWL.minQualifiedCardinality, None) not in g
            and (node, OWL.qualifiedCardinality, None) not in g
            and (node, OWL.minCardinality, None) not in g
        ):
            g.add(
                (
                    node,
                    OWL.minQualifiedCardinality,
                    Literal(1, datatype=XSD.nonNegativeInteger),
                )
            )

    # Unqualified onClass / onDataRange (no cardinality) is invalid OWL; use allValuesFrom
    has_card_now = any(
        g.value(node, p) is not None
        for p in (
            OWL.qualifiedCardinality,
            OWL.minQualifiedCardinality,
            OWL.maxQualifiedCardinality,
            OWL.cardinality,
            OWL.minCardinality,
            OWL.maxCardinality,
        )
    )
    if not has_card_now and g.value(node, OWL.allValuesFrom) is None:
        on_class = g.value(node, OWL.onClass)
        if on_class is not None:
            g.remove((node, OWL.onClass, on_class))
            g.add((node, OWL.allValuesFrom, on_class))
        on_data = g.value(node, OWL.onDataRange)
        if on_data is not None:
            g.remove((node, OWL.onDataRange, on_data))
            g.add((node, OWL.allValuesFrom, on_data))

    # Qualified cardinality without onClass/onDataRange is invalid; demote to unqualified
    if g.value(node, OWL.onClass) is None and g.value(node, OWL.onDataRange) is None:
        swaps = (
            (OWL.qualifiedCardinality, OWL.cardinality),
            (OWL.minQualifiedCardinality, OWL.minCardinality),
            (OWL.maxQualifiedCardinality, OWL.maxCardinality),
        )
        for qpred, upred in swaps:
            val = g.value(node, qpred)
            if val is not None:
                g.remove((node, qpred, val))
                if g.value(node, upred) is None:
                    g.add((node, upred, val))


def _simple_universal_restriction(g: Graph, node):
    """If node is (or unwraps to) ``P only C``, return ``(P, C)``; else None.

    Unwraps single-element ``owl:Class`` / ``owl:intersectionOf ( R )`` introduced
    for OWLAPI Turtle workarounds.
    """
    if not isinstance(node, BNode):
        return None

    inter = g.value(node, OWL.intersectionOf)
    if inter is not None:
        items = list_items(g, inter)
        if len(items) != 1:
            return None
        return _simple_universal_restriction(g, items[0])

    if g.value(node, OWL.onProperty) is None and (node, RDF.type, OWL.Restriction) not in g:
        return None

    prop = g.value(node, OWL.onProperty)
    filler = g.value(node, OWL.allValuesFrom)
    if prop is None or filler is None:
        return None

    allowed = {RDF.type, OWL.onProperty, OWL.allValuesFrom}
    if {p for p, _ in g.predicate_objects(node)} - allowed:
        return None
    return (prop, filler)


def _is_value_unit_chain(g: Graph, prop) -> bool:
    """True if prop is a blank node propertyChainAxiom (i72:value i72:unit_of_measure)."""
    if not isinstance(prop, BNode):
        return False
    head = g.value(prop, OWL.propertyChainAxiom)
    if head is None:
        return False
    items = list_items(g, head)
    return items == [I72.value, I72.unit_of_measure]


def ensure_value_unit_of_measure_property(g: Graph) -> URIRef:
    """Named property for i72:value ∘ i72:unit_of_measure (OWLAPI-safe vs inline chains)."""
    prop = NS.valueUnitOfMeasure
    if (prop, RDF.type, OWL.ObjectProperty) in g:
        return prop
    g.add((prop, RDF.type, OWL.ObjectProperty))
    if (NS.CityUnitObjectProperty, RDF.type, OWL.ObjectProperty) in g:
        g.add((prop, RDFS.subPropertyOf, NS.CityUnitObjectProperty))
    chain = BNode()
    Collection(g, chain, [I72.value, I72.unit_of_measure])
    g.add((prop, OWL.propertyChainAxiom, chain))
    g.add(
        (
            prop,
            SKOS.definition,
            Literal(
                "The unit of measure of a quantity's value "
                "(property chain of i72:value and i72:unit_of_measure)."
            ),
        )
    )
    return prop


def flatten_nested_all_values_from(g: Graph) -> None:
    """Rewrite nested ``value only (unit_of_measure only C)`` using a named chain property.

    Inline ``owl:onProperty [ owl:propertyChainAxiom … ]`` on restrictions is
    misread by OWLAPI's Turtle parser (shows up as a bogus inverse). A named
    ObjectProperty with ``propertyChainAxiom`` matches ActivityPattern style and
    parses cleanly.
    """
    chain_prop: URIRef | None = None

    def named_chain() -> URIRef:
        nonlocal chain_prop
        if chain_prop is None:
            chain_prop = ensure_value_unit_of_measure_property(g)
        return chain_prop

    for restr in list(g.subjects(RDF.type, OWL.Restriction)):
        if not isinstance(restr, BNode):
            continue
        outer_prop = g.value(restr, OWL.onProperty)
        outer_avf = g.value(restr, OWL.allValuesFrom)
        if outer_prop is None:
            continue

        # Already flattened to an inline blank chain → point at named property
        if _is_value_unit_chain(g, outer_prop):
            g.remove((restr, OWL.onProperty, outer_prop))
            g.add((restr, OWL.onProperty, named_chain()))
            continue

        if outer_avf is None:
            continue
        allowed = {RDF.type, OWL.onProperty, OWL.allValuesFrom}
        if {p for p, _ in g.predicate_objects(restr)} - allowed:
            continue

        # Case 1: value only (unit_of_measure only C)
        inner = _simple_universal_restriction(g, outer_avf)
        if inner is not None:
            inner_prop, inner_filler = inner
            if outer_prop == I72.value and inner_prop == I72.unit_of_measure:
                g.remove((restr, OWL.allValuesFrom, outer_avf))
                g.remove((restr, OWL.onProperty, outer_prop))
                g.add((restr, OWL.onProperty, named_chain()))
                g.add((restr, OWL.allValuesFrom, inner_filler))
            continue

        # Case 2: value only (N ∩ (unit_of_measure only C))
        if not isinstance(outer_avf, BNode) or outer_prop != I72.value:
            continue
        inter = g.value(outer_avf, OWL.intersectionOf)
        if inter is None:
            continue
        items = list_items(g, inter)
        named = [i for i in items if isinstance(i, URIRef)]
        rest = [i for i in items if i not in named]
        if len(named) != 1 or len(rest) != 1:
            continue
        inner2 = _simple_universal_restriction(g, rest[0])
        if inner2 is None or inner2[0] != I72.unit_of_measure:
            continue
        _, inner_filler = inner2

        g.remove((restr, OWL.allValuesFrom, outer_avf))
        g.add((restr, OWL.allValuesFrom, named[0]))

        parents = [s for s, _, _ in g.triples((None, RDFS.subClassOf, restr))]
        sibling = BNode()
        g.add((sibling, RDF.type, OWL.Restriction))
        g.add((sibling, OWL.onProperty, named_chain()))
        g.add((sibling, OWL.allValuesFrom, inner_filler))
        for parent in parents:
            g.add((parent, RDFS.subClassOf, sibling))


def collect_reachable_bnodes(g: Graph, root, seen: set | None = None) -> set:
    if seen is None:
        seen = set()
    if not isinstance(root, BNode) or root in seen:
        return seen
    seen.add(root)
    for _, _, o in g.triples((root, None, None)):
        collect_reachable_bnodes(g, o, seen)
    # Also follow rdf:rest chains when walking lists from first
    return seen


def prune_unreachable_bnodes(g: Graph) -> int:
    """Drop blank-node triples not reachable from any named subject."""
    reachable: set = set()
    for s in g.subjects():
        if isinstance(s, URIRef):
            for _, _, o in g.triples((s, None, None)):
                collect_reachable_bnodes(g, o, reachable)
    removed = 0
    for s, p, o in list(g):
        if isinstance(s, BNode) and s not in reachable:
            g.remove((s, p, o))
            removed += 1
        elif isinstance(o, BNode) and o not in reachable and not isinstance(s, URIRef):
            # object-only orphans already covered when subject is unreachable
            pass
    return removed


def transform_graph(g: Graph) -> None:
    for restr in list(g.subjects(RDF.type, OWL.Restriction)):
        if isinstance(restr, BNode):
            transform_restriction(g, restr)
    flatten_nested_all_values_from(g)
    prune_unreachable_bnodes(g)


def write_property_expr(g: Graph, node, prefixes: dict[str, str], indent: str) -> list[str]:
    """Serialize a property expression (URI or inverse blank node)."""
    if isinstance(node, URIRef):
        return [f"{indent}{qname(node, prefixes)}"]
    inv = g.value(node, OWL.inverseOf)
    if inv is not None:
        return [f"{indent}[ owl:inverseOf {qname(inv, prefixes)} ]"]
    return [f"{indent}{qname(node, prefixes)}"]


def write_restriction(g: Graph, node, prefixes: dict[str, str], indent: str) -> list[str]:
    lines = [f"{indent}["]
    inner = indent + "    "
    props = [
        (RDF.type, "rdf:type"),
        (OWL.onProperty, "owl:onProperty"),
        (OWL.onClass, "owl:onClass"),
        (OWL.onDataRange, "owl:onDataRange"),
        (OWL.qualifiedCardinality, "owl:qualifiedCardinality"),
        (OWL.minQualifiedCardinality, "owl:minQualifiedCardinality"),
        (OWL.maxQualifiedCardinality, "owl:maxQualifiedCardinality"),
        (OWL.cardinality, "owl:cardinality"),
        (OWL.minCardinality, "owl:minCardinality"),
        (OWL.maxCardinality, "owl:maxCardinality"),
        (OWL.hasValue, "owl:hasValue"),
        (OWL.allValuesFrom, "owl:allValuesFrom"),
        (OWL.someValuesFrom, "owl:someValuesFrom"),
        (OWL.complementOf, "owl:complementOf"),
    ]
    entries: list[list[str]] = []
    for pred, label in props:
        for obj in g.objects(node, pred):
            if pred == OWL.onProperty and isinstance(obj, BNode):
                expr = write_property_expr(g, obj, prefixes, inner + "    ")
                first = expr[0].strip()
                entries.append([f"{inner}{label:<28} {first} ;"])
            elif isinstance(obj, BNode) and is_class_expr(g, obj):
                expr = write_class_expr(g, obj, prefixes, inner + "    ")
                first = expr[0].strip()
                block = [f"{inner}{label:<28} {first}"]
                block.extend(expr[1:])
                entries.append(block)
            else:
                entries.append([f"{inner}{label:<28} {qname(obj, prefixes)} ;"])
    flat: list[str] = []
    for i, block in enumerate(entries):
        is_last = i == len(entries) - 1
        for j, line in enumerate(block):
            if j == len(block) - 1:
                line = line.rstrip(" ;")
                if not is_last:
                    line = line + " ;"
            flat.append(line)
    lines.extend(flat)
    lines.append(f"{indent}]")
    return lines


def write_class_expr(g: Graph, node, prefixes: dict[str, str], indent: str) -> list[str]:
    if isinstance(node, URIRef) or isinstance(node, Literal):
        return [f"{indent}{qname(node, prefixes)}"]
    if is_restriction(g, node):
        return write_restriction(g, node, prefixes, indent)

    # complementOf alone
    comp = g.value(node, OWL.complementOf)
    if comp is not None and (node, OWL.intersectionOf, None) not in g and (
        node,
        OWL.unionOf,
        None,
    ) not in g:
        lines = [f"{indent}["]
        inner = indent + "    "
        if (node, RDF.type, OWL.Class) in g:
            lines.append(f"{inner}rdf:type owl:Class ;")
        if isinstance(comp, BNode) and is_class_expr(g, comp):
            expr = write_class_expr(g, comp, prefixes, inner + "    ")
            lines.append(f"{inner}owl:complementOf {expr[0].strip()}")
            lines.extend(expr[1:])
        else:
            lines.append(f"{inner}owl:complementOf {qname(comp, prefixes)}")
        lines.append(f"{indent}]")
        return lines

    for pred, label in (
        (OWL.intersectionOf, "owl:intersectionOf"),
        (OWL.unionOf, "owl:unionOf"),
        (OWL.oneOf, "owl:oneOf"),
    ):
        head = g.value(node, pred)
        if head is not None:
            items = list_items(g, head)
            lines = [f"{indent}["]
            inner = indent + "    "
            lines.append(f"{inner}rdf:type owl:Class ;")
            lines.append(f"{inner}{label} (")
            for item in items:
                item_lines = write_class_expr(g, item, prefixes, inner + "    ")
                if len(item_lines) == 1:
                    lines.append(f"{inner}    {item_lines[0].strip()}")
                else:
                    # keep nested expression indented
                    first = item_lines[0].strip()
                    lines.append(f"{inner}    {first}")
                    lines.extend(item_lines[1:])
            lines.append(f"{inner})")
            lines.append(f"{indent}]")
            return lines

    # Fallback blank node dump
    lines = [f"{indent}["]
    for p, o in g.predicate_objects(node):
        if isinstance(o, BNode) and is_class_expr(g, o):
            expr = write_class_expr(g, o, prefixes, indent + "        ")
            lines.append(f"{indent}    {qname(p, prefixes)} {expr[0].strip()}")
            lines.extend(expr[1:])
            lines[-1] = lines[-1] + " ;"
        else:
            lines.append(f"{indent}    {qname(p, prefixes)} {qname(o, prefixes)} ;")
    if len(lines) > 1 and lines[-1].endswith(" ;"):
        lines[-1] = lines[-1][:-2]
    lines.append(f"{indent}]")
    return lines


def write_rdf_list(g: Graph, head, prefixes: dict[str, str], indent: str) -> list[str]:
    items = list_items(g, head)
    if not items:
        return [f"{indent}()"]
    lines = [f"{indent}("]
    for item in items:
        # Property chain members may be blank nodes with owl:inverseOf
        if isinstance(item, BNode) and (item, OWL.inverseOf, None) in g:
            inv = g.value(item, OWL.inverseOf)
            lines.append(f"{indent}    [ owl:inverseOf {qname(inv, prefixes)} ]")
        else:
            expr = write_class_expr(g, item, prefixes, indent + "    ")
            if len(expr) == 1:
                lines.append(f"{indent}    {expr[0].strip()}")
            else:
                lines.extend(expr)
    lines.append(f"{indent})")
    return lines


ANNOTATION_ORDER = [
    DCTERMS.title,
    DCTERMS.alternative,
    SKOS.definition,
    VANN.preferredNamespaceUri,
    VANN.preferredNamespacePrefix,
    NS.mainModule,
    DCTERMS.creator,
    DCTERMS.bibliographicCitation,
    RDFS.seeAlso,
    RDFS.comment,
    OWL.priorVersion,
    DCTERMS.modified,
    OWL.versionInfo,
    OWL.versionIRI,
    CC.license,
    OWL.imports,
]

PROP_ORDER = [
    RDF.type,
    RDFS.subPropertyOf,
    OWL.inverseOf,
    SKOS.definition,
    RDFS.domain,
    RDFS.range,
    RDFS.comment,
    OWL.propertyChainAxiom,
]

CLASS_ORDER = [
    RDF.type,
    SKOS.definition,
    RDFS.subClassOf,
    OWL.disjointWith,
    OWL.equivalentClass,
    RDFS.comment,
]


def ordered_predicates(preds: Iterable, order: list) -> list:
    preds = list(set(preds))
    ranked = []
    for i, p in enumerate(order):
        if p in preds:
            ranked.append(p)
            preds.remove(p)
    ranked.extend(sorted(preds, key=str))
    return ranked


def subject_sort_key(s, g: Graph):
    types = set(g.objects(s, RDF.type))
    if OWL.Ontology in types:
        return (0, str(s))
    if OWL.AnnotationProperty in types:
        return (1, str(s))
    if OWL.ObjectProperty in types or OWL.DatatypeProperty in types:
        return (2, str(s))
    if OWL.Class in types:
        return (3, str(s))
    return (4, str(s))


def write_subject(g: Graph, subject, prefixes: dict[str, str], consumed: set) -> str:
    types = set(g.objects(subject, RDF.type))
    if OWL.Ontology in types:
        order = ANNOTATION_ORDER + [RDF.type]
    elif OWL.Class in types:
        order = CLASS_ORDER
    elif OWL.ObjectProperty in types or OWL.DatatypeProperty in types:
        order = PROP_ORDER
    else:
        order = [RDF.type, SKOS.definition, RDFS.subClassOf, RDFS.subPropertyOf]

    preds = ordered_predicates([p for p, _ in g.predicate_objects(subject)], order)
    lines = [f"{qname(subject, prefixes)}"]
    pred_blocks = []
    for pred in preds:
        objs = list(g.objects(subject, pred))
        # Stable sort URIRefs first
        objs.sort(key=lambda o: (0 if isinstance(o, URIRef) else 1, str(o)))
        for obj in objs:
            if isinstance(obj, BNode) and obj in consumed:
                continue
            if pred in (RDFS.subClassOf, OWL.equivalentClass, OWL.disjointWith) and is_class_expr(
                g, obj
            ):
                if isinstance(obj, BNode):
                    consumed.update(collect_reachable_bnodes(g, obj))
                expr_lines = write_class_expr(g, obj, prefixes, "    ")
                if len(expr_lines) == 1 and not expr_lines[0].strip().startswith("["):
                    pred_blocks.append(
                        [f"    {qname(pred, prefixes):<24} {expr_lines[0].strip()} ;"]
                    )
                else:
                    # Put '[' on the same line as the predicate (RITSO style)
                    first = expr_lines[0].strip()
                    block = [f"    {qname(pred, prefixes)} {first}"]
                    for el in expr_lines[1:]:
                        block.append(el)
                    block[-1] = block[-1] + " ;"
                    pred_blocks.append(block)
            elif pred == OWL.propertyChainAxiom and isinstance(obj, BNode):
                consumed.update(collect_reachable_bnodes(g, obj))
                # propertyChainAxiom may point directly at rdf:List head
                list_lines = write_rdf_list(g, obj, prefixes, "        ")
                block = [f"    {qname(pred, prefixes)}"]
                block.extend(list_lines)
                block[-1] = block[-1] + " ;"
                pred_blocks.append(block)
            elif pred in (OWL.intersectionOf, OWL.unionOf, OWL.oneOf) and isinstance(obj, BNode):
                consumed.update(collect_reachable_bnodes(g, obj))
                list_lines = write_rdf_list(g, obj, prefixes, "        ")
                block = [f"    {qname(pred, prefixes)}"]
                block.extend(list_lines)
                block[-1] = block[-1] + " ;"
                pred_blocks.append(block)
            else:
                if isinstance(obj, BNode):
                    # Skip blank nodes that are only restriction/list internals
                    if is_restriction(g, obj) or (obj, RDF.first, None) in g:
                        consumed.update(collect_reachable_bnodes(g, obj))
                        continue
                    consumed.update(collect_reachable_bnodes(g, obj))
                    expr_lines = write_class_expr(g, obj, prefixes, "    ")
                    first = expr_lines[0].strip()
                    block = [f"    {qname(pred, prefixes)} {first}"]
                    for el in expr_lines[1:]:
                        block.append(el)
                    block[-1] = block[-1] + " ;"
                    pred_blocks.append(block)
                else:
                    pred_blocks.append(
                        [f"    {qname(pred, prefixes):<24} {qname(obj, prefixes)} ;"]
                    )

    flat = []
    for block in pred_blocks:
        flat.extend(block)
    if flat:
        flat[-1] = flat[-1].rstrip(" ;") + " ."
    lines.extend(flat)
    return "\n".join(lines)


def used_prefixes(g: Graph) -> dict[str, str]:
    needed = {p: u for p, u in PREFIX_MAP if p in ALWAYS_DECLARE_PREFIXES}
    text_terms = []
    for s, p, o in g:
        text_terms.extend([s, p, o])
        if isinstance(o, Literal) and o.datatype:
            text_terms.append(o.datatype)
    for term in text_terms:
        if not isinstance(term, URIRef):
            continue
        s = str(term)
        # Prefer longest namespace match, skipping the empty/default and cdm1 aliases
        # when a more specific external prefix applies.
        matches = [(pfx, uri) for pfx, uri in PREFIX_MAP if s.startswith(uri)]
        if matches:
            matches.sort(key=lambda x: len(x[1]), reverse=True)
            for pfx, uri in matches:
                if pfx in ("", "cdm1") and any(
                    len(u) > len(uri) for _, u in matches
                ):
                    continue
                needed[pfx] = uri
                break
    return needed


def serialize_pattern(g: Graph) -> str:
    """Serialize an OWL module graph as Protege/OWLAPI-style Turtle."""
    transform_graph(g)
    # Normalize mainModule string literals to boolean
    for s, o in list(g.subject_objects(NS.mainModule)):
        if isinstance(o, Literal) and str(o).lower() in ("true", "false"):
            g.remove((s, NS.mainModule, o))
            g.add((s, NS.mainModule, Literal(str(o).lower() == "true")))
    prefixes = used_prefixes(g)
    ordered = {p: u for p, u in PREFIX_MAP if p in prefixes}
    ordered.update({p: u for p, u in prefixes.items() if p not in ordered})
    return serialize_protege(g, ordered, str(NS))


def restriction_to_shacl_props(g: Graph, class_uri: URIRef) -> list[dict]:
    props = []
    for obj in g.objects(class_uri, RDFS.subClassOf):
        if not is_restriction(g, obj):
            continue
        path = g.value(obj, OWL.onProperty)
        if path is None:
            continue
        entry: dict = {}
        if isinstance(path, BNode):
            inv = g.value(path, OWL.inverseOf)
            if inv is None:
                continue
            entry["inversePath"] = inv
        else:
            entry["path"] = path

        on_class = g.value(obj, OWL.onClass)
        on_data = g.value(obj, OWL.onDataRange)
        # Skip complex class expressions in SHACL (anonymous intersections/unions)
        if on_class is not None:
            if isinstance(on_class, BNode):
                continue
            entry["class"] = on_class
        if on_data is not None:
            if isinstance(on_data, BNode):
                continue
            entry["datatype"] = on_data

        qc = g.value(obj, OWL.qualifiedCardinality)
        minq = g.value(obj, OWL.minQualifiedCardinality)
        maxq = g.value(obj, OWL.maxQualifiedCardinality)
        minc = g.value(obj, OWL.minCardinality)
        maxc = g.value(obj, OWL.maxCardinality)
        card = g.value(obj, OWL.cardinality)

        if qc is not None:
            n = int(qc)
            if n == 1:
                entry["node"] = "ExactlyOneShape"
            elif n == 0:
                entry["maxCount"] = 0
            else:
                entry["minCount"] = n
                entry["maxCount"] = n
        elif minq is not None:
            n = int(minq)
            if n == 1 and maxq is None:
                entry["node"] = "MinOneShape"
            else:
                entry["minCount"] = n
                if maxq is not None:
                    entry["maxCount"] = int(maxq)
        elif maxq is not None:
            n = int(maxq)
            if n == 1:
                entry["node"] = "MaxOneShape"
            else:
                entry["maxCount"] = n
        elif card is not None:
            n = int(card)
            if n == 1:
                entry["node"] = "ExactlyOneShape"
            else:
                entry["minCount"] = n
                entry["maxCount"] = n
        elif minc is not None:
            entry["minCount"] = int(minc)
            if maxc is not None:
                entry["maxCount"] = int(maxc)
        elif maxc is not None:
            if int(maxc) == 1:
                entry["node"] = "MaxOneShape"
            else:
                entry["maxCount"] = int(maxc)
        props.append(entry)
    return props


def write_shacl(pattern_g: Graph, local: str, label: str) -> str:
    """Build SHACL companion from class restrictions in the (pre-transform) graph."""
    g = Graph()
    for t in pattern_g:
        g.add(t)
    transform_graph(g)

    shapes = []
    for cls in sorted(g.subjects(RDF.type, OWL.Class), key=str):
        if not isinstance(cls, URIRef):
            continue
        props = restriction_to_shacl_props(g, cls)
        if not props:
            continue
        shapes.append((cls, props))

    prefixes = {p: u for p, u in PREFIX_MAP}

    # Collect URIRefs used so we can emit needed prefixes
    used_uris: set[str] = set()
    for cls, props in shapes:
        used_uris.add(str(cls))
        for p in props:
            if "path" in p:
                used_uris.add(str(p["path"]))
            if "inversePath" in p:
                used_uris.add(str(p["inversePath"]))
            if "class" in p:
                used_uris.add(str(p["class"]))
            if "datatype" in p:
                used_uris.add(str(p["datatype"]))

    # Header + SHACL vocabulary always appear in the written text.
    needed_pfx = set(ALWAYS_DECLARE_PREFIXES) | {
        "dcterms",
        "owl",
        "rdf",
        "skos",
        "vann",
        "sh",
    }
    for uri in used_uris:
        matches = [(pfx, base) for pfx, base in PREFIX_MAP if uri.startswith(base)]
        if not matches:
            continue
        matches.sort(key=lambda x: len(x[1]), reverse=True)
        for pfx, base in matches:
            if pfx in ("", "cdm1") and any(len(u) > len(base) for _, u in matches):
                continue
            needed_pfx.add(pfx)
            break

    lines = []
    for pfx, uri in PREFIX_MAP:
        if pfx in needed_pfx:
            if pfx == "":
                lines.append(f"@prefix : <{uri}> .")
            else:
                lines.append(f"@prefix {pfx}: <{uri}> .")
    lines.append("")

    ont = shacl_iri(local)
    pattern = ontology_iri(local)
    shacl_name = shacl_local_name(local)
    lines.append(f":{shacl_name}")
    lines.append("    rdf:type owl:Ontology ;")
    lines.append(f'    dcterms:title "City Data Model Part 1 - {label} - SHACL constraints" ;')
    lines.append(
        f'    skos:definition "SHACL validation shapes for the {label} pattern module." ;'
    )
    lines.append(f'    vann:preferredNamespaceUri "{NS}" ;')
    lines.append('    vann:preferredNamespacePrefix "cdm1" ;')
    if local != "CorePattern":
        lines.append(f"    owl:imports :{local} ;")
        lines.append(f"    owl:imports :{shacl_local_name('CorePattern')} .")
    else:
        lines.append(f"    owl:imports :{local} .")
    lines.append("")

    if local == "CorePattern":
        lines.extend(
            [
                ":ExactlyOneShape",
                "    rdf:type sh:NodeShape ;",
                "    sh:minCount 1 ;",
                "    sh:maxCount 1 .",
                "",
                ":MinOneShape",
                "    rdf:type sh:NodeShape ;",
                "    sh:minCount 1 .",
                "",
                ":MaxOneShape",
                "    rdf:type sh:NodeShape ;",
                "    sh:maxCount 1 .",
                "",
            ]
        )

    for cls, props in shapes:
        local_name = str(cls)[len(str(NS)) :]
        shape = f":{local_name}Shape"
        lines.append(f"{shape}")
        lines.append("    rdf:type sh:NodeShape ;")
        lines.append(f"    sh:targetClass {qname(cls, prefixes)} ;")
        for i, p in enumerate(props):
            lines.append("    sh:property [")
            if "inversePath" in p:
                lines.append(
                    f"        sh:path [ sh:inversePath {qname(p['inversePath'], prefixes)} ] ;"
                )
            else:
                lines.append(f"        sh:path {qname(p['path'], prefixes)} ;")
            if "node" in p:
                lines.append(f"        sh:node :{p['node']} ;")
            if "minCount" in p:
                lines.append(f"        sh:minCount {p['minCount']} ;")
            if "maxCount" in p:
                lines.append(f"        sh:maxCount {p['maxCount']} ;")
            if "class" in p:
                lines.append(f"        sh:class {qname(p['class'], prefixes)} ;")
            if "datatype" in p:
                lines.append(f"        sh:datatype {qname(p['datatype'], prefixes)} ;")
            if lines[-1].endswith(" ;"):
                lines[-1] = lines[-1][:-2]
            closing = "    ] ;" if i < len(props) - 1 else "    ] ."
            lines.append(closing)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def convert_module(owl_name: str, pattern_name: str, shacl_name: str, local: str) -> None:
    owl_path = DOCS / owl_name
    g = Graph()
    g.parse(owl_path, format="xml")

    # SHACL from original semantics (before/with transform applied inside writer)
    label = local.replace("Pattern", "").replace("Core", "Core")
    # human label
    label = "".join((" " + c if c.isupper() else c) for c in local).strip()
    shacl_text = write_shacl(g, local, label)

    pattern_text = serialize_pattern(g)
    (DOCS / pattern_name).write_text(pattern_text, encoding="utf-8")
    (DOCS / shacl_name).write_text(shacl_text, encoding="utf-8")
    print(f"Wrote {pattern_name}, {shacl_name}")


def write_master() -> None:
    g = Graph()
    g.parse(DOCS / "5087-1.owl", format="xml")
    # Add SHACL imports into the graph before serialization
    master = URIRef(str(NS))
    for _, _, local in MODULES.values():
        g.add((master, OWL.imports, shacl_iri(local)))
    # Normalize mainModule to boolean
    for o in list(g.objects(master, NS.mainModule)):
        g.remove((master, NS.mainModule, o))
    g.add((master, NS.mainModule, Literal(True)))
    text = serialize_pattern(g)
    (DOCS / "5087-1.ttl").write_text(text, encoding="utf-8")
    print("Wrote 5087-1.ttl")


def write_catalog() -> None:
    entries = [("https://w3id.org/citydata/part1/v1/", "5087-1.ttl")]
    for pattern, shacl, local in MODULES.values():
        entries.append((str(ontology_iri(local)), pattern))
        entries.append((str(shacl_iri(local)), shacl))
    lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        '<catalog prefer="public" xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">',
        '    <group prefer="public">',
    ]
    for name, uri in entries:
        lines.append(f'        <uri name="{name}" uri="{uri}"/>')
    lines.extend(["    </group>", "</catalog>", ""])
    (DOCS / "catalog-v001.xml").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote catalog-v001.xml")


def reformat_existing_ttl() -> None:
    """Re-serialize existing pattern/master TTL files in Protege layout (no OWL sources)."""
    paths = sorted(DOCS.glob("*Pattern.ttl")) + [DOCS / "5087-1.ttl"]
    for path in paths:
        if not path.is_file():
            continue
        g = Graph()
        g.parse(path, format="turtle")
        transform_graph(g)
        text = serialize_pattern(g)
        # Round-trip check
        g2 = Graph()
        g2.parse(data=text, format="turtle")
        if len(g2) < len(g) * 0.9:
            raise SystemExit(
                f"{path.name}: reformatted graph shrank suspiciously ({len(g)} → {len(g2)})"
            )
        path.write_text(text, encoding="utf-8")
        print(f"Reformatted {path.name} ({len(g)} → {len(g2)} triples)")


def reformat_existing_shacl() -> None:
    """Re-serialize existing *SHACL.ttl files in Protege layout."""
    for path in sorted(DOCS.glob("*SHACL.ttl")):
        g = Graph()
        g.parse(path, format="turtle")
        prefixes = used_prefixes(g)
        ordered = {p: u for p, u in PREFIX_MAP if p in prefixes}
        ordered.update({p: u for p, u in prefixes.items() if p not in ordered})
        text = serialize_protege(g, ordered, str(NS))
        g2 = Graph()
        g2.parse(data=text, format="turtle")
        path.write_text(text, encoding="utf-8")
        print(f"Reformatted {path.name} ({len(g)} → {len(g2)} triples)")


def main() -> int:
    import sys

    if "--reformat" in sys.argv or "-r" in sys.argv:
        reformat_existing_ttl()
        reformat_existing_shacl()
        return 0

    for owl_name, (pattern, shacl, local) in MODULES.items():
        convert_module(owl_name, pattern, shacl, local)
    write_master()
    write_catalog()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
