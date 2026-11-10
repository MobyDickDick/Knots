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

Status der halbautomatischen ersten Stufe: **umgesetzt am 01.11.2026**.

Dateien:

```text
src/knots_grid/image_tracer.py
src/knots_grid/image_tracer.html
```

Nach Abschluss von AP-01 ist die dokumentierte erste, halbautomatische Variante
mit angeklickten Stützpunkten und Kreuzungen verfügbar:

- [x] Offline-Editor mit lokaler Bildvorlage, Raster und geordneten Stützpunkten.
- [x] Explizite Über-/Unterwahl für jede Kreuzung sowie Annotation speichern/laden.
- [x] Reguläre rechtwinklige Projektion vollständig prüfen; unklare Eingaben
  zurückweisen, statt Über-/Unterangaben zu erraten.
- [x] Kollisionsfreien Pfad in `Z² × {0,1}` und exakt wiederherstellbaren
  Turtle-Code erzeugen; feste Gitterverfeinerung und begrenzte Expansion.
- [x] CLI, Herkunft, konservative Klassifikation, SVG/PNG und Offline-Galerie.
- [x] Reproduzierbares Trefoil-Beispiel einschließlich Bildvorlage und Annotation.
- [x] Referenzdiagramme, Spiegel, Kreuzungswahlen, Fehlerfälle, Grenzen,
  Export-Roundtrip und Editor-Bedienlogik automatisiert prüfen.

Abnahme: 94 Python-Tests sowie Editor- und Galerie-Laufzeittests erfolgreich.
Das Beispiel erzeugt einen Trefoil mit 102 Gitterpunkten, drei Kreuzungen und
Determinante 3. Eine visuelle Browserprüfung war wegen der Sperre lokaler
`file://`-Seiten nicht möglich. Bedienung, Format und geometrische Grenzen:
[Bild-Abzeichner](image_tracer.md).

## Arbeitspaket AP-02: Automatische Erkennung rechtwinkliger Rasterbilder

Status: **umgesetzt am 03.11.2026**. Der Offline-Abzeichner ergänzt die manuelle
Eingabe um eine begrenzte Pixelpipeline für saubere rechtwinklige Diagramme auf
einem vom Benutzer eingestellten Raster. Die allgemeine Freihanderkennung
bleibt ein separates Vorhaben.

```text
Lokales Bild
  → dunkle Linie isolieren
  → rastergebundene Mittellinie und Graph extrahieren
  → einen geschlossenen Strang durchlaufen
  → eindeutige Kreuzungslücken auswerten / offene Wahlen ergänzen
  → Projektion prüfen und Annotation speichern
  → bestehender geprüfter Gitter-/Turtle-/Galerieexport
```

Teilaufgaben und Abnahmekriterien:

- [x] Lokale Pixelverarbeitung ohne zusätzliche Pakete, Server oder Netz;
  Bildgröße, Raster und Erkennungsparameter endlich begrenzen.
- [x] Dunkle Linien auf hellem Grund isolieren, Transparenz berücksichtigen und
  eine rastergebundene Mittellinie mit Grad-2-/Grad-4-Knoten extrahieren.
- [x] Offene Enden, Verzweigungen, Fremdpixel außerhalb des Pfadkorridors und
  mehrere zyklische Komponenten begründet zurückweisen.
- [x] Bei Kreuzungen nur aus eindeutigen lokalen Bildlücken eine Überführung
  vorschlagen. Durchgezogene und unklare Kreuzungen brauchen eine manuelle Wahl.
- [x] Ergebnisse im vorhandenen Editor anzeigen; unvollständige Entwürfe
  speichern/laden und den endgültigen Gitterexport bei fehlenden Wahlen sperren.
- [x] Pixelursprung und Erkennungsbericht im JSON-Roundtrip sowie im
  Herkunftseintrag der Galerie erhalten; veraltete Berichte bei Änderungen der
  Punktfolge oder Rasterausrichtung verwerfen.
- [x] Die vorhandene Trefoil-PNG automatisch bis zum validierten Gitterpfad,
  exakten Turtle-Code und Offline-Galerie konvertieren. Reproduzierbares Beispiel:
  `node examples/make_raster_trace.cjs`, Ergebnis `examples/raster_trace/`.
- [x] Echte PNG-Pixel, Rastervarianten, Fehlerfälle, Grenzen, offene Wahlen,
  Bedienereignisse, Rotation/Spiegel und den Python-Galerieexport testen.

Abnahme: 96 Python-Tests, Editor- und Raster-Laufzeittests sowie die Galerieprüfungen
für Standardkatalog, Reisequelle, manuelles und automatisch erkanntes Bildbeispiel.
Die echte PNG ergibt zehn Stützpunkte, drei eindeutige Überführungen und einen
Trefoil `T(2,3)` mit 102 Gitterpunkten und Determinante 3. Die Browserrichtlinie
blockierte die visuelle Prüfung; sie ist nicht als durchgeführt behauptet.
Algorithmus, Bildkonventionen und Grenzen: [Rastererkennung](raster_tracer.md).

## Arbeitspaket AP-03: Automatische Rasterbestimmung

Status: **umgesetzt am 04.11.2026**. Der erste offene Schritt nach AP-02 ist
für saubere rechtwinklige Rasterbilder verfügbar. „Raster und Bild erkennen“
bestimmt Abstand und Ursprung und übernimmt den Pfad erst nach vollständiger
Prüfung durch die bestehende Pixel-/Graphpipeline. Die manuelle Ausrichtung
bleibt als eigener Bedienweg erhalten.

- [x] Horizontale und vertikale Linienbänder aus lokalen Bildpixeln bestimmen;
  gemeinsame Rasterabstände 8–100 und Ursprünge endlich prüfen.
- [x] Vorschläge nach Ausrichtungsabweichung und anschließend gröbstem Raster
  ordnen; höchstens 16 Vorschläge geometrisch und topologisch prüfen.
- [x] Rasterbedienelemente nur bei erfolgreicher Erkennung übernehmen; bei
  Fehlern Zeichnung, Kreuzungswahlen und Rastereinstellungen erhalten.
- [x] Automatische Rasterherkunft im bestehenden JSON-Format, beim
  Wiederladen und beim Python-/Galerieexport erhalten und validieren.
- [x] Die vorhandene Trefoil-PNG ohne vorgegebenes Raster bis zum Gitterpfad,
  exakten Turtle-Code und Offline-Galerie konvertieren; Beispiel neu erzeugen.
- [x] Rastervarianten, verschobene Ursprünge, fehlende Zwischenlinien,
  Drehungen/Spiegel, offene Kreuzungswahlen, Fehlerfälle und tatsächliche
  Editor-Ereignisse prüfen.

Die ursprüngliche Rasterteilung ist bei fehlenden Zwischenlinien nicht eindeutig.
Die Erkennung liefert den ersten vollständig geprüften Vorschlag nach der
dokumentierten Reihenfolge, keinen Beweis eines ursprünglichen Zeichenrasters.
Schmale achsenparallele Linien mit mindestens zwölf Pixeln sichtbarer gerader
Länge und mindestens zwei getrennten Linienbändern je Achse sind erforderlich.
Freihandkurven, Entzerrung und gescannte Papierstrukturen sind nicht abgedeckt.
Algorithmus, Grenzen und Abnahmebefehle: [Rastererkennung](raster_tracer.md).

Abnahme: 97 Python-Tests, beide Node-Editor-/Rasterprüfungen und die vier
Galerie-Laufzeitprüfungen erfolgreich. Der neu erzeugte Beispieldurchlauf erkennt
ohne Rastervorgabe Abstand 72, Ursprung 0/0 und einen Trefoil `T(2,3)` mit
102 Gitterpunkten und drei eindeutigen Kreuzungswahlen. Die Tests prüfen auch
den exakten Turtle-Roundtrip und die Spiegelunterscheidung. Für die Python-Tests
wurde in dieser Windows-Sandbox `TEMP`/`TMP` auf `.test_tmp` im Projekt gesetzt.
Eine manuelle visuelle Browserprüfung ist nicht Teil dieser Abnahme.

## Arbeitspaket AP-04: Saubere freie Kurven abzeichnen

Status: **umgesetzt am 05.11.2026**. Der nächste Schritt der allgemeinen
Bild-Abzeichnung ist als begrenzte Offline-Pipeline für saubere durchgezogene
Kurven verfügbar. Eine allgemeine Aufbereitung beliebiger Scans ist damit
weiterhin nicht abgeschlossen.

- [x] Dunkle Pixel isolieren und ohne stillschweigende Fremdpixelentfernung
  skelettieren; Komponenten und Euler-Charakteristik prüfen.
- [x] Grad-2-Ketten und lochfreie Kreuzungsregionen mit vier geordneten Armen
  rekonstruieren; offene, verzweigte und nicht unterstützte Fälle ablehnen.
- [x] Den fein aufgelösten und den gerasterten eingebetteten Graphen anhand
  von Kreuzungen, zyklischer Armreihenfolge und Kettenverbindungen vergleichen.
- [x] Rechtwinklige Gitterwege mit begrenzter lokaler Routensuche erzeugen;
  Kontakte außerhalb der geplanten Kreuzungen ausschließen und genau einen
  geschlossenen Strang sowie die exakten Segmentkreuzungen prüfen.
- [x] „Freie Kurve erkennen“ in den vorhandenen Editor integrieren;
  Über-/Unterwahlen manuell ergänzen, Entwürfe speichern/laden und bei Fehlern
  Zeichnung und Raster erhalten.
- [x] Kurvenherkunft und feine Zeichenraster im JSON-/Python-Roundtrip erhalten
  und Galerie, Gitterpfad sowie exakten Turtle-Code über die bestehende Pipeline
  exportieren.
- [x] Echtes PNG-Beispiel mit Kontrollüberlagerung und ergänzter Annotation
  bereitstellen: `node examples/make_curve_trace.cjs`, `examples/curve_trace/`.
- [x] Kurven, Drehungen, Spiegelungen, Fehlerfälle, Grenzen, Editor-Ereignisse,
  Klassifikation, Turtle-Roundtrip und Galerie automatisiert prüfen.

Die freie Kurvenerkennung schlägt bewusst keine Über-/Unterwahlen aus
durchgezogenen Kreuzungen vor. Das runde Trefoil-Beispiel besitzt 144
Stützpunkte und drei offene Kreuzungswahlen; nach deren expliziter Ergänzung
entstehen ein `T(2,3)` mit Determinante 3 und 3702 Gitterpunkte. Die
Kontrollüberlagerung wurde visuell geprüft. Algorithmus, topologische Prüfungen,
unterstützte Bilder und Abnahmebefehle: [Freie Kurven erkennen](curve_tracer.md).

Abnahme: 98 Python-Tests, die drei Node-Editor-/Erkennungsprüfungen und alle
fünf Galerie-Laufzeitprüfungen erfolgreich. Die Kurvenprüfung deckt auch den
Rückfall auf ein feineres Raster mit einem Pixel Zeichenabstand ab. Die
Python-/Node-Tests verwenden in der Windows-Sandbox `TEMP`/`TMP` im
Projektverzeichnis `.test_tmp`. Eine manuelle Browserprüfung ist nicht Teil
dieser Abnahme.

## Arbeitspaket AP-05: Lokale Aufbereitung gescannter Vorlagen

Status: **umgesetzt am 06.11.2026**. Der erste begrenzte Schritt der bisher
offenen Scan-Ausbaustufe korrigiert langsam veränderliche Beleuchtung und
schwache Papiertextur für durchgezogene freie Kurven. Allgemeine Scanerkennung
bleibt ein weiteres Vorhaben.

- [x] Alpha-korrigierte Helligkeit und lokale Mittelwerte mit einem Summenbild
  berechnen; Schwarzweißmaske mit explizitem Mindestkontrast erzeugen.
- [x] Offline-Vorschau mit Originalvergleich, begrenzten Parametern und eigenem
  Scan-Erkennungsweg im Editor ergänzen; Fehler erhalten Zeichnung und Raster.
- [x] Die vollständige Maske durch die geometrischen und topologischen
  AP-04-Prüfungen führen; weder Komponenten entfernen noch Lücken schließen.
- [x] Verwendete Parameter und Maskenzähler in JavaScript/Python validieren,
  im JSON-Roundtrip erhalten und als Scan-Herkunft in der Galerie anzeigen.
- [x] Reproduzierbare simulierte Scan-PNG, Maske, Kontrollüberlagerung,
  Entwurf, ergänzte Annotation und vollständigen Galerieexport bereitstellen.
- [x] Schatten, Textur, Drehungen, Spiegel, Grenzen, Fehlerfälle,
  Editor-Ereignisse, Klassifikation, Turtle-Roundtrip und Galerie prüfen.

Abnahme: 99 Python-Tests, vier Node-Editor-/Erkennungsprüfungen und sechs
Galerieprüfungen erfolgreich. Das simulierte Scan-Beispiel ergibt nach drei
manuellen Kreuzungswahlen einen Trefoil `T(2,3)` mit 3702 Gitterpunkten.
Maske und Überlagerung wurden visuell geprüft. Eine manuelle Browserprüfung
oder eine Abnahme beliebiger realer Papierscans ist damit nicht behauptet.
Algorithmus, Bedienung, Grenzen und Abnahmebefehle:
[Scan-Aufbereitung](scan_tracer.md).

## Arbeitspaket AP-06: Eindeutige Kreuzungslücken in freien Kurven

Status: **umgesetzt am 07.11.2026**. Der dokumentierte nächste begrenzte Schritt
erkennt kurze, lokal annähernd gerade Unterführungen anhand der ursprünglichen
Pixelmaske. Ein eigener Modus ergänzt die freie Kurvenerkennung und lässt sich
mit der Scan-Aufbereitung kombinieren.

- [x] Skelettenden endlich paaren; ausgerichtete Endarme, zwei weiße Schultern
  und einen durchgezogenen transversalen Überstrang lokal nachweisen.
- [x] Für jedes Ende genau einen gültigen Partner verlangen; offene, mehrdeutige,
  nahe und fremdbelegte Fälle ohne Teilübernahme zurückweisen.
- [x] Nur belegte Verbindungen ergänzen und die vollständige Rekonstruktion
  durch alle AP-04-Graphprüfungen bis zum einzelnen geschlossenen Strang führen.
- [x] Belegte Überführungen über die zyklische Armordnung in die rechtwinklige
  Einbettung übertragen; durchgezogene Kreuzungen zur manuellen Wahl offenlassen.
- [x] Zwei Offline-Bedienwege, Fehlererholung, gemischte Entwürfe, manuelle
  Änderungen und verlässliches Verwerfen veralteter Berichte integrieren.
- [x] Lokale Pixelbelege in JavaScript/Python validieren und im JSON-Roundtrip,
  Gitter-/Turtle-Export und Galerie einschließlich Scan-Parametern erhalten.
- [x] Reproduzierbare PNG-Vorlagen, Kontrollüberlagerung, teiloffenen Entwurf,
  vollständige Annotation, simulierten Scan und Galerie bereitstellen.
- [x] Echte PNG-Pixel, Drehungen, Spiegel, Händigkeit, Strichbreiten,
  Gegenbeispiele, Grenzen, Bedienereignisse und vollständige Exporte prüfen.

Abnahme: 100 Python-Tests, fünf Node-Editor-/Erkennungsprüfungen und sieben
Galerieprüfungen erfolgreich. `node examples/make_gap_trace.cjs` erzeugt
`examples/gap_trace/`: drei aus Pixeln belegte Überführungen, ein Trefoil
`T(2,3)` und 3702 Gitterpunkte ohne vorgegebene manuelle Kreuzungswahl.
Vorlage und Überlagerung wurden visuell geprüft. Keine manuelle Browserprüfung
oder Abnahme beliebiger realer Scans. Grenzen: höchstens 20 getrennte Lücken
mit Endabstand 10–40 Bildpixeln, ausreichend geraden Armen und eindeutigem
querendem Überstrang. Details: [Kreuzungslücken](gap_tracer.md).

## Arbeitspaket AP-07: Kurze Linienabbrüche in freien Kurven

Status: **umgesetzt am 08.11.2026**. Nach AP-06 war noch kein weiteres
nummeriertes Arbeitspaket beschrieben. Dieses Paket konkretisiert den dort
offenen Punkt „allgemein unterbrochene freie Kurven“ für kurze, lokal gerade,
isolierte Linienabbrüche; beliebige unterbrochene Zeichnungen bleiben offen.

- [x] Endpaare im Abstand 10–32 Pixel mit zwei unverzweigten, ausgerichteten
  Armen und genau einer weißen Unterbrechung in der Originalmaske prüfen.
- [x] Fremdstrukturen, nahe Kreuzungen, konkurrierende Partner und nahe Lücken
  zurückweisen; alle ursprünglichen Enden gemeinsam eindeutig paaren.
- [x] Nur geprüfte Mittellinien ergänzen und die vollständige Maske durch die
  bestehenden Topologie-/Graphprüfungen bis zum einzelnen geschlossenen Strang
  führen; keine Kreuzungswahl aus gewöhnlichen Linienabbrüchen ableiten.
- [x] Eigene Offline-Knöpfe für Kurven und Scan-Vorlagen, rote Markierungen,
  Ergänzungszähler und vollständige Fehlererholung ergänzen.
- [x] Linien- und Kreuzungslücken kombinieren, getrennte Pixelberichte in
  JavaScript/Python validieren und in JSON, Gitter-/Turtle-Export und Galerie
  erhalten; veraltete Herkunft bei Geometrie-/Rasteränderungen verwerfen.
- [x] Reproduzierbare PNG, Kontrollüberlagerung, vollständige Annotation,
  teiloffenen Entwurf, simulierten Scan und Offline-Galerie bereitstellen.
- [x] Echte PNG-Pixel, Vierteldrehungen und freie Drehung, Spiegel/Händigkeit,
  Strichbreiten, mehrere Lücken, Gegenbeispiele, Grenzen, Bedienereignisse,
  Klassifikation, Gittervalidierung und exakten Turtle-Roundtrip prüfen.

Abnahme: 101 Python-Tests, sechs Node-Editor-/Erkennungsprüfungen und acht
Galerieprüfungen erfolgreich. `node examples/make_line_gap_trace.cjs` erzeugt
`examples/line_gap_trace/`: eine dokumentierte Linienergänzung, drei belegte
Überführungen und einen Trefoil `T(2,3)` mit 3702 Gitterpunkten ohne manuelle
Kreuzungswahl. Vorlage und Kontrollüberlagerung wurden visuell geprüft.
Keine manuelle Browserprüfung oder Abnahme beliebiger realer Scans.
Grenzen und Abnahmebefehle: [Linienabbrüche](line_gap_tracer.md).

## Arbeitspaket AP-08: Kleine isolierte Fremdkomponenten in Scans

Status: **umgesetzt am 10.11.2026**. Nach AP-07 war kein weiteres nummeriertes
Paket festgelegt. AP-08 konkretisiert den dokumentierten offenen Bereich
„Beschriftungen und starke Papierstrukturen“ für kleine, klar getrennte
Tintenflecken und einzelne kleine Zeichen. Eine allgemeine Schrift- oder
Papierstrukturerkennung bleibt offen.

- [x] Standardmäßig ausgeschaltete Bereinigung nach der lokalen
  Helligkeitskorrektur; 8er-Komponenten vollständig und deterministisch erfassen.
- [x] Maximal 64 Pixel je Komponente, 32 Komponenten und insgesamt 1024
  entfernte Pixel zulassen; mindestens eine größere Komponente erhalten.
- [x] Mindestens zwölf Pixel Abstand zu jeder anderen Tinte einschließlich
  anderer Entfernungskandidaten prüfen; kleine Randanschnitte und nahe
  Fragmente ohne Teilübernahme zurückweisen.
- [x] Alle Scan-Modi einschließlich beider Lückenarten anbinden und die
  bereinigte Maske durch sämtliche bestehenden Graph-/Einbettungsprüfungen führen.
- [x] Violett markierte Vorschau, Entfernungszähler, Parameterwiederherstellung
  und vollständige Fehlererholung im Offline-Editor ergänzen.
- [x] Pixelbilanz und Komponentenrechtecke in JavaScript/Python validieren,
  im JSON-Roundtrip und Gitter-/Turtle-/Galerieexport erhalten; veraltete
  Herkunft bei Geometrie-/Rasteränderungen verwerfen.
- [x] Reproduzierbare Scan-PNG, Maske, Kontrollüberlagerung, Entwurf,
  ergänzte Annotation und Offline-Galerie bereitstellen.
- [x] Echte PNG-Pixel, Drehungen, Spiegelung, Strichbreiten, Transparenz,
  Kombinationsmodi, Abstands-/Größen-/Anzahlgrenzen, Gegenbeispiele,
  Editor-Ereignisse, Klassifikation und exakten Turtle-Roundtrip prüfen.

Abnahme: 102 Python-Tests, sieben Node-Editor-/Erkennungsprüfungen und neun
Galerieprüfungen erfolgreich. `node examples/make_cleanup_trace.cjs` erzeugt
`examples/cleanup_trace/`: drei entfernte Komponenten mit insgesamt 27 Pixeln,
eine pixelgenau zur sauberen Referenz passende Maske und nach drei manuellen
Kreuzungswahlen einen Trefoil `T(2,3)` mit 3702 Gitterpunkten.
Maske und Kontrollüberlagerung wurden visuell geprüft. Keine manuelle
Browserprüfung oder Abnahme beliebiger realer Scans. Die Bereinigung belegt
keine Zeichenabsicht; jede Entfernung ist mit dem Original zu vergleichen.
Bedienung, Bericht und Grenzen: [Fremdkomponenten](cleanup_tracer.md).

## Nächste Ausbaustufe: weitergehende Scanerkennung (weiter offen)

AP-02 und AP-03 erkennen saubere rechtwinklige Diagramme mit manuell oder
automatisch ermitteltem Raster. AP-04 ergänzt saubere freie Kurven mit
durchgezogenen Kreuzungen. AP-05 ergänzt eine kontrollierbare lokale
Helligkeitskorrektur. AP-06 ergänzt lokal belegte Kreuzungslücken; AP-07 ergänzt
kurze, gerade, isolierte Linienabbrüche mit dokumentierten Pixelbelegen.
AP-08 ergänzt die explizit zuschaltbare Entfernung kleiner isolierter
Fremdkomponenten mit Pixelbilanz und markierter Vorschau.
Die allgemeinere Bildaufbereitung bleibt offen:

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

Starke Papierstrukturen, abrupte Beleuchtungswechsel, allgemeine Beschriftungen,
lange oder stark gekrümmte Linienabbrüche, geometrisch unklare Kreuzungslücken und
Entzerrung sind weiterhin offen. Mehrdeutige Lücken erzeugen auch nach AP-07
keine stillschweigende Verbindung oder Kreuzungswahl. Die Übereinstimmung
der erkannten beziehungsweise manuell festgelegten Projektion mit der Bildvorlage
muss beim Abzeichnen geprüft werden.
