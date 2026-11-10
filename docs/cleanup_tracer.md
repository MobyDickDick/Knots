# Kleine isolierte Fremdkomponenten in Scans (AP-08)

Status: **umgesetzt am 10.11.2026**. Nach AP-07 war kein weiteres nummeriertes
Arbeitspaket festgelegt. AP-08 konkretisiert den dokumentierten offenen Bereich
„Beschriftungen und starke Papierstrukturen“ für kleine, isolierte Tintenflecken
und einzelne kleine Zeichen. Allgemeine Schrift- oder Papierstrukturerkennung
bleibt offen. Die Verarbeitung läuft offline ohne Zusatzpakete.

## Bedienung

1. `examples/image_tracer.html` öffnen und eine lokale Scan-Vorlage laden.
2. „Kleine Fremdkomponenten entfernen: bis … Pixel“ auf einen Wert von 1 bis 64
   stellen. **0 schaltet die Bereinigung aus** und ist der Standard.
   Die Grenze zählt schwarze Pixel einer zusammenhängenden Komponente nach
   der lokalen Helligkeitskorrektur, nicht die Fläche ihres Begrenzungsrechtecks.
3. „Scan-Vorschau“ wählen. Die bereinigte Maske zeigt entfernte Komponenten
   in **violetten Rechtecken**. Jede Stelle mit dem Original vergleichen.
4. Einen der drei Scan-Erkennungsknöpfe wählen. Alle berechnen die Maske mit den
   aktuellen Parametern neu; Linien- und Kreuzungslücken bleiben eigene,
   separat geprüfte Ergänzungen. Die Vorschau zeigt die Maske vor Ergänzungen.
5. Pfad und Kreuzungswahlen mit der Vorlage vergleichen. Durchgezogene
   Kreuzungen brauchen weiterhin manuelle Wahlen. Entwurf oder Annotation
   speichern und den vorhandenen Python-Export verwenden:

   ```bash
   python -m knots_grid.image_tracer trace annotation.json --output traced_cleanup
   ```

Vorschau und Erkennung verändern die Eingabepixel nicht. Fehler übernehmen
keine Teilbereinigung und erhalten Zeichnung, Raster und bisherige Vorschau.
Parameteränderungen verwerfen die Vorschau; die Herkunft der bestehenden
Zeichnung ändert sich erst bei erfolgreicher neuer Erkennung. Import stellt die
verwendete Komponentengrenze wieder her, bei älteren Annotationen den Wert 0.
Geometrie- oder Rasteränderungen verwerfen wie bisher den gesamten Bericht.

## Algorithmus und Grenzen

`ScanPreprocessor.prepare(image, {cleanup: 16})` beziehungsweise
`ScanTracer.recognize(image, {cleanup: 16})` aktiviert die Bereinigung.
Radius, Mindestkontrast und die Optionen `gaps`/`lineGaps` bleiben kombinierbar.
Die Reihenfolge ist Helligkeitskorrektur → Komponentenprüfung → Entfernung →
vollständige bisherige Skelett-/Graph-/Einbettungsprüfung.

- Alle schwarzen Pixel werden mit **8er-Nachbarschaft** in Komponenten zerlegt.
  Diagonal benachbarte Pixel gehören zur selben Komponente.
- Jede Komponente bis zur eingestellten Pixelgrenze ist ein Entfernungskandidat.
  Größere Komponenten bleiben vollständig erhalten. Es gibt keine Auswahl
  der größten Komponente und keine Interpretation als Buchstabe oder Knoten.
- Höchstens 32 Kandidaten und insgesamt 1024 zu entfernende Pixel sind erlaubt.
  Mindestens eine größere Komponente muss erhalten bleiben.
- Kein Kandidat darf den Bildrand berühren. Jeder Kandidatenpixel braucht
  **mindestens 12 Pixel Chebyshev-Abstand** zu jedem Pixel jeder anderen
  Komponente, auch zu anderen Entfernungskandidaten. Abstand 11 wird abgelehnt,
  Abstand 12 ist erlaubt. Es gibt keine Glättung, Zerlegung oder Teilentfernung.
- Scheitert eine Bedingung, wird die gesamte Bereinigung zurückgewiesen.
  Andernfalls werden ausschließlich die geprüften Komponenten weiß gesetzt.
- Die verbleibende Maske muss alle bestehenden Topologieprüfungen bestehen.
  Mehrere größere Komponenten, offene Linien und Fremdstrukturen werden dadurch
  nicht automatisch akzeptiert. Eine Kreuzungswahl wird nie aus einer
  Entfernung abgeleitet.

Die Bildgrenzen von 1200×900 und 200000 Vordergrundpixeln gelten bereits **vor**
der Bereinigung. Markierung und Bericht folgen der deterministischen
Zeilenreihenfolge der Komponenten. Laufzeit und Speicher sind durch die
Bildgrenze, 32 Kandidaten, 64 Pixel je Kandidat und den festen Suchradius begrenzt.

Kleine isolierte Teile eines absichtlich gezeichneten Diagramms können dieselben
Pixelmerkmale wie ein Fleck besitzen. Die Bereinigung ist deshalb ausdrücklich
zuschaltbar und benötigt die Sichtkontrolle jeder Entfernung. Die Graphprüfung
belegt nur die reguläre Interpretation der **bereinigten Maske**. Nahe Schrift,
größere Zeichen, zusammenhängende Papiertextur, abrupte Schatten, lange oder
stark gekrümmte Linienabbrüche und Entzerrung sind weiterhin offen.

## Bericht und Beispiel

Annotationsversion 1 und die bestehenden Algorithmen bleiben erhalten.
Bei aktivierter Bereinigung enthält `recognition.preprocessing.cleanup`:

| Feld | Bedeutung |
|---|---|
| `algorithm` | `isolated-components-v1` |
| `max_area` | eingestellte Pixelgrenze, 1–64 |
| `clearance` | fester Mindestabstand 12 |
| `original_foreground_pixels` | schwarze Pixel vor der Bereinigung, höchstens 200000 |
| `removed_pixels` | Summe der entfernten Pixel, 0–1024 |
| `components` | höchstens 32 Komponenten in deterministischer Reihenfolge |
| `components[].bounds` | inklusives Rechteck `[x_min, y_min, x_max, y_max]` in Bildpixeln |
| `components[].pixels` | schwarze Pixel dieser Komponente |

`preprocessing.foreground_pixels` und `recognition.foreground_pixels` zählen
die Pixel **nach** der Bereinigung und **vor** eventuellen Lückenergänzungen.
Originalzähler = Ergebniszähler + entfernte Pixel. Auch eine aktivierte
Bereinigung ohne Entfernung erhält einen Bericht mit leerer Komponentenliste.
JavaScript und Python prüfen Typen, Grenzen, Rechtecke und Summen. Ein JSON-Import
prüft Berichtstruktur und Diagrammgeometrie; eine erneute Pixelprüfung benötigt
das Originalbild und dieselben Erkennungsparameter.

Die Exportquelle bleibt `reviewed_scan_annotation` beziehungsweise bei
Lückenergänzung die bisherige Lückenquelle. Galerie und Status nennen
Komponenten- und Pixelzahlen; JSON, Gitter-/Turtle-Daten und Galerie erhalten
den vollständigen Bericht. Die Vorlage bleibt eine separate Datei.

```bash
node examples/make_cleanup_trace.cjs
```

`examples/cleanup_trace/` enthält eine simulierte Scan-PNG mit drei isolierten
3×3-Flecken, die bereinigte Maske, eine Kontrollüberlagerung mit violetten
Entfernungsmarkierungen, einen Entwurf, eine für diese Referenz manuell ergänzte
Annotation und die Offline-Galerie `index.html`. Genau 27 Pixel werden entfernt;
die Maske entspricht pixelgenau der sauberen AP-05-Referenz. Nach drei manuellen
Kreuzungswahlen entsteht ein Trefoil `T(2,3)` mit 3702 Gitterpunkten.

## Abnahme

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:TEMP = Join-Path (Get-Location) '.test_tmp'
$env:TMP = $env:TEMP
python -m unittest discover -s tests
node tests/test_cleanup_tracer_runtime.cjs
node tests/test_gallery_runtime.cjs examples/cleanup_trace/index.html
```

Die neue Laufzeitprüfung deckt echte PNG-Pixel, deterministische Masken,
Drehungen, Spiegelung, Strichbreiten, Transparenz, die Kombination beider
Lückenarten, 8er-Nachbarschaft, exakte Abstandsgrenzen, Randanschnitte,
nahe und verbundene Tinte, Größen-/Anzahl-/Gesamtgrenzen und offene Linien ab.
JavaScript/Python prüfen Berichtfehler, Entwurfssperre, JSON-Roundtrip,
Gittervalidierung, Klassifikation, exakten Turtle-Roundtrip und Galerieexport.
Das DOM-Modell prüft Zuschalten, Vorschau-Markierungen, Erkennung,
Fehlererholung, Import, manuelle Wahlen und Verwerfen veralteter Herkunft.
Maske und Kontrollüberlagerung wurden visuell geprüft. Eine manuelle
Browserprüfung oder Abnahme beliebiger realer Scans ist nicht Teil der Abnahme.

Abnahme am 10.11.2026: 102 Python-Tests, sieben Node-Editor-/Erkennungsprüfungen
und neun Galerieprüfungen erfolgreich.
