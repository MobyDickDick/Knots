# Scan-Aufbereitung (AP-05)

Status: **umgesetzt am 06.11.2026**. Dieser erste Teil der dokumentierten
Scan-Ausbaustufe ergänzt AP-04 um eine lokale Helligkeitskorrektur und die
Unterdrückung schwacher Papiertextur durch einen einstellbaren Mindestkontrast.
Er verarbeitet durchgezogene dunkle Kurven auf hellerem Papier offline ohne
Zusatzpakete. Eine allgemeine Erkennung beliebiger Scans ist weiterhin offen.

## Bedienung

1. `examples/image_tracer.html` öffnen und die lokale Bildvorlage laden.
2. „Scan-Vorschau“ wählen. „Aufbereitete Maske anzeigen“ schaltet zwischen
   Schwarzweißmaske und Original um; „Bild anzeigen“ blendet beide aus.
3. Bei Bedarf Fensterradius und Mindestkontrast einstellen und die Vorschau
   erneut berechnen. Der Radius muss deutlich größer als die Strichbreite sein.
   Der Mindestkontrast muss unterhalb des lokalen Linienkontrasts, aber oberhalb
   der schwachen Papiertextur liegen. Standard: Radius 24, Mindestkontrast 30.
   Die Dunkel-Schwelle der übrigen Erkennungsmodi wird hier nicht verwendet.
4. Die **gesamte** Maske mit der Vorlage vergleichen, insbesondere feine
   Schleifen, enge Nachbarschaften und Kreuzungen. Anschließend
   „Scan-Kurve erkennen“ wählen. Dieser Knopf berechnet immer eine neue Maske
   mit den aktuellen Parametern, auch ohne vorherige Vorschau.
5. Den Pfad mit der Vorlage vergleichen und alle Über-/Unterführungen manuell
   wählen. Offene Wahlen können als Entwurf gespeichert werden; der endgültige
   Gitterexport bleibt gesperrt. Zeichnung speichern und wie bisher exportieren:

   ```bash
   python -m knots_grid.image_tracer trace annotation.json --output traced_scan
   ```

Die Vorschau verändert weder Stützpunkte noch Kreuzungswahlen. Fehler bei der
Aufbereitung oder Graphprüfung erhalten Zeichnung, Raster und vorhandene
Vorschau. Parameteränderungen verwerfen die alte Vorschau. Eine gespeicherte
Annotation behält die tatsächlich verwendeten Parameter; Änderungen an den
Bedienelementen verändern ihre Herkunft erst bei einer neuen Erkennung.
Geometrie- und Rasteränderungen verwerfen den Erkennungsbericht wie bisher.

## Algorithmus und Grenzen

`ScanPreprocessor.prepare(imageData, {radius: 24, contrast: 30})` liefert eine
neue Schwarzweiß-RGBA-Maske und einen Bericht. Das Original bleibt unverändert.
`ScanTracer.recognize(imageData, options)` führt anschließend AP-04 aus.

- Alpha wird gegen Weiß verrechnet; die gewichtete Helligkeit wird auf ganze
  Werte von 0 bis 255 gerundet.
- Ein Summenbild bestimmt für jeden Pixel den mittleren Helligkeitswert im
  quadratischen Fenster mit Seitenlänge `2 * radius + 1`. Am Bildrand wird das
  Fenster auf die vorhandenen Pixel beschnitten.
- Ein Pixel wird genau dann Vordergrund, wenn seine Helligkeit mindestens
  `contrast` unter dem lokalen Mittelwert liegt. Es gibt keine weitere
  Pixelbereinigung, Komponentenauswahl, morphologische Glättung oder Lückenschließung.
- AP-04 prüft auf der vollständigen Maske Zusammenhang, Euler-Charakteristik,
  Skelett, Kreuzungsregionen, Armreihenfolge, Kettenverbindungen, einen einzigen
  geschlossenen Strang und die exakten Segmentkreuzungen. Hochkontrastige
  Fremdpixel werden nicht entfernt und führen weiterhin zu Fehlern.

Die Aufbereitung braucht lineare Laufzeit und linearen Speicher in der Pixelzahl.
Die Grenzen sind 1200×900 Pixel, Radius 8–80, Mindestkontrast 5–100 und höchstens
200000 Vordergrundpixel. Danach gelten alle [AP-04-Grenzen](curve_tracer.md).
Es gibt keine unbegrenzte Parametersuche oder automatische Wiederholung.

Breite, langsam veränderliche Beleuchtung und kontrastarme Textur lassen sich
so von ausreichend dünnen, kontrastreichen Linien trennen. Abrupte Schatten,
starke Textur, sehr breite oder schwache Linien, Schrift und Flecken können
zusätzliche Strukturen erzeugen oder Linien verlieren. Die Graphprüfung belegt
die reguläre Interpretation der **Maske**, nicht deren Übereinstimmung mit der
Zeichenabsicht. Eine Schwellenoperation ist kein topologischer Beweis für das
Originalfoto. Daher ist die Sichtkontrolle erforderlich. Kreuzungslücken,
allgemeine Schrifterkennung, perspektivische Entzerrung und beliebige Scans
bleiben offen.

## Format und Beispiel

Annotationsversion 1 und `recognition.algorithm: skeleton-orthogonal-v1` bleiben
erhalten. Der zusätzliche Bericht `recognition.preprocessing` enthält:

| Feld | Bedeutung |
|---|---|
| `algorithm` | `local-mean-v1` |
| `window_radius` | Radius in Pixeln der eingepassten Bildvorlage |
| `contrast` | Mindestdifferenz zum lokalen Helligkeitsmittel |
| `foreground_pixels` | Anzahl schwarzer Maskenpixel; identisch zum Erkennungszähler |
| `background_min`, `background_max` | kleinster/größter gerundeter lokaler Mittelwert |

JavaScript und Python validieren und erhalten diese Felder. Rasterberichte
dürfen keinen Scan-Aufbereitungsbericht tragen. Der Python-Export nennt die
Quelle `reviewed_scan_annotation`. Die Galerie zeigt „Scan-Aufbereitung“,
Fensterradius, Mindestkontrast und den Hinweis auf manuell gewählte Überführungen.
Die Bilddatei und die Maske bleiben separate Dateien.

```bash
node examples/make_scan_trace.cjs
```

`examples/scan_trace/` enthält eine **simulierte** beschattete PNG-Vorlage mit
schwacher Papiertextur, `mask.png`, `overlay.png`, `draft.json`, die für diese
Referenz explizit ergänzte `annotation.json`, Gitter-/Turtle-Daten und die
Offline-Galerie `index.html`. Es handelt sich um einen reproduzierbaren
Akzeptanzfall, keine Erprobung an beliebigen echten Scans. Die Maske entspricht
hier pixelgenau der ursprünglichen sauberen Linienmaske. Das Ergebnis hat
144 Stützpunkte, drei zunächst offene Wahlen und nach deren Ergänzung einen
Trefoil `T(2,3)` mit Determinante 3 und 3702 Gitterpunkten.

## Abnahme

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:TEMP = Join-Path (Get-Location) '.test_tmp'
$env:TMP = $env:TEMP
python -m unittest discover -s tests
node tests/test_image_tracer_runtime.cjs
node tests/test_raster_tracer_runtime.cjs
node tests/test_curve_tracer_runtime.cjs
node tests/test_scan_tracer_runtime.cjs
node tests/test_gallery_runtime.cjs
node tests/test_gallery_runtime.cjs examples/travel_catalog/index.html
node tests/test_gallery_runtime.cjs examples/image_trace/index.html
node tests/test_gallery_runtime.cjs examples/raster_trace/index.html
node tests/test_gallery_runtime.cjs examples/curve_trace/index.html
node tests/test_gallery_runtime.cjs examples/scan_trace/index.html
```

Abnahme am 06.11.2026: 99 Python-Tests, vier Node-Editor-/Erkennungstests und
sechs Galerieprüfungen erfolgreich. Die Scanprüfung deckt die tatsächlichen
PNG-Pixel, Schatten, schwache und starke Textur, Drehung, Spiegelung,
Strichbreiten, Transparenz, Parametergrenzen, Fremdpixel, offene Linien,
Entwurfssperre, JSON-Roundtrip, Herkunft, Klassifikation, Gittervalidierung und
exakten Turtle-Roundtrip ab. Die tatsächlichen Editor-Ereignisbehandlungen
werden im Node-DOM-Modell für Vorschau, Erkennung, Fehlererholung,
Speichern/Laden, Parameter und manuelle Kreuzungswahl geprüft.
Maske und Kontrollüberlagerung wurden visuell geprüft. Eine manuelle
Browserprüfung und eine Abnahme an realen Papierscans sind nicht Teil davon.
