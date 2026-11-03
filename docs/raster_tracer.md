# Automatische Rastererkennung (AP-02)

Status: **umgesetzt am 03.11.2026** für saubere rechtwinklige Rasterbilder.
Die Pixelverarbeitung läuft vollständig im vorhandenen Offline-Editor, ohne
Netzwerkanfragen oder zusätzliche Bibliotheken. Der Benutzer stellt Rasterabstand
und Ursprung ein und prüft die erkannte Projektion vor dem Speichern.

## Ablauf

1. `examples/image_tracer.html` im Browser öffnen und ein lokales PNG-, JPEG-
   oder WebP-Bild laden. Das Bild wird proportional auf höchstens 1200 × 900
   Pixel eingepasst. Die Rasterparameter beziehen sich auf diese Anzeigegröße.
2. Rasterabstand (8–100 Pixel) und Rasterursprung X/Y einstellen, sodass die
   Mittellinien und Ecken auf dem Raster liegen. Der Ursprung liegt jeweils
   zwischen 0 und Rasterabstand minus 1. Die Dunkel-Schwelle (1–254, Standard
   160) trennt dunkle Linien vom hellen Hintergrund.
3. „Bild automatisch erkennen“ wählen. Die erkannten Stützpunkte und
   Kreuzungswahlen erscheinen über dem Bild. Ein Fehler lässt die bisherige
   Zeichnung bestehen. Es gibt keinen automatischen Gitterexport bei einem
   Erkennungsfehler.
4. Den gesamten Pfad mit der Vorlage vergleichen. An orangefarbenen Kreuzungen
   fehlt eine eindeutige Über-/Unterangabe: den oberen Strang anklicken.
   Bereits grüne Wahlen lassen sich durch Anklicken wechseln. „Entwurf speichern“
   erhält offene Wahlen; der Entwurf kann als Zeichnung wieder geladen werden.
5. „Zeichnung speichern“ ist erst nach vollständiger Kreuzungswahl verfügbar.
   Anschließend mit dem bestehenden Konverter exportieren:

   ```bash
   python -m knots_grid.image_tracer trace annotation.json --output traced_knot
   ```

Für die vorhandene Vorlage `examples/image_trace/trefoil_reference.png`:
Rasterabstand **72**, Ursprung **0/0**, Dunkel-Schwelle **160**. Die Erkennung
liefert zehn Ecken und drei vertikale Überführungen. Das Beispiel in
`examples/raster_trace/` wurde direkt aus diesen PNG-Pixeln erzeugt und ergibt
einen Trefoil `T(2,3)` mit 102 Gitterpunkten und Determinante 3.

```bash
node examples/make_raster_trace.cjs
```

Dieses Skript dekodiert nur das bekannte RGB8-Beispiel mit ungefilterten
PNG-Zeilen. Im Editor übernimmt der Browser das allgemeine Dekodieren der
unterstützten Bildformate. Die Ergebnisgalerie ist
`examples/raster_trace/index.html`; Annotation und Bild können zur Kontrolle
auch im Editor geladen werden.

## Pixel, Mittellinie und Graph

`RasterTracer.recognize(imageData, options)` ist eine reine JavaScript-Funktion
im ersten Skript von `src/knots_grid/image_tracer.html`. Sie liest die
unveränderten Bildpixel aus einer separaten Zeichenfläche; das sichtbare Raster,
die halbtransparente Bildanzeige und die gezeichneten Annotationen gehen nicht
in die Erkennung ein.

- Die RGB-Helligkeit wird mit 0,299/0,587/0,114 gewichtet; transparente Pixel
  werden gegen Weiß verrechnet. Werte unter der Schwelle ergeben eine binäre
  Vordergrundmaske. Es werden keine dunklen Komponenten stillschweigend entfernt.
- Zwischen benachbarten Rasterpunkten wird das mittlere Fünftel der Kante
  abgetastet. Ein schmaler Suchstreifen mit Radius
  `max(1, floor(0,12 × Rasterabstand))` Pixel
  toleriert die Strichbreite. Mindestens 85 % der Proben müssen Linie liefern;
  höchstens 15 % gelten als leer. Dazwischen oder bei seitlicher Abweichung
  wird die Eingabe zurückgewiesen. Die Seitenabweichung darf im Mittel höchstens
  einen Pixel beziehungsweise 3 % des Rasterabstands betragen.
- Jede erkannte Kante wird zu einer Kante der diskreten Mittellinie. An einem
  belegten Rasterpunkt sind ausschließlich Grad 2 (Ecke oder gerade Strecke)
  und Grad 4 (transversale Kreuzung) zulässig. Der Rasterpunkt muss selbst
  Vordergrund enthalten. Weitere Proben prüfen den Anschluss der Kanten.
  An Kreuzungen dürfen lokale Lücken innerhalb von 40 % einer Rasterzelle
  auftreten, einschließlich eines kurzen freigestellten Überführungsstrichs.
- Jeder Vordergrundpixel muss in einem engen Korridor um die erkannten Kanten
  liegen (Radius `max(2, floor(0,16 × Rasterabstand))` Pixel).
  Zusätzliche Bildteile führen zum Fehler. Der Korridor ist eine begrenzte
  geometrische Plausibilitätsprüfung und kein allgemeiner Bildtreuebeweis.
- Der Graph wird einmal durchlaufen. An Grad 4 geht der Strang gerade weiter;
  an Grad 2 folgt er dem anderen Nachbarn. Nur wenn dabei jede ungerichtete
  Kante genau einmal erreicht wird, liegt genau eine zyklische Komponente vor.
  Gerade Zwischenpunkte werden entfernt, die Ecken mit der vorhandenen exakten
  Segmentprüfung erneut validiert.

Dies ist eine **rastergebundene Mittellinienextraktion**. Sie verwendet kein
allgemeines morphologisches Skelettieren und benötigt keine frei gezeichnete
Kurve als Zwischenformat. Die Laufzeit ist durch Bildgröße, Raster und die
bestehenden Grenzen von 500 Stützpunkten und 500 Kreuzungen beschränkt.

## Kreuzungsinformation und Herkunft

Nahe einer Kreuzung werden beide Arme jeder Achse getrennt vom zentralen
Schnittpixel geprüft. Wenn eine Achse durchgehend dunkel und die andere klar
unterbrochen ist, wird die durchgehende Achse als obere Führung vorgeschlagen.
Alle anderen Fälle bleiben offen. Insbesondere liefern zwei durchgezogene
Linien keine Über-/Unterwahl. Aus der im Bild vorausgesetzten Lückenkonvention
folgt kein unabhängiger mathematischer Beweis der Bildinterpretation.

Das vorhandene JSON-Format bleibt Version 1. Optional kommen hinzu:

- `editor_view.pixel_origin`: Pixelversatz `[x, y]` zur Bildausrichtung;
- `draft: true`: es fehlen noch Kreuzungswahlen;
- `recognition`: Algorithmus `grid-sampling-v1`, Schwelle, Zahl der
  Vordergrundpixel und Rasterkanten sowie anfangs erschlossene/offene Wahlen.

Der Bericht beschreibt den **ersten Erkennungslauf**. Manuelle Kreuzungswahlen
ändern diese ursprünglichen Zähler nicht. Punktänderungen, Änderungen der
Rasterausrichtung oder Laden eines anders benannten Bilds entfernen den
Bericht. Beim abgeschlossenen Python-Export wird die Herkunft als
`reviewed_raster_annotation` gespeichert; ohne Bericht bleibt die bisherige
manuelle Herkunft erhalten. Der Bericht ist keine zusätzliche Klassifikation
oder Evidenz für Knotenäquivalenz. Fehlende Wahlen werden vor dem Anlegen
eines Ergebnisverzeichnisses abgelehnt. Der weitere Weg nach Gitterpfad,
Turtle-Code, Klassifikation und Galerie entspricht dem manuellen Abzeichner.

## Grenzen und Abnahme

Unterstützt werden einfarbige dunkle, schmale, rechtwinklige Linien auf hellem
Grund mit ausreichend getrennten Rasterlinien und lokalen Kreuzungslücken.
Freihandkurven, gescannte Papierstrukturen, Beschriftungen, automatische
Rasterbestimmung, beliebige Perspektiven, mehrkomponentige Links und
allgemeines Skelettieren bleiben spätere Arbeit. Bei unpassender Vorlage hilft
der bestehende manuelle Abzeichner. Kleine Bilddetails innerhalb des akzeptierten
Korridors können unbemerkt bleiben; die Sichtprüfung der Projektion bleibt nötig.

Automatisierte Abnahme:

```bash
# Ohne Installation zusätzlich PYTHONPATH=src setzen.
python -m unittest discover -s tests
node tests/test_image_tracer_runtime.cjs
node tests/test_raster_tracer_runtime.cjs
node tests/test_gallery_runtime.cjs
node tests/test_gallery_runtime.cjs examples/travel_catalog/index.html
node tests/test_gallery_runtime.cjs examples/image_trace/index.html
node tests/test_gallery_runtime.cjs examples/raster_trace/index.html
```

Die Rastertests lesen die echte PNG-Vorlage und prüfen zusätzlich unterschiedliche
Rasterabstände/-ursprünge, Transparenz, Schwellen, Drehungen, Spiegel,
unaufgelöste Kreuzungen, offene Pfade, mehrere Komponenten, Fremdpixel,
ungültige Parameter und Bildgrenzen. Sie führen den erkannten Datensatz durch
den Python-Konverter bis zur Galerie, prüfen den exakten Turtle-Roundtrip und
die Klassifikation einschließlich der Spiegelunterscheidung. Die UI-Tests
führen die tatsächlichen Ereignisbehandlungen für Bildladen, Erkennung,
Fehlererholung, Entwurfsimport/-download und manuelle Vervollständigung aus.
Eine visuelle Browserprüfung wurde durch die lokale Browserrichtlinie blockiert
und ist nicht Teil der behaupteten Abnahme.
