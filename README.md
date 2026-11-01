# Knoten und Gitterdiagramme

Dieses Repository enthält drei Bausteine für zyklische Punktmengen in
`Z^2 x {0, 1}`.  Ein Knoten wird als Turtle-Step-Zyklus gespeichert: Jeder
Nachbarpunkt unterscheidet sich um genau einen Gitter-Schritt, der letzte Punkt
ist implizit mit dem ersten verbunden, und gültige Knoten enthalten keinen
3D-Punkt doppelt.

## Die drei Teile

### 1. Generator

Der Generator erzeugt reproduzierbare Beispielknoten:

- `unknot`: ein rechteckiger, minimaler Startzyklus,
- `ornamental`: ein schönerer Zyklus mit rechteckigen Umwegen,
- `layered`: ein zweischichtiger Zyklus mit sichtbaren Über-/Unterführungen.

```bash
python -m knots.cli generate --preset layered --seed 11 --json examples/layered.json --svg examples/layered.svg
```

### 2. Prüfer

Der Prüfer testet eine JSON-Datei auf die einfache Turtle-Step-Repräsentation:

1. alle Punkte liegen in `Z^2 x {0, 1}`,
2. keine Punkte sind doppelt,
3. jede Kante des zyklischen Tupels ist ein Turtle-Step.

```bash
python -m knots.cli check examples/layered.json
```

### 3. Optimierer

Der Optimierer vereinfacht konservativ: Er entfernt lokale Muster, die der
Generator erzeugt, nämlich rechteckige Umwege und kurze Layer-Lifts.  Damit ist
noch keine vollständige Minimalitätsentscheidung für beliebige Knoten bewiesen;
der Code schafft aber eine konkrete Experimentierplattform für weitere
Reidemeister- oder Grid-Moves.

```bash
python -m knots.cli optimize examples/layered.json --json examples/layered_optimized.json --svg examples/layered_optimized.svg
```

## Datenformat

```json
{
  "name": "layered",
  "points": [[0, 0, 0], [1, 0, 0], [1, 0, 1], [2, 0, 1]]
}
```

Der Startpunkt wird am Ende nicht wiederholt; die Schlusskante ist implizit.

## Entwicklung

```bash
python -m unittest discover -s tests
```

## Halbautomatischer Bild-Abzeichner (Modul 6)

Der Offline-Editor in `examples/image_tracer.html` lädt eine lokale Bildvorlage.
Den Strang als rechtwinklige Linie abklicken, schließen, an jeder Kreuzung den
oberen Strang wählen und die Annotation als JSON speichern. Danach erzeugt ein
Aufruf den geprüften Zweischicht-Gitterpfad, Turtle-Code, SVG/PNG und eine
drehbare Galerie:

```bash
python -m knots_grid.image_tracer trace annotation.json --output traced_knot
```

Ein neuer Editor lässt sich mit
`python -m knots_grid.image_tracer editor --output image_tracer.html` exportieren.
Das vollständige Beispiel liegt in `examples/image_trace/`: `annotation.json`
und anschließend `trefoil_reference.png` in den Editor laden oder die fertige
`index.html` öffnen. `python examples/make_image_trace.py` erzeugt das Beispiel
erneut. Die Übereinstimmung mit der Bildvorlage hängt von den manuell gesetzten
Stützpunkten und Kreuzungswahlen ab. Automatische Bilderkennung ist ein späterer
Ausbau. Format, Bedienung und Grenzen stehen in [docs/image_tracer.md](docs/image_tracer.md).

# Knots

Dieses Repository ist ein experimentelles Projekt für **Knoten und Gitterdiagramme**.

Die Grundidee ist, Knoten nicht zuerst als frei gezeichnete Kurven, sondern als exakte zyklische Wege im zweischichtigen Gitter

$$
\mathbb Z^2 \times \{0,1\}
$$

zu modellieren.

Ein Punkt hat die Form

$$
(x,y,z), \qquad x,y \in \mathbb Z, \quad z \in \{0,1\}.
$$

Die Darstellung verwendet zwei Ebenen:

$$
(x,y,0) \mapsto (x,y),
$$

$$
(x,y,1) \mapsto \left(x+\frac{\sqrt 2}{2},\; y+\frac{\sqrt 2}{2}\right).
$$

Damit erscheinen Punkte und Kanten der oberen Ebene leicht diagonal verschoben. Ebenenwechsel werden als kurze rote Diagonalen sichtbar.

## Turtle-Navigation

Der reduzierte Befehlssatz besteht aus vier Befehlen:

| Befehl | Bedeutung |
|---|---|
| `0` | gehe einen Schritt vorwärts in aktueller Richtung auf aktueller Ebene |
| `1` | drehe links und gehe einen Schritt vorwärts |
| `2` | drehe rechts und gehe einen Schritt vorwärts |
| `3` | Ebenenwechsel bei gleichem $(x,y)$; Richtung bleibt erhalten |

Startkonvention:

$$
P_0=(0,0,0)
$$

mit Anfangsrichtung Ost.

## Drei Projektteile

### 1. Generator

Der Generator soll gültige Turtle-Codes beziehungsweise Punktfolgen erzeugen.

Ziel ist zuerst nicht der perfekte mathematische Knotengenerator, sondern ein robuster Kandidatengenerator:

- geschlossene Wege erzeugen,
- doppelte Punkte vermeiden,
- interessante Projektionen erzeugen,
- schöne SVG-Visualisierungen ermöglichen.

### 2. Validator

Der Validator prüft eine zyklische Punktfolge in $\mathbb Z^2 \times \{0,1\}$.

Eine Punktfolge ist zunächst gültig, wenn:

1. sie geschlossen ist,
2. außer Start = Ende keine Punkte doppelt vorkommen,
3. alle Kanten zulässig sind:
   - horizontale oder vertikale Schritte auf derselben Ebene,
   - oder ein Ebenenwechsel bei gleichem $(x,y)$.

### 3. Knotenprüfer

Der spätere Knotenprüfer soll aus einem gültigen Zyklus ein klassisches Knotendiagramm gewinnen:

- flache Projektion,
- Kreuzungsliste,
- Über-/Unterinformation aus der Ebene $z$,
- später eventuell Reidemeister-Züge oder Knoteninvarianten.

## Erste technische Etappe

Die erste stabile Etappe ist bewusst klein:

```text
Turtle-Code
   ↓
Punktfolge in Z² × {0,1}
   ↓
Validator
   ↓
SVG-Visualisierung
```

Danach folgen Generator, Knotenprüfer und erst später ein möglicher Bild-Abzeichner.

## Lokale Ausführung

```bash
python -m pip install -e .
python -m unittest
```

Ein einfaches SVG kann später etwa so erzeugt werden:

```python
from knots_grid import trace_turtle, render_svg

trace = trace_turtle("0111")
render_svg(trace.points, "square.svg")
```

## Kompakte Turtle-Bitcodierung

Zusätzlich zur lesbaren Turtle-Zeichenkette gibt es einen bitweisen Codec in
`knots_grid.compact`.  Jeder Eintrag besteht aus zwei Befehlsbits und danach
einer selbstbegrenzenden Zahl.  Die Zahl wird als Binärziffern geschrieben;
nach jeder Ziffer folgt ein Fortsetzungsbit (`1` = weitere Ziffer, `0` = Ende).
So wird `4` zu `110100` und `7` zu `111110`.

| Bits | Bedeutung |
|---|---|
| `00 n` | `n` Schritte vorwärts |
| `01 n` | links drehen, dann `n` Schritte vorwärts |
| `10 n` | rechts drehen, dann `n` Schritte vorwärts |
| `11 n` | Ebene wechseln, dann `n` Schritte vorwärts (`n = 0` nur Ebenenwechsel) |

Beispiel am klassischen Unknoten `0_1` als Rechteckdiagramm:

```bash
python -m knots_grid.compact encode 0000010010000100
# 0011011001111001110110011110

python -m knots_grid.compact decode 0011011001111001110110011110
# 0000010010000100
```

Die alte Darstellung benötigt hier 16 Turtle-Befehle, also 32 Bits bei der
naiven 2-Bit-Codierung.  Die kompakte Darstellung benötigt 28 Bits und dekodiert
wieder exakt zur ursprünglichen Beschreibung.  Wichtig: Diese variable
Längencodierung ist nicht für jede kurze Eingabe kleiner, spart aber bei längeren
geraden Laufstücken Bits.

## Validierte Kandidaten erzeugen

Die erste Generatorstufe erzeugt mit einem lokalen Zufallszahlengenerator
reproduzierbare Rechteckzyklen. Abhängig von der Konfiguration wird eine Seite
vollständig in die obere Ebene angehoben; jeder Kandidat wird vor der Rückgabe
mit dem Validator geprüft.

```python
from knots_grid import GeneratorConfig, generate_candidate, generate_candidates

config = GeneratorConfig(
    min_side_length=2,
    max_side_length=8,
    layer_probability=0.75,
)

candidate = generate_candidate(seed=2026, config=config)
batch = generate_candidates(10, seed=2026, config=config)
```

## Vielfältigere Kandidaten suchen

Die lokale Suche startet mit einem validierten Rechteck und verändert zufällig
gewählte Kanten schrittweise. Eine Kante wird entweder durch einen rechteckigen
Umweg aus drei Kanten ersetzt oder vorübergehend in die andere Ebene gehoben.
Belegte Punkte werden dabei übersprungen, und das Endergebnis wird erneut durch
den Validator geprüft. Seed und Konfiguration machen einzelne Kandidaten sowie
ganze Batches reproduzierbar.

```python
from knots_grid import SearchConfig, search_candidate, search_candidates

config = SearchConfig(
    min_search_steps=6,
    max_search_steps=18,
    layer_probability=0.3,
)

candidate = search_candidate(seed=2026, config=config)
batch = search_candidates(10, seed=2026, config=config)
```

## Projektionen bewerten und gezielt auswählen

`score_projection(points)` bewertet einen validierten geschlossenen Gitterpfad.
Die Rückgabe enthält den Gesamtwert (`total`, größer ist besser) und die
einzelnen Kennzahlen (`metrics`). Die Bewertung verwendet die flache
`(x,y)`-Projektion vor der diagonalen Verschiebung des Renderers.

| Kennzahl | Definition | Standardgewicht |
|---|---|---|
| `crossings` | echte transversale Über-/Unterkreuzungen | +2,0 |
| `length` | Kantenanzahl einschließlich Schlusskante | −0,05 |
| `symmetry` | mittlerer erhaltener Punktanteil bei horizontaler/vertikaler Spiegelung und Halbdrehung um die Mitte des Begrenzungsrechtecks | +1,0 |
| `area_utilization` | belegte Projektionspunkte / Gitterpunkte im Begrenzungsrechteck | +1,0 |
| `layer_switches` | Anzahl Ebenenwechsel | −0,1 |
| `degeneracies` | überlappende Projektionskanten plus nicht transversale Doppelbesuche ohne Ebenenwechsel | −1,0 |

Symmetrie und Flächenausnutzung liegen zwischen 0 und 1. Die Gewichte sind
endliche, nichtnegative Zahlen; die Vorzeichen der Belohnungen und Abzüge sind
fest. Translationen, zyklischer Start, Umkehrung und die acht Gittersymmetrien
ändern die Kennzahlen nicht.

```python
from knots_grid import ProjectionWeights, score_projection, search_best_candidate

weights = ProjectionWeights(length=0.1, degeneracies=2.0)
candidate = search_best_candidate(50, seed=2026, weights=weights)
score = score_projection(candidate.points, weights=weights)
print(score.total, score.metrics)
```

Die Bestenauswahl bewertet denselben Batch wie `search_candidates(50, seed=2026)`;
bei Gleichstand gewinnt der erste Kandidat. Die bisherige Einzel- und
Batchsuche bleibt verfügbar. Die Bewertung ist eine anpassbare ästhetische
Heuristik, keine Knoteninvariante und kein Minimalitätsbeweis. Insbesondere
macht die Bestenauswahl aus den lokalen Rechteckumwegen keine echten Knoten.

## Einen wirklichen Knoten erzeugen

Lokale rechteckige Umwege und Kanten-Lifts ändern den Knotentyp nicht; aus
einem Rechteck entsteht damit weiterhin nur ein Unknoten. Für einen echten
Knoten wird deshalb ein **Grid-Diagramm** verwendet. `trefoil_candidate()`
verbindet die X-/O-Marker eines minimalen 5x5-Trefoil-Diagramms, legt alle
horizontalen Segmente nach `z=0` und alle vertikalen nach `z=1` und erzeugt so
drei eindeutige Über-/Unterkreuzungen.

```python
from knots_grid import find_crossings, trefoil_candidate

trefoil = trefoil_candidate()
assert len(find_crossings(trefoil.points)) == 3
```

`reidemeister_conditions(points)` wertet außerdem die notwendigen lokalen
Gauss-Wort-Bedingungen aus: benachbarte Doppelbesuche für Typ I, zwei gemeinsam
begrenzte Bögen mit konsistenter Überführung für Typ II und das Dreiecksmuster
für Typ III. Die Treffer sind bewusst Kandidaten; vor einer automatischen
Umformung muss zusätzlich geprüft werden, dass die betroffene Fläche leer ist.

## Katalog mit paarweise verschiedenen Knoten erzeugen

Der Katalog beginnt mit **höchstens einem Unknoten**. Danach werden reduzierte
Grid-Diagramme der Torusknoten `T(2,3)`, `T(2,5)`, `T(2,7)`, … erzeugt. Das
sind echte, paarweise verschiedene Knoten: Ihre Determinanten sind
3, 5, 7, … und unterscheiden daher bereits die Knotentypen. Die verwendeten
Diagramme haben weder einen reduzierenden Reidemeister-I- noch einen
Reidemeister-II-Kandidaten; ihre Grid-Größe ist zugleich die minimale
Bogenzahl dieser Knotenfamilie.

Der Kataloggenerator normalisiert Translationen auf `x >= 0, y >= 0`. Die kanonische Form
minimiert **zuerst ausschließlich die Punktzahl**. Nur wenn zwei als äquivalent
bekannte Darstellungen gleich viele Punkte besitzen, werden lexikographisch die
Cantor-Indizes der geordneten Punkte verglichen. Anders als bloße
Koordinatensummen ist dieses sekundäre Maß kollisionsfrei und erhält die
Reihenfolge des Pfades. `choose_shortest_equivalent(...)` wendet genau diese
Priorität auf eine bereits festgestellte Äquivalenzklasse an.

```bash
python -m knots_grid.catalog --count 100 --mode random --seed 2026 --output knot_catalog
```

Für einen reproduzierbaren Durchlauf über aufsteigende Generator-Seeds:

```bash
python -m knots_grid.catalog --count 100 --mode systematic --output knot_catalog
```

Das Zielverzeichnis enthält für jeden Eintrag **ein SVG und ein PNG** sowie eine
`catalog.json` mit Knotennamen, Determinante, Punkten, Maßen und Seeds.
„Kanonisch“ bezieht sich hier auf
die genannten exakten Gittersymmetrien. Eine vollständige Entscheidung der
Reidemeister- beziehungsweise Knotenäquivalenz ist damit ausdrücklich noch
nicht geleistet. Die Funktion zur Repräsentantenwahl setzt deshalb voraus,
dass die Äquivalenz der übergebenen Knoten zuvor bewiesen wurde.

## Knotengalerie mit drehbarer 3-D-Ansicht

Eine anklickbare Liste des vorhandenen Katalogs lässt sich als einzelne,
offline nutzbare HTML-Datei erzeugen:

```bash
python -m knots_grid.gallery --count 8 --output examples/knot_gallery.html
```

Die fertige Beispieldatei ist `examples/knot_gallery.html`. Die interne Vorlage
heißt `src/knots_grid/gallery.html.template` und wird erst beim Export mit Daten
gefüllt. Die frühere Vorlagenadresse `src/knots_grid/gallery.html` leitet zur
fertigen Beispieldatei weiter.

Die Datei im Browser öffnen und einen Knoten auswählen. Die Ansicht bietet:

- **2-D · Dein Format:** dieselbe Projektion wie im SVG, mit der oberen
  Schicht um `sqrt(2)/2` in beide Koordinatenrichtungen verschoben.
- **3-D · Drehbar:** die tatsächlichen Gitterkoordinaten `(x, y, z)` auf genau
  zwei Ebenen; Ziehen mit Maus oder Finger dreht, das Mausrad zoomt.
- Pfeiltasten zum Drehen nach Fokus auf die Zeichenfläche, `+`/`-` zum Zoomen,
  ein ausblendbares Gitter und ein einstellbarer visueller Schichtabstand.

Blau bezeichnet Ebene 0, Grün Ebene 1 und Rot die Ebenenwechsel. Der
Schichtabstand ändert nur die Ansicht; die gespeicherten Punkte bleiben auf
`z=0` und `z=1`. Die räumliche Darstellung verschiebt die obere Ebene nicht
seitlich. Kanten werden nach Kameratiefe gezeichnet.

Auch der bisherige Katalogexport erstellt nun eine `index.html` neben den
SVG-, PNG- und JSON-Dateien. Für eigene Listen kann
`knots_grid.gallery.render_gallery(entries, filename)` mit `CatalogEntry`-Objekten
verwendet werden. Die Galerie benötigt weder einen Server noch externe
Bibliotheken. Liste und SVG-Vorschauen stehen bereits im HTML und können auch
ohne JavaScript über die Vorschaulinks betrachtet werden. Für die drehbare
Ansicht muss JavaScript aktiviert sein. Falls ihr Start fehlschlägt, bleiben
die 2-D-Ansichten sichtbar und die Fehlermeldung erscheint oberhalb der Galerie.
Das enthaltene Beispiel zeigt den Unknoten und die vorhandene
Torusknotenfamilie, nicht eine vollständige klassische Knotentabelle wie auf
dem Referenzfoto.

Die Galerie-Bedienlogik kann zusätzlich ohne Browser geprüft werden:

```bash
node tests/test_gallery_runtime.cjs
```

## Alternative Generationsstrategie: Reisen durch eindeutige Punkte

Neben Rechtecken und lokaler Suche gibt es nun eine bounded Strategie, die nicht
mehr in einem unbeschränkten Verbesserungsversuch hängen bleibt. Sie wählt eine
feste Anzahl von Marker-Punkten (standardmäßig 10), verwendet jede x- und jede
y-Komponente genau einmal und probiert eine begrenzte Teilliste zufälliger Reisen
durch diese Punkte. Horizontale Teilstücke liegen auf Ebene `z=0`, vertikale
Teilstücke auf Ebene `z=1`; dadurch werden Projektionstreffer zu kontrollierten
Über-/Unterkreuzungen statt zu verbotenen Überschneidungen auf derselben Ebene.

```python
from knots_grid import TravelConfig, travel_candidate, travel_candidates

config = TravelConfig(point_count=10, max_attempts=500)
candidate = travel_candidate(seed=2026, config=config)
batch = travel_candidates(5, seed=2026, config=config)
```

Der erzeugte Turtle-Trace beginnt und endet weiterhin bei `(0, 0, 0)`. Wenn
innerhalb von `max_attempts` keine einkomponentige geschlossene Reise gefunden
wird, bricht der Generator mit einer klaren Fehlermeldung ab, statt endlos zu
suchen.

## Reisegenerator bis zur Galerie (AP-01)

Ein Aufruf erzeugt jetzt eine Sammlung aus Reise-Kandidaten, prüft ihre
Kreuzungsdiagramme, entfernt belegte Duplikate, vereinfacht die Gitterpfade
und exportiert Original und Ergebnis mit einer Offline-Galerie:

```bash
python -m knots_grid.catalog --source travel --count 8 --seed 2026 --point-count 10 --max-attempts 40 --travel-attempts 500 --max-moves 100 --output examples/travel_catalog
```

Die fertige Galerie ist `examples/travel_catalog/index.html`. Die Schalter
**Original** und **Beste gefunden** funktionieren sowohl in 2-D als auch in der
drehbaren 3-D-Ansicht. Angezeigt werden Punktzahlen vorher/nachher, Anzahl der
Umformungen, Seed, Klassifikationsevidenz und eine separate ästhetische Bewertung.
Ungeklärte Einträge heißen in der Ansicht „Kandidat … · ungeklärt“ und werden
in den Daten ausdrücklich als `unknown` gespeichert.

Der Export enthält:

- `catalog.json`: Ausgangs- und Ergebnispunkte, Klassifikation, Herkunft,
  Kennzahlen und ein einzeln wiederholbares Änderungsprotokoll;
- `report.json`: Suchgrenzen, Anzahl der Versuche, Generatorfehler sowie
  getrennte Zähler für exakte und nachweislich äquivalente Duplikate;
- SVG-Dateien für Original und Ergebnis, PNG-Vorschauen und `index.html`.

`--point-count` bestimmt die Anzahl der X/O-Markerpaare. `--travel-attempts`
begrenzt die innere Suche pro Seed, `--max-attempts` die Zahl der Kandidaten-Seeds
und `--max-moves` die Vereinfachung pro Kandidat. Reicht das Versuchslimit
nicht aus, werden die Teilsammlung und der Status `attempt_limit` gespeichert.
Gleiche Seeds, Parameter und Grenzen erzeugen dieselben Daten und Exporte.
Der Standard `--source torus` erhält den bisherigen konstruierten Katalog.

Die Knotendeterminante wird exakt aus der Fox-Färbungsmatrix berechnet. Ein
Knotenname wird nur bei einer kreuzungsfreien regulären Projektion oder einem
vollständigen signierten Diagrammvergleich mit einer Referenz vergeben.
Referenzen sind `T(2,3)` bis `T(2,15)` einschließlich ihrer Spiegel und der
Achterknoten `4_1`. Dessen Gitterdarstellung stammt aus der
[Sechs-Bogen-Darstellung im Knot Atlas](https://katlas.org/wiki/4_1).
Die Fox-Matrix und ihre Minoren sind in den
[Vorlesungsnotizen von Danny Calegari](https://math.uchicago.edu/~dannyc/notes/knot_theory.pdf)
beschrieben. Ein gleicher Invariantenwert allein begründet keine Äquivalenz:
auch ungeklärte Kandidaten mit derselben Determinante bleiben erhalten.
Die Sammlung verspricht daher keine paarweise verschiedenen Knotentypen.

Die neue Pipeline ignoriert die Durchlaufrichtung, erhält aber Spiegelbilder
als getrennte Klassen; Ausnahmen sind die belegten amphichiralen Referenzen
Unknoten und Achterknoten. Zur Duplikatsuche werden Translation, zyklischer
Start, Umkehrung und Drehungen des Gitters entfernt. Spiegelungen gehören
weiterhin zur alten D4-Kanonisierung, werden in der neuen Pipeline aber
ausdrücklich ausgeschaltet.

Die Flächenzüge der Optimierung bewegen den Pfad über nachweislich freie
Einheitsquadrate im räumlichen Gitter. Drei Kanten können durch eine ersetzt
werden; zwei durch die beiden anderen Quadratseiten. Weil Einheits-Gitterkanten
das Innere eines solchen Quadrats nicht durchstoßen können und die neue
Randbelegung geprüft wird, liegt für jede Änderung eine lokale Isotopie vor.
Das Protokoll lässt sich mit `knots_grid.optimization.apply_face_move` erneut
prüfen und ausführen. Minimiert wird zuerst die Punktzahl, danach die
Cantor-Folge; die ästhetische Bewertung entscheidet nicht über Vereinfachung
oder Äquivalenz. Eine bereits aus der Originalprojektion bekannte Determinante
bleibt auch bei einer degenerierten Ergebnisprojektion erhalten.

Zusätzlich rekonstruiert `analyze_reidemeister_moves(points)` einfache, leere
Ein-, Zwei- und Dreiecksregionen aus den Gauss-Kandidaten. Direkte Typ-I- und
Typ-II-Reduktionen sowie Typ-III-Verschiebungen werden geometrisch geprüft und
mit denselben Protokollfeldern gespeichert. Ein zyklisches Über-/Untermuster im
Dreieck ist ausdrücklich kein ausführbarer Typ-III-Zug.

Bei II/III muss der bewegte obere oder untere Teilpfad in einer Ebene liegen.
Die begrenzte Gitterroutensuche verwendet einen Drei-Zellen-Rand und höchstens
`--route-states 5000` Zustände pro Bogen. Nicht unterstützte Fälle liefern
konkrete Ablehnungsgründe. Die Optimierung nimmt auch bei direkten Zügen nur
Verbesserungen nach Punktzahl und Cantor-Folge an; längere Zwischenschritte
werden nicht untersucht. Dies bleibt eine lokale Suche ohne globale
Minimalitätsentscheidung oder vollständige Knotenerkennung.

Gemischte gespeicherte Protokolle lassen sich mit
`knots_grid.optimization.move_from_dict` einlesen und mit `apply_move` erneut
geometrisch prüfen und ausführen. `apply_face_move` bleibt für alte reine
Flächenprotokolle verfügbar. Details und Isotopieargument stehen in
[docs/reidemeister_moves.md](docs/reidemeister_moves.md), der aktualisierte
Projektstatus in [docs/project_plan.md](docs/project_plan.md).

Zusätzliche Laufzeitprüfung für die Vergleichsansicht:

```bash
node tests/test_gallery_runtime.cjs examples/travel_catalog/index.html
```
