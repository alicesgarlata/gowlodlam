# God of War (2018): a Linked Open Data model

This repository contains an individual project for the **Information Science and Cultural Heritage** course in the Digital Humanities and Digital Knowledge MA at the University of Bologna (a.y. 2025–2026).

The project starts from the Wikipedia article on *God of War* (2018) and develops it through a three-phase LODLAM workflow: knowledge organisation and TEI/XML encoding, conceptual modelling, and RDF knowledge representation. Its central modelling question is how a video game character relates to the mythological figure it reworks. The coined property `gow:reinterprets`, defined as a subproperty of `dcterms:relation`, keeps this relation distinct from identity links such as `owl:sameAs`.

## Live website

[Explore the project website](https://alicesgarlata.github.io/gowlodlam/)

## Project contents

- `files/entita_god_of_war.csv` — initial inventory of the central work and the 15 selected entities, with their authority identifiers
- `assets/mind-map.png` — theoretical model developed during the knowledge-organisation phase
- `files/tei.xml` — TEI P5 encoding of the source article, including standoff entity definitions and authority reconciliation
- `files/tei_to_html.py` — Python transformation from TEI/XML to the interactive HTML article
- `files/index.html` — generated HTML output
- `files/build_entity_data.py` — generator for the browser-based entity explorer
- `files/entities.json` — generated entity metadata, TEI mention counts, and related RDF statements
- `js/entity-explorer.js` — filters entities, displays their data, and highlights their mentions in the article
- `assets/graffoo.png` — Graffoo conceptual model
- `files/tei_to_rdf.py` — Python transformation from TEI/XML to RDF
- `files/gow.ttl` — generated Turtle graph (104 triples across 18 subjects)
- `assets/rdf-graph.svg` — complete visualisation of the RDF graph

The root-level HTML, CSS, and JavaScript files form the explanatory project website published through GitHub Pages.

## Reproducing the transformations

Python 3.10 or later is recommended. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python files/tei_to_html.py files/tei.xml files/index.html
python files/tei_to_rdf.py files/tei.xml files/gow.ttl
python files/build_entity_data.py files/tei.xml files/gow.ttl files/entities.json
```

The RDF script reports the number of triples and subjects produced. The generated Turtle can be checked by reparsing it with RDFLib; this verifies that the serialisation is syntactically readable, but it is not a substitute for semantic or SHACL validation. The final command combines entity metadata from the TEI with the RDF statements in which each entity appears as subject or object, keeping the website's Entity Explorer aligned with both sources.

## Modelling choices

Real people and organisations are reconciled with external authority records using `owl:sameAs`; subject concepts use `skos:exactMatch`. Mythological figures are linked through `gow:reinterprets` because the in-game characters are adaptations of, rather than identical to, their mythological counterparts.

Local resources use dereferenceable hash URIs in the Entity Explorer namespace (for example, `https://alicesgarlata.github.io/gowlodlam/html-rendering.html#kratos`). Opening one of these identifiers loads the public project page and automatically selects the corresponding entity.

Attributed direct speech is encoded with TEI `<said who="#…">`, while unattributed quoted material uses `<quote>`. The HTML transformation preserves this distinction through different visual treatments and attribution tooltips.

## Sources and credits

The textual source is a fixed revision of the English Wikipedia article [*God of War* (2018 video game)](https://en.wikipedia.org/w/index.php?title=God_of_War_(2018_video_game)&oldid=1357494264), consulted on 3 July 2026. Authority reconciliation uses Wikidata and, where applicable, VIAF.

Project code, original data, and documentation are released under CC BY-SA 4.0. Third-party images and source material remain subject to their original licences or rights; detailed credits are listed on the website's [Resources page](https://alicesgarlata.github.io/gowlodlam/resources.html).
