# Fetch- und Decode-Phase: Handzeichnungs-Checkliste

Diese Beschreibung ist als 1:1-Zeichenhilfe für eine einfache 16-Bit-von-Neumann-CPU gedacht. Sie ersetzt ein unübersichtliches Schaltbild durch eine Bauteil-für-Bauteil-Liste. Wenn die konkrete CPU andere Signalnamen verwendet, bleiben die Verbindungen gleich, nur die Namen ändern sich.

## Gemeinsame Annahmen

- Datenbus: 16 Bit breit; transportiert Daten, Instruktionen und Adressen zwischen Registern, ALU und Speicher.
- Adressbus: 16 Bit breit; transportiert die Speicheradresse vom Memory Address Register zum Speicher.
- Steuerbus: einzelne 1-Bit-Signale; aktiviert Ladeeingänge, Speicherausgänge und Multiplexer-Auswahlen.
- Takt: alle Register übernehmen ihren D-Eingang nur an der aktiven Taktflanke, wenn ihr Load-Signal aktiv ist.
- Reset: setzt den Program Counter auf die Startadresse, typischerweise 0x0000.

## Fetch-Phase

Ziel der Fetch-Phase: Die Instruktion an der Adresse im Program Counter wird aus dem Speicher gelesen und in das Instruction Register geladen. Danach zeigt der Program Counter auf die nächste Instruktion.

### Bauteil: Register "PC" (Program Counter)

Verbindungen:

D:
- Bezeichnet den 16-Bit-Eingang des PC.
- Wird mit dem Ausgang eines Multiplexers verbunden, der entweder `PC + 1`, eine Sprungadresse oder die Reset-/Startadresse auswählt.

Q:
- Bezeichnet den 16-Bit-Ausgang des PC.
- Wird mit Eingang A des Inkrementierers verbunden.
- Wird außerdem mit einem Eingang des Adress-Multiplexers oder direkt mit `MAR.D` verbunden, damit die aktuelle Instruktionsadresse in das Memory Address Register geladen werden kann.

Load / PCWrite:
- Bezeichnet das 1-Bit-Ladesignal des PC.
- Wird in der normalen Fetch-Phase aktiviert, nachdem `PC + 1` berechnet wurde.
- Wird bei Sprungbefehlen ebenfalls aktiviert, aber dann wählt der PC-Multiplexer die Sprungadresse statt `PC + 1`.

Reset:
- Bezeichnet das 1-Bit-Rücksetzsignal.
- Wird mit der globalen Reset-Leitung verbunden und setzt `PC.Q` auf die Startadresse.

### Bauteil: Inkrementierer "PC + 1"

Verbindungen:

A:
- Bezeichnet den 16-Bit-Eingang.
- Wird mit `PC.Q` verbunden.

Y:
- Bezeichnet den 16-Bit-Ausgang.
- Liefert `PC.Q + 1`.
- Wird mit einem Eingang des PC-Multiplexers verbunden.

### Bauteil: Multiplexer "PC-Quelle"

Verbindungen:

Eingang 0:
- Bezeichnet den normalen Weiterzählpfad.
- Wird mit `PC + 1.Y` verbunden.

Eingang 1:
- Bezeichnet den Sprungpfad.
- Wird mit der berechneten Sprungadresse verbunden, typischerweise aus ALU-Ausgang, Immediate-Erweiterung oder einem Adressfeld der Instruktion.

Eingang 2, falls vorhanden:
- Bezeichnet die Reset- oder Interrupt-Adresse.
- Wird mit einer Konstanten oder Interrupt-Vektor-Adresse verbunden.

Select / PCSrc:
- Bezeichnet das Steuersignal für die Auswahl.
- Wird von der Control Unit erzeugt.
- Ist im normalen Fetch auf Eingang 0 eingestellt.

Y:
- Bezeichnet den 16-Bit-Ausgang.
- Wird mit `PC.D` verbunden.

### Bauteil: Register "MAR" (Memory Address Register)

Verbindungen:

D:
- Bezeichnet den 16-Bit-Eingang.
- Wird in der Fetch-Phase mit `PC.Q` verbunden, entweder direkt oder über einen Adress-Multiplexer.

Q:
- Bezeichnet den 16-Bit-Ausgang.
- Wird mit dem Adressbus verbunden.
- Der Adressbus geht zum Adresseingang des Speichers.

Load / MARWrite:
- Bezeichnet das 1-Bit-Ladesignal des MAR.
- Wird in der ersten Fetch-Teilstufe aktiviert, damit die aktuelle PC-Adresse im MAR steht.

### Bauteil: Speicher "Memory"

Verbindungen:

Address:
- Bezeichnet den 16-Bit-Adresseingang.
- Wird mit `MAR.Q` über den Adressbus verbunden.

DataOut:
- Bezeichnet den 16-Bit-Datenausgang.
- Wird in der Fetch-Phase mit `IR.D` verbunden, direkt oder über den Datenbus.

DataIn:
- Bezeichnet den 16-Bit-Dateneingang.
- Wird beim Fetch nicht benutzt.
- Wird bei Store-Befehlen mit dem Datenbus oder einem Datenregister verbunden.

MemRead:
- Bezeichnet das 1-Bit-Lesesignal.
- Wird in der Fetch-Phase aktiviert.

MemWrite:
- Bezeichnet das 1-Bit-Schreibsignal.
- Bleibt in der Fetch-Phase deaktiviert.

### Bauteil: Register "IR" (Instruction Register)

Verbindungen:

D:
- Bezeichnet den 16-Bit-Eingang.
- Wird mit `Memory.DataOut` verbunden, direkt oder über den Datenbus.

Q:
- Bezeichnet den 16-Bit-Ausgang.
- Wird in einzelne Felder aufgeteilt: Opcode, Registerfelder, Immediate-/Adressfeld.
- Wird mit der Control Unit und den Registeradress-Eingängen der Registerbank verbunden.

Load / IRWrite:
- Bezeichnet das 1-Bit-Ladesignal des IR.
- Wird aktiviert, wenn `Memory.DataOut` die gelesene Instruktion stabil bereitstellt.

## Zeitlicher Ablauf der Fetch-Phase

1. `PC.Q` enthält die Adresse der nächsten Instruktion.
2. `MARWrite` wird aktiviert; `MAR.D` erhält `PC.Q`.
3. Nach der Taktflanke enthält `MAR.Q` die Instruktionsadresse.
4. `MemRead` wird aktiviert; der Speicher liest die Zelle an `MAR.Q`.
5. `IRWrite` wird aktiviert; `IR.D` erhält `Memory.DataOut`.
6. Nach der Taktflanke enthält `IR.Q` die neue Instruktion.
7. Der Inkrementierer berechnet parallel `PC.Q + 1`.
8. `PCSrc` wählt den Eingang `PC + 1`.
9. `PCWrite` wird aktiviert; nach der Taktflanke enthält `PC.Q` die Adresse der nächsten Instruktion.

## Decode-Phase

Ziel der Decode-Phase: Die Instruktion im Instruction Register wird in Steuerinformationen und Operanden zerlegt. Die CPU entscheidet, welche Register gelesen werden, welche ALU-Operation nötig ist und ob später Speicher, Registerbank oder Program Counter geschrieben werden.

### Bauteil: Feldaufteilung "IR-Splitter"

Verbindungen:

IR[15:12] / Opcode:
- Bezeichnet das Opcode-Feld.
- Wird mit dem Opcode-Eingang der Control Unit verbunden.

IR[11:8] / Rd oder Zielregister:
- Bezeichnet je nach Befehl das Zielregister oder ein weiteres Opcode-Feld.
- Wird mit `RegisterFile.WriteAddress` oder der Control Unit verbunden.

IR[7:4] / Rs:
- Bezeichnet das erste Quellregister.
- Wird mit `RegisterFile.ReadAddressA` verbunden.

IR[3:0] / Rt oder Immediate-Niederteil:
- Bezeichnet das zweite Quellregister oder einen Teil eines Immediate-Werts.
- Wird mit `RegisterFile.ReadAddressB` oder dem Immediate-Extender verbunden.

### Bauteil: Control Unit

Verbindungen:

Opcode-Eingang:
- Wird mit `IR[15:12]` verbunden.
- Bestimmt die Art des Befehls, zum Beispiel ALU, Load, Store, Jump oder Branch.

Weitere Instruktionsbits:
- Werden bei Bedarf mit Funktionsbits, Registerbits oder Adressbits aus `IR.Q` verbunden.

Steuerausgänge:
- `RegWrite`: aktiviert später das Schreiben in die Registerbank.
- `ALUSrc`: wählt später zwischen Registeroperand und Immediate-Operand.
- `ALUOp`: legt die ALU-Funktion fest.
- `MemRead`: aktiviert später Speicherlesen bei Load.
- `MemWrite`: aktiviert später Speicherschreiben bei Store.
- `MemToReg`: wählt später, ob ALU-Ergebnis oder Speicherwert in ein Register geschrieben wird.
- `PCSrc`: wählt später den normalen PC-Pfad, Branch-Pfad oder Jump-Pfad.
- `IRWrite`: bleibt in Decode normalerweise deaktiviert.
- `PCWrite`: bleibt in Decode normalerweise deaktiviert, außer bei sehr einfachen Jump-Implementierungen.

### Bauteil: Registerbank "Register File"

Verbindungen:

ReadAddressA:
- Bezeichnet die Adresse des ersten Quellregisters.
- Wird mit dem passenden Feld aus `IR.Q` verbunden, typischerweise `IR[7:4]`.

ReadAddressB:
- Bezeichnet die Adresse des zweiten Quellregisters.
- Wird mit dem passenden Feld aus `IR.Q` verbunden, typischerweise `IR[3:0]` oder `IR[11:8]`, abhängig vom Instruktionsformat.

ReadDataA:
- Bezeichnet den 16-Bit-Ausgang des ersten gelesenen Registers.
- Wird mit einem Operandenregister `A.D` oder direkt mit `ALU.A` verbunden.

ReadDataB:
- Bezeichnet den 16-Bit-Ausgang des zweiten gelesenen Registers.
- Wird mit einem Operandenregister `B.D`, direkt mit `ALU.B` oder mit dem Speicher-Dateneingang für Store-Befehle verbunden.

WriteAddress:
- Bezeichnet die Adresse des Zielregisters.
- Wird mit dem Zielregisterfeld aus `IR.Q` verbunden, oft `IR[11:8]` oder `IR[7:4]`.

WriteData:
- Bezeichnet den 16-Bit-Dateneingang für späteres Zurückschreiben.
- Wird nicht während Decode geschrieben; er wird in der Writeback-Phase von ALU- oder Speicherergebnis gespeist.

RegWrite:
- Bleibt während Decode deaktiviert.
- Wird erst in der Writeback-Phase für Befehle aktiviert, die ein Register verändern.

### Bauteil: Immediate-Extender

Verbindungen:

In:
- Bezeichnet das Immediate- oder Adressfeld aus `IR.Q`.
- Wird zum Beispiel mit `IR[7:0]` oder `IR[3:0]` verbunden.

Mode / SignZero:
- Bezeichnet die Auswahl zwischen Vorzeichenerweiterung und Nullerweiterung.
- Wird von der Control Unit gesteuert.

Out:
- Bezeichnet den 16-Bit-erweiterten Immediate-Wert.
- Wird mit einem Eingang des ALU-B-Multiplexers und bei Jump/Branch mit der Adressberechnung verbunden.

### Bauteil: Operandenregister "A" und "B", falls vorhanden

Verbindungen Register A:

D:
- Wird mit `RegisterFile.ReadDataA` verbunden.

Q:
- Wird mit `ALU.A` verbunden.

Load:
- Wird in Decode aktiviert, wenn die CPU Operanden zwischen Decode und Execute zwischenspeichert.

Verbindungen Register B:

D:
- Wird mit `RegisterFile.ReadDataB` verbunden.

Q:
- Wird mit einem Eingang des ALU-B-Multiplexers verbunden.
- Wird außerdem mit `Memory.DataIn` verbunden, falls der Befehl ein Store ist.

Load:
- Wird in Decode aktiviert, wenn die CPU Operanden zwischen Decode und Execute zwischenspeichert.

## Zeitlicher Ablauf der Decode-Phase

1. `IR.Q` enthält die gerade geholte Instruktion.
2. Der IR-Splitter stellt Opcode, Registerfelder und Immediate-Feld gleichzeitig bereit.
3. Die Control Unit liest den Opcode und erzeugt die Steuersignale für die folgenden Phasen.
4. Die Registerbank liest die durch die Instruktionsfelder angegebenen Quellregister.
5. Der Immediate-Extender erweitert das Immediate-Feld auf 16 Bit.
6. Falls Operandenregister vorhanden sind, übernehmen `A` und `B` die Registerwerte an der nächsten Taktflanke.
7. In Decode werden normalerweise weder Speicher noch Zielregister beschrieben.

## Wichtigste Zeichenregel

Beim Nachzeichnen zuerst den Datenfluss zeichnen: `PC -> MAR -> Memory -> IR -> Control/RegisterFile`. Danach den Nebenpfad `PC -> PC+1 -> PC-Mux -> PC` ergänzen. Erst ganz am Ende die 1-Bit-Steuersignale einzeichnen, weil diese sonst das Bild unlesbar machen.
