/*
##################
# lut.c
#
# Copyright David Baddeley, 2011
# d.baddeley@auckland.ac.nz
#
# This file may NOT be distributed without express permision from David Baddeley
#
##################
 */

#include "Python.h"
#include <complex.h>
#include <math.h>
#include "numpy/arrayobject.h"
#include <stdio.h>

#define MIN(X,Y) ((X) < (Y) ? (X) : (Y))
#define MAX(X,Y) ((X) > (Y) ? (X) : (Y))

static PyObject * applyLUTuint16(PyObject *self, PyObject *args, PyObject *keywds)
{
    unsigned short *data = 0;
    unsigned char *LUTR = 0;
    unsigned char *LUTG = 0;
    unsigned char *LUTB = 0;
    unsigned char *out = 0;
    float gain = 0;
    float offset = 0;
    //float d = 0;

    int tmp = 0;

    PyObject *odata =0;
    PyObject *adata =0;
    PyObject *oLUT =0;
    PyObject *oout =0;

    int sizeX;
    int sizeY;
    int N, N1;
    int i,j;

    static char *kwlist[] = {"data", "gain", "offest", "LUT", "output", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, keywds, "OffOO", kwlist,
         &odata, &gain, &offset, &oLUT, &oout))
        return NULL;

    /* Do the calculations */

    adata = PyArray_GETCONTIGUOUS(odata);


    if (!PyArray_Check(adata)  || !PyArray_ISCONTIGUOUS(adata))
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a contiguous numpy array");
        Py_DECREF(adata);
        return NULL;
    }

    if (PyArray_NDIM(adata) != 2)
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a 2 dimensional array");
        Py_DECREF(adata);
        return NULL;
    }

    if (!PyArray_Check(oLUT) || !PyArray_ISCONTIGUOUS(oLUT))
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a contiguous numpy array");
        Py_DECREF(adata);
        return NULL;
    }

    if (PyArray_NDIM(oLUT) != 2)
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a 2 dimensional array");
        Py_DECREF(adata);
        return NULL;
    }

    if (!PyArray_Check(oout) || !PyArray_ISCONTIGUOUS(oout))
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a contiguous numpy array");
        Py_DECREF(adata);
        return NULL;
    }

    if (PyArray_NDIM(oout) != 3)
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a 2 dimensional array");
        Py_DECREF(adata);
        return NULL;
    }

    sizeX = PyArray_DIM(odata, 0);
    sizeY = PyArray_DIM(odata, 1);

    N = PyArray_DIM(oLUT, 1);


    if ((PyArray_NDIM(oout) != 3) || (PyArray_DIM(oout, 0) != sizeX)|| (PyArray_DIM(oout, 1) != sizeY)|| (PyArray_DIM(oout, 2) != 3))
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a data.shape[0] x data.shape[1] x 3 array");
        Py_DECREF(adata);
        return NULL;
    }

    data = (unsigned short*) PyArray_DATA(adata);

    LUTR = (unsigned char*) PyArray_DATA(oLUT);
    LUTG = LUTR + N;
    LUTB = LUTG + N;
    out = (unsigned char*) PyArray_DATA(oout);

    N1 = N - 1;

    gain = gain*(float)N1;

    //printf("%d\n", N);


    Py_BEGIN_ALLOW_THREADS;

    for (i=0;i < sizeX; i++)
    {
        for (j=0;j< sizeY;j++)
        {
            //d = (float)(*(unsigned short *)PyArray_GETPTR2(odata, i, j));
            tmp =  (int)(gain*(((float) *data) - offset));
            //tmp =  (int)(((float)(N-1))*gain*(d - offset));
            //printf("%d", tmp);
            tmp = MIN(tmp, (N1));
            tmp = MAX(tmp, 0);
            *out += LUTR[tmp];
            out++;
            *out += LUTG[tmp];
            out++;
            *out += LUTB[tmp];
            out++;
            data ++;
        }
    }

    Py_END_ALLOW_THREADS;

    Py_DECREF(adata);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * applyLUTuint8(PyObject *self, PyObject *args, PyObject *keywds)
{
    unsigned char *data = 0;
    unsigned char *LUTR = 0;
    unsigned char *LUTG = 0;
    unsigned char *LUTB = 0;
    unsigned char *out = 0;
    float gain = 0;
    float offset = 0;
    //float d = 0;

    int tmp = 0;

    PyObject *odata =0;
    PyObject *adata =0;
    PyObject *oLUT =0;
    PyObject *oout =0;

    int sizeX;
    int sizeY;
    int N, N1;
    int i,j;

    static char *kwlist[] = {"data", "gain", "offest", "LUT", "output", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, keywds, "OffOO", kwlist,
         &odata, &gain, &offset, &oLUT, &oout))
        return NULL;

    /* Do the calculations */

    adata = PyArray_GETCONTIGUOUS(odata);


    if (!PyArray_Check(adata)  || !PyArray_ISCONTIGUOUS(adata))
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a contiguous numpy array");
        Py_DECREF(adata);
        return NULL;
    }

    if (PyArray_NDIM(adata) != 2)
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a 2 dimensional array");
        Py_DECREF(adata);
        return NULL;
    }

    if (!PyArray_Check(oLUT) || !PyArray_ISCONTIGUOUS(oLUT))
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a contiguous numpy array");
        Py_DECREF(adata);
        return NULL;
    }

    if (PyArray_NDIM(oLUT) != 2)
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a 2 dimensional array");
        Py_DECREF(adata);
        return NULL;
    }

    if (!PyArray_Check(oout) || !PyArray_ISCONTIGUOUS(oout))
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a contiguous numpy array");
        Py_DECREF(adata);
        return NULL;
    }

    if (PyArray_NDIM(oout) != 3)
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a 2 dimensional array");
        Py_DECREF(adata);
        return NULL;
    }

    sizeX = PyArray_DIM(odata, 0);
    sizeY = PyArray_DIM(odata, 1);

    N = PyArray_DIM(oLUT, 1);


    if ((PyArray_NDIM(oout) != 3) || (PyArray_DIM(oout, 0) != sizeX)|| (PyArray_DIM(oout, 1) != sizeY)|| (PyArray_DIM(oout, 2) != 3))
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a data.shape[0] x data.shape[1] x 3 array");
        Py_DECREF(adata);
        return NULL;
    }

    data = (unsigned char*) PyArray_DATA(adata);

    LUTR = (unsigned char*) PyArray_DATA(oLUT);
    LUTG = LUTR + N;
    LUTB = LUTG + N;
    out = (unsigned char*) PyArray_DATA(oout);

    N1 = N - 1;

    gain = gain*(float)N1;

    //printf("%d\n", N);


    Py_BEGIN_ALLOW_THREADS;

    for (i=0;i < sizeX; i++)
    {
        for (j=0;j< sizeY;j++)
        {
            //d = (float)(*(unsigned short *)PyArray_GETPTR2(odata, i, j));
            tmp =  (int)(gain*(((float) *data) - offset));
            //tmp =  (int)(((float)(N-1))*gain*(d - offset));
            //printf("%d", tmp);
            tmp = MIN(tmp, N1);
            tmp = MAX(tmp, 0);
            *out += LUTR[tmp];
            out++;
            *out += LUTG[tmp];
            out++;
            *out += LUTB[tmp];
            out++;
            data ++;
        }
    }

    Py_END_ALLOW_THREADS;

    Py_DECREF(adata);

    Py_INCREF(Py_None);
    return Py_None;
}


static PyObject * applyLUTfloat(PyObject *self, PyObject *args, PyObject *keywds)
{
    float *data = 0;
    unsigned char *LUTR = 0;
    unsigned char *LUTG = 0;
    unsigned char *LUTB = 0;
    unsigned char *out = 0;
    float gain = 0;
    float offset = 0;
    //float d = 0;

    int tmp = 0;

    PyObject *odata =0;
    PyObject *adata =0;
    PyObject *oLUT =0;
    PyObject *oout =0;

    int sizeX;
    int sizeY;
    int N, N1;
    int i,j;

    static char *kwlist[] = {"data", "gain", "offest", "LUT", "output", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, keywds, "OffOO", kwlist,
         &odata, &gain, &offset, &oLUT, &oout))
        return NULL;

    /* Do the calculations */

    adata = PyArray_GETCONTIGUOUS(odata);


    if (!PyArray_Check(adata)  || !PyArray_ISCONTIGUOUS(adata))
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a contiguous numpy array");
        Py_DECREF(adata);
        return NULL;
    }

    if (PyArray_NDIM(adata) != 2)
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a 2 dimensional array");
        Py_DECREF(adata);
        return NULL;
    }

    if (!PyArray_Check(oLUT) || !PyArray_ISCONTIGUOUS(oLUT))
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a contiguous numpy array");
        Py_DECREF(adata);
        return NULL;
    }

    if (PyArray_NDIM(oLUT) != 2)
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a 2 dimensional array");
        Py_DECREF(adata);
        return NULL;
    }

    if (!PyArray_Check(oout) || !PyArray_ISCONTIGUOUS(oout))
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a contiguous numpy array");
        Py_DECREF(adata);
        return NULL;
    }

    if (PyArray_NDIM(oout) != 3)
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a 2 dimensional array");
        Py_DECREF(adata);
        return NULL;
    }

    sizeX = PyArray_DIM(odata, 0);
    sizeY = PyArray_DIM(odata, 1);

    N = PyArray_DIM(oLUT, 1);


    if ((PyArray_NDIM(oout) != 3) || (PyArray_DIM(oout, 0) != sizeX)|| (PyArray_DIM(oout, 1) != sizeY)|| (PyArray_DIM(oout, 2) != 3))
    {
        PyErr_Format(PyExc_RuntimeError, "Expecting a data.shape[0] x data.shape[1] x 3 array");
        Py_DECREF(adata);
        return NULL;
    }

    data = (float*) PyArray_DATA(adata);

    LUTR = (unsigned char*) PyArray_DATA(oLUT);
    LUTG = LUTR + N;
    LUTB = LUTG + N;
    out = (unsigned char*) PyArray_DATA(oout);

    N1 = N - 1;

    gain = gain*(float)N1;

    //printf("%d\n", N);

    Py_BEGIN_ALLOW_THREADS;

    for (i=0;i < sizeX; i++)
    {
        for (j=0;j< sizeY;j++)
        {
            //d = (float)(*(unsigned short *)PyArray_GETPTR2(odata, i, j));
            tmp =  (int)(gain*(((float) *data) - offset));
            //tmp =  (int)(((float)(N-1))*gain*(d - offset));
            //printf("%d", tmp);
            tmp = MIN(tmp, N1);
            tmp = MAX(tmp, 0);
            *out += LUTR[tmp];
            out++;
            *out += LUTG[tmp];
            out++;
            *out += LUTB[tmp];
            out++;
            data ++;
        }
    }

    Py_END_ALLOW_THREADS;

    Py_DECREF(adata);

    Py_INCREF(Py_None);
    return Py_None;
}





static PyMethodDef lutMethods[] = {
    {"applyLUTu16",  applyLUTuint16, METH_VARARGS | METH_KEYWORDS,
    ""},
    {"applyLUTu8",  applyLUTuint8, METH_VARARGS | METH_KEYWORDS,
    ""},
    {"applyLUTf",  applyLUTfloat, METH_VARARGS | METH_KEYWORDS,
    ""},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};


PyMODINIT_FUNC initlut(void)
{
    PyObject *m;

    m = Py_InitModule("lut", lutMethods);
    import_array()

    //SpamError = PyErr_NewException("spam.error", NULL, NULL);
    //Py_INCREF(SpamError);
    //PyModule_AddObject(m, "error", SpamError);
}