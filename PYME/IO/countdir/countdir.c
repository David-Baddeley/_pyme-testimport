#include <Python.h>
#include <stdio.h>
#include <dirent.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <string.h>

#define FILETYPE_NORMAL             0
#define FILETYPE_DIRECTORY          1 << 0
#define FILETYPE_SERIES             1 << 1 // a directory which is actually a series - treat specially
#define FILETYPE_SERIES_COMPLETE    1 << 2 // a series which has finished spooling

int count_files(const char *path)
{
    DIR *dir;
    struct dirent *ent;
    long count=0;

    dir = opendir(path);

    while((ent = readdir(dir)))
            ++count;

    closedir(dir);

    return count;
}



static PyObject * dirsize(PyObject *self, PyObject *args)
{
    const char *path;
    long count=0;

    if (!PyArg_ParseTuple(args, "s", &path))
        return NULL;

    Py_BEGIN_ALLOW_THREADS

    count = count_files(path);

    Py_END_ALLOW_THREADS

    return Py_BuildValue("i", count);
}


#define BUF_SIZE 256
static PyObject * file_info(PyObject *self, PyObject *args)
{
    struct stat stat_info;
    struct stat test_stat;
    int status;

    int type=FILETYPE_NORMAL;
    long size;

    const char *path;
    char test_path[BUF_SIZE];

    if (!PyArg_ParseTuple(args, "s", &path))
        return NULL;

    Py_BEGIN_ALLOW_THREADS

    status = stat(path, &stat_info);

    if (status == 0)
    {
        if (S_ISDIR(stat_info.st_mode))
        {
            type |= FILETYPE_DIRECTORY;

            //test for presence of metadata file
            strncpy(test_path, path,BUF_SIZE - 1);
            strncat(test_path, "/metadata.json", BUF_SIZE - strlen(test_path) -1);

            if (stat(test_path, &test_stat) == 0) type |= FILETYPE_SERIES;

            //test for presence of events file
            strncpy(test_path, path, BUF_SIZE - 1);
            strncat(test_path, "/events.json", BUF_SIZE - strlen(test_path) -1);

            if (stat(test_path, &test_stat) == 0) type |= FILETYPE_SERIES_COMPLETE;

            size = count_files(path);
        } else
        {
            size = stat_info.st_size;
        }
    }

    Py_END_ALLOW_THREADS

    if (status != 0) return NULL;

    return Py_BuildValue("i, i", type, size);
}

static PyMethodDef countdirMethods[] = {
    {"dirsize",  dirsize, METH_VARARGS,
     "count the number of files in a directory."},
     {"file_info",  file_info, METH_VARARGS,
     "get info for a specific directory."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

PyMODINIT_FUNC initcountdir(void)
{
    (void) Py_InitModule("countdir", countdirMethods);
}