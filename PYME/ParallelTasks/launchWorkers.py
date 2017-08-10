#!/usr/bin/python

##################
# launchWorkers.py
#
# Copyright David Baddeley, 2009
# d.baddeley@auckland.ac.nz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##################

#!/usr/bin/python

import os
import subprocess
import sys
import time

#import Pyro.naming

def cpuCount():
    """
    Returns the number of CPUs in the system
    borrowed from the python 'processing' package
    """
    if sys.platform == 'win32':
        try:
            num = int(os.environ['NUMBER_OF_PROCESSORS'])
        except (ValueError, KeyError):
            num = 0
    elif sys.platform == 'darwin':
        try:
            num = int(os.popen('sysctl -n hw.ncpu').read())
        except ValueError:
            num = 0
    else: #assuming unix
        try:
            num = os.sysconf('SC_NPROCESSORS_ONLN')
        except (ValueError, OSError, AttributeError):
            num = 0
        
    if num >= 1:
        return num
    else:
        raise NotImplementedError('cannot determine number of cpus')


#get rid of any previously started queues etc...
#os.system('killall taskServerM.py')
#os.system('killall taskWorkerM.py')
#os.system('killall fitMon.py')

#launch pyro name server
#os.system('pyro-nsd start')

#SERVER_PROC = 'taskServerMP.py'
#WORKER_PROC = 'taskWorkerMP.py'
SERVER_PROC = 'taskServerZC'
WORKER_PROC = 'taskWorkerZC'

fstub = os.path.split(__file__)[0]

def main():
    global SERVER_PROC, WORKER_PROC
    #get number of processors 
    numProcessors = cpuCount()
#    try: #try and find the name server
#        ns=Pyro.naming.NameServerLocator().getNS()
#    except: #launch our own
#        print("""Could not find PYRO nameserver - launching a local copy:
#            
#        This should work if you are only using one computer, or if you are 
#        really, really careful not to close this process before all other 
#        computers are done but is not going to be very robust.
#        
#        I highly recommend running the pyro nameserver as a seperate process, 
#        ideally on a server somewhere where it's not likely to get interrupted.
#        """)
#        
#        subprocess.Popen('pyro-ns', shell=True)
#        #wait for server to come up
#        time.sleep(3)

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--local', dest='local', action='store_true',
                        help='run in local only mode')
    parser.add_argument('-w', '--no-server', dest='run_server', action='store_false',default=True,
                        help='Only launch the workers (no server)')
    parser.add_argument('--no-gui', dest='gui', action='store_false',default=True)
    parser.add_argument('NWorkers', type=int, nargs='?', default=cpuCount(),
                        help='Number of worker processes to use')
    parser.add_argument('-k', '--kill', dest='kill', default=False, action='store_true', help='Kill all existing workers without launching new ones')
    args = parser.parse_args()
    
    if args.local:
        SERVER_PROC = 'taskServerML.py'
        WORKER_PROC = 'taskWorkerML.py'

    numProcessors = args.NWorkers
    
    if sys.platform == 'win32':
        if args.kill:
            raise RuntimeError('Kill functionality not supported on windows. Close the window that the previous launchWorkers instance was run from instead')

        if args.run_server:
            print('Launching server ...')
            subprocess.Popen('python "%s\\%s.py"' % (fstub, SERVER_PROC), shell=True)

            print('Waiting for server to come up ...')
            time.sleep(10)

        if args.gui:
            print('Launching task monitor ...')
            subprocess.Popen('python "%s\\fitMonP.py"' % fstub, shell=True)
    
        print('Launching %d workers ...' % numProcessors)
        for i in range(numProcessors):
            subprocess.Popen('python "%s\\%s.py"' % (fstub, WORKER_PROC), shell=True)
    elif sys.platform == 'darwin':
        import psutil
        
        #kill off previous workers and servers
        for p in psutil.process_iter():
            try:
                if 'python' in p.name():
                    c = p.cmdline()
                    #print c, SERVER_PROC, WORKER_PROC
                    if (SERVER_PROC in c[1] and args.run_server) or (WORKER_PROC in c[1]) or ('fitMonP' in c[1] and args.gui):
                        print('killing %s' % c)
                        p.kill()
            except (psutil.ZombieProcess, psutil.AccessDenied):
                pass

        if args.kill:
            return

        if args.run_server:
            subprocess.Popen('%s %s.py' % (sys.executable, os.path.join(fstub, SERVER_PROC)), shell=True)

            time.sleep(10)
        if args.gui:
            subprocess.Popen('%s %s' % (sys.executable, os.path.join(fstub,'fitMonP.py')), shell=True)
    
        for i in range(numProcessors):
            subprocess.Popen('%s %s.py' % (sys.executable, os.path.join(fstub,WORKER_PROC)), shell=True)
    else: #operating systems which can launch python scripts directly
        #get rid of any previously started queues etc...
        if args.run_server:
            os.system('killall %s' % SERVER_PROC)

        if args.gui:
            os.system('killall %s' % WORKER_PROC)
        os.system('killall fitMonP')

        if args.kill:
            return

        if args.run_server:
            subprocess.Popen(SERVER_PROC, shell=True)

            time.sleep(3)

        if args.gui:
            subprocess.Popen('fitMonP', shell=True)
    
        for i in range(numProcessors):
            subprocess.Popen(WORKER_PROC, shell=True)
            

if __name__ == '__main__':
    main()
