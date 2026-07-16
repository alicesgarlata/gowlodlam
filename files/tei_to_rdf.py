import sys

from lxml import etree
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD, DCTERMS, SKOS, FOAF

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"

GOW = Namespace(
    "https://alicesgarlata.github.io/gowlodlam/html-rendering.html#"
)
ONTOLOGY = URIRef("https://alicesgarlata.github.io/gowlodlam/")

WD = Namespace("http://www.wikidata.org/entity/")
VIAF = Namespace("http://viaf.org/viaf/")
SCHEMA = Namespace("https://schema.org/")
DBO = Namespace("http://dbpedia.org/ontology/")



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
        for idno in obj.findall(f".//{_q('idno')}"):
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


def extract_game(root) -> dict:
    """Read the central video-game resource from the TEI standOff."""
    for bibl in root.iter(_q("bibl")):
        game_id = _xml_id(bibl)
        if not game_id or bibl.get("type") != "video-game":
            continue

        title_el = bibl.find(_q("title"))
        date_el = bibl.find(_q("date"))
        wikidata = ""
        for idno in bibl.findall(_q("idno")):
            if idno.get("type") == "Wikidata":
                wikidata = clean_id(idno.text)

        if title_el is None or not (title_el.text or "").strip():
            raise ValueError(f"Video game #{game_id} has no TEI title")
        if date_el is None or not date_el.get("when"):
            raise ValueError(f"Video game #{game_id} has no machine-readable TEI date")

        return {
            "id": game_id,
            "title": title_el.text.strip(),
            "date": date_el.get("when"),
            "wikidata": wikidata,
        }

    raise ValueError(
        "No <bibl xml:id='...' type='video-game'> resource found in TEI standOff"
    )



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
    ont = ONTOLOGY
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


def add_game(g: Graph, game_data: dict) -> None:
    """Emit the central game from metadata extracted from the TEI."""
    game = GOW[game_data["id"]]
    title = game_data["title"]
    g.add((game, RDF.type, SCHEMA.VideoGame))
    g.add((game, RDFS.label, Literal(title, lang="en")))
    g.add((game, DCTERMS.title, Literal(title, lang="en")))
    g.add((game, DCTERMS.date,
           Literal(game_data["date"], datatype=XSD.date)))
    if game_data["wikidata"]:
        g.add((game, OWL.sameAs, WD[game_data["wikidata"]]))


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
            g.add((uri, RDF.type, DBO.FictionalCharacter))
            if wikidata:
                g.add((uri, GOW["reinterprets"], WD[wikidata]))

        else:
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


def _resolve_relation_pointer(pointer: str, local_ids: set[str]) -> URIRef:
    """Resolve a TEI pointer to either a local project URI or an absolute URI."""
    pointer = pointer.strip()
    if pointer.startswith("#"):
        local_id = pointer[1:]
        if local_id not in local_ids:
            raise ValueError(f"TEI relation points to undefined local ID: {pointer}")
        return GOW[local_id]
    if pointer.startswith(("http://", "https://")):
        return URIRef(pointer)
    raise ValueError(
        f"Unsupported TEI relation pointer {pointer!r}; use #xml-id or an absolute URI"
    )


def add_relations_from_tei(g: Graph, root, local_ids: set[str]) -> int:
    """
    Materialise every TEI <relation> as RDF.

    For a directed relation, @active is the RDF subject, @ref is the
    predicate URI, and @passive is the object. Space-separated values are
    expanded as a Cartesian product. @mutual is also supported and produces
    both directions for every pair of distinct participants.
    """
    added = 0

    for relation in root.iter(_q("relation")):
        predicate_ref = clean_id(relation.get("ref", ""))
        if not predicate_ref.startswith(("http://", "https://")):
            relation_name = relation.get("name", "unnamed")
            raise ValueError(
                f"TEI relation {relation_name!r} needs an absolute predicate URI in @ref"
            )
        predicate = URIRef(predicate_ref)

        active = relation.get("active", "").split()
        passive = relation.get("passive", "").split()
        mutual = relation.get("mutual", "").split()

        if active and mutual:
            raise ValueError("A TEI relation cannot have both @active and @mutual")
        if passive and not active:
            raise ValueError("A TEI relation with @passive must also have @active")

        triples = []
        if mutual:
            participants = [
                _resolve_relation_pointer(pointer, local_ids)
                for pointer in mutual
            ]
            triples = [
                (subject, predicate, obj)
                for subject in participants
                for obj in participants
                if subject != obj
            ]
        elif active and passive:
            subjects = [
                _resolve_relation_pointer(pointer, local_ids)
                for pointer in active
            ]
            objects = [
                _resolve_relation_pointer(pointer, local_ids)
                for pointer in passive
            ]
            triples = [
                (subject, predicate, obj)
                for subject in subjects
                for obj in objects
            ]
        else:
            raise ValueError(
                "A directed TEI relation needs both @active and @passive, "
                "or it must use @mutual"
            )

        for triple in triples:
            before = len(g)
            g.add(triple)
            added += len(g) - before

    return added



def build_graph(tei_path: str) -> Graph:
    tree = etree.parse(tei_path)
    root = tree.getroot()
    entities = extract_entities(root)
    game_data = extract_game(root)
    local_ids = set(entities) | {game_data["id"]}

    g = Graph()
    bind_prefixes(g)
    add_ontology_header(g)
    add_game(g, game_data)
    for eid, ent in entities.items():
        add_entity_triples(g, eid, ent)
    add_relations_from_tei(g, root, local_ids)

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
