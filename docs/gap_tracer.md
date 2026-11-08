# Kreuzungslücken in freien Kurven (AP-06)

Status: **umgesetzt am 07.11.2026**. Dieser begrenzte Schritt erkennt kurze,
lokal annähernd gerade Unterbrechungen unter einem durchgezogenen querenden
Strang. Er ergänzt die freie Kurvenerkennung (AP-04) und kann mit der lokalen
Scan-Aufbereitung (AP-05) kombiniert werden. Alle Schritte laufen offline ohne
Zusatzpakete. [AP-07](line_gap_tracer.md) ergänzt einen eigenen Modus für kurze,
gerade Linienabbrüche ohne querenden Strang. Der AP-06-Modus behält die hier
beschriebenen Grenzen. Allgemeine unterbrochene Zeichnungen bleiben offen.

## Bedienung und Beispiel

1. `examples/image_tracer.html` öffnen und eine lokale Bildvorlage laden.
2. „Kurve mit Kreuzungslücken erkennen“ wählen; die Dunkel-Schwelle gilt wie
   bei der freien Kurvenerkennung. Für langsam veränderliche Beleuchtung und
   schwache Papiertextur „Scan mit Kreuzungslücken erkennen“ wählen. Dieser Weg
   benutzt den eingestellten Scan-Radius und Mindestkontrast statt der Schwelle.
   Die Scan-Vorschau bleibt die **ursprüngliche** lokale Maske vor Ergänzungen.
3. Den vollständigen Pfad und jede grüne Überführung mit der Vorlage vergleichen.
   Nur belegte Lücken erzeugen eine Wahl. Durchgezogene Kreuzungen bleiben
   orange und müssen manuell gewählt werden. Ein Klick auf eine grüne Kreuzung
   kann die Wahl auch nachträglich ändern.
4. Offene Wahlen mit „Entwurf speichern“ erhalten oder alle Wahlen ergänzen und
   „Zeichnung speichern“ verwenden. Ein Fehler übernimmt keine Teilrekonstruktion
   und erhält die bisherige Zeichnung, Rastereinstellungen und Vorschau.
5. Export wie bisher:

   ```bash
   python -m knots_grid.image_tracer trace annotation.json --output traced_gap
   ```

```bash
node examples/make_gap_trace.cjs
```

`examples/gap_trace/` enthält `gapped_trefoil.png`, die vollständig automatisch
gewählte `annotation.json`, Gitter-/Turtle-Daten und die Offline-Galerie
`index.html`. Das Ergebnis ist ein Trefoil `T(2,3)` mit drei belegten Kreuzungen,
144 Stützpunkten und 3702 Gitterpunkten. Der Generator gibt keine manuellen
Kreuzungswahlen vor. `overlay.png` zeigt den Pfad blau und die ursprünglichen
Enden sowie Kreuzungsbelege rot. `partial_trefoil.png` und `draft.json` zeigen
eine belegte und zwei offene Wahlen. `simulated_scan.png` mit
`scan_annotation.json` demonstriert die Kombination mit AP-05. Dies sind
synthetische, reproduzierbare Referenzen, keine Abnahme beliebiger Papierscans.

## Lokale Evidenz und Rekonstruktion

`CurveTracer.recognize(image, {threshold: 160, gaps: true})` ergänzt die reine
JavaScript-API. `ScanTracer.recognize(image, {radius: 24, contrast: 30,
gaps: true})` wendet dieselbe Prüfung auf die vollständige Scan-Maske an.
Die bisherigen Modi schließen weiterhin keine Lücken.

1. Die unveränderte Vordergrundmaske wird skelettiert. Die Nachbarschaft
   unterdrückt diagonale Abkürzungen genau wie AP-04. Isolierte Pixel sind
   Fehler. Höchstens 40 Enden werden geprüft; ihre Anzahl muss gerade sein.
2. Alle Endpaare im Abstand **10 bis 40 Bildpixel** werden endlich geprüft.
   Auf beiden Seiten müssen zehn Skelettschritte ohne Verzweigung in die
   Gegenrichtung weiterführen. Die Richtungsabweichung zur Verbindung beträgt
   höchstens etwa 18 Grad (Kosinus > 0,95); die Seitenabweichung höchstens 3 Pixel.
3. Auf der geraden Pixelverbindung muss die **ursprüngliche** Maske genau fünf
   abwechselnde Läufe zeigen: Endstrang, Weiß, querender Strang, Weiß, Endstrang.
   Jede weiße Schulter braucht mindestens zwei Pixel. Der mittlere dunkle Lauf
   darf höchstens die halbe Verbindung belegen und muss von beiden Enden
   mindestens 30 Prozent des Endabstands entfernt liegen.
4. Innerhalb von vier Pixeln vom mittleren Lauf muss ein durchgezogener
   Skelettstrang mit zwei unverzweigten Zehn-Schritt-Armen liegen. Seine Arme
   verlaufen entgegengesetzt und lokal gerade (höchstens 1,8 Pixel Abweichung).
   Sein Winkel zur Lückenverbindung liegt zwischen etwa 70 und 110 Grad.
5. Im Kreis um den Beleg mit Radius halbem Endabstand plus vier Pixeln dürfen
   weder Verzweigungen noch Skelettpixel außerhalb der beiden 3,5 Pixel breiten
   Linienkorridore vorkommen. Jedes ursprüngliche Ende muss **genau einen**
   gültigen Partner haben. Alle Belegzentren müssen mindestens 48 Pixel
   auseinanderliegen. Unbelegte, konkurrierende und zu nahe Fälle sind Fehler.
6. Nur diese geprüften Verbindungen werden als ein Pixel breite Mittellinien
   ergänzt. Diagonalschritte erhalten eine orthogonale Verbindung. Kein
   Originalpixel wird entfernt; das Eingabebild bleibt unverändert. Anschließend
   wird die gesamte ergänzte Maske durch Zusammenhangs-, Euler-, Skelett- und
   Graphprüfungen von AP-04 geführt. Ein einziger geschlossener Strang ist Pflicht.
7. Jeder Beleg muss zu genau einer feinen Kreuzungsregion passen. Die Richtungen
   der Lückenenden müssen zu gegenüberliegenden Armen gehören. Die Zuordnung
   zum gröberen Graphen bewahrt wie bisher zyklische Armordnung und alle
   Kettenverbindungen. Die anderen beiden Arme bestimmen die Überführung auch
   dann, wenn die lokale Gittereinbettung den mittleren Plusstern anders dreht.
   Vor der Rückgabe werden die exakten Segmentkreuzungen erneut geprüft.

Diese Bedingungen sind eine konservative Bildkonvention, kein Beweis der
Zeichenabsicht. Auch eine versehentliche Unterbrechung kann unter dieser
Konvention wie eine Unterführung aussehen. Die Sichtkontrolle bleibt nötig.
Die Euler-Prüfung bezieht sich ausdrücklich auf die **ergänzte** Maske; die
beabsichtigte Verbindung wird durch die lokalen Pixelbelege dokumentiert.

## Format und Herkunft

Annotationsversion 1 und `recognition.algorithm: skeleton-orthogonal-v1`
bleiben erhalten. Der optionale Bericht `recognition.crossing_gaps` enthält:

| Feld | Bedeutung |
|---|---|
| `algorithm` | `local-crossing-gaps-v1` |
| `evidence` | höchstens 20 lokale Belege, sortiert nach Gitterkreuzungskoordinaten |
| `evidence[].endpoints` | die zwei ursprünglichen Skelettenden in Bildpixeln |
| `evidence[].crossing_pixel` | ursprünglicher Pixel des durchgezogenen Überstrangs |
| `evidence[].added_pixels` | ergänzte Vordergrundpixel für diese Verbindung (4–80) |
| `evidence[].coordinate` | zugeordnete Kreuzung der rechtwinkligen Annotation |
| `evidence[].over_segment` | ursprünglich aus dem Beleg bestimmter oberer Abschnitt |

`inferred_crossings` entspricht der Belegzahl; `unresolved_crossings` zählt
die anfangs offenen Kreuzungen. `foreground_pixels` zählt die ursprüngliche
Maske, `skeleton_pixels` und `grid_edges` die ergänzte Rekonstruktion. Ein
zusätzlicher AP-05-Bericht behält ebenfalls seinen ursprünglichen Maskenzähler.
Ohne Lückenbelege bleibt die Zahl automatisch gewählter Kurvenkreuzungen null.

JavaScript und Python prüfen Typen, Grenzen, Zähler, eindeutige Koordinaten und
die Zuordnung der belegten Abschnitte zu echten Segmentkreuzungen. Die Bilddatei
bleibt separat: Ein JSON-Import überprüft die Berichtstruktur und Geometrie,
liest aber keine Bildpixel. Zur Pixelprüfung dieselbe Vorlage mit denselben
Parametern erneut erkennen und die deterministischen Belege vergleichen.
Nachträgliche manuelle Wahlen verändern die anfänglichen Belege nicht.
Geometrie- und Rasteränderungen verwerfen den Bericht wie bisher.

Der Python-Export nennt die Quelle `reviewed_gap_annotation`. Die Galerie zeigt
„Kurve mit Kreuzungslücken“, die Belegzahl, anfangs offene Wahlen und gegebenenfalls
Scan-Parameter. Sie weist auf mögliche nachträgliche manuelle Änderungen hin.

## Grenzen und Abnahme

Es gelten die AP-04-Grenzen von 1200×900 Pixeln, 200000 Vordergrundpixeln,
100000 Skelettpixeln, 128 Skelettierungsiterationen, 500 Stützpunkten und 100000
Exportpunkten. Nach der Ergänzung wird die Vordergrundgrenze erneut geprüft.
Zusätzlich gelten höchstens 40 Enden/20 Belege und die obigen lokalen Abstände.
Die Suche versucht keine alternativen Verbindungsnetze nach einem Fehler.

Sehr kurze oder lange Lücken, stark gekrümmte Unterbrechungen, fehlende oder
unterbrochene Überstränge, flache Kreuzungswinkel, nahe Kreuzungen,
Beschriftungen und Fremdpixel sind nicht allgemein unterstützt. Starke Textur,
abrupte Schatten und Entzerrung bleiben offen. Eine kleinere Bildskalierung
kann lokale Evidenz verlieren; der Editor arbeitet auf den eingepassten Pixeln.

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:TEMP = Join-Path (Get-Location) '.test_tmp'
$env:TMP = $env:TEMP
python -m unittest discover -s tests
node tests/test_gap_tracer_runtime.cjs
node tests/test_gallery_runtime.cjs examples/gap_trace/index.html
```

Abnahme am 07.11.2026: 100 Python-Tests, fünf Node-Editor-/Erkennungsprüfungen
und sieben Galerieprüfungen erfolgreich. Die neuen Prüfungen verwenden echte
PNG-Pixel und testen Drehungen, Spiegelungen, umgekehrte Überführungen,
Strichbreiten, gemischte offene/belegte Kreuzungen, ungültige Belege, Grenzen,
fehlende Überstränge, Fremdpixel und Scan-Aufbereitung. Für alle vollständigen
Varianten werden die erwartete Trefoil-Händigkeit, Gittervalidierung und der
exakte Turtle-Roundtrip geprüft. Das DOM-Modell prüft beide neuen Knöpfe,
Fehlererholung, Entwürfe, Speichern/Laden, manuelle Änderungen und das Verwerfen
veralteter Herkunft. Vorlage und Überlagerung wurden visuell geprüft;
eine manuelle Browserprüfung und reale Papierscans sind nicht Teil der Abnahme.
