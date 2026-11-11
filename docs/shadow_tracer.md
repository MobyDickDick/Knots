# Abrupte achsenparallele Schattenkanten (AP-10)

Status: **umgesetzt am 11.11.2026**.

AP-01 bis AP-09 waren abgeschlossen; ein weiteres nummeriertes Paket war nicht
festgelegt. AP-10 konkretisiert den dokumentierten offenen Punkt „abrupte
Beleuchtungswechsel“ für einzelne senkrechte oder waagrechte Schattenkanten
bei ausreichend dünner, kontrastreicher Tinte. Allgemeine Schatten- und
Papierstrukturerkennung bleiben offen.

## Bedienung

1. `examples/image_tracer.html` öffnen und eine lokale Vorlage laden.
2. „Abrupte Schattenkanten berücksichtigen“ einschalten. Standard ist aus;
   dann bleiben Verfahren und Berichtsformat von AP-05 erhalten.
3. „Scan-Vorschau“ wählen und die gesamte Maske mit dem Original vergleichen.
   Fensterradius und Mindestkontrast bei Bedarf einstellen. Der Radius muss
   deutlich größer als die Strichbreite sein. Standard: 24 und 30.
4. Einen der drei Scan-Erkennungsknöpfe wählen. Beide Lückenarten, längere
   Linienlücken und die Fremdkomponentenbereinigung sind kombinierbar.
5. Pfad, Ergänzungen, entfernte Komponenten und Über-/Unterwahlen prüfen.
   Schatten erzeugen keine Kreuzungswahl. Offene Wahlen bleiben im Entwurf;
   vor dem Gitterexport müssen sie ausdrücklich ergänzt werden.

```bash
python -m knots_grid.image_tracer trace annotation.json --output traced_shadow
```

Parameteränderungen verwerfen die Vorschau; die bestehende Zeichnung behält
ihre Herkunft bis zu einer erfolgreichen neuen Erkennung. Fehler erhalten
Zeichnung, Raster und bisherige Vorschau. Import stellt den Schalter aus dem
Bericht wieder her; Altdaten und Annotationen ohne Scan-Bericht schalten ihn
aus. Änderungen an Geometrie oder Raster verwerfen veraltete Herkunft.

## Algorithmus und Grenzen

`ScanPreprocessor.prepare(image, {directional:true, radius:24, contrast:30})`
aktiviert `local-quadrant-v1`. Dieselben Optionen gelten für
`ScanTracer.recognize`. `directional` akzeptiert ausschließlich boolesche Werte.
Alpha wird wie bisher gegen Weiß verrechnet, anschließend wird die gewichtete
Helligkeit gerundet und ein Summenbild erzeugt. Eingabepixel bleiben unverändert.

Für jeden Pixel werden die vier quadratischen Kontexte mit Seitenlänge
`radius + 1` betrachtet, in denen er jeweils eine Ecke bildet. Nur vollständig
im Bild liegende Quadrate zählen. Der **kleinste** ihrer mittleren
Helligkeitswerte dient als Hintergrundschätzung. Ein Pixel wird Vordergrund,
wenn er mindestens `contrast` dunkler ist. Bei einer senkrechten oder
waagrechten Schattenkante kann dadurch ein Kontext auf der dunklen Papierseite
die künstliche Schattenlinie des bisherigen symmetrischen Mittelwerts vermeiden.
Es gibt keine automatische Wiederholung, Parametersuche oder Glättung.

Das Bild muss je Achse mindestens `2 * radius + 1` Pixel groß sein. Damit hat
jeder Pixel mindestens einen vollständigen Kontext. Ein auf einen einzigen
Randpixel beschnittenes Quadrat könnte Tinte verschlucken und wird ausdrücklich
nicht verwendet. Laufzeit und Speicher bleiben linear in der Pixelzahl.
Die Grenzen 1200×900 Pixel, Radius 8–80, Kontrast 5–100 und 200000
Vordergrundpixel sowie sämtliche Graph-, Topologie- und Exportbudgets bleiben
erhalten. Bereinigung und Lückenrekonstruktion folgen erst nach der Schätzung.

Die dunklere Schätzung kann breite oder schwache Striche verlieren. Im
Strichbreiten-Test braucht ein Radius von fünf Pixeln deshalb einen größeren
Fensterradius von 40. Sehr dunkle Schatten, schräge Schatten am Bildrand,
mehrere nahe Schattenkanten, feine Papierstrukturen und Schrift sind nicht
allgemein unterstützt. Die Tests enthalten abgelehnte Gegenbeispiele; daraus
folgt keine Garantie, jede ungeeignete Vorlage automatisch abzulehnen.
Die Graphprüfung belegt die reguläre Interpretation der Maske, keine
Zeichenabsicht oder Übereinstimmung mit dem Original. Die Sichtkontrolle bleibt
erforderlich.

## Bericht und Beispiel

Annotationsversion 1 bleibt bestehen. `recognition.preprocessing.algorithm`
lautet im neuen Modus `local-quadrant-v1`, sonst unverändert `local-mean-v1`.
`window_radius`, `contrast`, `foreground_pixels`, `background_min` und
`background_max` bleiben erhalten. Die beiden Hintergrundgrenzen bezeichnen
jetzt die gerundeten gewählten Quadrantenmittelwerte. Optionale
Bereinigungsberichte und beide Lückenberichte bleiben getrennt erhalten.
JavaScript und Python prüfen auch die neuen Verfahrensnamen und die dafür
notwendigen Bildmaße. Import prüft Struktur und Diagramm; für eine erneute
Pixelprüfung ist die Bilddatei nötig.

Der Export verwendet weiter `reviewed_scan_annotation` beziehungsweise bei
Lücken die bestehenden Quellen. Die Galerie zeigt das Scan-Verfahren als
„Gerichtete Schattenkorrektur“ sowie Radius und Mindestkontrast.

```bash
node examples/make_shadow_trace.cjs
```

`examples/shadow_trace/` enthält die simulierte Vorlage `abrupt_shadow.png`,
`mask.png`, `overlay.png`, `draft.json`, die explizit für diese Referenz
ergänzte `annotation.json`, Gitter-/Turtle-Daten und die Offline-Galerie.
Die Papierhelligkeit wechselt abrupt von ungefähr 150 auf 245, mit schwacher
synthetischer Textur. Die Maske stimmt pixelgenau mit der sauberen Referenz
überein. Nach drei ausdrücklich gesetzten Kreuzungswahlen entsteht ein Trefoil
`T(2,3)` mit Determinante 3 und 3702 Gitterpunkten.

## Abnahme

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:TEMP = Join-Path (Get-Location) '.test_tmp'
$env:TMP = $env:TEMP
python -m unittest discover -s tests
node tests/test_shadow_tracer_runtime.cjs
node tests/test_gallery_runtime.cjs examples/shadow_trace/index.html
```

Die Laufzeitprüfung verwendet echte PNG-Pixel, unabhängige saubere Referenzen,
senkrechte und waagrechte Schatten an mehreren Positionen, tatsächliche
Bilddrehung, gedrehte Kurven, Spiegel, Strichbreiten, Transparenz und sämtliche
Scan-Modi einschließlich Bereinigung und langer Linienlücken. Sie prüft
abgelehnte Gegenbeispiele, Parameter- und Bildgrenzen, erhaltene Randtinte,
Altdaten, ungültige Berichte, Entwurfssperre, Klassifikation und Händigkeit bei
pixelbelegten Kreuzungswahlen, exakten Turtle-Roundtrip und Herkunft.
Das DOM-Modell prüft Zuschaltung, Vorschau, Fehlererholung, Parameterwechsel,
Import, manuelle Kreuzungswahl und das Verwerfen veralteter Herkunft.
Maske und Kontrollüberlagerung wurden visuell geprüft. Keine manuelle
Browserprüfung oder Abnahme beliebiger realer Scans.

Abnahme am 11.11.2026: 104 Python-Tests, neun Node-Editor-/Erkennungsprüfungen
und elf Galerieprüfungen erfolgreich.
