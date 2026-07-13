"""
tei_to_rdf.py — TEI/XML → RDF/Turtle transformation for the God of War
(2018) LODLAM project.

Reads the TEI file, extracts entity definitions from <standOff> and
<taxonomy>, and builds an RDF graph that:

  - defines the project ontology header and the one coined property
    (gow:reinterprets, subPropertyOf dcterms:relation), used for the
    fictional-adaptation-of-myth relation

  - types every entity using standard vocabularies (schema.org, FOAF, DBO,
    SKOS)

  - reconciles each entity with external authorities via one of three
    strategies, chosen by what the Wikidata QID actually represents:
      * owl:sameAs         — for real persons, orgs, objects, and fictional
                             characters whose Wikidata entry is about the
                             game character (Kratos, Atreus)
      * gow:reinterprets   — for mythological figures whose Wikidata entry
                             is about the myth version, not the game version
      * skos:exactMatch    — for concepts (Norse mythology, Greek mythology)
    Real persons and organisations also get owl:sameAs to VIAF.

  - links the game to production entities via schema/dcterms/dbo properties
    (director, developer, publisher, musicBy, gamePlatform, character,
    subject)

  - adds in-game and myth-derived family relations that expose where the
    game's genealogy departs from Norse myth (Freyja as Baldur's mother in
    the game, Frigg in myth) and where fiction closes back on myth (Atreus
    revealed as Loki, whose son Jörmungandr the trio meets in the game)

Usage:
    python tei_to_rdf.py <input.xml> <output.ttl>

Requires: lxml, rdflib   (pip install lxml rdflib)
"""

import sys
from pathlib import Path

from lxml import etree
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD, DCTERMS, SKOS, FOAF


# =======================================================================
# Namespaces
# =======================================================================

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"

# Project namespace — change this to your actual base URL if you publish
# the ontology online. All coined terms (gow:reinterprets) and all
# individual resources (gow:kratos, gow:god-of-war-2018, …) live here.
GOW = Namespace("https://alicesgarlata.github.io/gowlodlam/")

WD = Namespace("http://www.wikidata.org/entity/")
VIAF = Namespace("http://viaf.org/viaf/")
SCHEMA = Namespace("https://schema.org/")
DBO = Namespace("http://dbpedia.org/ontology/")


# =======================================================================
# ID cleaning helpers (mirror of tei_to_html.py)
# =======================================================================

def clean_id(text: str) -> str:
    """Strip square brackets and whitespace from an authority ID."""
    if text is None:
        return ""
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()
    return text


def _q(tag: str) -> str:
    return f"{{{TEI_NS}}}{tag}"


def _xml_id(el) -> str:
    return el.get(f"{{{XML_NS}}}id", "")


def viaf_id_only(viaf: str) -> str:
    """Extract just the numeric fragment from a VIAF URL, or return as-is."""
    viaf = clean_id(viaf)
    if viaf.startswith("http"):
        return viaf.rsplit("/", 1)[-1]
    return viaf


# =======================================================================
# Entity extraction (same shape as tei_to_html.py)
# =======================================================================

def extract_entities(root) -> dict:
    """
    Walk the standoff and taxonomy sections and return
      { xml_id: {type, name, role, wikidata, viaf} }
    for every defined entity.
    """
    entities = {}

    for person in root.iter(_q("person")):
        pid = _xml_id(person)
        if not pid:
            continue
        name_el = person.find(_q("persName"))
        wikidata = viaf = ""
        for idno in person.findall(_q("idno")):
            if idno.get("type") == "Wikidata":
                wikidata = clean_id(idno.text)
            elif idno.get("type") == "VIAF":
                viaf = clean_id(idno.text)
        entities[pid] = {
            "type": "person",
            "name": name_el.text if name_el is not None else pid,
            "role": person.get("role", ""),
            "wikidata": wikidata,
            "viaf": viaf,
        }

    for org in root.iter(_q("org")):
        oid = _xml_id(org)
        if not oid:
            continue
        name_el = org.find(_q("orgName"))
        wikidata = viaf = ""
        for idno in org.findall(_q("idno")):
            if idno.get("type") == "Wikidata":
                wikidata = clean_id(idno.text)
            elif idno.get("type") == "VIAF":
                viaf = clean_id(idno.text)
        entities[oid] = {
            "type": "org",
            "name": name_el.text if name_el is not None else oid,
            "role": "",
            "wikidata": wikidata,
            "viaf": viaf,
        }

    for obj in root.iter(_q("object")):
        oid = _xml_id(obj)
        if not oid:
            continue
        name_el = obj.find(f"{_q('objectIdentifier')}/{_q('objectName')}")
        wikidata = ""
        for idno in obj.findall(_q("idno")):
            if idno.get("type") == "Wikidata":
                wikidata = clean_id(idno.text)
        entities[oid] = {
            "type": "object",
            "name": name_el.text if name_el is not None else oid,
            "role": "",
            "wikidata": wikidata,
            "viaf": "",
        }

    for cat in root.iter(_q("category")):
        cid = _xml_id(cat)
        if not cid:
            continue
        desc = cat.find(_q("catDesc"))
        name_text = cid.replace("-", " ").title()
        if desc is not None and desc.text:
            name_text = desc.text.split("—")[0].strip() or name_text
        corresp = clean_id(cat.get("corresp", ""))
        wikidata = corresp.rsplit("/", 1)[-1] if corresp.startswith("http") else corresp
        entities[cid] = {
            "type": "concept",
            "name": name_text,
            "role": "",
            "wikidata": wikidata,
            "viaf": "",
        }

    return entities


# =======================================================================
# Graph construction
# =======================================================================

def bind_prefixes(g: Graph) -> None:
    g.bind("gow", GOW)
    g.bind("wd", WD)
    g.bind("viaf", VIAF)
    g.bind("schema", SCHEMA)
    g.bind("dcterms", DCTERMS)
    g.bind("skos", SKOS)
    g.bind("foaf", FOAF)
    g.bind("dbo", DBO)
    g.bind("owl", OWL)


def add_ontology_header(g: Graph) -> None:
    """Declare the project ontology and the coined gow:reinterprets property."""
    ont = URIRef(str(GOW).rstrip("/"))
    g.add((ont, RDF.type, OWL.Ontology))
    g.add((ont, RDFS.label,
           Literal("God of War (2018) LODLAM ontology", lang="en")))
    g.add((ont, RDFS.comment, Literal(
        "Ontology for the LODLAM project on the God of War (2018) Wikipedia page. "
        "Reuses schema.org, dcterms, FOAF, SKOS, and DBO; adds one coined "
        "property (gow:reinterprets) for the fictional-adaptation-of-myth relation.",
        lang="en")))

    reinterprets = GOW["reinterprets"]
    g.add((reinterprets, RDF.type, OWL.ObjectProperty))
    g.add((reinterprets, RDFS.subPropertyOf, DCTERMS.relation))
    g.add((reinterprets, RDFS.label, Literal("reinterprets", lang="en")))
    g.add((reinterprets, RDFS.comment, Literal(
        "Relates a character in the game to the mythological figure they are "
        "based on. Used instead of owl:sameAs when the Wikidata entry describes "
        "the myth figure, not the fictional character.", lang="en")))


def add_game(g: Graph) -> None:
    """The game itself: God of War (2018)."""
    game = GOW["god-of-war-2018"]
    g.add((game, RDF.type, SCHEMA.VideoGame))
    g.add((game, RDFS.label, Literal("God of War", lang="en")))
    g.add((game, DCTERMS.title, Literal("God of War", lang="en")))
    g.add((game, DCTERMS.date, Literal("2018-04-20", datatype=XSD.date)))
    g.add((game, OWL.sameAs, WD["Q18345138"]))


def add_entity_triples(g: Graph, eid: str, ent: dict) -> None:
    """Emit rdf:type, labels, and reconciliation links for one entity."""
    uri = GOW[eid]
    etype = ent["type"]
    role = ent["role"]
    wikidata = ent["wikidata"]
    viaf = ent["viaf"]
    name = ent["name"]

    if etype == "person":
        g.add((uri, RDF.type, FOAF.Person))
        g.add((uri, FOAF.name, Literal(name, lang="en")))
        g.add((uri, RDFS.label, Literal(name, lang="en")))

        if role == "fictional-character":
            g.add((uri, RDF.type, DBO.FictionalCharacter))
            if wikidata:
                g.add((uri, OWL.sameAs, WD[wikidata]))

        elif role == "mythological-figure":
            # Mythological figures are also active characters within the
            # game's narrative (they appear, speak, and act — not just
            # cited references), so they get the same dbo:FictionalCharacter
            # typing as Kratos and Atreus. This makes gow:reinterprets have
            # a single, uniform domain class instead of splitting across
            # foaf:Person for some characters and dbo:FictionalCharacter
            # for others.
            g.add((uri, RDF.type, DBO.FictionalCharacter))
            # Every mythological-figure entity in this dataset belongs to
            # Norse mythology specifically (there are no Greek deities in
            # the entity set — Kratos is a fictional-character, not a
            # mythological-figure). This makes explicit, at the individual
            # level, the pantheon each figure belongs to — a tighter link
            # than just having the game itself carry dcterms:subject.
            g.add((uri, DCTERMS.subject, GOW["norse-mythology"]))
            if wikidata:
                # game character reinterprets the mythological figure —
                # not owl:sameAs because Wikidata's entry is about the myth
                g.add((uri, GOW["reinterprets"], WD[wikidata]))

        else:
            # real person (director, composer, …)
            if wikidata:
                g.add((uri, OWL.sameAs, WD[wikidata]))
            if viaf:
                g.add((uri, OWL.sameAs, VIAF[viaf_id_only(viaf)]))

    elif etype == "org":
        g.add((uri, RDF.type, FOAF.Organization))
        g.add((uri, FOAF.name, Literal(name, lang="en")))
        g.add((uri, RDFS.label, Literal(name, lang="en")))
        if wikidata:
            g.add((uri, OWL.sameAs, WD[wikidata]))
        if viaf:
            g.add((uri, OWL.sameAs, VIAF[viaf_id_only(viaf)]))

    elif etype == "object":
        g.add((uri, RDF.type, SCHEMA.Product))
        g.add((uri, SCHEMA.name, Literal(name, lang="en")))
        g.add((uri, RDFS.label, Literal(name, lang="en")))
        if wikidata:
            g.add((uri, OWL.sameAs, WD[wikidata]))

    elif etype == "concept":
        g.add((uri, RDF.type, SKOS.Concept))
        g.add((uri, SKOS.prefLabel, Literal(name, lang="en")))
        g.add((uri, RDFS.label, Literal(name, lang="en")))
        if wikidata:
            g.add((uri, SKOS.exactMatch, WD[wikidata]))


def add_game_relations(g: Graph) -> None:
    """Production, characters, subjects: from the game to the entities."""
    game = GOW["god-of-war-2018"]

    g.add((game, SCHEMA.director, GOW["cory-barlog"]))
    g.add((game, DBO.developer, GOW["santa-monica-studio"]))
    g.add((game, DCTERMS.publisher, GOW["sony-ie"]))
    g.add((game, SCHEMA.musicBy, GOW["bear-mccreary"]))
    g.add((game, SCHEMA.gamePlatform, GOW["playstation-4"]))
    g.add((game, SCHEMA.character, GOW["kratos"]))
    g.add((game, SCHEMA.character, GOW["atreus"]))
    g.add((game, DCTERMS.subject, GOW["norse-mythology"]))
    g.add((game, DCTERMS.subject, GOW["greek-mythology"]))


def add_character_relations(g: Graph) -> None:
    """
    In-game and myth-derived family relations. These are the triples that
    expose the fiction↔myth interplay (the standout modelling angle for
    the report).
    """
    # In-game genealogy: Kratos → Atreus
    g.add((GOW["kratos"], SCHEMA.children, GOW["atreus"]))

    # In-game genealogy: Odin & Freyja are Baldur's parents
    # NOTE: Freyja-as-Baldur's-mother is a game-specific reinterpretation
    #       of Norse myth, where Frigg (not Freyja) is Baldur's mother.
    g.add((GOW["odin"], SCHEMA.children, GOW["baldur"]))
    g.add((GOW["freyja"], SCHEMA.children, GOW["baldur"]))

    # Odin → Thor (both game and myth; Thor is Baldur's half-brother)
    g.add((GOW["odin"], SCHEMA.children, GOW["thor"]))

    # Myth-derived: Loki fathers Jörmungandr.
    # Combined with the in-game reveal that Atreus is Loki, and the trio
    # (Kratos, Atreus, Jörmungandr) meeting on the boat, this triple
    # closes the fiction↔myth loop.
    g.add((GOW["loki"], SCHEMA.children, GOW["jormungandr"]))


# =======================================================================
# Main
# =======================================================================

def build_graph(tei_path: str) -> Graph:
    tree = etree.parse(tei_path)
    root = tree.getroot()
    entities = extract_entities(root)

    g = Graph()
    bind_prefixes(g)
    add_ontology_header(g)
    add_game(g)
    for eid, ent in entities.items():
        add_entity_triples(g, eid, ent)
    add_game_relations(g)
    add_character_relations(g)

    return g


def main(input_path: str, output_path: str) -> None:
    g = build_graph(input_path)
    print(f"Graph built: {len(g)} triples across {len(set(g.subjects()))} subjects")
    g.serialize(destination=output_path, format="turtle")
    print(f"Turtle written to: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python tei_to_rdf.py <input.xml> <output.ttl>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
