# Globale Gitterverdichtung

Lokale Flächenzüge können einen langen Pfad unverändert lassen: Eine notwendige
Zwischenverschiebung verbessert weder Punktzahl noch das sekundäre Maß. Ein
solches lokales Minimum ist keine kürzestmögliche Darstellung.

Die interaktive Suche verwendet deshalb zusätzlich zwei globale Umformungen.
Beide erhalten z; sie tauschen keine Über-/Unterführungen oder Spiegelbilder.

## Abstände zwischen aktiven Koordinaten

Aktiv sind die x- und y-Koordinaten aller Ecken und Ebenenwechsel. Rein
kollineare Zwischenpunkte, einschließlich eines beliebigen Startpunkts auf
einer Geraden, sind keine zusätzlichen geometrischen Einschränkungen.
Jede sortierte Folge aktiver Koordinaten wird auf 0, 1, 2, … abgebildet.
Die geraden Verbindungen werden danach wieder in Einheitskanten zerlegt.

Zwischen aktiven Koordinaten wird die Abbildung linear, außerhalb durch
Translation fortgesetzt. Es entstehen streng wachsende Homöomorphismen f und g
der reellen Achsen. Auch ihre konvexe Interpolation mit der Identität ist
streng wachsend. Daher ist (f_t(x), g_t(y), z) eine räumliche Isotopie, die alle
Kreuzungen samt Höhenordnung erhält. Die Endpunkte des neuen Gitters sind
ganzzahlig; kollineare Unterteilungspunkte werden neu gesetzt.

## Zusammenziehen eines Einheitsstreifens

Ein Schnitt wird durch Achse und ganzzahlige Koordinate k beschrieben. Links
von k bleibt die Koordinate fest, rechts von k+1 wird sie um t verschoben,
und der Streifen [k,k+1] wird linear auf Breite 1−t komprimiert.
Für t<1 bleibt die Abbildung streng wachsend, daher gibt es keine Berührungen.
Bei t=1 schrumpfen die querenden Einheitskanten zu Punkten. Ausschließlich
aufeinanderfolgende gleiche Punkte dürfen aus dem Zyklus entfernt werden.

Der komplette Ergebniszyklus wird erneut validiert. Treffen nicht benachbarte
Teile zusammen, entsteht ein doppelter Punkt oder eine wiederholte Kante; der
Schnitt wird verworfen. Da alle verbleibenden Kanten Einheits-Gitterkanten sind,
können sich ihre Inneren nicht unerkannt schneiden. Erlaubte Kontraktionen
betreffen somit nur einzelne Teilbögen in getrennten Strangumgebungen. Ihre
zusammengezogenen Unterteilungen lassen sich dort lokal glätten; es entsteht
derselbe eingebettete Knoten. Ein zu einer Linie oder zu einem Punkt
kollabierender Gesamtzyklus wird ebenfalls verworfen.

## Suche und Protokoll

Beide Umformungen sind in `apply_move` und `move_from_dict` erneut prüfbar.
`coordinate_compression` speichert die aktiven Koordinaten, die beim Wiederholen
exakt mit dem Eingabepfad übereinstimmen müssen. `grid_slab_contraction` speichert
Achse und Schnittkoordinate; die Kollisionsprüfung wird erneut ausgeführt.

Die Studio-Suche aktiviert `compress_coordinates=True`. Kürzere Punktfolgen
haben Vorrang, dann die Ebenenverteilung, danach die kanonische Cantor-Folge.
Turtle-Kompatibilität und die bisherigen Zeit-/Zuggrenzen bleiben erhalten.
Die Erweiterung behauptet weiterhin kein globales Minimum: Beispielsweise
können andere Reihenfolgen der aktiven Linien, längere Zwischenwege oder
weitergehende Reidemeister-Züge bessere Ergebnisse liefern.

Der gemeldete Regressionstest mit 194 Befehlen benötigt lokal keinen einzigen
verbessernden Zug. Die Erweiterung verkürzt ihn auf 52 Schritte in einem
6×6-Begrenzungsrechteck. Die 44 planaren Schritte verteilen sich gleich auf
beide Ebenen; acht Schritte wechseln die Ebene. Das erkannte Referenzdiagramm
des Achterknotens und seine Determinante 5 bleiben erhalten. Daraus folgt keine
Minimalität dieser 52-Schritt-Darstellung.
