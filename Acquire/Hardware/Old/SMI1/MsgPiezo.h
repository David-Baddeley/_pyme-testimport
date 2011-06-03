// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
// * MsgPiezo.h: Fehlermeldungen der Klasse CPiezoOp.                      *
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

#ifndef _MSG_PIEZO
#define _MSG_PIEZO

#define _MSG_PIEZO_DEVICE "PZT"

#ifdef _DEUTSCH
#include "MsgPiezo-de.h"
#else
#include "MsgPiezo-en.h"
#endif

#endif // _MSG_PIEZO