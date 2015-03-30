#include "Python.h"
#include <complex.h>
#include <math.h>
#include "numpy/arrayobject.h"
#include <stdio.h>

#define MIN(a, b) ((a<b) ? a : b) 
#define MAX(a, b) ((a>b) ? a : b)

#define LITTLEENDIAN


//Really dodgy fast approximation to exponential
static union
{
  double d;
  struct
  {

#ifdef LITTLEENDIAN
    int j, i;
#else
    int i, j;
#endif
  } n;
} eco;

#define EXP_A (1048576/M_LN2) /* use 1512775 for integer version */
#define EXP_C 60801 /* see text for choice of c values */
#define EXP(y) (eco.n.i = EXP_A*(y) + (1072693248 - EXP_C), eco.d)
//end exponential approx

static PyObject * NRFilter(PyObject *self, PyObject *args, PyObject *keywds);
