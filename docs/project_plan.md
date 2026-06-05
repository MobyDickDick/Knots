# Projektplan: Knoten und Gitterdiagramme

## Ziel

Das Projekt untersucht Knoten als exakte zyklische Wege im zweischichtigen Gitter

$$
\mathbb Z^2 \times \{0,1\}.
$$

Der Schwerpunkt liegt zuerst auf einer maschinell verlässlichen Darstellung:

1. Turtle-Code expandieren,
2. Punktfolge validieren,
3. exakte SVG-Grafik erzeugen.

Erst danach werden Generator, Knotenprüfer und Bild-Abzeichner ausgebaut.

## Modul 1: Turtle-Kern

Dateien:

```text
src/knots_grid/core.py
```

Aufgaben:

- Punkte als Tripel $(x,y,z)$ darstellen,
- Richtungen verwalten,
- Turtle-Code interpretieren,
- aus Code eine Punktfolge erzeugen.

Befehlssatz:

```text
0 = vorwärts
1 = links + vorwärts
2 = rechts + vorwärts
3 = Ebenenwechsel
```

Start:

$$
(0,0,0)
$$

mit Anfangsrichtung Ost.

## Modul 2: Validator

Dateien:

```text
src/knots_grid/validator.py
```

Prüfungen:

- Geschlossenheit: letzter Punkt ist erster Punkt,
- keine doppelten Punkte außer Start = Ende,
- zulässige Kanten:
  - horizontal/vertikal auf derselben Ebene,
  - Ebenenwechsel bei gleichem $(x,y)$.

Für eine vollständig expandierte Turtle-Punktfolge folgt die Grad-2-Bedingung im Wesentlichen aus der geschlossenen einfachen Zyklusstruktur.

## Modul 3: SVG-Renderer

Dateien:

```text
src/knots_grid/svg.py
```

Darstellung:

$$
(x,y,0) \mapsto (x,y),
$$

$$
(x,y,1) \mapsto \left(x+\frac{\sqrt 2}{2},\; y+\frac{\sqrt 2}{2}\right).
$$

Farben:

- Ebene $z=0$: blau,
- Ebene $z=1$: grün,
- Ebenenwechsel: rot,
- Gitter $z=0$: dunkelgrau,
- verschobenes Gitter $z=1$: hellgrau.

## Modul 4: Generator

Dateien:

```text
src/knots_grid/generator.py
```

Erste Stufe (umgesetzt):

- [x] einfache, reproduzierbare Rechteckkandidaten erzeugen,
- [x] optional eine Seite in die zweite Ebene anheben,
- [x] Validierung für jeden erzeugten Kandidaten erzwingen.

Nächste Stufe:

- [ ] Suchverfahren für vielfältigere Kandidaten ergänzen,
- [ ] Bewertungsfunktion für schöne Projektionen einführen.

Mögliche Kriterien:

- Anzahl projektiver Kreuzungen,
- Länge,
- Symmetrie,
- Flächenausnutzung,
- Anzahl Ebenenwechsel,
- keine engen lokalen Degenerationen.

## Modul 5: Knotenprüfer

Dateien später:

```text
src/knots_grid/crossings.py
src/knots_grid/reidemeister.py
```

Ziel:

- flache Projektion erzeugen,
- Schnittpunkte von Kanten finden,
- Über-/Unterinformation aus $z$ bestimmen,
- später Reidemeister-Züge oder einfache Knoteninvarianten.

## Modul 6: Bild-Abzeichner

Dateien später:

```text
src/knots_grid/image_tracer.py
```

Nicht als erste Etappe.

Mögliche Pipeline:

```text
Bild
  ↓
Linie isolieren
  ↓
Mittellinie / Skelett
  ↓
Kreuzungen erkennen
  ↓
planarer Graph
  ↓
Gitterpfad
  ↓
Turtle-Code
```

Für den Anfang realistischer: halbautomatischer Abzeichner mit angeklickten Stützpunkten und Kreuzungen.
