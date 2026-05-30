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
