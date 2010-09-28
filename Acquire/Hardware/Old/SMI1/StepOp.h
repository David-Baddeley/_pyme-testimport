// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
// * StepOp.h: Schnittstelle f�r die Klasse CStepOp.                         *
// * (C) 1999/2000 by Benno Albrecht, Kirchhoff-Institut f�r Physik          *
// *     Erstellt am 30. M�rz     2000                                       *
// * 13. �nderung am  8. Dezember 2000                                       *
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *

// Klasse zur Ansteuerung der Hardware der Schrittmotor-Steuerung (Mitglied
// der Dokumentklasse)

#if !defined(AFX_STEPOP_H__C8EA0593_0622_11D4_99AE_0000C0E169AB__INCLUDED_)
#define AFX_STEPOP_H__C8EA0593_0622_11D4_99AE_0000C0E169AB__INCLUDED_

#if _MSC_VER > 1000
#pragma once
#endif // _MSC_VER > 1000

#include "SerialOp.h"

class CStepOp: public CSerialOp{
public:
  CStepOp();
  virtual ~CStepOp();

  // Elementzugriff:
  bool GetCalStatus()       {return m_bIsCalibrating;}
  void SetZStatus(bool bStatus){m_bIsSettingZInterval = bStatus;}
  bool GetZStatus()         {return m_bIsSettingZInterval;}
  bool GetCalibrationOK()   {return m_bCalibrated;}
  bool GetOSStatus()        {return m_bOSStatus;}
  string GetVersion()      {return m_strVersion;}
  float GetPosX()           {return m_fPosX;}
  float GetPosY()           {return m_fPosY;}
  float GetPosZ()           {return m_fPosZ;}
  string GetStrX()         {return m_strPosX;}
  string GetStrY()         {return m_strPosY;}
  string GetStrZ()         {return m_strPosZ;}
  float GetMinX()           {return m_fMinX;}
  float GetMaxX()           {return m_fMaxX;}
  float GetMinY()           {return m_fMinY;}
  float GetMaxY()           {return m_fMaxY;}
  float GetMinZ()           {return m_fMinZ;}
  float GetMaxZ()           {return m_fMaxZ;}
  string GetStrMinX()      {return m_strMinX;}
  string GetStrMaxX()      {return m_strMaxX;}
  string GetStrMinY()      {return m_strMinY;}
  string GetStrMaxY()      {return m_strMaxY;}
  string GetStrMinZ()      {return m_strMinZ;}
  string GetStrMaxZ()      {return m_strMaxZ;}
  int GetMoveAccel()        {return m_iMoveAccel;}
  int GetMoveSpeed()        {return m_iMoveSpeed;}
  bool GetJoystickStatus()  {return m_bJoystickStatus;}
  int GetJoystickSpeed()    {return m_iJoystickSpeed;}
  float GetNullX()          {return m_fNullX;}
  float GetNullY()          {return m_fNullY;}
  float GetNullZ()          {return m_fNullZ;}


  // Kommandos:
  int Init(int iMode);                 // Initialisierung der Schrittmotor-
                                       // Steuerung
  int Calibrate(int iMode);            // Kalibrierung und Verfahrbereich der
                                       // Schrittmotoren ermitteln
  void InitAreaValues();               // Initialisierung der Bereichs-Variab-
                                       // len (Schrittmotoren)
  int SetArea(bool bJoystick);         // gesamten physikalischen Verfahr-
                                       // bereich freigeben 
  int SetArea(float fMinX, float fMaxX, float fMinY, float MaxY, float fMinZ,
    float fMaxZ, bool bJoystick);      // Verfarbereich setzen
  void Break();                        // Schrittmotor-Aktionen abbrechen
  int StartContIO();                   // Kontinuierliche Positionsabfrage der
                                       // Schrittmotoren beginnen
  void ContIO();                       // Verwaltet koninuierliche Kommunika-
                                       // tion mit Schrittmotor-Steuerung
  void StopContIO();                   // Beenden der kontinuierlichen Kommuni-
                                       // kation mit Schrittmotor-Steuerung
  void MoveTo(float fPosX, float fPosY, float fPosZ);  // Verfahrbefehl f�r
  void MoveRel(float fDeltaX, float fDeltaY, float fDeltaZ);
                                       // Schrittmotoren ausf�hren
  void MoveOSInOut();                  // Objekttr�ger in/aus Objektiv-
                                       // Zwischenraum herein/heraus bewegen
  void SetMoveAccel(int iAccel);       // Beschleunigung f�r Verfahrbefehle
                                       // setzen
  void SetMoveSpeed(int iSpeed);       // Geschwindigkeit f�r Verfahrbefehle
                                       // setzen
  void SetJoystickOnOff();             // Joystick ein-/ausschalten
  void SetJoystickSpeed(int iSpeed);   // Joystick-Geschwindigkeit setzen
  void SetNull();                      // Nullpunkt festlegen
  void SavePos(int iIndex);            // Position iIndex speichern
  void MoveToPos(int iIndex);          // Position iIndex anfahren

private:
  // Variablen/Attribute:
  bool m_bIsCalibrating;               // = TRUE, solange Kalibrierung l�uft
  bool m_bIsSettingZInterval;          // = TRUE, solange z-Intervall gesetzt
                                       //         wird
  bool m_bJoystickStatus;              // = TRUE, falls Joystick eingeschaltet
  bool m_bCalibrated;                  // = TRUE: Kalibrierung der Schrittmoto-
                                       //         ren wurde abgeschlossen.
  bool m_bOSStatus;                    // = TRUE: Objekttr�ger befindet sich
                                       //         zwischen den Objektiven bzw.
                                       //         innerhalb des gesetzten Ver-
                                       //         fahrbereichs
  int m_iJoystickSpeed;                // Geschwindigkeit f�r Joystick = 1..10
  int m_iMoveAccel;                    // Beschleunigung f�r Verfahrbefehle
  int m_iMoveSpeed;                    // Geschwindigkeit f�r schnellste Achse
                                       // bei Verfahrbefehlen
  int m_iExpect;                       // = 0: Es werden keine Daten von der
                                       //      Steuerung erwartet
                                       // = Befehlsnr. > 0: Es werden Daten
                                       //      erwartet
  int m_iTryGetPos;                    // z�hlt Anzahl der Versuche, die Pos-
                                       // ition abzufragen
  int m_iMaxTryGetPos;                 // maximale Anzahl Versuche f�r Posi-
                                       // tionsabfrage
  int m_iCalibrationMode;              // = 1: gesamtes physikalisches z-Inter-
                                       //      vall bei Kalibrierung freigeben
                                       // = 2: geladene Werte verwenden
  char* m_chParPath;                   // Pfad f�r Parameter f�r Verfahrbereich
  int m_iDummy;                        // Platzhalter f�r Serialisierung
  // --------------------------------------------------------------
  // |    Alle Positionswerte sind in Mikrometer angegeben!       |
  // --------------------------------------------------------------
  float   m_fPosX;                     // Position in aktuellen Koordinaten
  float   m_fPosY;
  float   m_fPosZ;
  string m_strPosX;                   // s. m_fPosX, aber als String
  string m_strPosY;
  string m_strPosZ;
  float   m_fMinX;                     // minimale Position in aktuellen
  float   m_fMinY;                     // Koordinaten
  float   m_fMinZ;
  string m_strMinX;
  string m_strMinY;
  string m_strMinZ;
  float   m_fMinXS;                    // wird serialisiert (Verfahrbereich)
  float   m_fMinYS;
  float   m_fMinZS;
  float   m_fMaxX;                     // maximale Position in aktuellen
  float   m_fMaxY;                     // Koordinaten
  float   m_fMaxZ;
  string m_strMaxX;
  string m_strMaxY;
  string m_strMaxZ;
  float   m_fMaxXS;                    // vgl. m_fMinXS, wird serialisiert
  float   m_fMaxYS;
  float   m_fMaxZS;
  float   m_fNullX;                    // Koordinaten des Koordinaten-Ursprungs
  float   m_fNullY;                    // bez�glich unterer Endschalter (abso-
  float   m_fNullZ;                    // lute Nullpunkts-Koordinaten)
  float   m_fMaxPhysX;                 // Koordinaten der maximalen physika-
  float   m_fMaxPhysY;                 // lischen Position bez�glich unterer
  float   m_fMaxPhysZ;                 // Endschalter
  float   m_fPosXOSOut;                // Position f�r Objekttr�ger ausserhalb
  float   m_fPosYOSOut;                // der Objektive
  float   m_fPosXS[2];                 // Positionsspeicher, wird serialisiert
  float   m_fPosYS[2];                 // Diese Koordinaten m�ssen sich wegen
  float   m_fPosZS[2];                 // des variablen Koordinaten-Nullpunkts
                                       // auf die unteren Endschalter beziehen!

  // -------------------------------------------------------------- Funktionen:
  void InitUserValues();               // Vom Benutzer einstellbare Parameter
                                       // initialisieren
  void ExecuteCommand(int iNumber, string strCommand);  // Kommando f�r
                                       // Schrittmotoren ausf�hren
  void ExtractPos();                   // aktuelle Schrittmotor-Position aus
                                       // Puffer-String extrahieren
  bool LoadAreaValues();               // Parameter f�r Verfahrbereich laden
  bool SaveAreaValues();               //     "      "         "       speichern
};

#endif // !defined(AFX_STEPOP_H__C8EA0593_0622_11D4_99AE_0000C0E169AB__INCLUDED_)
