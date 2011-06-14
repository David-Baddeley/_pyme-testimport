// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
// * MsgPiezo-de.h: Fehlermeldungen der Klasse CPiezoOp.                     *
// * (C) 2002/2004 by Udo Sp�ri, Kirchhoff-Institut f�r Physik               *
// *     Erstellt am 30. Oktober   2002                                      *
// *  2. �nderung am 30. Oktober   2002                                      *
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *

// die maximale Anzahl an Nachrichten ist definiert 
// in der Klasse SerialOp
// z.Z. m_strMessage[100]



// um die deutschen Fehlermeldungen einzubinden, ist es notwending
// den zus�tzlichen compile-Parmeter _DEUTSCH einzuf�gen
// bei   -> Einstellungen
//         -> C++
//           -> Pr�prozessor definitionen
//              ..., _DEUTSCH

#define _MSG_PIEZO_KEY "PiezoOperations"

// Achtung: Die Fehlermeldungen k�nnen zus�tzliche
//          Strings enthalten, diese sind durch 
//          Platzhalter, z.B. %s gekennzeichnet
#define _MSG_PIEZO_0 "Fehler beim �ffnen."
#define _MSG_PIEZO_1 "Fehler. Bitte zuerst initialisieren."
#define _MSG_PIEZO_2 "Fehler beim Schreiben."
#define _MSG_PIEZO_3 "Keine Antwort."
#define _MSG_PIEZO_4 "Keine Antwort oder\nfalsche Interpreter-Version."
#define _MSG_PIEZO_5 "Serielle Schnittstelle "
  // Spezielle Kommandos f�r Piezosteuerung:
#define _MSG_PIEZO_10 "Fehler beim Laden der Initialisierungs-\nkommandos f�r die Piezo-Steuerung.\nFile '%s'"
#define _MSG_PIEZO_11 "Fehler! Verwenden Sie Werte zwischen %d �m und %d �m!"

  // anderweitig benutzer Strings
#define _STR_PIEZO_0 "Stellbereich[�m]"
