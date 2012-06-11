#!/usr/bin/python
import sys
import os

micrDataDir = '/smb/MicrData/'
lDataDir = len(micrDataDir)
nasDir = '/smb/NasData/'
#backupDir = '/media/disk/LMNAS1/'

def deleteFiles(directory):
    #dir_size = 0
    for (path, dirs, files) in os.walk(directory):
        for file in files:
            filename = os.path.join(path, file)
            #print filename

            nFilename = nasDir + filename[lDataDir:]
            bFilename = backupDir + filename[lDataDir:]

            print nFilename, bFilename

            if os.path.exists(nFilename) and os.path.getsize(nFilename) == os.path.getsize(filename): #and os.path.exists(bFilename) and os.path.getsize(filename) == os.path.getsize(nFilename):
                print 'Deleting %s' % filename
                os.remove(filename)
            else:
                print 'Keeping %s' % filename

        for dir in dirs:
            dirname = os.path.join(path, dir)

            if len(os.listdir(dirname)) == 0 and not 'System Volume Information' in dirname:
                print 'Removing %s' % dirname
                os.rmdir(dirname)


if __name__ == '__main__':
    deleteFiles(sys.argv[1])
