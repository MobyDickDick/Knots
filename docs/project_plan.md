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
- [x] geometrisch leere Reidemeister-Zugregionen prüfen und direkte
  Reidemeister-I--III-Züge mit begrenzten Gitterrealisierungen ausführen
  (`reidemeister_moves.py`, Ablehnungsgründe und Replay),
- [x] als konservative Grundlage geometrisch leere lokale Gitterflächen prüfen
  und knotentyp-erhaltende Flächenzüge ausführen (`optimization.py`, mit Replay-Protokoll),
- [x] die Knotendeterminante aus der Fox-Färbungsmatrix exakt berechnen
  (`classification.py`).

Der geometrische Zugmotor kombiniert freie Einheitsquadrate im Raum (3→1 und
2→2) mit direkten Schleifen-/Zweieckreduktionen und Dreiecksverschiebungen.
Er führt keine ungeprüften Gauss-Kandidaten aus. Die begrenzte Routensuche und
die Anforderung eines ebenen bewegten Extremstrangs bei II/III machen ihn
weiterhin zu keinem vollständigen Reidemeister-Entscheider.

## Arbeitspaket AP-01: Generator-Pipeline bis zur Galerie

Status: **umgesetzt am 01.11.2026**. Die durchgängige Pipeline mit konservativer
Referenzklassifikation, freien Gitterflächen und direkten geometrisch geprüften
Reidemeister-I--III-Zügen ist verfügbar. Die Gitterrealisierungen bleiben bewusst
begrenzt; nicht unterstützte Fälle werden begründet zurückgegeben.

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

- [x] `travel_candidates(...)` als alternative Quelle an den Katalog anbinden;
  Seed, Generatorparameter und Versuchslimit konfigurierbar machen.
- [x] Klassifikation aus Kreuzungsdaten und geeigneten Knoteninvarianten
  ergänzen. Bekannte Referenzknoten zur Prüfung verwenden, darunter auch
  Knotentypen außerhalb der Torusknotenfamilie. Nicht sicher zugeordnete
  Kandidaten ausdrücklich als `unknown` speichern.
- [x] Exakte Darstellungsduplikate und nachgewiesene Knotenäquivalenz getrennt
  behandeln. Gleiche Invarianten allein dürfen keine Äquivalenz begründen;
  ungeklärte Kandidaten bleiben erhalten. Den Umgang mit Spiegelbildern und
  Orientierung explizit festlegen.
- [x] Geometrisch abgesicherte, knotentyp-erhaltende Umformungen aus Modul 5
  für die Optimierung implementieren und jede Änderung protokollieren.
  Primär die Zahl der Gitterpunkte minimieren; bei gleicher Länge weiterhin
  die bestehende Cantor-Reihenfolge verwenden. Ästhetische Bewertung separat
  anzeigen und keine globale Minimalität behaupten. Als Grundlage sind freie
  Gitterflächen-Züge mit Punktzahl-/Cantor-Optimierung und vollständigem Protokoll
  umgesetzt; direkte Reidemeister-I--III-Züge sind mit geprüften Regionen,
  begrenzter Routensuche und erneut geometrisch geprüftem Replay ergänzt.
- [x] Original und beste gefundene Darstellung mit Klassifikationsstatus,
  Herkunft, Punktzahl vorher/nachher und angewandten Umformungen speichern.
- [x] Einen durchgängigen CLI-Aufruf für Generierung bis Galerieexport anbieten.
  Die Galerie um neu erzeugte Kandidaten und einen Original/Optimiert-Vergleich
  in 2-D und drehbarem 3-D erweitern.

Abnahmekriterien:

- [x] Derselbe Seed mit denselben Parametern und Grenzen erzeugt dieselbe
  Sammlung. Die Suche endet auch dann nach dem Versuchslimit mit einem klaren
  Ergebnisbericht, wenn die gewünschte Zahl unterscheidbarer Knoten nicht
  erreicht wird.
- [x] Jeder gespeicherte Ausgangs- und Ergebnispfad besteht die Validierung;
  Ebenen außerhalb von `z=0` und `z=1` sind ausgeschlossen.
- [x] Tests decken bekannte Knotentypen, äquivalente Darstellungen,
  nicht äquivalente Beispiele und ungeklärte Klassifikationen ab. Ein
  Knotennamen- oder Eindeutigkeitsversprechen benötigt nachvollziehbare Evidenz.
- [x] Optimierte Ergebnisse sind nicht länger als ihre Ausgangspfade. Die
  Äquivalenz ergibt sich aus den abgesicherten Umformungen, nicht allein aus
  unveränderten Invarianten oder einem besseren ästhetischen Score.
- [x] Ein vollständiger Beispieldurchlauf liefert eine gespeicherte Sammlung
  und eine offline nutzbare Galerie mit auswählbaren Originalen und Ergebnissen.

Betroffene Bereiche: `generator.py`, `reidemeister.py`, `catalog.py`,
`gallery.py`, `gallery.html.template` sowie zusätzliche Klassifikations- und
Optimierungsmodule nach Bedarf. Die Prüf- und Umformungsaufgaben aus
Modul 5 sind Bestandteil dieses Arbeitspakets. Der Bild-Abzeichner bleibt ein
späteres, separates Vorhaben.

Umsetzung und Grenzen:

- `pipeline.py` verbindet die Reisequelle mit `classification.py`,
  `optimization.py`, Katalogexport und Galerie. Pro Seed gilt das innere
  `travel-attempts`-Limit; für die Sammlung gilt zusätzlich `max-attempts`.
  `report.json` dokumentiert auch unvollständige Suchen und verworfene Kandidaten.
- Die Determinante ist ein exakter erster Minor der Fox-Matrix. Namen werden
  ausschließlich durch vollständige signierte Diagrammvergleiche mit
  Referenzen belegt (Unknoten, `T(2,3)` bis `T(2,15)`, deren Spiegel und der
  Achterknoten `4_1`). Ein gleicher Determinantenwert genügt niemals.
- Orientierung wird ignoriert. Spiegel bleiben getrennt, außer bei den als
  amphichiral bekannten Referenzen `0_1` und `4_1`. Die neue Pipeline verwendet
  daher nur Drehungen bei der Kanonisierung; das bisherige D4-Verhalten des
  Toruskatalogs bleibt als Standard der alten API erhalten.
- Die Optimierung prüft freie Einheitsquadrate in den Ebenen xy, xz und yz.
  Jedes akzeptierte Ergebnis verbessert streng `(Punktzahl, Cantor-Folge)`;
  direkte Reidemeister-Züge unterliegen derselben Priorität. Alle Änderungen
  lassen sich mit `optimization.apply_move` wiederholen, JSON-Protokolle mit
  `move_from_dict` einlesen. Das Bewegungsbudget und `--route-states` begrenzen
  die Suche. Auch innerhalb belegter Äquivalenzklassen
  wird der kürzere beziehungsweise bei Gleichstand kleinere Repräsentant behalten.
- `examples/travel_catalog/index.html` ist der vollständige Offline-Beispiellauf.
  Original und Ergebnis sind in beiden Ansichten umschaltbar. Die Python-Tests
  prüfen Validierung, Referenzen, Spiegel, ungeklärte Fälle, Grenzen, Zug-Replay
  und bytegleiche Exporte. Der Node-Laufzeittest prüft zusätzlich die
  Original-/Ergebnisumschaltung. Die Tests der direkten Züge prüfen alle drei
  Typen, leere und belegte Regionen, zyklische Über-/Untermuster, Transformationen,
  manipulierte Protokolle und begrenzte Suchen.

## Abschluss von AP-01: direkte Reidemeister-Züge

- [x] Für die Gauss-Kandidaten aus `reidemeister_conditions` die zugehörigen
  ebenen Ein-, Zwei- und Dreiecksregionen explizit rekonstruieren.
- [x] Deren Leerheit einschließlich der übrigen Stränge geometrisch prüfen
  und direkte Gitterrealisierungen für Reidemeister I--III ergänzen.
- [x] Nicht ausführbare oder degenerierte Fälle begründet zurückgeben;
  jede tatsächlich ausgeführte Änderung weiter mit einem Replay-Protokoll belegen.

`reidemeister_moves.py` rekonstruiert einfache begrenzte Flächen des exakten
Projektionsgraphen und prüft Punkte sowie Kanten der übrigen Stränge. Typ I
kontrahiert eine leere Schleife, Typ II entfernt zwei Kreuzungen und Typ III
verschiebt einen oberen oder unteren Strang über die mittlere Kreuzung.
Zyklische Über-/Untermuster werden ausdrücklich abgelehnt. Jeder ausgeführte
Zug besitzt ein Protokoll aus Index, vorherigem und folgendem Teilpfad sowie Typ;
das Replay rekonstruiert die Region erneut und prüft die lokale Geometrie.

Grenzen: Bei II/III muss der bewegte Teilpfad einschließlich seiner direkten
Nachbarn in einer Ebene liegen. Die Suche bleibt in einem Drei-Zellen-Rand um
die Region und verwendet höchstens `--route-states` Zustände je bewegtem Strang.
Keine inversen I/II-Züge, automatische Gitterverfeinerung oder längenvergrößernden
Zwischenschritte in der Optimierung. Solche Fälle dürfen zurückgewiesen werden;
sie begründen keine Aussage über Unveränderbarkeit oder globale Minimalität.
Details und Isotopieargument: [Direkte Reidemeister-Züge](reidemeister_moves.md).

Abnahme am 01.11.2026: 83 Python-Tests sowie beide Node-Galerieprüfungen
erfolgreich. Der dokumentierte CLI-Beispiellauf mit Seed 2026 erzeugt 8 Einträge
in 21 Versuchen (13 nachgewiesene Äquivalenzduplikate). Die gespeicherten
Ergebnisprotokolle enthalten 9 direkte I-, 7 direkte II- und 528 Flächenzüge;
Typ III wird zusätzlich anhand einer eigenen Dreiecks-Testdarstellung ausgeführt.
Alle Katalog- und Duplikatprotokolle des Beispiels wurden geometrisch erneut
ausgeführt. Der Galerieexport ist aktualisiert; eine manuelle visuelle
Browserprüfung ist damit nicht behauptet.

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
