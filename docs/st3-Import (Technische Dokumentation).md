# st3-Import – Technische Dokumentation

**Version:** 1.0.0 
**Autor:** Fabian Schöpflin  
**Datum:** 24. Mai 2026

## Übersicht

Dieses Dokument beschreibt das **Zusi-3-Streckendateiformat** (`.st3`) und das daraus
abzuleitende **Knoten-Kanten-Modell**.

Zusi 3 speichert Streckennetze als XML-Dateien mit geometrischen und topologischen
Informationen. Ziel ist es, diese in zwei Datensätze:

| Layer | Geometrietyp | Inhalt |
|---|---|---|
| `Gleiskante` | LineString | Gleisabschnitte zwischen Knoten |
| `Gleisknoten` | Point | Weichen, Modulgrenzen, Gleisenden |
| `Hüllkurve` ¹ | Polygon | Umgrenzungspolygon des Streckenmoduls (Geländeformer) |

¹ Optional; nur wenn **Hüllkurve importieren** aktiviert ist.

---

## Zielstruktur: Knoten-Kanten-Modell

Die `st3`-Datei enthält Streckenelemente mit kontinuierlicher Geometrie. Das Zielmodell
abstrahiert diese in eine Gleistopologie aus Knoten und Kanten:

```
Gleisgeometrie (StrElemente in der .st3):

  ·─[1]─·─[2]─·─[3]─·─[4]─·─[5]─·─[6]─·─[7]─·─[8]─·
         Gerade        Bogen         Gerade      Bogen
                   ·─────────────────────────·
                          Gerade (Ast)

  (jeder Punkt = g- oder b-Koordinate eines StrElements)


Gleistopologie (Knoten-Kanten-Modell):

  ──◉──────────────────◉═══════════════════◉────────◉──
    W21    Kante 1     W22    Kante 2      W23      P45
                        ╚═══ Kante 3 ═══╝
                         (Parallelgleis)

  Legende:  ◉ = Gleisknoten   ─── / ═══ = Gleiskante (LineString)
```

*Abb.: Beziehung zwischen Gleisgeometrie und Gleistopologie.
Mehrere StrElemente zwischen zwei Gleisknoten bilden eine Gleiskante.
Parallelgleise zwischen denselben Knoten werden als separate LineString-Features geführt.*

### Gleisknoten

Gleisknoten werden **primär aus der Koordinatentopologie und den Modulverweisen**
abgeleitet. Jedes StrElement hat zwingend eine Länge – `g`- und `b`-Koordinate sind
nie identisch (Eingangsvalidierung; Elemente mit identischen Endpunkten werden mit
Warnung übersprungen). In den Koordinatengraph gehen ausschließlich die **Endpoints**
(`g` und `b`) ein; ein Knotenpunkt liegt daher immer an einem Endpoint, nie in der
Mitte eines Elements.

Zwei Elemente sind topologisch verbunden, wenn sie eine Koordinate teilen (innerhalb
einer Fangtoleranz). Der **Vertex-Grad** – die Anzahl der an einem Punkt treffenden
Elementenden – bestimmt den Knotentyp. Modulgrenz-Vertices werden unabhängig vom
Vertex-Grad explizit aus `<NachNormModul>`/`<NachGegenModul>`-Einträgen registriert
(ein Modulgrenz-Vertex hat typischerweise Grad 1, kann an Streckenenden mit Modul-
Anschluss aber auch Grad 2 aufweisen und wäre dann koordinatentopologisch nicht
erkennbar):

| Vertex-Grad | Knotentyp | Beispiele |
|---|---|---|
| beliebig + `NachNormModul`/`NachGegenModul` am betroffenen Element | `Modulgrenze` | `Freudenstein_96G` |
| 1 (kein Modulverweis) | `Gleisende` | `Freudenstein_12E` |
| 3 | `Weiche` (Weichenspitze EW, EKW-Arm, DKW-Arm …) | W21 |
| 4 | `Weiche` (Kreuzungspunkt KR, EKW-Zentrum, DKW-Herzstück …) | K47 |
| ≥ 5 | `Weiche` (seltener Sonderfall – Warnung wird geloggt) | – |

Tritt ein Modulverweis und Grad ≥ 3 am selben Vertex auf (Modulgrenze an einer
Weichenspitze), werden **beide Knoten angelegt**: ein `Modulgrenze`-Knoten und ein
`Weiche`-Knoten mit identischer Koordinate. Beide sind im Knoten-Layer attributiv
unterscheidbar (`typ`, `knotenname`). Mehrere Knoten an identischen Koordinaten sind
in der Spezifikation explizit erlaubt.

Komplexe Gleisanlagen (DKW, EKW, DGV, …) werden nicht als Ganzes erkannt, sondern
zerfallen natürlich in ihre topologischen Bestandteile: jede Weichenspitze (Grad 3)
und jedes Herzstück oder jede Kreuzung (Grad 4) wird ein eigener Knoten, verbunden
durch kurze Kanten. Nicht alle Grad-3-Vertices gehen auf ein Fkt=4-Element zurück –
bei komplexen Weichen entstehen weitere Verzweigungspunkte aus anderen
Weichenbausatz-Elementen (z. B. Fkt=12, 20, 28). Ein Fkt=4-Element ist daher
*keine* notwendige Bedingung für einen Weichenknoten; maßgeblich ist ausschließlich
der Vertex-Grad.

Signal-Elemente in der `.st3` dienen ausschließlich der **Benennung**: liegt an einem
Grad-≥-3-Vertex ein Signal mit `SignalTyp 2`, werden `Signalname` und die Weichenbauart aus dem SignalFrame-Dateinamen
(Präfix vor `_Schienen`, → `knotenbeschr`) als Attribute übernommen. Die Erkennung selbst ist davon
unabhängig.

#### Richtungskonvention bei Modulgrenze und Gleisende

- `NachNormModul` am Element → Modulgrenze am **b**-Vertex des Elements
- `NachGegenModul` am Element → Modulgrenze am **g**-Vertex des Elements
- Kein Modulverweis, Grad 1 → Gleisende am einzigen Endpoint des Elements

#### Richtungskonvention bei Weichen

Im Zusi 3D-Editor wird jedes StrElement mit zwei Richtungspfeilen dargestellt:
ein **grüner Pfeil** am g-Ende (Gegenrichtung) und ein **blauer Pfeil** am b-Ende
(Normrichtung), jeweils vom Element wegzeigend. An einer Weiche zeigt der grüne
Pfeil des Weichenkörperelements in das freie Zufahrtsgleis – der g-Vertex ist also
stets der **äußere, eingleisige Zufahrtspunkt** (Weichenspitze).

Das **erste StrElement einer Weiche** (Weichenkörper) hat eine weichentyp-abhängige
Länge (typisch 1,2000 m bis 1,8000 m, je nach Bauart). Sein g-Vertex ist die
Weichenspitze (Grad 2, Durchgang); sein b-Vertex ist der Verzweigungspunkt, an dem
die Äste abgehen (Grad ≥ 3).

Der Gleisknoten (Typ `Weiche`) wird am **b-Vertex** des Weichenkörpers gesetzt.
Das ist der einzig korrekte Ort: würde man den Knoten stattdessen am g-Vertex
(der Weichenspitze) setzen, entstünde zwangsläufig eine eigenständige Kante
vom g- zum b-Vertex und ein zusätzlicher, namenloser Knoten am b-Vertex – die
Kanten wären zwar geometrisch vorhanden, aber nicht mehr sauber zusammengefasst
und enthielten eine unerwünschte Fehlstelle im Modell. Durch die Wahl des b-Vertex
als Knotenposition wird der Weichenkörper stattdessen lückenlos in die Zulaufkante
aufgenommen.

### Gleiskanten und Kantenaufteilung

Eine Gleiskante ist eine ununterbrochene Kette von StrElementen zwischen zwei
Gleisknoten. **An jedem Gleisknoten werden die Kanten aufgebrochen** – d. h. jede
einlaufende und jede auslaufende Kante endet bzw. beginnt exakt an der
Knotenkoordinate. Kanten werden durch **Traversierung des Koordinatengraphen** gebildet:

1. Alle Vertices mit Grad ≠ 2 sowie Modulgrenz-Vertices sind **Breakpoints**.
2. Von jedem Breakpoint wird für jede anliegende Kante ein Walk gestartet (sofern das
   Element noch nicht besucht ist). Der Walk folgt dem Graphen über Grad-2-Vertices,
   bis der nächste Breakpoint erreicht ist.
3. Die dabei gesammelten StrElement-Koordinaten bilden den Linienzug der Kante.
   `knotenname_von` und `knotenname_bis` werden aus den Breakpoint-Namen belegt.

Da der Weichenknoten am b-Vertex liegt, ist die Aufteilung eindeutig und lückenlos
(Beispiel Freudenstein W73: StrElement 96.b = 97.g = 106.g = Koordinate P):

```
      g──[96, 1,2306 m]──b=P        ← Weichenkörper endet bei P
                       g=P──[97]──b──···   ← Arm 1 beginnt bei P
                       g=P──[106]──b──···  ← Arm 2 beginnt bei P

  Kante A:  PrevKnoten ···─[96]─ P         knotenname_von=… knotenname_bis=W73
  Kante B:  P ─[97]─··· NextKnotenA        knotenname_von=W73 knotenname_bis=…
  Kante C:  P ─[106]─·· NextKnotenB        knotenname_von=W73 knotenname_bis=…
```

Element 96 (der 1,2306 m-Weichenkörper) liegt ausschließlich in Kante A – keine
Überlappung, kein Versatz, lückenloser geometrischer Anschluss aller drei Kanten
am gemeinsamen Punkt P. Jede Kante ist ein vollständiges LineString-Feature mit
gesetzten `knotenname_von`/`knotenname_bis`.

Verlaufen mehrere Gleise zwischen denselben zwei Knoten (Parallelgleise), entsteht
für jedes Parallelgleis ein **eigenes LineString-Feature** mit unabhängig gesetzten
Attributen (`km_von`, `km_bis`, `strelement_von`, `strelement_bis`). Mehrere Kanten
zwischen demselben Knotenpaar sind ausdrücklich erlaubt und über `strelement_von`
eindeutig unterscheidbar.

#### Sonderfall: geschlossene Schleifen

Verläuft ein Gleisabschnitt ringförmig ohne jeden Breakpoint (alle Vertices Grad 2,
keine Modulgrenze), wird ein beliebiger Startpunkt gewählt. `knotenname_von` und
`knotenname_bis` bleiben `NULL`. Eine geschlossene Schleife ist physisch selten und
in der Praxis häufig ein Hinweis auf einen Modellierungsfehler; der Algorithmus
loggt sie daher als Warnung mit Elementanzahl und geografischer Ausdehnung.

### Verknüpfung zwischen den Layern

Kanten und Knoten teilen einen gemeinsamen **Namensschlüssel**:

| Kanten-Layer | Knoten-Layer |
|---|---|
| `knotenname_von` | `knotenname` |
| `knotenname_bis` | `knotenname` |
| `bst_von` | `bst_name` |
| `bst_bis` | `bst_name` |

`knotenname_von`/`knotenname_bis` können `NULL` sein, wenn am Endpunkt kein
benannter Knoten liegt. `bst_von`/`bst_bis` sind nur gefüllt, wenn der jeweilige
Endknoten ein Weichenknoten mit gesetztem `NameBetriebsstelle`-Attribut ist.

---

## Algorithmus zur Graphenextraktion

### Schritt 1 – XML einlesen und StrElemente sammeln

Aus dem `<UTM>`-Element werden Referenzkoordinaten ausgelesen
(`UTM_WE` und `UTM_NS` in km, `UTM_Zone` → Quell-EPSG = 32600 + Zone).

Für jedes `<StrElement>` mit **Bit 1 = 0** (`Fkt & 2 == 0`, d. h. ohne „Keine Gleisfunktion"-Flag)
werden erfasst:

- Absolute Koordinaten: `abs_g = (UTM_WE·1000 + X_g, UTM_NS·1000 + Y_g)` (analog für b)
- Kilometrierung aus `<InfoGegenRichtung km="…">` (Fallback: `<InfoNormRichtung>`)
- `<Signal>`-Kindelemente mit `SignalTyp`, `Signalname`, `BoundingR`; erfasst als direkte Kindelemente des `<StrElement>` sowie innerhalb von `<InfoGegenRichtung>` und `<InfoNormRichtung>`
- `<NachNorm Nr="…">` / `<NachGegen Nr="…">` – Nachfolger-Nummern im selben Modul
- `<NachNormModul>` / `<NachGegenModul>` mit dem Dateinamen der Nachbarmodul-Datei
- `Anschluss`-Attribut als Integer (fehlendes Attribut = 0)

### Schritt 2 – Element-Seiten-Topologie aufbauen

Aus den `<NachNorm>`-/`<NachGegen>`-Verweisen und dem `Anschluss`-Bitfeld wird die
Topologie als **Union-Find auf Element-Seiten** aufgebaut. Jedes StrElement besitzt
eine g-Seite (Gegenrichtungs-Endpunkt) und eine b-Seite (Normrichtungs-Endpunkt).

**Verbindungsregeln:**

| Verweis an E | Verbindet | Nachfolger-Seite |
|---|---|---|
| `<NachNorm Nr="i">` | E.**b** ↔ i.? | `g` wenn `Anschluss`-Bit = 0, sonst `b` |
| `<NachGegen Nr="j">` | E.**g** ↔ j.? | `g` wenn `Anschluss`-Bit = 0, sonst `b` |

Das zugehörige Anschluss-Bit ergibt sich für den i-ten Norm-Nachfolger aus Bit `i`
und für den j-ten Gegen-Nachfolger aus Bit `8+j` (0-indiziert, siehe
[`Anschluss`-Attribut](#anschluss-attribut-des-strelement-knotens)):

```python
def successor_side(connection: int, idx: int, direction: str) -> str:
    """'g' oder 'b' — Seite des idx-ten Nachfolgers, die an E anschließt."""
    shift = idx + (8 if direction == "GEGEN" else 0)
    return "b" if (connection >> shift) & 1 else "g"
```

**Union-Find-Schritt:**

```
Für jedes Element E:
  für i, N_i in enumerate(NachNorm-Nachfolger von E):
      union((E, "b"), (N_i, successor_side(Anschluss_E, i, "NORM")))
  für j, G_j in enumerate(NachGegen-Nachfolger von E):
      union((E, "g"), (G_j, successor_side(Anschluss_E, j, "GEGEN")))
```

Jede resultierende Äquivalenzklasse ist ein **Vertex**. Für jeden Vertex wird eine
Inzidenzliste geführt:

```
vertex_inc[vertex_id] → [(elem_nr, seite), …]   # seite ∈ {"g", "b"}
```

Der **Grad** eines Vertex ist `len(vertex_inc[vertex_id])`.

Koordinaten werden **nicht** zur Topologiebestimmung herangezogen; sie dienen
ausschließlich der geometrischen Darstellung (Schritt 7) und dem Cross-Check in
Schritt 5. Floating-Point-Artefakte können die Topologie daher nicht verfälschen.

### Schritt 3 – Modulgrenz-Vertices registrieren

Für jedes StrElement mit `<NachNormModul>` → b-Vertex ist eine Modulgrenze.
Für jedes StrElement mit `<NachGegenModul>` → g-Vertex ist eine Modulgrenze.

Modulgrenz-Vertices werden separat notiert; ihr Typ ist `Modulgrenze` unabhängig
vom Vertex-Grad (der in der Regel 1 ist, an Streckenenden mit Modul-Anschluss aber
auch 2 sein kann).

### Schritt 4 – Breakpoints klassifizieren

Ein Vertex ist ein **Breakpoint**, wenn:

| Bedingung | Knotentyp |
|---|---|
| Grad = 1, kein Modulverweis | `Gleisende` |
| Modulverweis vorhanden (beliebiger Grad) | `Modulgrenze` |
| Grad ≥ 3 | `Weiche` (Weichenspitze, Herzstück oder Kreuzungspunkt) |

Signal-Attribute (`Signalname` sowie Weichenbauart aus dem SignalFrame-Dateinamen → `knotenbeschr`)
werden dem Knoten angehängt, wenn ein angrenzendes StrElement ein Signal mit `SignalTyp="2"` trägt.

#### Namen von Weichenknoten normalisieren

Signalnamen von Weichenknoten (Typ `Weiche`) werden vor dem Speichern normalisiert:

- Eine optionale numerische **ESTW-Bereichskennziffer** vor dem W-Typ-Präfix
  (z. B. `44` in `44W1`) wird ignoriert.
- Buchstaben-Präfixe wie `W`, `EW`, `DKW` werden entfernt.
- Eine optionale DKW-Kennung (`a`, `b`, `c`, `d`, `a/b`, `c/d`) direkt nach der Zahl
  wird in Großbuchstaben übernommen.
- Kein Match → Signalname wird unverändert übernommen.

Das Normalisieren ist standardmäßig aktiv und kann im Einstellungsmenü
(Option **4. Namen von Weichenknoten normalisieren**) oder
im CLI per `--no-normalize-switches` deaktiviert werden.

| Eingangsname | Normalisierter `knotenname` | Anmerkung |
|---|---|---|
| `W 1` | `1` | |
| `EW 135` | `135` | |
| `DKW 3 A` | `3A` | |
| `DKW 3 a/b` | `3A/B` | |
| `DKW 3 c/d` | `3C/D` | |
| `44W1` | `1` | ESTW: Bereichskennziffer wird ignoriert |
| `44EW135` | `135` | ESTW: Bereichskennziffer wird ignoriert |
| `44DKW3A` | `3A` | ESTW: Bereichskennziffer wird ignoriert |

Modulgrenz- und Gleisende-Knoten werden **nicht** normalisiert; dort wird der Signalname
direkt übernommen (in der Praxis tragen diese Knotentypen selten ein Signal vom Typ 2).

#### Nachbeschriftung (knotenbeschr-Propagierung)

Bei komplexen Weichenanlagen (EKW, DKW) trägt das Weichensignal häufig nur an einem
der Weichenknoten eine `BoundingR`-Angabe (Bounding-Radius des SignalFrames im `.ls3`-Koordinatensystem).
Alle Weichenknoten ohne `knotenbeschr`, deren UTM-Koordinate innerhalb dieses Radius' um
den beschrifteten Knoten liegt, erhalten dieselbe `knotenbeschr`-Beschriftung.

Diese Propagierung erfolgt noch vor Schritt 5, auf UTM-Koordinaten (vor der KBS-Transformation).

### Schritt 5 – Topologie-Validierung

Vor der Traversierung werden folgende Konsistenzprüfungen durchgeführt; Abweichungen
werden als Warnung geloggt und beeinflussen den Import nicht:

| Prüfung | Bedingung | Aktion |
|---|---|---|
| Nulllängen-Element | g-Koordinate == b-Koordinate | Warnung, Element wird übersprungen |
| Hochgradiger Vertex | Grad ≥ 5 | Warnung mit Vertex-Position und Grad |
| Isolierte Komponente | Zusammenhangskomponente ohne jeglichen Breakpoint (kein Vertex mit Grad 1, Grad ≥ 3 oder Modulverweis) | Warnung (möglicher Modellierungsfehler) |
| Koordinaten-Abweichung | Koordinaten zweier per `NachNorm`/`NachGegen` verbundener Element-Seiten liegen > 5 cm auseinander | Warnung (Datenfehler im .st3) |

Die vierte Prüfung ist der Cross-Check zwischen der topologischen Verbindung aus
Schritt 2 und der geometrischen Übereinstimmung aus den `<g>`/`<b>`-Koordinaten.

### Schritt 6 – Graphtraversierung: Kanten bilden

Von jedem Breakpoint B aus wird für jede anliegende Kante ein **Walk** gestartet,
sofern das Element noch nicht besucht ist:

```
Walk(B, elem, entry_side):
    pts ← [B]
    loop:
        exit_vertex ← die andere Seite von elem (b wenn entry=g, g wenn entry=b)
        markiere elem als besucht
        pts.append(exit_vertex)
        if exit_vertex ist Breakpoint: STOP
        elem ← das an exit_vertex anliegende andere Element (Grad = 2)
    return Kette(pts, knotenname_von=name(B), knotenname_bis=name(exit_vertex))
```

Jedes StrElement wird genau einmal besucht → keine Überlappungen, keine Lücken.

#### Kilometrierung der Kanten

Nach der Traversierung werden `km_von` und `km_bis` jeder Kante durch lineare Interpolation
(bzw. Extrapolation) aus den bekannten `km`-Werten der enthaltenen StrElemente ermittelt.
Gewichtet wird nach der kumulativen Bogenlänge entlang der Kette:

1. Die Bogenlänge (Euklidischer Abstand) zwischen den Eintrittspunkten der StrElemente
   wird kumuliert.
2. Die bekannten `(Bogenlänge, km)`-Paare bilden Stützstellen für die lineare Interpolation.
3. `km_von` wird aus dem ersten StrElement übernommen (oder linear extrapoliert); `km_bis`
   analog aus dem letzten.
4. Sind keinerlei `km`-Werte vorhanden, bleiben `km_von` und `km_bis` `NULL`.

#### Kilometrierung der Knoten

Nach Abschluss der Traversierung werden fehlende `km`-Werte an Gleisknoten aus den
`km_von`/`km_bis`-Werten der anliegenden Kanten ergänzt: der erste nicht-`NULL`-Wert
einer anliegenden Kante wird übernommen (bestehende Werte werden nicht überschrieben).

### Schritt 7 – Koordinatentransformation

Alle gesammelten Vertex-Koordinaten (UTM WGS84, Zone aus `<UTM>`) werden in einem
einzigen Bulk-Aufruf in die Ziel-CRS transformiert (Standard: EPSG 31467,
DHDN/Gauß-Krüger Zone 3).

### Schritt 8 – Layer-Ausgabe

`st3Converter.convert()` gibt zwei Listen von Feature-Dicts zurück:

```python
nodes_features, edges_features = converter.convert()
# nodes_features: [{"geometry": (x, y), "attrs": {...}}, …]
# edges_features: [{"geometry": [(x1,y1),(x2,y2),…], "attrs": {...}}, …]
```

- **`edges_features`**: ein Eintrag pro Gleiskante; `geometry` ist eine Liste von `(x, y)`-Tupeln;
  Attribute gemäß [Zielattribute – Kanten-Layer](#kanten-layer-linestring)
- **`nodes_features`**: ein Eintrag pro Gleisknoten; `geometry` ist ein `(x, y)`-Tupel;
  Attribute gemäß [Zielattribute – Knoten-Layer](#knoten-layer-point)

Die Weiterverarbeitung der Feature-Dicts ist aufruferabhängig:

| Kontext | Ausgabe |
|---|---|
| Python-Bibliothek (`st3Converter.convert()`) | Gibt `(nodes_features, edges_features)` zurück — Feature-Listen ohne GeoPackage-Schreibzugriff |
| CLI (`core/cli.py`) | GeoPackage mit Layern `Gleiskante` / `Gleisknoten` / optional `Hüllkurve` (via `geopandas`/`shapely`) |

## Hüllkurven-Import

### Fachliche Bedeutung

Neben dem Gleistopologie-Algorithmus (Schritte 1–8) kann aus jeder `.st3`-Datei
optional ein **Umgrenzungspolygon** (Hüllkurve) importiert werden. Die Hüllkurve
beschreibt den geografischen Geltungsbereich des Streckenmoduls für den sog.
**Geländeformer** in Zusi 3 — sie umreißt das Gebiet, für das das Modul
Höhenformationen und Geländestrukturen definiert. Sie ist ein einfaches Polygon
ohne feste Punktanzahl.

### XML-Struktur

```xml
<Strecke>
  <UTM UTM_WE="472" UTM_NS="5509" UTM_Zone="32" UTM_Zone2="U"/>
  <Huellkurve>
    <PunktXYZ X="2497.085"  Y="4725.0908"/>
    <PunktXYZ X="-2323.53"  Y="6052.373"/>
    <PunktXYZ X="-2244.7129" Y="-4880.5708"/>
    <PunktXYZ X="2725.999"  Y="-4340.1792"/>
  </Huellkurve>
  ...
</Strecke>
```

`<Huellkurve>` ist ein direktes Kindelement von `<Strecke>`; es gibt pro `.st3`-Datei
höchstens eine Hüllkurve. Die `X`/`Y`-Attribute der `<PunktXYZ>`-Knoten sind relativ
zum **selben `<UTM>`-Referenzpunkt** wie die `<g>`/`<b>`-Koordinaten der StrElemente:

```
abs_x = UTM_WE * 1000 + X
abs_y = UTM_NS * 1000 + Y
```

Die Anzahl der Punkte ist variabel (mindestens 3). Das Polygon ist im Format **nicht**
explizit geschlossen (letzter Punkt ≠ erster Punkt); der Import schließt den Ring
beim Erstellen des WKT/`shapely.Polygon` automatisch.

### Implementierung (`convert/convert_envelope.py`)

Die Funktion `convert_envelope()` im Unterpaket `convert/` kann eigenständig oder
optimiert zusammen mit `st3Converter` aufgerufen werden:

```python
convert_envelope(
    input_path,           # Pfad zur .st3-Datei
    target_epsg=31467,    # Ziel-KBS
    auto_detect_crs=True, # UTM-Zone aus <UTM UTM_Zone> lesen
    fallback_epsg=32632,  # Rückfall-KBS
    _route_el=None,       # interner Parameter: bereits geparstes <Strecke>-Element
) -> list  # [] oder [Feature-Dict]
```

`_route_el` ist ein **interner** Parameter (Unterstrich-Konvention): Wird das
already-geparste lxml-`<Strecke>`-Element übergeben, entfällt `ET.parse()` vollständig
— kein zweiter Disk-Zugriff, kein zweiter XML-Parse. Im CLI-Modus bleibt der Parameter
`None`; die Funktion parst die Datei dann selbstständig.

Rückgabe: Liste mit **0 oder 1** Feature-Dict:

```python
[{
    "geometry": [(x1, y1), (x2, y2), …],   # transformierte Koordinaten, Ring nicht geschlossen
    "attrs":    {"id": 1, "streckenmodul": "<dateistem>", "utm_zone": 32},
}]
```

Leer, wenn kein `<Huellkurve>`-Element vorhanden ist oder weniger als 3 Punkte enthalten sind.
Bei fehlerhafter Datei gibt die Funktion ebenfalls `[]` zurück (kein `raise`).

Die UTM-Zone wird **immer dynamisch** aus dem `<UTM UTM_Zone>`-Attribut der jeweiligen
Datei bestimmt (`source_epsg = 32600 + utm_zone`). Der `fallback_epsg`-Parameter greift
nur dann, wenn `auto_detect_crs=False` übergeben wird.

Für die Koordinatentransformation nutzt das Modul einen **modulweiten Transformer-Cache**
(`_TRANSFORMER_CACHE: dict`). Pyproj-`Transformer`-Objekte werden je
`(source_epsg, target_epsg)`-Schlüsselpaar einmalig erzeugt und danach wiederverwendet.
Im Batch-Betrieb mit vielen Dateien gleicher Projektion entfällt so der wiederholte
pyproj-Datenbank-Lookup.

### Steuerung

| Kontext | Option |
|---|---|
| CLI | `--import-envelope` / `--no-import-envelope` |
| Einstellungsmenü (interaktiv) | Option **7. Hüllkurve importieren** |
| `Config`-Schlüssel | `import_envelope` (bool, Default `true`) |

---


---

## Das st3-Format

`.st3` ist ein **XML-basiertes Dateiformat** von Zusi 3 (Eisenbahnsimulator). Es beschreibt
das Streckennetz eines geografischen Moduls (Ausschnitt).

### XML-Struktur

```xml
<Zusi>
  <Strecke RekTiefe="..." ZufallsNr="...">

    <!-- Koordinaten-Ursprung für alle relativen g/b-Angaben -->
    <UTM UTM_WE="537" UTM_NS="5315" UTM_Zone="32" />

    <!-- Umgrenzungspolygon für den Geländeformer (optional) -->
    <Huellkurve>
      <PunktXYZ X="2497.085"  Y="4725.0908"/>
      <PunktXYZ X="-2323.53"  Y="6052.373"/>
      ...
    </Huellkurve>

    <!-- Geometrie- und Topologieelement -->
    <StrElement Nr="1" Fkt="0" ...>
      <g X="-423.456" Y="102.789" />   <!-- Gegenrichtungs-Endpunkt (relativ) -->
      <b X="-419.123" Y="105.234" />   <!-- Normrichtungs-Endpunkt (relativ) -->

      <InfoNormRichtung  km="12.345" ... />
      <InfoGegenRichtung km="12.340" ... />

      <!-- Verweise auf benachbarte Module (Modulgrenzen) -->
      <NachNormModul>
        <Datei Dateiname="Routes\DB\...\Nachbar.st3" />
      </NachNormModul>

      <!-- Betriebsstellen und Weichensignale -->
      <Signal SignalTyp="2" Signalname="Bf Musterstadt" ...>
        <SignalFrame>
          <Datei Dateiname="...\54_760_1-18_5_Rechts_Schienen_K-Oberbau.ls3" />
        </SignalFrame>
      </Signal>
    </StrElement>

    <StrElement Nr="2" Fkt="4" ...>
      ...
    </StrElement>

  </Strecke>
</Zusi>
```

### Norm- und Gegenrichtung (blau/grün)

In der Zusi-Programmoberfläche werden ausschließlich die Begriffe **blaue** und **grüne
Richtung** verwendet. Im Dateiformat entsprechen diese:

| Dateiformat | Programmoberfläche | XML-Element |
|---|---|---|
| Normrichtung | blau | `<b>` (b-Endpunkt des StrElements) |
| Gegenrichtung | grün | `<g>` (g-Endpunkt des StrElements) |

Merkhilfe: **g**rün = **G**egenrichtung.

Diese Zuordnung gilt auch für `NachNorm`/`NachGegen`, `InfoNormRichtung`/`InfoGegenRichtung`
und alle anderen richtungsabhängigen Attribute.

### Koordinatensystem

Alle `X`/`Y`-Angaben der `g`- und `b`-Punkte sind **relativ** zum UTM-Referenzpunkt des
Moduls. Die absoluten Koordinaten ergeben sich als:

```
abs_x = UTM_WE * 1000 + X   [Meter, Easting]
abs_y = UTM_NS * 1000 + Y   [Meter, Northing]
```

`UTM_WE` und `UTM_NS` sind in **Kilometern** angegeben. `UTM_Zone` bestimmt den
Quell-EPSG-Code (`32600 + Zone`, z. B. Zone 32 → EPSG:32632).

### Fkt-Werte (Elementfunktion)

`Fkt` ist ein **6-Bit-Feld**; jedes Bit kodiert eine unabhängige Eigenschaft des StrElements:

| Bit |  Wert | Eigenschaft |
|----:|------:|-------------|
|   0 |     1 | Tunnel |
|   1 |     2 | Keine Gleisfunktion |
|   2 |     4 | Weichenbausatz |
|   3 |     8 | Keine Schulter rechts |
|   4 |    16 | Keine Schulter links |
|   5 |    32 | ETCS Trusted Area |

Für den Import sind ausschließlich **Bit 1** (Keine Gleisfunktion) und **Bit 2** (Weichenbausatz)
relevant; alle anderen Bits beeinflussen Rendering und Fahrwegsicherung, nicht die Gleistopologie.
**Bit 1 ist dominant**: sobald es gesetzt ist, wird das Element unabhängig von allen anderen Bits
übersprungen – weder Knoten noch Kanten werden angelegt:

| Bit 1 (Kein Gleis) | Bit 2 (Weiche) | Behandlung im Import | Beispiel-`Fkt` |
|:---:|:---:|---|---|
| – | – | **Gleis** – Geometrie und Topologie werden eingelesen | 0, 1, 8, 9, 16, 17 … |
| – | x | **Weichenbausatz** – wird eingelesen; trägt ggf. Weichenknoten | 4, 5, 12, 13, 20, 21, 28, 29 … |
| x | beliebig | **Kein Gleis** – wird **übersprungen** | 2, 3, 6, 7, 10, 11, 14, 15, 30, 31 … |

**Vollständige Bit-Matrix**
(T = Tunnel · KG = Kein Gleis · W = Weichenbausatz · −SR = keine Schulter rechts · −SL = keine Schulter links · E = ETCS Trusted Area):

| Fkt |  T | KG |  W | −SR | −SL |  E |
|----:|:--:|:--:|:--:|:---:|:---:|:--:|
|   0 |  – |  – |  – |  –  |  –  |  – |
|   1 |  x |  – |  – |  –  |  –  |  – |
|   2 |  – |  x |  – |  –  |  –  |  – |
|   3 |  x |  x |  – |  –  |  –  |  – |
|   4 |  – |  – |  x |  –  |  –  |  – |
|   5 |  x |  – |  x |  –  |  –  |  – |
|   6 |  – |  x |  x |  –  |  –  |  – |
|   7 |  x |  x |  x |  –  |  –  |  – |
|   8 |  – |  – |  – |  x  |  –  |  – |
|   9 |  x |  – |  – |  x  |  –  |  – |
|  10 |  – |  x |  – |  x  |  –  |  – |
|  11 |  x |  x |  – |  x  |  –  |  – |
|  12 |  – |  – |  x |  x  |  –  |  – |
|  13 |  x |  – |  x |  x  |  –  |  – |
|  14 |  – |  x |  x |  x  |  –  |  – |
|  15 |  x |  x |  x |  x  |  –  |  – |
|  16 |  – |  – |  – |  –  |  x  |  – |
|  17 |  x |  – |  – |  –  |  x  |  – |
|  18 |  – |  x |  – |  –  |  x  |  – |
|  19 |  x |  x |  – |  –  |  x  |  – |
|  20 |  – |  – |  x |  –  |  x  |  – |
|  21 |  x |  – |  x |  –  |  x  |  – |
|  22 |  – |  x |  x |  –  |  x  |  – |
|  23 |  x |  x |  x |  –  |  x  |  – |
|  24 |  – |  – |  – |  x  |  x  |  – |
|  25 |  x |  – |  – |  x  |  x  |  – |
|  26 |  – |  x |  – |  x  |  x  |  – |
|  27 |  x |  x |  – |  x  |  x  |  – |
|  28 |  – |  – |  x |  x  |  x  |  – |
|  29 |  x |  – |  x |  x  |  x  |  – |
|  30 |  – |  x |  x |  x  |  x  |  – |
|  31 |  x |  x |  x |  x  |  x  |  – |
|  32 |  – |  – |  – |  –  |  –  |  x |
|  33 |  x |  – |  – |  –  |  –  |  x |
|  34 |  – |  x |  – |  –  |  –  |  x |
|  35 |  x |  x |  – |  –  |  –  |  x |
|  36 |  – |  – |  x |  –  |  –  |  x |
|  37 |  x |  – |  x |  –  |  –  |  x |
|  38 |  – |  x |  x |  –  |  –  |  x |
|  39 |  x |  x |  x |  –  |  –  |  x |
|  40 |  – |  – |  – |  x  |  –  |  x |
|  41 |  x |  – |  – |  x  |  –  |  x |
|  42 |  – |  x |  – |  x  |  –  |  x |
|  43 |  x |  x |  – |  x  |  –  |  x |
|  44 |  – |  – |  x |  x  |  –  |  x |
|  45 |  x |  – |  x |  x  |  –  |  x |
|  46 |  – |  x |  x |  x  |  –  |  x |
|  47 |  x |  x |  x |  x  |  –  |  x |
|  48 |  – |  – |  – |  –  |  x  |  x |
|  49 |  x |  – |  – |  –  |  x  |  x |
|  50 |  – |  x |  – |  –  |  x  |  x |
|  51 |  x |  x |  – |  –  |  x  |  x |
|  52 |  – |  – |  x |  –  |  x  |  x |
|  53 |  x |  – |  x |  –  |  x  |  x |
|  54 |  – |  x |  x |  –  |  x  |  x |
|  55 |  x |  x |  x |  –  |  x  |  x |
|  56 |  – |  – |  – |  x  |  x  |  x |
|  57 |  x |  – |  – |  x  |  x  |  x |
|  58 |  – |  x |  – |  x  |  x  |  x |
|  59 |  x |  x |  – |  x  |  x  |  x |
|  60 |  – |  – |  x |  x  |  x  |  x |
|  61 |  x |  – |  x |  x  |  x  |  x |
|  62 |  – |  x |  x |  x  |  x  |  x |
|  63 |  x |  x |  x |  x  |  x  |  x |
---

## Paket-Struktur

```
st3-Import/
  ├─ st3_converter.py        # Klasse st3Converter (Konvertierungslogik, 8 Schritte)
  ├─ config/
  │    └─ st3_converter_config.json   # Persistente Einstellungen
  ├─ convert/
  │    ├─ __init__.py
  │    └─ convert_envelope.py  # Hüllkurven-Import (convert_envelope())
  └─ core/
       ├─ core.py            # VERSION, Logging, Config-Klasse, print()-Wrapper
       ├─ cli.py             # CLI (interaktiver Modus + argparse)
```

### `st3Converter` (`st3_converter.py`)

Hauptklasse; Kann als Bibliothek oder von CLI (`core/cli.py`)
gleichermaßen genutzt werden. Konstruktor:

```python
st3Converter(
    input_path,                  # Pfad zur .st3-Datei
    target_epsg=31467,           # Ziel-KBS
    auto_detect_crs=True,
    normalize_switch_names=True, # Weichenknoten-Namen normalisieren
    progress_callback=None
)
```

Rückgabe von `convert()`: `(nodes_features, edges_features)` — Listen von Feature-Dicts
(siehe [Schritt 8](#schritt-8--layer-ausgabe)).

### `Config` (`core/core.py`)

Verwaltet die persistenten Einstellungen; lädt/speichert
`config/st3_converter_config.json`. Schlüssel und Defaults:

| Schlüssel | Default | Beschreibung |
|---|---|---|
| `auto_detect_crs` | `true` | Quell-KBS aus `<UTM UTM_Zone>` lesen |
| `fallback_epsg` | `32632` | Rückfall-KBS wenn Auto-Erkennung fehlschlägt |
| `target_epsg` | `31467` | Ziel-KBS der Ausgabe-Geometrien |
| `normalize_switch_names` | `true` | Namen von Weichenknoten normalisieren (W/EW/DKW-Präfix und ESTW-Bereichskennziffer entfernen) |
| `import_envelope` | `true` | Hüllkurve aus `<Huellkurve>` als Polygon-Layer importieren |
| `create_log_file` | `true` | `.log`-Datei neben Eingabedatei anlegen |
| `open_log_file` | `false` | Protokoll nach Abschluss öffnen |

### `cli.py` (`core/cli.py`)

Standard-Einstiegspunkt mit zwei Modi:

- **Interaktiver Modus** (`python core/cli.py`): menügesteuerter Dialog mit dreistufiger
  Dateisuche (Arbeitsverzeichnis → Ordnerpfad → direkter Pfad) und Einstellungsmenü.
- **CLI-Modus** (`python core/cli.py -i ... -o ...`): Argparse-basiert; alle
  Konvertierungsoptionen über Schalter steuerbar.

Ausgabe ist stets ein GeoPackage (via `geopandas`/`shapely`). Ist der Hüllkurven-Import
aktiv, wird ein dritter Layer `Hüllkurve` in dieselbe `.gpkg`-Datei geschrieben.

**Hüllkurven-spezifische Schalter:**

| Schalter | Bedeutung |
|---|---|
| `--import-envelope` | Hüllkurven-Import erzwingen (unabhängig von gespeicherter Config) |
| `--no-import-envelope` | Hüllkurven-Import deaktivieren |

### Signal-Elemente

Innerhalb eines `StrElement` können `<Signal>`-Kindelemente auftreten:

- **`SignalTyp="1"`**: Tafel – wird im Import nicht zur Knotenbildung herangezogen
- **`SignalTyp="2"`**: Weichensignal – liefert `Signalname`, Bauart aus `SignalFrame`-Dateinamen und `NameBetriebsstelle` (→ `bst_name` am Weichenknoten)
  (Präfix vor `_Schienen` im `.ls3`-Dateinamen, z. B. `54_760_1-18_5_Rechts`)
- **`SignalFrame/Datei`**: Pfad zur 3D-Grafikdatei; enthält der Dateiname den Teilstring
  `_Schienen` (case-insensitiv), wird das Präfix davor (letzter Pfadabschnitt, führende und
  abschließende Unterstriche entfernt) als `knotenbeschr` übernommen.
  Das `BoundingR`-Attribut des `<Signal>`-Elements liefert den Radius für die
  [knotenbeschr-Propagierung](#nachbeschriftung-knotenbeschr-propagierung).

### Nachfolger-Verweise (`NachNorm`, `NachNormModul`)

Jedes `StrElement` kann Verweise auf seine Nachfolger in Norm- und Gegenrichtung tragen.
Es gibt zwei Varianten:

| Kindknoten | Bedeutung |
|---|---|
| `<NachNorm Nr="…">` | Nummer eines **Nachfolger-Elements im selben Modul** (Normrichtung) |
| `<NachGegen Nr="…">` | Nummer eines **Nachfolger-Elements im selben Modul** (Gegenrichtung) |
| `<NachNormModul Nr="…"><Datei Dateiname="…"/></NachNormModul>` | Nummer eines **Referenzpunkts vom Typ „Modulgrenze"** in einem anderen Modul (Normrichtung) |
| `<NachGegenModul Nr="…"><Datei Dateiname="…"/></NachGegenModul>` | Wie oben, Gegenrichtung |

Der 3D-Editor schreibt diese Knoten immer in fester Reihenfolge:
1. alle `NachNorm`-Knoten
2. alle `NachGegen`-Knoten
3. alle `NachNormModul`-Knoten
4. alle `NachGegenModul`-Knoten

Ein Mischen von `NachXXX` und `NachXXXModul` im selben StrElement ist daher nicht
vorgesehen.

### `Anschluss`-Attribut des `StrElement`-Knotens

Dieses Attribut kodiert die **Richtung der Nachfolger-Elemente** innerhalb desselben
Moduls als 16-Bit-Ganzzahl. Es wird in **Schritt 2** aktiv verwendet, um die Seite
(g oder b) zu bestimmen, mit der ein Nachfolger-Element an das aktuelle Element
anschließt.

- **Bits 0–7:** Richtung der (maximal 8) Normrichtungs-Nachfolger (blau),
  beginnend mit Bit 0 für den ersten Nachfolger
- **Bits 8–15:** Richtung der (maximal 8) Gegenrichtungs-Nachfolger (grün)
- **Bit = 0** → Nachfolger schließt mit seiner **g-Seite** an; **Bit = 1** → mit seiner **b-Seite**

**Pseudocode** zur Bestimmung der angeschlossenen Nachfolger-Seite (0-indiziert):

```python
def successor_side(connection: int, idx: int, direction: str) -> str:
    """Liefert 'g' oder 'b' — die Seite des idx-ten Nachfolgers, die an E anschließt.

    direction ∈ {"NORM", "GEGEN"}: an welcher Seite von E der Nachfolger hängt
    (NachNorm-Nachfolger hängen an E.b, NachGegen-Nachfolger an E.g).
    Bit=0 → g-Seite des Nachfolgers; Bit=1 → b-Seite des Nachfolgers.
    """
    shift = idx + (8 if direction == "GEGEN" else 0)
    return "b" if (connection >> shift) & 1 else "g"
```

**Beispiel-Tabelle** (grünes Ende `==Nr==>` blaues Ende):

| Situation | Nachfolger von (2, NORM) | Nachfolger von (2, GEGEN) | `Anschluss` von Element 2 |
|---|---|---|---|
| `==1==> ==2==> ==3==>` | (3, NORM) | (1, GEGEN) | 256 = 2⁸ |
| `==1==> ==2==> <==3==` | (3, GEGEN) | (1, GEGEN) | 257 = 2⁸ + 2⁰ |
| `<==1== ==2==> ==3==>` | (3, NORM) | (1, NORM) | 0 |
| `<==1== ==2==> <==3==` | (3, GEGEN) | (1, NORM) | 1 = 2⁰ |

### Einheiten und XML-Konventionen

Für alle Zusi-XML-Formate gelten folgende Grundregeln
([Quelle: ZusiWiki](https://zusiwiki.echoray.de/wiki/Erg%C3%A4nzungen_zu_den_XML-Dateiformaten)):

**Standardwerte bei fehlenden Attributen:**

| Attributtyp | Standardwert |
|---|---|
| Ganzzahl (integer, bool, enum) | `0` |
| Gleitkommazahl (single) | `0.0` |
| Zeichenkette (string) | `""` (leer) |

Fehlende oder leere Attribute (`Attribut=""`) gelten als Standardwert. Zusi lässt
Attribute weg, wenn ihr Wert dem Standardwert entspricht.

**Einheiten in der XML-Datei:**

| Größe | XML-Einheit | Anzeige in der Oberfläche |
|---|---|---|
| Geschwindigkeit | m/s | km/h |
| Winkel | Bogenmaß (rad) | Grad (°) |
| Krümmung | 1/m | 1/km (3D-Editor) |
| Überhöhung | Winkel im Bogenmaß | Grad und mm (je nach Oberbau); positive Werte = Rechtsneigung (bei Blick vom Elementanfang zum -ende) |

**Dateipfade** (`<Datei Dateiname="…">`):
- Enthalten Backslashes → relativ zum Zusi-Datenverzeichnis; ein führender Backslash
  wird ignoriert
- Kein Backslash → Datei liegt im selben Verzeichnis wie die referenzierende Datei

---

## Zielattribute

### Kanten-Layer (`LineString`)

| Feldname | Typ | Beschreibung |
|---|---|---|
| `id` | Integer | Laufende Kanten-Nummer |
| `knotenname_von` | String (200) | Name des Gleisknotens am Anfangspunkt der Kante |
| `knotenname_bis` | String (200) | Name des Gleisknotens am Endpunkt der Kante |
| `bst_von` | String (200) | `NameBetriebsstelle` des Weichenknotens am Anfangspunkt; `NULL` wenn kein Weichenknoten |
| `bst_bis` | String (200) | `NameBetriebsstelle` des Weichenknotens am Endpunkt; `NULL` wenn kein Weichenknoten |
| `km_von` | Double (6 Nachkommastellen) | Kilometerstand am ersten StrElement der Kante |
| `km_bis` | Double (6 Nachkommastellen) | Kilometerstand am letzten StrElement der Kante |
| `strelemente_anz` | Integer | Anzahl der StrElemente in der Kante |
| `strelement_von` | Integer | `Nr` des ersten StrElements |
| `strelement_bis` | Integer | `Nr` des letzten StrElements |

> `knotenname_von`/`knotenname_bis` können `NULL` sein, wenn am Endpunkt kein benannter Knoten liegt.
> `bst_von`/`bst_bis` sind nur gesetzt, wenn der jeweilige Endknoten ein Weichenknoten mit `NameBetriebsstelle`-Signal ist.
> Mehrere Features können dasselbe Knotenpaar (`knotenname_von`, `knotenname_bis`) aufweisen
> (Parallelgleise); sie sind über `strelement_von` eindeutig unterscheidbar.

### Knoten-Layer (`Point`)

| Feldname | Typ | Beschreibung |
|---|---|---|
| `id` | Integer | Laufende Knoten-Nummer |
| `knotenname` | String (200) | Weiche mit Signal: normalisierter Signalname (Präfixe W/EW/DKW entfernt, DKW-Suffix in Großbuchstaben); Weiche ohne Signal: auto-generiert `<dateistem>_<nr>X`; Modulgrenze: `<dateistem>_<nr>G`; Gleisende: `<dateistem>_<nr>E` |
| `bst_name` | String (200) | `NameBetriebsstelle` des Weichensignals (SignalTyp 2); `NULL` bei allen anderen Knotentypen |
| `typ` | String (200) | `Weiche`, `Modulgrenze`, `Gleisende` |
| `knotenbeschr` | String (200) | Weichenbauart (Präfix aus `_Schienen`-Dateinamen), z. B. `54_760_1-18_5_Rechts` |
| `nr` | Integer | `Nr`-Attribut des zugehörigen StrElements |
| `km` | Double (6 Nachkommastellen) | Kilometerstand des zugehörigen StrElements |
| `datei` | String (400) | Stem des Quelldateinamens (ohne `.st3`) |
| `nachbarmodul` | String (400) | Stem des referenzierten Nachbarmoduls (nur bei `typ=Modulgrenze`) |

**Knotentypen:**

| `typ` | Herkunft | `knotenname` |
|---|---|---|
| `Weiche` | Vertex-Grad ≥ 3 | normalisierter Signalname (→ Normalisieren s. o.); ohne Signal: `<dateistem>_<nr>X` (auto) |
| `Modulgrenze` | `NachNormModul` oder `NachGegenModul` im StrElement | `<dateistem>_<nr>G` (auto) |
| `Gleisende` | Freistehender Endpunkt ohne anderen Knotentyp | `<dateistem>_<nr>E` (auto) |

`<dateistem>` ist der Dateiname der importierten `.st3`-Datei ohne Erweiterung (z. B. `Freudenstein_2025`).
Damit sind Auto-Knotennamen modul-übergreifend eindeutig, auch wenn mehrere Module zusammengeführt werden.

### Hüllkurven-Layer (`Polygon`)

| Feldname | Typ | Beschreibung |
|---|---|---|
| `id` | Integer | Laufende Polygon-Nummer (1 im Einzelimport; 1…n im Batch) |
| `streckenmodul` | String (400) | Datei-Stem des Quellmoduls (z. B. `Freudenstein_2025`) |
| `utm_zone` | Integer | UTM-Zonennummer aus `<UTM UTM_Zone>` der Quelldatei (z. B. `32`) |

Layer-Name im GeoPackage: `Hüllkurve`