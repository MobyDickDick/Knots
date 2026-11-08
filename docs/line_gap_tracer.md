# Kurze Linienabbrüche in freien Kurven (AP-07)

Status: **umgesetzt am 08.11.2026**. Dieses Arbeitspaket konkretisiert den nach
AP-06 dokumentierten offenen Punkt „allgemein unterbrochene freie Kurven“ für
kurze, lokal gerade und isolierte Linienabbrüche. Die Rekonstruktion läuft
offline ohne Zusatzpakete und lässt sich mit Kreuzungslücken und der lokalen
Scan-Aufbereitung kombinieren. Beliebige unterbrochene Zeichnungen bleiben offen.

## Bedienung und Beispiel

1. `examples/image_tracer.html` öffnen und eine lokale Bildvorlage laden.
2. „Kurve mit Linienlücken erkennen“ wählen. Der Knopf berücksichtigt sowohl
   die unten beschriebenen Linienabbrüche als auch die belegten Unterführungen
   aus [AP-06](gap_tracer.md). Für langsam veränderliche Beleuchtung und schwache
   Papiertextur „Scan mit Linienlücken erkennen“ verwenden. Dabei gelten
   Scan-Radius und Mindestkontrast statt der Dunkel-Schwelle.
3. Jede **rot markierte Linienergänzung** mit dem Original vergleichen. Status
   und Galerie nennen ihre Anzahl. Linienabbrüche erzeugen keine Kreuzungswahl;
   nur die eigenen Kreuzungsbelege aus AP-06 bestimmen eine Überführung.
   Durchgezogene Kreuzungen bleiben zur manuellen Wahl offen.
4. Offene Wahlen als Entwurf speichern oder alle Wahlen ergänzen und die
   Zeichnung speichern. Fehler übernehmen keine Teilrekonstruktion und erhalten
   Zeichnung, Raster und Scan-Vorschau. Die Scan-Vorschau zeigt immer die Maske
   vor Ergänzungen.
5. Den geprüften Gitter-/Turtle-/Galerieexport wie bisher erzeugen:

   ```bash
   python -m knots_grid.image_tracer trace annotation.json --output traced_line_gap
   ```

```bash
node examples/make_line_gap_trace.cjs
```

`examples/line_gap_trace/` enthält eine synthetische PNG-Vorlage mit einem
gewöhnlichen Linienabbruch und drei Kreuzungslücken, die vollständige Annotation,
eine Kontrollüberlagerung, einen Entwurf mit drei offenen Kreuzungswahlen sowie
eine simulierte Scan-Variante. Die vollständige Erkennung liefert ohne manuelle
Kreuzungswahl einen Trefoil `T(2,3)` mit Determinante 3, 144 Stützpunkten und
3702 Gitterpunkten. Die Galerie liegt in `index.html`.

## Lokale Prüfung und Grenzen

`CurveTracer.recognize(image, {lineGaps: true, gaps: true})` und
`ScanTracer.recognize(image, {lineGaps: true, gaps: true})` aktivieren beide
Lückenarten. `lineGaps: true` allein ergänzt nur gewöhnliche Linienabbrüche.
Die vorhandenen Modi behalten ihre bisherigen Grenzen.

- Die unveränderte Maske wird skelettiert; höchstens 40 Enden werden gemeinsam
  geprüft. Jedes Ende braucht genau einen gültigen Partner. Es gibt keine
  Auswahl nach dem nächsten Nachbarn und keine Suche alternativer Paarungen.
- Ein Linienabbruch braucht **10–32 Pixel Abstand zwischen den Skelettenden**.
  Beide Endarme müssen zehn unverzweigte Skelettschritte nach außen führen.
  Richtungsabweichung zur Verbindung: Kosinus > 0,95; seitliche Abweichung:
  höchstens 3 Pixel. Dies begrenzt die örtliche Krümmung.
- Die ursprüngliche Maske muss entlang der Verbindung genau drei Läufe zeigen:
  Endstrang, mindestens drei weiße Pixel, Endstrang. Ein querender oder
  zusätzlicher dunkler Lauf ist kein gewöhnlicher Linienabbruch.
- In der Umgebung mit Radius halbem Endabstand plus vier Pixeln um die Mitte
  dürfen nur die beiden geprüften Skelettarme vorkommen, ohne Verzweigungen.
  Originale Vordergrundpixel müssen höchstens acht Pixel von diesen Armen
  entfernt liegen. Das berücksichtigt Strichbreite und Skelettversatz;
  Fremdstrukturen werden nicht ausgeschnitten oder gelöscht.
- Alle Lückenmitten einschließlich der Kreuzungsbelege müssen mindestens
  48 Pixel auseinanderliegen. Nach der Ergänzung muss die Mitte einer
  gewöhnlichen Linienlücke mindestens 24 Pixel von jeder feinen Kreuzungsregion
  entfernt sein.
- Nur geprüfte Verbindungen werden als ein Pixel breite Mittellinien ergänzt,
  mit orthogonalen Zwischenpixeln bei Diagonalschritten. Die vollständige Maske
  durchläuft anschließend alle Zusammenhangs-, Euler-, Skelett-, Graph- und
  Einbettungsprüfungen aus AP-04. Ein einzelner geschlossener Strang ist Pflicht.

Die gemeinsamen Grenzen sind 20 Ergänzungen, 1200×900 Bildpixel,
200000 Vordergrundpixel auch nach Ergänzung, 100000 Skelettpixel,
128 Skelettierungsiterationen, drei Einbettungsraster, 500 Stützpunkte und
100000 Exportpunkte. Die Eingabepixel bleiben unverändert.

Diese lokale Bildkonvention belegt keine Zeichenabsicht. Zwei getrennt gedachte
Linien können dieselbe Ausrichtung besitzen; die Sichtkontrolle jeder Ergänzung
bleibt erforderlich. Lange, stark gekrümmte, nahe oder mehrdeutige Lücken,
fehlende Überstränge, Beschriftungen, starke Papiertextur, abrupte Schatten und
Entzerrung sind nicht allgemein unterstützt. Die Topologieprüfung bezieht sich
auf die ergänzte Maske.

## Bericht und Herkunft

Annotationsversion 1 und `recognition.algorithm: skeleton-orthogonal-v1`
bleiben erhalten. Der optionale Bericht `recognition.line_gaps` enthält:

| Feld | Bedeutung |
|---|---|
| `algorithm` | `local-line-gaps-v1` |
| `evidence` | Belege in der deterministischen Reihenfolge der ursprünglichen Skelettenden |
| `evidence[].endpoints` | zwei ursprüngliche Skelettenden in Bildpixeln |
| `evidence[].added_pixels` | Anzahl ergänzter Vordergrundpixel (3–64) |

`crossing_gaps` behält sein separates Format. `inferred_crossings` zählt nur
belegte Überführungen; Linienabbrüche erhöhen diesen Zähler nicht.
`foreground_pixels` und ein zusätzlicher Scan-Bericht beschreiben die
ursprüngliche Maske; Skelett- und Gitterzähler die ergänzte Rekonstruktion.

JavaScript und Python prüfen Typen, Pixelgrenzen, Endabstände, Ergänzungszähler,
das gemeinsame Beleglimit, einmalige Endverwendung und Kreuzungszähler.
Speichern/Laden erhält beide Lückenberichte sowie Scan-Parameter. Manuelle
Kreuzungswahlen erhalten die anfänglichen Belege; Änderungen an Geometrie oder
Raster verwerfen sie. Die Bilddatei bleibt separat. JSON-Import validiert
Berichtstruktur und Diagrammgeometrie; zur erneuten Pixelprüfung ist die Vorlage
mit denselben Parametern erneut zu erkennen.

Die Exportquelle heißt `reviewed_line_gap_annotation`. Die Galerie zeigt
Linienergänzungen, belegte Überführungen, anfangs offene Wahlen und gegebenenfalls
Scan-Parameter und erinnert an den Vergleich mit der Vorlage.

## Abnahme

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:TEMP = Join-Path (Get-Location) '.test_tmp'
$env:TMP = $env:TEMP
python -m unittest discover -s tests
node tests/test_line_gap_tracer_runtime.cjs
node tests/test_gallery_runtime.cjs examples/line_gap_trace/index.html
```

Die Laufzeitprüfung verwendet echte PNG-Pixel, Vierteldrehungen und eine freie
Drehung, Spiegelung mit erwarteter Händigkeit, verschiedene Strichbreiten,
mehrere Linienabbrüche, einen Unknoten und die Scan-Aufbereitung. Gegenbeispiele
prüfen zu kurze/lange/nahe Lücken, offene Linien, zusätzliche Striche und
Fremdpixel. JavaScript/Python prüfen fehlerhafte und wiederverwendete Belege,
Entwurfssperre, Herkunft, Klassifikation, Gittervalidierung und den exakten
Turtle-Roundtrip. Das DOM-Modell prüft beide Knöpfe, Ergänzungszähler,
Fehlererholung, Speichern/Laden, manuelle Wahlen und veraltete Herkunft.

Vorlage und Kontrollüberlagerung wurden visuell geprüft. Eine manuelle
Browserprüfung oder eine Abnahme beliebiger realer Papierscans ist nicht Teil
dieser Abnahme.
