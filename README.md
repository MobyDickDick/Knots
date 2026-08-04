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
=======
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

## Kanonischen Katalog mit 100 Kandidaten erzeugen

Der Kataloggenerator normalisiert Translationen auf `x >= 0, y >= 0` und
entfernt Dubletten, die sich nur durch Startpunkt, Laufrichtung oder eine der
acht Symmetrien des quadratischen Gitters unterscheiden. Die kanonische Form
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

Das Zielverzeichnis enthält `knot_000.svg` bis `knot_099.svg` und eine
`catalog.json` mit Punkten, Maßen und Seeds. „Kanonisch“ bezieht sich hier auf
die genannten exakten Gittersymmetrien. Eine vollständige Entscheidung der
Reidemeister- beziehungsweise Knotenäquivalenz ist damit ausdrücklich noch
nicht geleistet. Die Funktion zur Repräsentantenwahl setzt deshalb voraus,
dass die Äquivalenz der übergebenen Knoten zuvor bewiesen wurde.
