// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
// * MsgStep.h: Fehlermeldungen der Klasse CStepOp.                          *
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

#ifndef _MSG_STEP
#define _MSG_STEP

#define _MSG_STEP_DEVICE "STP"

#ifdef _DEUTSCH
#include "MsgStep-de.h"
#else
#include "MsgStep-en.h"
#endif

#endif // _MSG_STEP