"""
tei_to_html.py — TEI/XML → HTML transformation for the God of War (2018)
LODLAM project. Reads a TEI file with entities defined in <standOff> and
concepts in <taxonomy>, and produces a self-contained HTML document with:
  - article text, section headings, paragraphs
  - entities colour-highlighted by type (person / org / object / concept / place)
  - hover tooltips showing name + role + Wikidata QID + VIAF (where available)
  - external links to Wikidata on entity click
  - sticky sidebar with table of contents
  - attributed quotes (Barlog, McCreary) visually distinct
  - citation markers as small superscript

Usage:
    python tei_to_html.py <input.xml> <output.html>

Requires: lxml  (pip install lxml)
"""

import sys
from html import escape
from pathlib import Path

from lxml import etree

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"


# =======================================================================
# ID cleaning helpers
# =======================================================================

def clean_id(text: str) -> str:
    """Strip square brackets and whitespace from an authority ID."""
    if text is None:
        return ""
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()
    return text


def wikidata_url(qid: str) -> str:
    """Build a canonical Wikidata URL from a QID."""
    qid = clean_id(qid)
    if qid and qid.startswith("Q"):
        return f"https://www.wikidata.org/wiki/{qid}"
    return ""


def viaf_display(viaf: str) -> str:
    """Return a short human-readable VIAF fragment."""
    viaf = clean_id(viaf)
    if viaf.startswith("http"):
        return viaf.rsplit("/", 1)[-1]
    return viaf


# =======================================================================
# Entity extraction (from <standOff> and <taxonomy>)
# =======================================================================

def _q(tag: str) -> str:
    return f"{{{TEI_NS}}}{tag}"


def _xml_id(el) -> str:
    return el.get(f"{{{XML_NS}}}id", "")


def extract_entities(root) -> dict:
    """
    Walk the standoff and taxonomy sections and return
      { xml_id: {type, name, role, wikidata, viaf} }
    for every defined entity.
    """
    entities = {}

    # Real / fictional / mythological persons
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

    # Organisations
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

    # Physical / cultural objects (e.g. PlayStation 4)
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

    # Concepts (from <taxonomy><category>)
    for cat in root.iter(_q("category")):
        cid = _xml_id(cat)
        if not cid:
            continue
        desc = cat.find(_q("catDesc"))
        # catDesc is like "Norse mythology — description here"; take the head
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
# Tooltip / entity rendering
# =======================================================================

def tooltip_for(entity: dict) -> str:
    """Build a plain-text tooltip string (goes into title="…")."""
    parts = [entity["name"]]
    if entity["role"]:
        parts.append(f"({entity['role'].replace('-', ' ')})")
    tail = []
    if entity["wikidata"]:
        tail.append(f"Wikidata: {entity['wikidata']}")
    if entity["viaf"]:
        tail.append(f"VIAF: {viaf_display(entity['viaf'])}")
    if tail:
        return f"{' '.join(parts)} — {' · '.join(tail)}"
    return " ".join(parts)


def render_entity_span(css_class: str, content: str, ref: str, entities: dict) -> str:
    """
    Wrap `content` in a coloured entity span. If the reference resolves
    to a known entity, add a tooltip and link to Wikidata (if any).
    """
    if ref and ref in entities:
        ent = entities[ref]
        title = escape(tooltip_for(ent))
        wd = wikidata_url(ent["wikidata"])
        if wd:
            return (f'<a class="entity {css_class}" href="{wd}" '
                    f'title="{title}" target="_blank" rel="noopener">{content}</a>')
        return f'<span class="entity {css_class}" title="{title}">{content}</span>'
    return f'<span class="entity {css_class}">{content}</span>'


# =======================================================================
# Recursive TEI element → HTML rendering
# =======================================================================

def render_children(element, entities: dict) -> str:
    """Render an element's mixed content (text + children + tails).
    Skips comments and processing instructions, which have a non-string .tag."""
    out = []
    if element.text:
        out.append(escape(element.text))
    for child in element:
        if isinstance(child.tag, str):
            out.append(render_element(child, entities))
        if child.tail:
            out.append(escape(child.tail))
    return "".join(out)


def render_element(el, entities: dict) -> str:
    tag = etree.QName(el).localname

    # --- structural: div / head / p -----------------------------------
    if tag == "div":
        div_type = el.get("type", "")
        div_id = _xml_id(el)
        css_class = f"tei-div tei-{div_type}" if div_type else "tei-div"
        id_attr = f' id="{div_id}"' if div_id else ""
        return f'<section class="{css_class}"{id_attr}>{render_children(el, entities)}</section>'

    if tag == "head":
        parent = el.getparent()
        parent_type = parent.get("type", "") if parent is not None else ""
        level = "h3" if parent_type == "subsection" else "h2"
        return f"<{level}>{render_children(el, entities)}</{level}>"

    if tag == "p":
        return f"<p>{render_children(el, entities)}</p>"

    # --- entities -----------------------------------------------------
    if tag == "persName":
        ref = el.get("ref", "").lstrip("#")
        return render_entity_span("person", render_children(el, entities), ref, entities)

    if tag == "orgName":
        ref = el.get("ref", "").lstrip("#")
        return render_entity_span("org", render_children(el, entities), ref, entities)

    if tag == "objectName":
        ref = el.get("ref", "").lstrip("#")
        return render_entity_span("object", render_children(el, entities), ref, entities)

    if tag == "rs":
        rs_type = el.get("type", "")
        ref = el.get("ref", "").lstrip("#")
        klass = rs_type if rs_type else "reference"
        return render_entity_span(klass, render_children(el, entities), ref, entities)

    if tag == "placeName":
        place_type = el.get("type", "")
        title = escape(f"{place_type.capitalize()} place") if place_type else "Place"
        return f'<span class="entity place" title="{title}">{render_children(el, entities)}</span>'

    # --- quotes -------------------------------------------------------
    if tag == "quote":
        who = el.get("who", "").lstrip("#")
        inner = render_children(el, entities)
        if who and who in entities:
            speaker = entities[who]["name"]
            return (f'<span class="quote attributed" title="Attributed to {escape(speaker)}">'
                    f'&ldquo;{inner}&rdquo;</span>')
        return f'<span class="quote">&ldquo;{inner}&rdquo;</span>'

    # --- titles (game / album / track names) --------------------------
    if tag == "title":
        rend = el.get("rend", "")
        ref = el.get("ref", "")
        content = render_children(el, entities)
        if rend == "italic":
            inner = f'<cite class="title-italic">{content}</cite>'
        else:
            inner = f'<span class="title-quoted">&ldquo;{content}&rdquo;</span>'
        if ref:
            return (f'<a class="title-link" href="{escape(ref)}" '
                    f'target="_blank" rel="noopener">{inner}</a>')
        return inner

    # --- refs / citations ---------------------------------------------
    if tag == "ref":
        ref_type = el.get("type", "")
        content = render_children(el, entities)
        if ref_type == "citation":
            return f'<sup class="citation">{content}</sup>'
        target = el.get("target", "")
        if target:
            return f'<a href="{escape(target)}" target="_blank" rel="noopener">{content}</a>'
        return content

    if tag == "hi":
        rend = el.get("rend", "")
        content = render_children(el, entities)
        if rend == "italic":
            return f"<em>{content}</em>"
        return content

    # --- unknown tag: emit children, drop wrapper ---------------------
    return render_children(el, entities)


# =======================================================================
# TOC extraction
# =======================================================================

def extract_toc(body):
    """Extract top-level sections (divs directly under <body>) for the nav.
    Skips comments and other non-element nodes."""
    toc = []
    for child in body:
        if not isinstance(child.tag, str):
            continue
        if etree.QName(child).localname != "div":
            continue
        div_id = _xml_id(child)
        div_type = child.get("type", "")
        head = child.find(_q("head"))
        if head is not None and head.text:
            title = head.text
        elif div_type == "introduction":
            title = "Introduction"
        else:
            title = div_id.capitalize() if div_id else "Section"
        toc.append((div_id, title))
    return toc


# =======================================================================
# HTML template + CSS
# =======================================================================

CSS = r"""
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: 'Crimson Pro', Georgia, "Times New Roman", serif;
  color: #1c2530;
  background:
    radial-gradient(ellipse at top, #171e28 0%, #0f131a 62%),
    repeating-linear-gradient(115deg, rgba(255,255,255,0.015) 0px, rgba(255,255,255,0.015) 1px, transparent 1px, transparent 7px);
  background-attachment: fixed;
  line-height: 1.65;
}

.site-header {
  padding: 2rem 3rem 1.2rem;
  background: #1a212b;
  color: #e7ecec;
  border-bottom: 3px solid #4e7f97;
  box-shadow: 0 2px 0 0 #4f7f6b;
}
.site-header h1 {
  margin: 0;
  font-family: 'Cinzel', Georgia, serif;
  font-size: 1.5rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.source-link { margin: 0.6rem 0 0; font-size: 0.85rem; color: #93a3ac; font-family: system-ui, sans-serif; }
.source-link a { color: #7fb8cc; text-decoration: none; border-bottom: 1px dotted #7fb8cc; }

.layout {
  display: grid;
  grid-template-columns: 250px 1fr;
  max-width: 1340px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
  gap: 2.5rem;
}

/* ---- sidebar nav & legend ------------------------------------ */
.toc {
  position: sticky;
  top: 1rem;
  align-self: start;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 0.9rem;
}
.toc h2 {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #57666e;
  margin: 0 0 0.5rem;
  font-weight: 700;
}
.toc ul { list-style: none; padding: 0; margin: 0 0 1.8rem; }
.toc li { margin: 0.15rem 0; }
.toc a {
  color: #1c2530;
  text-decoration: none;
  display: block;
  padding: 0.2rem 0 0.2rem 0.6rem;
  border-left: 2px solid transparent;
  transition: border-color 0.15s, color 0.15s;
}
.toc a:hover { border-left-color: #4e7f97; color: #000; }

.legend { list-style: none; padding: 0; font-size: 0.85rem; }
.legend li { margin: 0.35rem 0; }

/* ---- main content ------------------------------------------- */
.content {
  background: #dee6e6;
  padding: 2.6rem 3.4rem;
  border-radius: 3px;
  box-shadow: 0 12px 28px rgba(0,0,0,0.3), 0 0 0 1px #b7c5c6;
}
.content h2 {
  font-family: 'Cinzel', Georgia, serif;
  font-size: 1.35rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: #22384a;
  border-bottom: 3px solid #4e7f97;
  padding-bottom: 0.35rem;
  margin: 2.4rem 0 1.1rem;
  position: relative;
}
.content h2::after {
  content: "";
  position: absolute;
  left: 0;
  bottom: -6px;
  width: 36px;
  height: 2px;
  background: #a2472f;
}
.content h2:first-child { margin-top: 0; }
.content h3 {
  font-family: 'Cinzel', Georgia, serif;
  font-size: 1.1rem;
  font-weight: 600;
  color: #3d6779;
  margin: 1.8rem 0 0.8rem;
}
.content p { margin: 1rem 0; text-align: justify; hyphens: auto; -webkit-hyphens: auto; }

/* ---- entities: colour by type (cold pigment palette) --------- */
.entity {
  padding: 1px 4px;
  border-radius: 3px;
  text-decoration: none;
  cursor: help;
  transition: filter 0.15s, box-shadow 0.15s;
  color: inherit;
}
.entity:hover {
  filter: brightness(0.94);
  box-shadow: 0 1px 0 rgba(0,0,0,0.15);
}

.entity.person  { background: #d2e0e6; color: #1f4a5c; border-bottom: 1px dotted #1f4a5c; }
.entity.org     { background: #e2dcc4; color: #5a5023; border-bottom: 1px dotted #5a5023; }
.entity.object  { background: #d7dbe1; color: #37414d; border-bottom: 1px dotted #37414d; }
.entity.concept { background: #d1e2d7; color: #29563f; border-bottom: 1px dotted #29563f; }
.entity.place   { background: #e3d6cc; color: #5f4432; border-bottom: 1px dotted #5f4432; font-style: italic; }

/* ---- quotes ------------------------------------------------ */
.quote { font-style: italic; color: #33404a; }
.quote.attributed {
  background: #dbe8ec;
  padding: 1px 5px;
  border-left: 3px solid #4e7f97;
  border-radius: 0 2px 2px 0;
  cursor: help;
}

/* ---- citations -------------------------------------------- */
.citation {
  font-size: 0.72em;
  color: #8a97a0;
  margin-left: 1px;
  font-family: system-ui, sans-serif;
}

/* ---- titles ---------------------------------------------- */
.title-italic { font-style: italic; color: #33404a; }
.title-quoted { color: #33404a; }
.title-link { color: inherit; text-decoration: none; border-bottom: 1px dashed #8a97a0; }
.title-link:hover { border-bottom-style: solid; }

/* ---- footer ---------------------------------------------- */
footer {
  text-align: center;
  padding: 2rem 1rem;
  font-family: system-ui, sans-serif;
  font-size: 0.85rem;
  color: #93a3ac;
  background: #1a212b;
  border-top: 3px solid #4e7f97;
  margin-top: 1rem;
}

@media (max-width: 800px) {
  .layout { grid-template-columns: 1fr; padding: 1rem; }
  .toc { position: static; }
  .content { padding: 1.5rem; }
  .site-header { padding: 1.5rem; }
}
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{page_title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;600;700&family=Crimson+Pro:ital,wght@0,400;0,500;0,600;1,400&display=swap" rel="stylesheet">
<style>
{css}
</style>
</head>
<body>
<header class="site-header">
  <h1>{page_title}</h1>
  <p class="source-link">Source: <a href="{source_url}" target="_blank" rel="noopener">Wikipedia (permanent version, {source_date})</a></p>
</header>

<div class="layout">
  <nav class="toc">
    <h2>Contents</h2>
    <ul>
      {toc_items}
    </ul>
    <h2>Entity types</h2>
    <ul class="legend">
      <li><span class="entity person">Person</span></li>
      <li><span class="entity org">Organisation</span></li>
      <li><span class="entity object">Object</span></li>
      <li><span class="entity concept">Concept</span></li>
      <li><span class="entity place">Mythical place</span></li>
    </ul>
  </nav>

  <main class="content">
    {body}
  </main>
</div>

<footer>
  <p>TEI encoding for the LODLAM project — Information Science and Cultural Heritage,
     University of Bologna, a.y. 2025-2026.</p>
</footer>
</body>
</html>
"""


# =======================================================================
# Main
# =======================================================================

def main(input_path: str, output_path: str) -> None:
    tree = etree.parse(input_path)
    root = tree.getroot()

    # entities from standoff + taxonomy
    entities = extract_entities(root)
    print(f"Extracted {len(entities)} entities:")
    for eid, ent in entities.items():
        print(f"  #{eid:22s} {ent['type']:8s} {ent['name']}  (Wikidata: {ent['wikidata'] or '-'})")

    # metadata for template
    title_el = root.find(f"{_q('teiHeader')}//{_q('titleStmt')}/{_q('title')}")
    page_title = title_el.text if title_el is not None else "TEI Document"

    source_ref = root.find(f"{_q('teiHeader')}//{_q('sourceDesc')}//{_q('ref')}")
    source_url = source_ref.get("target") if source_ref is not None else ""
    source_date_el = root.find(f"{_q('teiHeader')}//{_q('sourceDesc')}//{_q('date')}")
    source_date = source_date_el.text if source_date_el is not None else ""

    # body
    body = root.find(f"{_q('text')}/{_q('body')}")
    if body is None:
        raise RuntimeError("No <body> in the TEI document.")

    # TOC + rendered body
    toc = extract_toc(body)
    toc_items = "\n      ".join(
        f'<li><a href="#{tid}">{escape(ttitle)}</a></li>' for tid, ttitle in toc
    )
    body_html = render_children(body, entities)

    html = HTML_TEMPLATE.format(
        page_title=escape(page_title),
        source_url=escape(source_url),
        source_date=escape(source_date),
        toc_items=toc_items,
        body=body_html,
        css=CSS,
    )

    Path(output_path).write_text(html, encoding="utf-8")
    print(f"\nHTML written to: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python tei_to_html.py <input.xml> <output.html>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
