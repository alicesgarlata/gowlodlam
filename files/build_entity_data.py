import json
import sys
from pathlib import Path

from lxml import etree
from rdflib import Graph, Literal, URIRef

from tei_to_html import TEI_NS, extract_entities
from tei_to_rdf import GOW


IMAGE_PAIRS = {
    "odin": [
        {"label": "Mythology", "src": "assets/odinmyth.png"},
        {"label": "In the game", "src": "assets/odingame.png"},
    ],
    "thor": [
        {"label": "Mythology", "src": "assets/thormyth.png"},
        {"label": "In the game", "src": "assets/thorgame.png"},
    ],
    "freyja": [
        {"label": "Mythology", "src": "assets/freyjamyth.png"},
        {"label": "In the game", "src": "assets/freya.png"},
    ],
    "baldur": [
        {"label": "Mythology", "src": "assets/baldurmyth.png"},
        {"label": "In the game", "src": "assets/balduergow.png"},
    ],
    "loki": [
        {"label": "Mythology", "src": "assets/loki.png"},
        {"label": "In the game (Atreus)", "src": "assets/atreusgow.png"},
    ],
    "jormungandr": [
        {"label": "Mythology", "src": "assets/jormungandrmyth.png"},
        {"label": "In the game", "src": "assets/jormungandrgow.jpg"},
    ],
}


def layer_for(entity: dict) -> tuple[str, str]:
    role = entity["role"]
    if role == "fictional-character":
        return "fictional", "Fictional character"
    if role == "mythological-figure":
        return "mythological", "Mythological figure"
    if entity["type"] == "concept":
        return "concepts", "Concept"
    return "production", "Production"


def type_label(entity: dict) -> str:
    role = entity["role"]
    if role:
        return role.replace("-", " ").capitalize()
    return {
        "org": "Organisation",
        "object": "Object",
        "concept": "Concept",
        "person": "Person",
    }.get(entity["type"], entity["type"].capitalize())


def reconciliation_for(entity: dict) -> dict:
    if entity["role"] == "mythological-figure":
        return {
            "property": "gow:reinterprets",
            "note": "The in-game portrayal is linked to the mythological figure without asserting identity.",
        }
    if entity["type"] == "concept":
        return {
            "property": "skos:exactMatch",
            "note": "The local subject concept is aligned with the corresponding Wikidata concept.",
        }
    return {
        "property": "owl:sameAs",
        "note": "The local resource is reconciled with the authority record that describes the same entity.",
    }


def display_term(graph: Graph, term) -> str:
    if isinstance(term, URIRef):
        return graph.namespace_manager.normalizeUri(term)
    if isinstance(term, Literal):
        return term.n3(namespace_manager=graph.namespace_manager)
    return str(term)


def main(tei_path: str, ttl_path: str, output_path: str) -> None:
    tree = etree.parse(tei_path)
    root = tree.getroot()
    entities = extract_entities(root)

    graph = Graph().parse(ttl_path, format="turtle")
    ns = {"tei": TEI_NS}
    output = []

    for entity_id, entity in entities.items():
        layer, layer_label = layer_for(entity)
        subject = GOW[entity_id]
        related_triples = set(graph.triples((subject, None, None)))
        related_triples.update(graph.triples((None, None, subject)))
        triples = [
            {
                "subject": display_term(graph, triple_subject),
                "predicate": display_term(graph, predicate),
                "object": display_term(graph, obj),
            }
            for triple_subject, predicate, obj in related_triples
        ]
        triples.sort(key=lambda triple: (
            triple["subject"], triple["predicate"], triple["object"]
        ))

        output.append({
            "id": entity_id,
            "name": entity["name"],
            "type": type_label(entity),
            "layer": layer,
            "layerLabel": layer_label,
            "uri": str(subject),
            "wikidata": entity["wikidata"],
            "wikidataUrl": (
                f"https://www.wikidata.org/wiki/{entity['wikidata']}"
                if entity["wikidata"] else ""
            ),
            "viaf": entity["viaf"],
            "viafUrl": (
                f"https://viaf.org/viaf/{entity['viaf'].rstrip('/').rsplit('/', 1)[-1]}"
                if entity["viaf"] else ""
            ),
            "mentionCount": int(root.xpath(
                "count(//*[@ref=$entity_ref])",
                namespaces=ns,
                entity_ref=f"#{entity_id}",
            )),
            "reconciliation": reconciliation_for(entity),
            "triples": triples,
            "images": IMAGE_PAIRS.get(entity_id, []),
        })

    Path(output_path).write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Entity explorer data written to {output_path}: {len(output)} entities")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python build_entity_data.py <input.xml> <input.ttl> <output.json>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
