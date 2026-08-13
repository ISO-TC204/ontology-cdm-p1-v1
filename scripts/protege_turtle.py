"""Protege / OWLAPI-style Turtle serialization for stable diffs.

Layout matches OWLAPI's Turtle renderer as used by Protege:
  - @prefix / @base headers (base = preferred namespace)
  - ontology axioms first (ontology subject as absolute IRI)
  - section banners (Object Properties, Data Properties, Classes, …)
  - ``###  <IRI>`` banners per entity
  - ``rdf:type`` (not ``a``)
  - predicate / multi-object column alignment
  - same-namespace terms as ``:LocalName``
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS, XSD

SH_NODE_SHAPE = URIRef("http://www.w3.org/ns/shacl#NodeShape")
SH_PROPERTY_SHAPE = URIRef("http://www.w3.org/ns/shacl#PropertyShape")

# OWLAPI-ish prefix declaration order (from Protege exports)
PREFIX_DECL_ORDER = [
    "",
    "cc",
    "owl",
    "rdf",
    "xml",
    "xsd",
    "prov",
    "rdfs",
    "skos",
    "time",
    "org",
    "geo",
    "foaf",
    "i72",
    "sh",
    "vann",
    "dcterms",
    "cdm1",
]

ONTOLOGY_PRED_ORDER = [
    RDF.type,
    OWL.imports,
    URIRef("http://creativecommons.org/ns#license"),
    DCTERMS.alternative,
    DCTERMS.creator,
    DCTERMS.modified,
    DCTERMS.title,
    DCTERMS.bibliographicCitation,
    URIRef("http://purl.org/vocab/vann/preferredNamespacePrefix"),
    URIRef("http://purl.org/vocab/vann/preferredNamespaceUri"),
    RDFS.seeAlso,
    RDFS.comment,
    OWL.priorVersion,
    OWL.versionIRI,
    OWL.versionInfo,
    SKOS.definition,
]

PROPERTY_CHARACTERISTICS = {
    OWL.TransitiveProperty,
    OWL.SymmetricProperty,
    OWL.AsymmetricProperty,
    OWL.FunctionalProperty,
    OWL.InverseFunctionalProperty,
    OWL.ReflexiveProperty,
    OWL.IrreflexiveProperty,
}

PROPERTY_PRED_ORDER = [
    RDF.type,
    RDFS.subPropertyOf,
    OWL.inverseOf,
    # characteristic rdf:types are re-inserted after subPropertyOf/inverseOf
    RDFS.domain,
    RDFS.range,
    OWL.propertyChainAxiom,
    RDFS.comment,
    RDFS.label,
    SKOS.definition,
]

CLASS_PRED_ORDER = [
    RDF.type,
    RDFS.subClassOf,
    OWL.disjointWith,
    OWL.equivalentClass,
    RDFS.comment,
    RDFS.label,
    SKOS.definition,
]

RESTRICTION_PRED_ORDER = [
    RDF.type,
    OWL.onProperty,
    OWL.onProperties,
    OWL.cardinality,
    OWL.minCardinality,
    OWL.maxCardinality,
    OWL.qualifiedCardinality,
    OWL.minQualifiedCardinality,
    OWL.maxQualifiedCardinality,
    OWL.onClass,
    OWL.onDataRange,
    OWL.hasValue,
    OWL.someValuesFrom,
    OWL.allValuesFrom,
    OWL.hasSelf,
]


def _pn_local_ok(local: str) -> bool:
    import re

    if local == "":
        return True
    return re.fullmatch(r"[A-Za-z_][A-Za-z0-9_\-\.]*", local) is not None


def _pad(width: int) -> str:
    return " " * max(0, width)


def term(
    term_,
    prefixes: dict[str, str],
    default_ns: str | None = None,
    *,
    absolute: bool = False,
) -> str:
    """Render a term in Protege style (:LocalName for default namespace)."""
    if isinstance(term_, Literal):
        if term_.datatype == XSD.boolean:
            return "true" if str(term_).lower() == "true" else "false"
        raw = str(term_)
        # Triple-quotes only when the lexical form contains a newline (Protege)
        if "\n" in raw or "\r" in raw:
            esc = raw.replace("\\", "\\\\").replace('"""', '\\"""')
            if term_.datatype:
                return f'"""{esc}"""^^{term(term_.datatype, prefixes, default_ns)}'
            if term_.language:
                return f'"""{esc}"""@{term_.language}'
            return f'"""{esc}"""'
        text = (
            raw.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\t", "\\t")
        )
        if term_.datatype:
            return f'"{text}"^^{term(term_.datatype, prefixes, default_ns)}'
        if term_.language:
            return f'"{text}"@{term_.language}'
        return f'"{text}"'

    if isinstance(term_, BNode):
        return f"_:{term_}"

    s = str(term_)
    if absolute:
        return f"<{s}>"

    # Prefer longest matching prefix, including default ":"
    matches = [(pfx, uri) for pfx, uri in prefixes.items() if s.startswith(uri)]
    if matches:
        matches.sort(key=lambda x: len(x[1]), reverse=True)
        # Prefer a named prefix over default when lengths equal and named exists
        best = matches[0]
        for pfx, uri in matches:
            if len(uri) < len(best[1]):
                break
            if pfx not in ("", "cdm1"):
                best = (pfx, uri)
                break
            best = (pfx, uri)
        pfx, uri = best
        # Skip cdm1 duplicate of default :
        if pfx == "cdm1" and "" in prefixes and prefixes[""] == uri:
            pfx = ""
        local = s[len(uri) :]
        if _pn_local_ok(local):
            if pfx == "":
                return f":{local}" if local else ":"
            return f"{pfx}:{local}" if local else f"{pfx}:"
    return f"<{s}>"


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


def ordered_preds(preds: Iterable, order: list) -> list:
    preds = list(dict.fromkeys(preds))
    ranked = []
    for p in order:
        if p in preds:
            ranked.append(p)
            preds.remove(p)
    ranked.extend(sorted(preds, key=str))
    return ranked


def render_inverse_of(inv, prefixes: dict[str, str], default_ns: str) -> list[str]:
    """Protege splits inverse blank nodes across two lines."""
    return [f"[ owl:inverseOf {term(inv, prefixes, default_ns)}", "]"]


def render_rdf_list(g: Graph, head, prefixes: dict[str, str], default_ns: str) -> list[str]:
    """Return list lines without leading indent; first line starts with '('."""
    items = list_items(g, head)
    if not items:
        return ["()"]

    lines: list[str] = []
    # First item may be inverse-of blank node → Protege style
    first = items[0]
    if isinstance(first, BNode) and g.value(first, OWL.inverseOf) is not None:
        inv_lines = render_inverse_of(g.value(first, OWL.inverseOf), prefixes, default_ns)
        lines.append(f"( {inv_lines[0]}")
        lines.append(inv_lines[1])
    elif isinstance(first, BNode) and is_class_expr(g, first):
        expr = render_class_expr(g, first, prefixes, default_ns)
        lines.append(f"( {expr[0]}")
        lines.extend(expr[1:])
    else:
        lines.append(f"( {term(first, prefixes, default_ns)}")

    for item in items[1:]:
        if isinstance(item, BNode) and g.value(item, OWL.inverseOf) is not None:
            lines.extend(render_inverse_of(g.value(item, OWL.inverseOf), prefixes, default_ns))
        elif isinstance(item, BNode) and is_class_expr(g, item):
            lines.extend(render_class_expr(g, item, prefixes, default_ns))
        else:
            lines.append(term(item, prefixes, default_ns))
    lines.append(")")
    return lines


def render_restriction(g: Graph, node, prefixes: dict[str, str], default_ns: str) -> list[str]:
    """Restriction blank node; first line starts with '['."""
    preds = ordered_preds([p for p, _ in g.predicate_objects(node)], RESTRICTION_PRED_ORDER)
    axiom_blocks: list[list[str]] = []
    for pred in preds:
        if pred == RDF.type:
            continue
        for obj in g.objects(node, pred):
            pred_s = term(pred, prefixes, default_ns)
            if pred == OWL.onProperty and isinstance(obj, BNode) and g.value(obj, OWL.inverseOf):
                inv = g.value(obj, OWL.inverseOf)
                inv_lines = render_inverse_of(inv, prefixes, default_ns)
                axiom_blocks.append([f"owl:onProperty {inv_lines[0]}"] + inv_lines[1:])
            elif pred == OWL.onProperty and isinstance(obj, BNode) and g.value(
                obj, OWL.propertyChainAxiom
            ):
                chain = g.value(obj, OWL.propertyChainAxiom)
                lst = render_rdf_list(g, chain, prefixes, default_ns)
                block = [f"owl:onProperty [ owl:propertyChainAxiom {lst[0]}"]
                block.extend(lst[1:])
                block.append("]")
                axiom_blocks.append(block)
            elif isinstance(obj, BNode) and is_class_expr(g, obj):
                nested = render_class_expr(g, obj, prefixes, default_ns)
                axiom_blocks.append([f"{pred_s} {nested[0]}"] + nested[1:])
            else:
                axiom_blocks.append([f"{pred_s} {term(obj, prefixes, default_ns)}"])

    lines = ["[ rdf:type owl:Restriction ;"]
    for i, block in enumerate(axiom_blocks):
        last = i == len(axiom_blocks) - 1
        for j, line in enumerate(block):
            if j == len(block) - 1 and not last:
                line = line + " ;"
            lines.append(line)
    lines.append("]")
    return lines


def render_class_expr(g: Graph, node, prefixes: dict[str, str], default_ns: str) -> list[str]:
    if isinstance(node, (URIRef, Literal)):
        return [term(node, prefixes, default_ns)]
    if is_restriction(g, node):
        return render_restriction(g, node, prefixes, default_ns)

    for pred, label in (
        (OWL.intersectionOf, "owl:intersectionOf"),
        (OWL.unionOf, "owl:unionOf"),
        (OWL.oneOf, "owl:oneOf"),
    ):
        head = g.value(node, pred)
        if head is None:
            continue
        lst = render_rdf_list(g, head, prefixes, default_ns)
        lines = [f"[ rdf:type owl:Class ;", f"{label} {lst[0]}"]
        lines.extend(lst[1:])
        lines.append("]")
        return lines

    comp = g.value(node, OWL.complementOf)
    if comp is not None:
        inner = render_class_expr(g, comp, prefixes, default_ns)
        if len(inner) == 1:
            return [
                "[ rdf:type owl:Class ;",
                f"owl:complementOf {inner[0]}",
                "]",
            ]
        lines = ["[ rdf:type owl:Class ;", f"owl:complementOf {inner[0]}"]
        lines.extend(inner[1:])
        lines.append("]")
        return lines

    return render_blank_node(g, node, prefixes, default_ns)


def render_blank_node(g: Graph, node, prefixes: dict[str, str], default_ns: str) -> list[str]:
    if is_class_expr(g, node):
        return render_class_expr(g, node, prefixes, default_ns)
    if g.value(node, OWL.inverseOf) is not None:
        return render_inverse_of(g.value(node, OWL.inverseOf), prefixes, default_ns)
    if (node, RDF.first, None) in g:
        return render_rdf_list(g, node, prefixes, default_ns)

    preds = sorted({p for p, _ in g.predicate_objects(node)}, key=str)
    if not preds:
        return ["[]"]

    lines = ["["]
    for i, pred in enumerate(preds):
        objs = list(g.objects(node, pred))
        last_pred = i == len(preds) - 1
        for j, obj in enumerate(objs):
            last_obj = j == len(objs) - 1
            sep = "" if last_pred and last_obj else " ;"
            if isinstance(obj, BNode):
                nested = render_blank_node(g, obj, prefixes, default_ns)
                lines.append(f"{term(pred, prefixes, default_ns)} {nested[0]}{sep if len(nested) == 1 else ''}")
                if len(nested) > 1:
                    lines.extend(nested[1:-1])
                    lines.append(f"{nested[-1]}{sep}")
            else:
                lines.append(
                    f"{term(pred, prefixes, default_ns)} {term(obj, prefixes, default_ns)}{sep}"
                )
    lines.append("]")
    # Put '[' on first content line like Protege property shapes: [ sh:path ...
    if len(lines) >= 3:
        first_content = lines[1]
        lines = [f"[ {first_content}"] + lines[2:]
    return lines


def _place_value_block(block: list[str], obj_col: int) -> list[str]:
    """Indent a value block so its first token starts at obj_col.

    Nested blank nodes / lists get Protege/OWLAPI-style relative indentation.
    OWLAPI's Turtle parser is sensitive to flattened nested ``[ Restriction ]``
    fillers; matching its layout avoids Error#N anonymous class failures.
    """
    if not block:
        return [""]
    first = block[0]
    if len(block) == 1:
        return [first]

    # Bracket/paren-depth aware placement for blank nodes and RDF lists
    if first.startswith("[") or first.startswith("("):
        out = [first]
        # Depth inside the opening delimiter on the first line
        depth = first.count("[") + first.count("(") - first.count("]") - first.count(")")
        for extra in block[1:]:
            stripped = extra.lstrip()
            # Closing-only lines sit at the depth of the open they finish
            if stripped in ("]", ")"):
                depth = max(0, depth - 1)
                out.append(f"{_pad(obj_col + 2 * depth)}{stripped}")
                continue
            opens = stripped.count("[") + stripped.count("(")
            closes = stripped.count("]") + stripped.count(")")
            # If the line starts by closing, reduce indent first (rare)
            leading_close = 0
            for ch in stripped:
                if ch in "])":
                    leading_close += 1
                elif not ch.isspace():
                    break
            indent_depth = max(0, depth - leading_close)
            out.append(f"{_pad(obj_col + 2 * indent_depth)}{stripped}")
            depth = max(0, depth + opens - closes)
        return out

    out = [first]
    for extra in block[1:]:
        out.append(f"{_pad(obj_col)}{extra}")
    return out


# Protege/OWLAPI-like ordering of restriction kinds on classes, then by onProperty.
RESTRICTION_KIND_ORDER = {
    "allValuesFrom": 0,
    "someValuesFrom": 1,
    "hasValue": 2,
    "hasSelf": 3,
    "minCardinality": 4,
    "minQualifiedCardinality": 4,
    "qualifiedCardinality": 5,
    "cardinality": 5,
    "maxCardinality": 6,
    "maxQualifiedCardinality": 6,
}


def restriction_kind(g: Graph, node) -> str:
    """Primary restriction facet used for Protege-style sort order."""
    for pred, name in (
        (OWL.allValuesFrom, "allValuesFrom"),
        (OWL.someValuesFrom, "someValuesFrom"),
        (OWL.hasValue, "hasValue"),
        (OWL.hasSelf, "hasSelf"),
        (OWL.minQualifiedCardinality, "minQualifiedCardinality"),
        (OWL.minCardinality, "minCardinality"),
        (OWL.qualifiedCardinality, "qualifiedCardinality"),
        (OWL.cardinality, "cardinality"),
        (OWL.maxQualifiedCardinality, "maxQualifiedCardinality"),
        (OWL.maxCardinality, "maxCardinality"),
    ):
        if g.value(node, pred) is not None:
            return name
    return "other"


def on_property_sort_key(g: Graph, node) -> str:
    prop = g.value(node, OWL.onProperty)
    if prop is None:
        return ""
    if isinstance(prop, BNode):
        inv = g.value(prop, OWL.inverseOf)
        if inv is not None:
            return str(inv).rsplit("/", 1)[-1].rsplit("#", 1)[-1].lower()
        chain = g.value(prop, OWL.propertyChainAxiom)
        if chain is not None:
            items = list_items(g, chain)
            if items:
                first = items[0]
                if isinstance(first, BNode):
                    inv = g.value(first, OWL.inverseOf)
                    if inv is not None:
                        first = inv
                if isinstance(first, URIRef):
                    return str(first).rsplit("/", 1)[-1].rsplit("#", 1)[-1].lower()
        return str(prop)
    return str(prop).rsplit("/", 1)[-1].rsplit("#", 1)[-1].lower()


def subclass_sort_key(g: Graph, obj):
    """
    Sort rdfs:subClassOf fillers like Protege:
      1. named classes (by IRI)
      2. restrictions by kind (AVF, some, hasValue, min, exact, max)
         then by onProperty local name
      3. other class expressions last
    """
    if isinstance(obj, URIRef):
        return (0, str(obj).lower(), "")
    if isinstance(obj, BNode) and is_restriction(g, obj):
        kind = restriction_kind(g, obj)
        kind_rank = RESTRICTION_KIND_ORDER.get(kind, 50)
        return (1, kind_rank, on_property_sort_key(g, obj))
    if isinstance(obj, BNode) and is_class_expr(g, obj):
        return (2, str(obj), "")
    return (3, str(obj), "")


def property_chain_sort_key(g: Graph, list_head) -> str:
    """Sort property chains by the first property's local name (Protege-like)."""
    items = list_items(g, list_head)
    if not items:
        return ""
    first = items[0]
    if isinstance(first, BNode):
        inv = g.value(first, OWL.inverseOf)
        if inv is not None:
            first = inv
    if isinstance(first, URIRef):
        return str(first).rsplit("/", 1)[-1].rsplit("#", 1)[-1].lower()
    return str(first)


def render_entity(
    g: Graph,
    subject: URIRef,
    prefixes: dict[str, str],
    default_ns: str,
    pred_order: list,
    *,
    absolute_subject: bool = False,
) -> str:
    subj_s = term(subject, prefixes, default_ns, absolute=absolute_subject)
    # Protege/OWLAPI uses subject_len+1 for CURIE subjects and subject_len+2
    # for absolute <IRI> subjects (ontology header).
    pred_col = len(subj_s) + (2 if absolute_subject or subj_s.startswith("<") else 1)

    pred_objs: dict = defaultdict(list)
    for p, o in g.predicate_objects(subject):
        pred_objs[p].append(o)

    # Protege emits property characteristics as a second rdf:type after
    # subPropertyOf / inverseOf (not grouped with the declaration type).
    characteristic_types = []
    if RDF.type in pred_objs:
        primary = []
        for t in pred_objs[RDF.type]:
            if t in PROPERTY_CHARACTERISTICS:
                characteristic_types.append(t)
            else:
                primary.append(t)
        pred_objs[RDF.type] = primary

    preds = ordered_preds(pred_objs.keys(), pred_order)
    # Insert characteristic rdf:types after inverseOf (or subPropertyOf)
    if characteristic_types:
        insert_at = None
        for i, p in enumerate(preds):
            if p in (OWL.inverseOf, RDFS.subPropertyOf):
                insert_at = i + 1
        if insert_at is None:
            # after primary rdf:type
            insert_at = 1 if preds and preds[0] == RDF.type else 0
        preds.insert(insert_at, "__characteristic_types__")

    rows: list[tuple[str, list[list[str]]]] = []
    for pred in preds:
        if pred == "__characteristic_types__":
            blocks = [[term(t, prefixes, default_ns)] for t in sorted(characteristic_types, key=str)]
            rows.append((term(RDF.type, prefixes, default_ns), blocks))
            continue
        if pred in (RDFS.subClassOf, OWL.equivalentClass, OWL.disjointWith):
            objs = sorted(pred_objs[pred], key=lambda o: subclass_sort_key(g, o))
        elif pred == OWL.propertyChainAxiom:
            objs = sorted(pred_objs[pred], key=lambda o: property_chain_sort_key(g, o))
        else:
            objs = sorted(
                pred_objs[pred],
                key=lambda o: (
                    0 if isinstance(o, URIRef) else 1 if isinstance(o, Literal) else 2,
                    str(o),
                ),
            )
        blocks: list[list[str]] = []
        for obj in objs:
            if pred == OWL.propertyChainAxiom and isinstance(obj, BNode):
                blocks.append(render_rdf_list(g, obj, prefixes, default_ns))
            elif isinstance(obj, BNode) and is_class_expr(g, obj):
                blocks.append(render_class_expr(g, obj, prefixes, default_ns))
            elif isinstance(obj, BNode):
                blocks.append(render_blank_node(g, obj, prefixes, default_ns))
            else:
                blocks.append([term(obj, prefixes, default_ns)])
        rows.append((term(pred, prefixes, default_ns), blocks))

    if not rows:
        return f"{subj_s} rdf:type owl:Thing .\n"

    lines: list[str] = []
    for pi, (pred_s, blocks) in enumerate(rows):
        last_pred = pi == len(rows) - 1
        obj_col = pred_col + len(pred_s) + 1
        for oi, block in enumerate(blocks):
            last_obj = oi == len(blocks) - 1
            if not last_obj:
                sep = " ,"
            elif not last_pred:
                sep = " ;"
            else:
                sep = " ."

            placed = _place_value_block(block, obj_col)

            if pi == 0 and oi == 0:
                lines.append(f"{subj_s} {pred_s} {placed[0]}")
                lines.extend(placed[1:])
            elif oi == 0:
                lines.append(f"{_pad(pred_col)}{pred_s} {placed[0]}")
                lines.extend(placed[1:])
            else:
                # continued object under same predicate
                lines.append(f"{_pad(obj_col)}{placed[0]}")
                lines.extend(placed[1:])
            lines[-1] = lines[-1] + sep

    return "\n".join(lines) + "\n"


def section_banner(title: str) -> str:
    bar = "#################################################################"
    return f"{bar}\n#    {title}\n{bar}\n"


def entity_banner(iri: str, *, leading_blanks: int = 2) -> str:
    return ("\n" * leading_blanks) + f"###  {iri}\n"


def classify_subjects(g: Graph) -> dict[str, list[URIRef]]:
    buckets = {
        "ontology": [],
        "object_properties": [],
        "data_properties": [],
        "annotation_properties": [],
        "classes": [],
        "shapes": [],
        "individuals": [],
        "other": [],
    }
    object_prop_markers = {
        OWL.ObjectProperty,
        OWL.InverseFunctionalProperty,
        OWL.TransitiveProperty,
        OWL.SymmetricProperty,
        OWL.AsymmetricProperty,
        OWL.FunctionalProperty,
        OWL.IrreflexiveProperty,
        OWL.ReflexiveProperty,
    }
    seen = set()
    for s in g.subjects():
        if not isinstance(s, URIRef) or s in seen:
            continue
        seen.add(s)
        types = set(g.objects(s, RDF.type))
        if OWL.Ontology in types:
            buckets["ontology"].append(s)
        elif types & object_prop_markers and OWL.DatatypeProperty not in types:
            buckets["object_properties"].append(s)
        elif OWL.DatatypeProperty in types:
            buckets["data_properties"].append(s)
        elif OWL.AnnotationProperty in types:
            buckets["annotation_properties"].append(s)
        elif OWL.Class in types:
            buckets["classes"].append(s)
        elif SH_NODE_SHAPE in types or SH_PROPERTY_SHAPE in types:
            buckets["shapes"].append(s)
        elif OWL.NamedIndividual in types:
            buckets["individuals"].append(s)
        elif any(True for _ in g.predicate_objects(s)):
            buckets["other"].append(s)

    for key in buckets:
        buckets[key].sort(key=str)
    return buckets


def _ordered_prefixes(prefixes: dict[str, str]) -> list[tuple[str, str]]:
    ordered: list[tuple[str, str]] = []
    seen = set()
    for pfx in PREFIX_DECL_ORDER:
        if pfx in prefixes and pfx not in seen:
            ordered.append((pfx, prefixes[pfx]))
            seen.add(pfx)
    for pfx, uri in sorted(prefixes.items(), key=lambda x: x[0]):
        if pfx not in seen:
            ordered.append((pfx, uri))
            seen.add(pfx)
    # Always include xml like Protege
    if "xml" not in seen:
        ordered.insert(
            min(4, len(ordered)),
            ("xml", "http://www.w3.org/XML/1998/namespace"),
        )
    return ordered


def serialize_protege(
    g: Graph,
    prefixes: dict[str, str],
    default_ns: str,
    ontology_iri: URIRef | None = None,
) -> str:
    """Serialize ``g`` as Protege/OWLAPI-style Turtle."""
    # Ensure default prefix points at preferred namespace
    prefixes = dict(prefixes)
    prefixes[""] = default_ns

    out: list[str] = []
    for pfx, uri in _ordered_prefixes(prefixes):
        if pfx == "cdm1":
            continue  # duplicate of :
        if pfx == "":
            out.append(f"@prefix : <{uri}> .")
        else:
            out.append(f"@prefix {pfx}: <{uri}> .")

    if ontology_iri is None:
        for s in g.subjects(RDF.type, OWL.Ontology):
            if isinstance(s, URIRef):
                ontology_iri = s
                break
    # Protege uses the preferred namespace as @base, not the ontology IRI
    out.append(f"@base <{default_ns}> .")
    out.append("")

    buckets = classify_subjects(g)

    for s in buckets["ontology"]:
        out.append(
            render_entity(
                g, s, prefixes, default_ns, ONTOLOGY_PRED_ORDER, absolute_subject=True
            ).rstrip()
        )
        out.append("")

    sections = [
        ("object_properties", "Object Properties", PROPERTY_PRED_ORDER),
        ("data_properties", "Data properties", PROPERTY_PRED_ORDER),
        ("annotation_properties", "Annotation Properties", PROPERTY_PRED_ORDER),
        ("classes", "Classes", CLASS_PRED_ORDER),
        ("shapes", "Shapes", CLASS_PRED_ORDER),
        ("individuals", "Individuals", CLASS_PRED_ORDER),
        ("other", "General Axioms", CLASS_PRED_ORDER),
    ]

    first_section = True
    for key, title, order in sections:
        subjects = buckets[key]
        if not subjects:
            continue
        if out and out[-1] != "":
            out.append("")
        # Extra blank before later sections (Protege); not before the first
        if not first_section:
            out.append("")
        first_section = False
        out.append(section_banner(title).rstrip())
        for i, s in enumerate(subjects):
            # Protege: one blank after section banner, two blanks between entities
            blanks = 1 if i == 0 else 2
            out.append(entity_banner(str(s), leading_blanks=blanks).rstrip())
            out.append(render_entity(g, s, prefixes, default_ns, order).rstrip())
        out.append("")

    text = "\n".join(out).rstrip() + "\n"
    return text
