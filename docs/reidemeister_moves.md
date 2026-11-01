# Direkte Reidemeister-Züge (AP-01)

`knots_grid.reidemeister_moves` ergänzt die freien Einheitsquadrate um direkte
Züge I, II und III. Die Prüfung verwendet die exakte, unverschobene
`(x,y)`-Projektion; die diagonale Verschiebung der SVG-Ansicht spielt keine Rolle.
Eine Einführung in die drei Diagrammzüge gibt
[Adkisson, Abschnitt 3: Reidemeister moves](https://math.uchicago.edu/~may/REU2015/REUPapers/Adkisson.pdf).

## Regionen und lokale Evidenz

1. Der Eingangspfad muss ein gültiger geschlossener Zweischicht-Gitterzyklus sein.
   Überlappende Projektionskanten und nicht transversale Doppelbesuche führen zu
   `nonregular projection`. Der bisherige Flächenzugmotor kann diese Pfade
   weiterhin verarbeiten.
2. Der ebene Graph enthält jede horizontale/vertikale Einheitskante; reine
   Ebenenwechsel werden für die Flächensuche zusammengezogen. Gerichtete Kanten
   werden mit konsistenter Drehrichtung umlaufen. Nur einfache begrenzte
   Polygone mit positiver orientierter Fläche werden betrachtet.
3. Ein-, Zwei- und Dreiecksregionen werden mit den Gauss-Kandidaten abgeglichen.
   Ihre Seiten müssen tatsächlichen Teilpfaden des Knotens entsprechen.
   Punkt- und Kantenmittelpunkttests prüfen zusätzlich die Leerheit.
   Die Rechnungen auf ganzen und halben Gitterkoordinaten sind exakt.
4. Typ II benötigt einen durchgehend überliegenden und einen unterliegenden
   Randbogen an beiden Kreuzungen. Typ III benötigt einen oberen, mittleren und
   unteren Strang. Ein zyklisches Muster wird abgelehnt; das Dreieck im
   alternierenden Trefoil ist deshalb kein ausführbarer Typ-III-Zug.

## Ausführung und Isotopieargument

**I:** Der Schleifenteilpfad zwischen den zwei Besuchen einer Kreuzung wird durch
den direkten Ebenenwechsel an dieser Stelle ersetzt. Die einfache Projektion
der Schleife begrenzt eine leere Scheibe. Es bleiben weder andere Stränge im
Inneren noch weitere Kreuzungen auf dem Bogen; dies ist die lokale
Reidemeister-I-Kontraktion. Die beiden äußeren Strangrichtungen bleiben erhalten.

**II/III:** Bewegt wird ein oberer oder unterer Randbogen einschließlich je eines
Gitterpunkts vor und nach den Kreuzungen. Dieser Teilpfad muss vollständig auf
`z=1` beziehungsweise `z=0` liegen. Eine deterministische Breitensuche sucht einen
neuen ebenen Gitterbogen mit unveränderten Endpunkten. Die beiden Bögen müssen
zusammen eine einfache projizierte Scheibe begrenzen. Der Ersatzpfad muss im
räumlichen Gitter kollisionsfrei sein und eine reguläre Projektion besitzen.

Der bewegte obere Bogen kann während einer räumlichen Isotopie über die gesamte
Zweischichtplatte angehoben, über diese Scheibe bewegt und danach abgesenkt
werden; unten gilt das entsprechende Argument unter der Platte. Die Endpunkte
bleiben fest, ihre äußeren Fortsetzungen liegen außerhalb der Scheibe. Es gibt
keine festen Stränge oberhalb beziehungsweise unterhalb der Platte. Daher
können auch Ebenenwechsel der stationären Stränge im Scheibeninneren kein
Hindernis erzeugen. Die gespeicherten Ausgangs- und Ergebniswege bleiben im
Zweischichtgitter; die kontinuierliche Isotopie ist nicht auf dessen Kanten
beschränkt.

Zusätzlich wird geprüft, dass diese räumliche Isotopie genau den beabsichtigten
Diagrammzug realisiert:

- Bei II enthält die Scheibe genau einen zusammenhängenden stationären Bogen.
  Er durchquert den Rand an den zwei alten Kreuzungen; beide fallen weg und es
  entstehen keine neuen Kreuzungen.
- Bei III enthält sie genau zwei stationäre Bögen, ihre mittlere Kreuzung liegt
  strikt innen, und keine andere Kreuzung liegt im Inneren. Jeder Bogen verbindet
  eine alte mit einer neuen Randkreuzung. Die Kreuzungsreihenfolge auf dem
  bewegten Strang kehrt sich um, die Vorzeichen der gepaarten Kreuzungen bleiben
  erhalten. Alle anderen Kreuzungen bleiben unverändert.
- Weitere Randberührungen, mitbewegte Anschlussstränge und zusätzliche Bögen
  führen zur Ablehnung. Die Knotendeterminante dient nur als zusätzlicher
  Regressionstest, niemals als Äquivalenzbeweis.

## API und Protokolle

```python
from knots_grid import analyze_reidemeister_moves, apply_reidemeister_move
from knots_grid.optimization import apply_move, move_from_dict, optimize_cycle

analysis = analyze_reidemeister_moves(points, max_route_states=5000)
for rejection in analysis.rejections:
    print(rejection.move_type, rejection.crossing_ids, rejection.reason)
if analysis.moves:
    next_points = apply_reidemeister_move(points, analysis.moves[0])

result = optimize_cycle(points, max_moves=100, max_route_states=5000)
for record in saved_metadata["moves"]:
    points = apply_move(points, move_from_dict(record))
```

`regions` enthält nachgewiesene leere Regionen, `moves` deren unterstützte
Gitterrealisierungen und `rejections` die Gründe für nicht unterstützte
Kandidaten/Regionen. Ein Protokolleintrag enthält `start_index`, `before`, `after`
und `kind` (`empty_unit_face` oder `reidemeister_I`, `_II`, `_III`). Beim Replay
werden die Region und die gesamte Zertifizierung neu berechnet. Eine geänderte
Typangabe, ein anderer Ausgangspfad oder ein unzulässiger Ersatz wird abgelehnt.
Alte Flächenprotokolle bleiben mit `apply_face_move` oder `apply_move` ausführbar.

Die Pipeline speichert die letzten geometrischen Ablehnungen unter
`metadata.reidemeister_rejections`; bei ausgeschalteter Optimierung ist die Liste
leer. Ihre Herkunft enthält Algorithmus `travel-reidemeister-v2` und das
Routenzustandslimit. Das CLI bietet `--route-states 5000` an.

## Suchgrenzen

Die Routensuche bleibt innerhalb eines Drei-Zellen-Randes um die geprüfte
Region und besucht höchstens `max_route_states` Zustände pro bewegtem Bogen.
Die erste gefundene Route muss alle geometrischen Prüfungen bestehen; schlägt
dies fehl, wird nicht unbegrenzt nach Alternativen gesucht. Bei III liegen die
neuen Kreuzungen auf den Fortsetzungen der stationären Bögen jenseits ihrer
mittleren Kreuzung. Zu dicht liegende Kreuzungen oder ungünstige Ebenenwechsel
können damit eine unterstützte Realisierung verhindern.

Es gibt keine inversen I/II-Züge, keine automatische Gitterverfeinerung und keinen
Anspruch, jeden möglichen Reidemeister-Zug im festen Gitter auszuführen. Die
Optimierung akzeptiert strikt kleinere `(Punktzahl, kanonische Cantor-Folge)`.
Ein längerer III-Zug ist über die API ausführbar, wird aber vom Optimierer nicht
als Zwischenschritt genommen. `local_minimum` bezieht sich nur auf diese
begrenzte Nachbarschaft. Ästhetik, globale Minimalität und vollständige
Knotenerkennung sind davon unabhängig.

## Prüfungen

`tests/test_reidemeister_moves.py` enthält eigene Schleifen-, Zweieck- und
Dreiecksbeispiele, einen belegten äußeren Schleifenbereich sowie das unzulässige
Trefoil-Dreieck. Tests prüfen alle Zugtypen, Kreuzungszahlen, Determinanten,
Replay nach JSON-Roundtrip, Manipulationen, zyklischen Start, Richtungsumkehr,
Spiegelung, Drehung, Ebenentausch und Routengrenzen. Die Pipeline-Tests prüfen
gemischte Protokolle und bytegleiche Exporte.
