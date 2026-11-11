# Längere gerade Linienabbrüche (AP-09)

Status: **umgesetzt am 11.11.2026**. Nach AP-08 war kein weiteres nummeriertes
Arbeitspaket festgelegt. AP-09 konkretisiert den dokumentierten offenen Punkt
„lange Linienabbrüche“ für isolierte, gerade Lücken bis 64 Pixel Endabstand.
Beliebige lange oder gekrümmte Unterbrechungen bleiben offen.

## Bedienung

1. `examples/image_tracer.html` öffnen und die lokale Vorlage laden.
2. „Längere Linienlücken zulassen (bis 64 Pixel)“ einschalten. Standard ist aus;
   dann bleibt die AP-07-Grenze von 32 Pixeln erhalten.
3. „Kurve mit Linienlücken erkennen“ oder „Scan mit Linienlücken erkennen“
   wählen. Der Schalter gilt nur für diese beiden Modi. Scan-Aufbereitung,
   Fremdkomponentenbereinigung und Kreuzungslücken bleiben kombinierbar.
4. Jede rote Ergänzung sowie Pfad und Kreuzungswahlen mit dem Original
   vergleichen. Ausrichtung und Freiraum belegen keine Zeichenabsicht.
5. Annotation oder Entwurf speichern; offene Kreuzungswahlen müssen vor dem
   Gitterexport ergänzt werden. Der bestehende Export bleibt unverändert:

   ```bash
   python -m knots_grid.image_tracer trace annotation.json --output traced_long_gap
   ```

Import stellt die Zuschaltung aus dem Bericht wieder her; alte Annotationen
schalten sie aus. Ein Wechsel des Schalters betrifft die nächste Erkennung.
Die Herkunft einer bestehenden Zeichnung bleibt bis zu einer erfolgreichen
neuen Erkennung erhalten. Fehler erhalten Zeichnung, Raster und Scan-Vorschau.
Geometrie- und Rasteränderungen verwerfen wie bisher veraltete Herkunft.

## Prüfung und Grenzen

`CurveTracer.recognize(image, {lineGaps:true, gaps:true, maxLineGap:64})` und
`ScanTracer.recognize(image, {lineGaps:true, gaps:true, maxLineGap:64})`
aktivieren die Erweiterung. `maxLineGap` akzeptiert ausschließlich die ganzen
Zahlen 32 und 64; Standard ist 32. Die Erweiterung verändert die Regeln für
Kreuzungslücken nicht: deren Endabstand bleibt auf 10–40 Pixel begrenzt.

Für gewöhnliche Lücken bis einschließlich 32 Pixel gelten weiterhin die
[AP-07-Regeln](line_gap_tracer.md). Bei mehr als 32 bis einschließlich 64 Pixeln:

- Beide Endarme müssen jeweils `ceil(Endabstand / 2)` unverzweigte
  Skelettschritte lang sein. Sie müssen auf der abgewandten Seite der Lücke
  liegen, Richtungskosinus > 0,985 und höchstens zwei Pixel seitlichen
  Abstand zur Verbindungsgeraden besitzen.
- Die ursprüngliche Pixelmaske muss weiterhin genau die Läufe Endstrang,
  mindestens drei weiße Pixel, Endstrang zeigen. Fremde dunkle Läufe oder ein
  querender Strang begründen keinen gewöhnlichen Linienabbruch.
- Der Prüfradius um die Lückenmitte wächst auf halben Endabstand plus zwölf
  Pixel. Jeder Skelettpixel in dieser Scheibe muss zu den geprüften Armen
  gehören und unverzweigt sein; jeder ursprüngliche Tintenpixel muss höchstens
  acht Pixel von einem dieser Arme entfernt sein. Die Maske wird dafür nicht
  geglättet und Fremdtinte nicht entfernt.
- Die Mitte muss mindestens diesen Radius von jeder rekonstruierten feinen
  Kreuzungsregion entfernt sein. Zwischen Lückenmitten ist mindestens die
  Summe ihrer Schutzradien nötig; kurze Linien- und Kreuzungslücken verwenden
  dafür weiterhin jeweils 24 Pixel.

Alle ursprünglichen Enden brauchen gemeinsam genau einen gültigen Partner.
Mehrdeutige Paarungen führen zum Fehler, ohne Auswahl eines nächsten Nachbarn
oder Teilübernahme. Nur geprüfte Mittellinien werden ergänzt. Die vollständige
Maske durchläuft anschließend sämtliche Zusammenhangs-, Euler-, Skelett-,
Graph- und Einbettungsprüfungen aus AP-04. Ein einzelner geschlossener Strang
ist Pflicht. Gewöhnliche Linienabbrüche erzeugen keine Über-/Unterwahl.

Die gemeinsamen Budgets bleiben 20 Lückenergänzungen, 40 Enden, 1200×900
Bildpixel, 200000 Vordergrundpixel auch nach Ergänzung, 100000 Skelettpixel,
128 Skelettierungsiterationen, drei Einbettungsraster, 500 Stützpunkte und
100000 Exportpunkte. Eingabepixel bleiben unverändert. Die Topologieprüfung
bezieht sich auf die ergänzte Maske; sie beweist keine Übereinstimmung mit
einer unbekannten Zeichenabsicht. Gekrümmte, nahe, fremdbelegte oder mehrdeutige
Lücken und beliebige reale Scans sind nicht allgemein unterstützt.

## Bericht und Beispiel

Ohne Zuschaltung bleibt `recognition.line_gaps.algorithm: local-line-gaps-v1`
bytegleich im bisherigen Format. Mit Zuschaltung wird der Bericht als
`local-line-gaps-v2` mit obligatorischem `max_distance:64` gespeichert, auch
wenn keine lange Lücke gefunden wurde. Das vermeidet eine stillschweigende
Erweiterung alter Berichte. `evidence` enthält wie bisher ursprüngliche
Skelettenden und `added_pixels`, jetzt mit Obergrenze 128 statt 64. Die höhere
Pixelzahl berücksichtigt orthogonale Zwischenpixel bei diagonalen Brücken.
JavaScript und Python prüfen Version, Grenzwert, Koordinaten, Endabstand,
Pixelzahlen, gemeinsame Budgets und einmalige Endverwendung. Ein JSON-Import
prüft Berichtstruktur und Diagramm; eine erneute Pixelprüfung braucht das Bild.

Die Exportquelle bleibt `reviewed_line_gap_annotation`. Die Galerie nennt
Ergänzungszahl und maximalen Endabstand. Kreuzungsbelege, Scan-Parameter und
gegebenenfalls entfernte Fremdkomponenten bleiben separat erhalten.

```bash
node examples/make_long_line_gap_trace.cjs
```

`examples/long_line_gap_trace/` enthält eine synthetische Trefoil-PNG mit einer
55 Pixel langen geraden Unterbrechung und drei Kreuzungslücken, vollständige
Annotation, Kontrollüberlagerung, teiloffenen Entwurf, simulierte Scan-Variante
und Offline-Galerie. Ohne manuelle Kreuzungswahl entsteht ein Trefoil `T(2,3)`
mit Determinante 3 und 3702 Gitterpunkten. Die Vorlage besitzt für dieses
Beispiel einen geraden Bogen; die ursprüngliche runde AP-07-Kurve mit langer
Unterbrechung wird wegen ihrer gekrümmten Arme ausdrücklich abgelehnt.

## Abnahme

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:TEMP = Join-Path (Get-Location) '.test_tmp'
$env:TMP = $env:TEMP
python -m unittest discover -s tests
node tests/test_long_line_gap_tracer_runtime.cjs
node tests/test_gallery_runtime.cjs examples/long_line_gap_trace/index.html
```

Die Prüfungen decken echte PNG-Pixel, unveränderte Eingabe, deterministische
Erkennung, 32/33/64/65-Pixel-Grenzen, die genaue Trennung zweier langer Lücken
bei 88 statt 87 Pixeln, längere und gekrümmte Gegenbeispiele, störende Tinte,
Drehungen, Spiegel/Händigkeit, Strichbreiten, Transparenz, Scan-Kombination,
Altdaten, fehlerhafte Berichte, Entwurfssperre, Klassifikation, Gittervalidierung
und exakten Turtle-Roundtrip ab. Das DOM-Modell prüft die Zuschaltung für beide
Modi, Fehlererholung, Import alter und neuer Berichte, manuelle Kreuzungswahl
und das Verwerfen veralteter Herkunft. Vorlage und Kontrollüberlagerung wurden
visuell geprüft. Eine manuelle Browserprüfung ist nicht Teil der Abnahme.

Abnahme am 11.11.2026: 103 Python-Tests, acht Node-Editor-/Erkennungsprüfungen
und zehn Galerieprüfungen erfolgreich.
