# Halbautomatischer Bild-Abzeichner (Modul 6)

Die erste Stufe setzt auf manuell angeklickte Stützpunkte und Kreuzungen.
`image_tracer.html` ist ein eigenständiger Offline-Editor. Er lädt ein lokales
PNG-, JPEG- oder WebP-Bild als Hintergrund und speichert eine Annotation als JSON.
Es gibt weder Server noch externe Bibliotheken oder Netzwerkanfragen.
Die Bilddatei bleibt separat und wird nicht in die Annotation eingebettet.

## Bedienung

Nach `python -m pip install -e .` im Projektverzeichnis:

```bash
python -m knots_grid.image_tracer editor --output examples/image_tracer.html
```

Die HTML-Datei lokal im Browser öffnen:

1. Optional eine Bildvorlage laden und die Rastergröße einstellen. Das Bild
   wird proportional auf höchstens 1200 × 900 Pixel eingepasst.
2. Den einzigen geschlossenen Strang einmal entlanglaufen und seine Ecken in
   Reihenfolge anklicken. Der nächste Punkt rastet entlang der überwiegenden
   Mausbewegung horizontal oder vertikal zum vorherigen Punkt ein. Runde Bögen
   müssen als rechtwinklige Strecken nachgezeichnet werden. Den Startpunkt
   nicht nochmals setzen. Segmentnummern beginnen bei 0.
3. „Linie schließen“ ergänzt auch die letzte Strecke zum Startpunkt. Ist sie
   diagonal oder berührt ein Segment einen fremden Endpunkt, wird die Zeichnung
   zurückgewiesen. „Letzten Punkt zurück“ erlaubt eine Korrektur und löscht
   alle Kreuzungswahlen, damit keine veraltete Über-/Unterangabe übernommen wird.
4. Im Kreuzungsmodus jede orange markierte Kreuzung anklicken. Der grüne Strang
   liegt oben. Erneutes Anklicken wechselt die Über-/Unterwahl.
5. Erst nach vollständiger Kreuzungswahl lässt sich `annotation.json` speichern.
   Eine kreuzungsfreie Zeichnung benötigt keine Kreuzungswahl. Raster,
   Zeichenflächenmaße und Ursprung werden für die spätere Bildausrichtung
   mitgespeichert. Beim erneuten Laden der Annotation muss die Bilddatei
   gegebenenfalls zusätzlich geladen werden.

Anschließend konvertieren:

```bash
python -m knots_grid.image_tracer trace annotation.json --output traced_knot
```

Das Ziel enthält `annotation.json`, `trace.json` mit expandierter geschlossener
Punktfolge und Turtle-Code, `catalog.json`, SVG, PNG und die vorhandene drehbare
2-D-/3-D-Galerie `index.html`. Die Galerie zeigt die Quelle und die konservative
Klassifikation des erzeugten Diagramms. Der Bild-Abzeichner führt keine
Optimierung durch. Die Übereinstimmung mit der Vorlage muss der Benutzer beim
Abzeichnen prüfen; aus der Konvertierung folgt kein Äquivalenzbeweis zum Bild.

## Eingabeformat und API

```json
{
  "schema_version": 1,
  "source_image": "rechteck.png",
  "waypoints": [[0, 0], [3, 0], [3, 2], [0, 2]],
  "crossings": []
}
```

Koordinaten sind ganzzahlig, mit mathematischer y-Richtung nach oben.
Segment `i` verbindet Punkt `i` mit `(i+1) mod n`; das letzte Segment schließt
den Zyklus implizit. Jede transversale Kreuzung im Inneren zweier Segmente
braucht genau einen Eintrag:

```json
{"coordinate": [1, 0], "over_segment": 3}
```

`over_segment` muss eines der zwei tatsächlich beteiligten Segmente sein.
Zusätzliche, doppelte, fehlende und nicht passende Angaben führen zum Fehler.
Optionales `editor_view` enthält `spacing`, `offset`, `width` und `height` für
die Bildausrichtung; die Gitterkonvertierung hängt davon nicht ab.

```python
import json
from knots_grid.image_tracer import annotation_from_dict, trace_annotation

annotation = annotation_from_dict(json.loads(text))
trace = trace_annotation(annotation, max_vertices=100_000)
# trace_turtle(trace.code).points == trace.points
```

`DiagramAnnotation`, `CrossingChoice`, `diagram_crossings`,
`annotation_to_dict`, `write_traced_diagram` und `write_tracer_editor` sind
ebenfalls im Modul verfügbar.

## Geometrie und Grenzen

Die gesamte geschlossene Projektion wird vor dem Expandieren geprüft:
keine mehrfachen Stützpunkte, Diagonalen, Nullstrecken, Kehrtwenden,
kollinearen Überlappungen oder fremden Endpunktberührungen. Zulässig sind
ausschließlich transversale Kreuzungen im Inneren beider Strecken. Kollineare
aufeinanderfolgende Stützpunkte ohne Richtungsumkehr sind zulässig.

Der Konverter verfeinert alle Koordinaten um den festen Faktor 4. Grundsätzlich
liegt der Pfad auf `z=0`. An jeder Überkreuzung wechselt er einen verfeinerten
Schritt davor nach `z=1` und einen Schritt danach zurück. Wegen ganzzahliger
Eingabekoordinaten liegen verschiedene Kreuzungen mindestens vier verfeinerte
Schritte auseinander; die lokalen Lift-Bereiche sind getrennt. Auch zu Ecken
bleibt ausreichend Abstand. Zwischen diesen Stellen gibt es weder neue
Projektionskreuzungen noch zusätzliche räumliche Schnittpunkte.

Der erste Stützpunkt wird zum Ursprung verschoben, die erste Strecke durch eine
reine Drehung nach Osten ausgerichtet. Es gibt keine Spiegelung und keinen
automatischen Ebenentausch. Der Start ist damit `(0,0,0)` mit Richtung Ost.
Der vollständige Pfad besteht die vorhandene Validierung und muss exakt mit
dem erneut expandierten Turtle-Code übereinstimmen.

Die Grenzen sind 500 Stützpunkte, 500 Kreuzungen und standardmäßig 100.000
expandierte Gitterpunkte ohne wiederholten Schluss. `--max-vertices` ändert
das letzte Limit; die Punktzahl einschließlich aller Ebenenwechsel wird vor
der Expansion geprüft. Die geometrische Prüfung vergleicht endlich viele
Segmentpaare, ohne Routensuche. Ungültige Eingaben führen vor dem Export zu
einer Fehlermeldung und CLI-Status 2.

Die erste Stufe erkennt keine Pixel, Skelette oder Kreuzungen im Bild. Freie
Kurven, automatische Umroutung, mehrere Komponenten, Verschieben einzelner
Stützpunkte und eine vollständige Tastatur-Zeichenbedienung sind nicht enthalten.

## Beispiel und Abnahme

`examples/image_tracer.html` ist der fertige Editor. Darin erst
`examples/image_trace/annotation.json`, dann `trefoil_reference.png` aus demselben
Verzeichnis laden: Die drei grünen Kreuzungen liegen über der Bildvorlage.
Die Ergebnisgalerie liegt in `examples/image_trace/index.html`.

```bash
python examples/make_image_trace.py
python -m knots_grid.image_tracer trace examples/image_trace/annotation.json --output examples/image_trace
python -m unittest discover -s tests
node tests/test_image_tracer_runtime.cjs
node tests/test_gallery_runtime.cjs examples/image_trace/index.html
```

Das Beispiel ist ein manuell angegebenes Trefoil-Diagramm mit drei Kreuzungen,
102 Gitterpunkten und Determinante 3. Die Tests vergleichen Trefoil und Achterknoten
mit ihren bestehenden vollständigen signierten Referenzdiagrammen, prüfen jede
Kreuzungswahl, Drehungen, Spiegel, zyklische Starts, Richtungsumkehr, ungültige
Eingaben, Suchgrenzen, Turtle-Roundtrips und bytegleiche Exporte. Die Node-Tests
prüfen zusätzlich die tatsächlichen Editor-Ereignisbehandlungen und den
Galeriestart. Die visuelle Browserprüfung wurde durch die Browserrichtlinie für
lokale `file://`-Seiten blockiert; sie wird deshalb nicht als durchgeführt behauptet.
