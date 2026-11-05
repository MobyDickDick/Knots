# Freie Kurven erkennen (AP-04)

Status: **umgesetzt am 05.11.2026** für saubere, durchgezogene dunkle
Kurvendiagramme auf hellem Grund. Die Erkennung läuft im Offline-Editor ohne
Netz oder Zusatzbibliotheken. Sie ergänzt AP-02/AP-03; gescannte Papierstrukturen
und automatische Über-/Untererkennung bei freien Kurven bleiben offen.

## Bedienung und Beispiel

1. `examples/image_tracer.html` öffnen, eine lokale Bildvorlage laden und
   „Freie Kurve erkennen“ wählen. Bei Bedarf die Dunkel-Schwelle einstellen.
2. Den rechtwinkligen Pfad mit der gesamten Vorlage vergleichen. Die Erkennung
   stellt ein feines Raster von 1, 2 oder 3 Pixeln ein; Kreuzungsregionen können
   dabei etwas anders als im Ausgangsbild verlaufen.
3. An **jeder** orangefarbenen Kreuzung den oberen Strang wählen. Durchgezogene
   Kreuzungen enthalten keine Über-/Unterinformation. Die Erkennung rät keine
   Wahlen. Unvollständige Ergebnisse lassen sich als Entwurf speichern/laden;
   der endgültige Export bleibt bis zur Vervollständigung gesperrt.
4. „Zeichnung speichern“, anschließend wie bisher exportieren:

   ```bash
   python -m knots_grid.image_tracer trace annotation.json --output traced_curve
   ```

`examples/curve_trace/` enthält die echte PNG-Vorlage `curved_trefoil.png`,
den noch unvollständigen `draft.json`, eine explizit ergänzte `annotation.json`
und die Offline-Galerie `index.html`. `overlay.png` legt den erkannten Pfad in
Blau über die Vorlage und dient der visuellen Kontrolle. Der Beispielgenerator
setzt für **diese Referenz** eine alternierende Kreuzungswahl. Diese Wahl ist
kein Ergebnis der Pixelanalyse und keine allgemeine Klassifikationsmethode.

```bash
node examples/make_curve_trace.cjs
```

Ergebnis: 144 rechtwinklige Stützpunkte, drei offene Wahlen im Entwurf;
nach der ergänzten Wahl ein Trefoil `T(2,3)`, Determinante 3 und 3702 Punkte
im Zweischicht-Gitterpfad. Der Turtle-Code stellt diesen Pfad exakt wieder her.

## Skelett und eingebetteter Graph

`CurveTracer.recognize(imageData, {threshold: 160})` ist eine reine Funktion im
ersten Skript von `src/knots_grid/image_tracer.html`.

1. Dieselbe alpha-korrigierte Helligkeitsmaske wie bei der Rastererkennung
   isoliert dunkle Pixel. **Alle** Vordergrundpixel müssen bereits vor dem
   Skelettieren eine einzige 8-zusammenhängende Komponente bilden. Kein
   Fremdpixel und keine kleine Komponente wird stillschweigend entfernt.
2. Zhang-Suen-Skelettierung löscht Randpixel in zwei simultanen Teilschritten
   pro Iteration. Sie ist nach höchstens 128 Iterationen beendet oder liefert
   einen Fehler. Die Euler-Charakteristik für 8-zusammenhängenden Vordergrund
   und 4-zusammenhängenden Hintergrund muss erhalten bleiben. Zusammen mit
   der Komponentenkontrolle schützt das auch vor verschwundenen kleinen Löchern.
3. Die Skelettpixel werden über ihre acht Nachbarn verbunden. Eine Diagonale
   entfällt, wenn bereits eine Verbindung über einen orthogonalen Nachbarpixel
   existiert; so erzeugen Treppenecken keine künstlichen Dreiecke. Offene Enden
   und isolierte Pixel sind Fehler.
4. Nahe Verzweigungspixel werden in disjunkten rechteckigen Kreuzungsregionen
   zusammengefasst. Jede Region muss zusammenhängend und ohne Loch sein und
   genau vier austretende Arme besitzen. Voll belegte 2×2-Pixelquadrate zählen
   als gefüllte Flächen, nicht als Löcher des Pixelgraphen. Die Winkel zwischen
   benachbarten Austrittsarmen müssen zwischen 30 und 150 Grad liegen.
   Alle übrigen Skelettkanten müssen vollständig als Grad-2-Ketten erfasst sein.
   Die Euler-Charakteristik des Ausgangsbilds muss zur Kreuzungszahl passen.

Das ist eine konservative Interpretation des Schwellenbildes als reguläres
Kurvendiagramm. Sie beweist weder die Absicht der Zeichnung noch, dass jede
denkbare Berührung oder jedes Detail unterhalb der Pixelauflösung erkannt wurde.

## Überführung auf das rechtwinklige Raster

Es werden höchstens drei Zellgrößen geprüft, in der Reihenfolge **12, 8, 4**
Bildpixel. Das fein aufgelöste Skelett belegt die Rasterzellen; eine erneute
Skelettierung und Graphprüfung ergeben einen gröberen eingebetteten Graphen.
Eine Übernahme erfordert:

- dieselbe Kreuzungszahl und eine eindeutige räumliche Zuordnung der Regionen,
- dieselbe zyklische Reihenfolge der vier Arme an jeder Kreuzung, nur bis auf
  zyklische Verschiebung, ohne Spiegelung,
- genau dieselben Kettenverbindungen zwischen den zugeordneten Armen.

Jede digitale Kette wird auf einem vierfach verfeinerten Gitter rechtwinklig
eingebettet. Diagonalschritte erhalten kurze Treppen innerhalb ihres Pixelkorridors.
In jeder Kreuzungsregion sucht ein begrenztes Breitensuchverfahren vier
disjunkte Verbindungen von den Austrittsarmen zu einem zentralen Plus. Die
zyklische Armreihenfolge bleibt erhalten; gegenüberliegende Arme werden gepaart.
Die übrigen Wege sind für diese Suche gesperrt. Die Verbindungssuche probiert
höchstens vier zyklische Zuordnungen und 24 Armreihenfolgen je Region.

Die Erhaltung von Armreihenfolge und Kettenverbindungen erhält den eingebetteten
Projektionsgraphen auf der orientierten Sphäre. Die Kreuzungsregionen sind
lochfreie Scheiben und die äußeren Ketten schneiden sich nicht. Damit führt die
Umzeichnung keine zusätzlichen Kreuzungen ein; die Über-/Unterwahl erfolgt erst
anschließend. Eine Gleichheit der Knotendeterminanten wird für diese Prüfung
nicht verwendet.

Beim anschließenden Durchlauf muss jeder Graphbogen genau einmal zu **einem**
geschlossenen Strang gehören. Zwei sich kreuzende geschlossene Komponenten
werden auch bei zusammenhängender dunkler Bildmaske abgelehnt. Vor der Rückgabe
prüft die Erkennung alle Gitterpunktbesuche, entfernt nur gerade Zwischenpunkte
und führt die bestehende exakte Segmentprüfung aus. Die einzigen zweifachen
Besuche müssen die geplanten zentralen Kreuzungen sein. Anzahl und Koordinaten
der Segmentkreuzungen müssen exakt zu diesen Zentren passen.

## Format und Herkunft

Das Annotationsformat bleibt Version 1. Die bestehenden Zeichenflächenangaben
erlauben nun ganzzahlige Rasterabstände von **1 bis 100** statt 8 bis 100 Pixeln;
die Rasterbild-Erkennung selbst benötigt weiterhin 8 bis 100 Pixel.

`recognition.algorithm` ist `skeleton-orthogonal-v1`. Neben den bestehenden
Schwellen-/Vordergrund-/Kantenzählern enthält der Bericht `sample_size` (4/8/12),
`skeleton_pixels` und `thinning_iterations`. `inferred_crossings` ist immer 0;
`unresolved_crossings` beschreibt den ersten Erkennungslauf, auch nachdem man
später manuell Wahlen ergänzt hat. Ein Rasterbestimmungsbericht gehört nicht
zu diesem Algorithmus. JavaScript und Python prüfen und erhalten den Bericht.

Der Python-Export speichert die Herkunft als `reviewed_curve_annotation`, die
Galerie zeigt „Kurvenerkennung“ und nennt die manuell gewählten Überführungen.
Geometrie- und Rasteränderungen verwerfen den Bericht wie bei AP-02/AP-03.
Fehler übernehmen weder Teilpfade noch neue Rastereinstellungen.

## Grenzen und Abnahme

Es gelten höchstens 1200×900 Bildpixel, 200000 Vordergrundpixel, 100000
Skelettpixel, 100 getrennte Kreuzungsregionen, 500 Stützpunkte und 100000
Punkte nach Gitterexport. Verzweigungspixel sind auf 2000 begrenzt;
Kreuzungsrechtecke dürfen höchstens 96 Pixel beziehungsweise 24 Rasterzellen
je Achse überspannen. Die lokale Routensuche besucht höchstens 2000000
Zustände pro Rastervorschlag. Erschöpfte Grenzen liefern eine Fehlermeldung.

Durchgezogene, ausreichend getrennte Kurven funktionieren ohne vorgegebenes
Zeichenraster. Kreuzungslücken, offene Kurven, nahe oder verschmolzene Stränge,
Beschriftungen, Flecken, Papiertextur, Perspektivkorrektur und allgemeine
Scanaufbereitung sind nicht abgedeckt. Eine saubere digitalisierte Zeichnung
kann funktionieren; beliebige Handzeichnungen sind damit nicht gelöst.

```bash
python -m unittest discover -s tests
node tests/test_image_tracer_runtime.cjs
node tests/test_raster_tracer_runtime.cjs
node tests/test_curve_tracer_runtime.cjs
node tests/test_gallery_runtime.cjs
node tests/test_gallery_runtime.cjs examples/travel_catalog/index.html
node tests/test_gallery_runtime.cjs examples/image_trace/index.html
node tests/test_gallery_runtime.cjs examples/raster_trace/index.html
node tests/test_gallery_runtime.cjs examples/curve_trace/index.html
```

Die Kurventests prüfen echte PNG-Pixel, Ellipsen und Trefoils, Drehungen,
Spiegelungen, Strichbreiten, Skalierung, Helligkeit und Transparenz. Offene
Linien, Berührungen, mehrere Komponenten, Fremdpixel einschließlich kleiner
2×2-Komponenten, Bildrand und Eingabegrenzen werden abgelehnt. Der vollständige
Python-Durchlauf prüft gültige Zweischichtpfade, die Trefoil-Klassifikation mit
beiden Händigkeiten, exakte Turtle-Roundtrips, Entwurfssperre, Herkunft und
Galeriestart. Tatsächliche Editor-Ereignisbehandlungen werden im Node-DOM-Modell
für Erkennung, Fehlererholung, Speichern/Laden und manuelle Kreuzungswahl geprüft.
Die Überlagerungs-PNG wurde visuell kontrolliert; eine manuelle Browserprüfung
ist damit nicht behauptet.

Abnahme am 05.11.2026: 98 Python-Tests, alle drei Editor-/Erkennungsprüfungen
und alle fünf Galerieprüfungen erfolgreich. Der Rückfall vom groben auf ein
feineres Raster wird ebenfalls bis zum Python-Konverter geprüft. In der
Windows-Sandbox wurde `TEMP`/`TMP` auf `.test_tmp` im Projekt gesetzt.
