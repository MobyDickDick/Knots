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

Interaktive Katalogansicht (`src/knots_grid/gallery.py`, `gallery.html.template`):

- [x] anklickbare Liste mit Vorschau der vorhandenen Katalogknoten,
- [x] verschobene 2-D-Projektion in derselben Darstellung wie SVG,
- [x] drehbare 3-D-Ansicht mit zwei Ebenen, Zoom und Gitter,
- [x] eigenständiger Offline-Export sowie Galerie beim Katalogexport.

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

- [x] reproduzierbare lokale Suche mit rechteckigen Umwegen und Kanten-Lifts ergänzen,
- [x] Bewertungsfunktion für schöne Projektionen einführen (Kennzahlen, konfigurierbare Gewichte und reproduzierbare Bestenauswahl).
- [x] echten Trefoil über ein 5x5-Grid-Diagramm konstruieren.

Mögliche Kriterien:

- Anzahl projektiver Kreuzungen,
- Länge,
- Symmetrie,
- Flächenausnutzung,
- Anzahl Ebenenwechsel,
- keine engen lokalen Degenerationen.

## Modul 5: Knotenprüfer

Dateien:

```text
src/knots_grid/reidemeister.py
```

Ziel:

- [x] flache Kreuzungen samt Über-/Unterinformation aus $z$ bestimmen,
- [x] notwendige Gauss-Wort-Bedingungen für Reidemeister I--III erkennen,
- [ ] geometrisch leere Zugregionen prüfen und Züge tatsächlich ausführen,
- [ ] einfache Knoteninvarianten ergänzen.

## Arbeitspaket AP-01: Generator-Pipeline bis zur Galerie

Status: **offen – nächstes Arbeitspaket**.

Ziel: Den vorhandenen experimentellen Generator mit Knotenprüfung, kontrollierter
Duplikaterkennung, Optimierung und Galerieexport verbinden. Die Sammlung soll
auch Kandidaten außerhalb der bisher verwendeten Familie `T(2,q)` aufnehmen
können. Alle Darstellungen bleiben zyklische Gitterpfade in
`Z^2 x {0,1}`.

```text
Kandidaten generieren
  → validieren
  → Knotentyp bestimmen, soweit belegt
  → Duplikate prüfen
  → äquivalent optimieren
  → Sammlung speichern und Galerie erzeugen
```

Teilaufgaben in Umsetzungsreihenfolge:

- [ ] `travel_candidates(...)` als alternative Quelle an den Katalog anbinden;
  Seed, Generatorparameter und Versuchslimit konfigurierbar machen.
- [ ] Klassifikation aus Kreuzungsdaten und geeigneten Knoteninvarianten
  ergänzen. Bekannte Referenzknoten zur Prüfung verwenden, darunter auch
  Knotentypen außerhalb der Torusknotenfamilie. Nicht sicher zugeordnete
  Kandidaten ausdrücklich als `unknown` speichern.
- [ ] Exakte Darstellungsduplikate und nachgewiesene Knotenäquivalenz getrennt
  behandeln. Gleiche Invarianten allein dürfen keine Äquivalenz begründen;
  ungeklärte Kandidaten bleiben erhalten. Den Umgang mit Spiegelbildern und
  Orientierung explizit festlegen.
- [ ] Geometrisch abgesicherte, knotentyp-erhaltende Umformungen aus Modul 5
  für die Optimierung implementieren und jede Änderung protokollieren.
  Primär die Zahl der Gitterpunkte minimieren; bei gleicher Länge weiterhin
  die bestehende Cantor-Reihenfolge verwenden. Ästhetische Bewertung separat
  anzeigen und keine globale Minimalität behaupten.
- [ ] Original und beste gefundene Darstellung mit Klassifikationsstatus,
  Herkunft, Punktzahl vorher/nachher und angewandten Umformungen speichern.
- [ ] Einen durchgängigen CLI-Aufruf für Generierung bis Galerieexport anbieten.
  Die Galerie um neu erzeugte Kandidaten und einen Original/Optimiert-Vergleich
  in 2-D und drehbarem 3-D erweitern.

Abnahmekriterien:

- [ ] Derselbe Seed mit denselben Parametern und Grenzen erzeugt dieselbe
  Sammlung. Die Suche endet auch dann nach dem Versuchslimit mit einem klaren
  Ergebnisbericht, wenn die gewünschte Zahl unterscheidbarer Knoten nicht
  erreicht wird.
- [ ] Jeder gespeicherte Ausgangs- und Ergebnispfad besteht die Validierung;
  Ebenen außerhalb von `z=0` und `z=1` sind ausgeschlossen.
- [ ] Tests decken bekannte Knotentypen, äquivalente Darstellungen,
  nicht äquivalente Beispiele und ungeklärte Klassifikationen ab. Ein
  Knotennamen- oder Eindeutigkeitsversprechen benötigt nachvollziehbare Evidenz.
- [ ] Optimierte Ergebnisse sind nicht länger als ihre Ausgangspfade. Die
  Äquivalenz ergibt sich aus den abgesicherten Umformungen, nicht allein aus
  unveränderten Invarianten oder einem besseren ästhetischen Score.
- [ ] Ein vollständiger Beispieldurchlauf liefert eine gespeicherte Sammlung
  und eine offline nutzbare Galerie mit auswählbaren Originalen und Ergebnissen.

Betroffene Bereiche: `generator.py`, `reidemeister.py`, `catalog.py`,
`gallery.py`, `gallery.html.template` sowie zusätzliche Klassifikations- und
Optimierungsmodule nach Bedarf. Die offenen Prüf- und Umformungsaufgaben aus
Modul 5 sind Bestandteil dieses Arbeitspakets. Der Bild-Abzeichner bleibt ein
späteres, separates Vorhaben.

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
