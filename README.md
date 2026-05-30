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
