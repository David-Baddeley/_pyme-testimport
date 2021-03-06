import cherrypy
import threading
import requests

import queue as Queue
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('nodeserver')
logger.setLevel(logging.DEBUG)

import time
import sys

from PYME.misc import computerName
from PYME import config
from PYME.IO import clusterIO

from PYME.ParallelTasks import webframework

import ujson as json

WORKER_GET_TIMEOUT = config.get('nodeserver-worker-get-timeout', 60)

#disable socket timeout to prevent us from generating 408 errors
cherrypy.server.socket_timeout = 0

class NodeServer(object):
    def __init__(self, distributor, ip_address, port, nodeID=computerName.GetComputerName()):
        self._tasks = Queue.Queue()
        self._handins = Queue.Queue()

        self.nodeID = nodeID
        self.distributor_url = distributor
        self.ip_address = ip_address
        self.port = port

        self.workerIDs = set()

        self._lastUpdateTime = 0
        self._lastAnnounceTime = 0
        self._anounce_url = self.distributor_url + 'distributor/announce?nodeID=%s&ip=%s&port=%d' % (self.nodeID, self.ip_address, self.port)

        cherrypy.engine.subscribe('stop', self.stop)

        self._do_poll = True
        self._update_tasks_lock = threading.Lock()

        self._num_connection_fails = 0

        #set up threads to poll the distributor and announce ourselves and get and return tasks
        self.handinSession = requests.Session()
        self.pollThread = threading.Thread(target=self._poll)
        self.pollThread.start()

        self.announceSession = requests.Session()
        self.announceThread = threading.Thread(target=self._announce_loop)
        self.announceThread.start()

        self.taskSession = requests.Session()
        self.taskThread = threading.Thread(target=self._poll_tasks)
        self.taskThread.start()


    def _announce(self):
        t = time.time()
        if True:#(t - self._lastAnnounceTime) > .5:
            self._lastAnnounceTime = t

            #logger.debug('Announcing to %s' % self.distributor_url)
            if self.announceSession is None:
                self.announceSession = requests.Session()

            try:
                r = self.announceSession.post(self._anounce_url, timeout=1)
                if not r.status_code == 200 or not r.json()['ok']:
                    logger.error('Announce failed')
            except requests.ConnectionError:
                self.announceSession = None
                logger.error('Error announcing - could not connect to distributor %s' % self.distributor_url)
            except requests.Timeout:
                logger.error('Error announcing - distributor %s timed out' % self.distributor_url)



    @property
    def num_tasks_to_request(self):
        return config.get('nodeserver-chunksize', 50)*len(self.workerIDs)

    def _update_tasks(self):
        """Update our task queue"""
        with self._update_tasks_lock:
            t = time.time()
            if (t - self._lastUpdateTime) < 0.1:
                return

            self._lastUpdateTime = t

            if self.taskSession is None:
                self.taskSession = requests.Session()

            url = self.distributor_url + 'distributor/tasks?nodeID=%s&numWant=%d&timeout=5' % (self.nodeID, self.num_tasks_to_request)
            try:
                r = self.taskSession.get(url, timeout=120)
                resp = json.loads(r.content) #r.json()
                if resp['ok']:
                    for task in resp['result']:
                        self._tasks.put(task)

                if self._num_connection_fails > 0:
                    logger.info('Re-established connection to distributor after %d failures' % self._num_connection_fails)
                self._num_connection_fails = 0
            except requests.Timeout:
                logger.warn('Timeout getting tasks from distributor')
            except requests.ConnectionError:
                self.taskSession = None
                self._num_connection_fails += 1
                if self._num_connection_fails < 2:
                    #don't log subsequent failures to avoid filling up the disk
                    logger.error('Error getting tasks: Could not connect to distributor')

    def _do_handins(self):
        handins = []

        if self.handinSession is None:
            self.handinSession = requests.Session()

        try:
            while True:
                handins.append(self._handins.get_nowait())
        except Queue.Empty:
            pass

        if len(handins) > 0:
            try:
                r = self.handinSession.post(self.distributor_url + 'distributor/handin?nodeID=%s' % self.nodeID, json=handins)
                resp = r.json()
                if not resp['ok']:
                    raise RuntimeError('')
            except:
                logger.error('Error handing in tasks')
                self.handinSession = None


    def _poll(self):
        while self._do_poll:
            #self._announce()
            self._do_handins()
            #self._update_tasks()
            time.sleep(.5)

    def _poll_tasks(self):
        while self._do_poll:
            self._update_tasks()
            time.sleep(.1)

    def _announce_loop(self):
        while self._do_poll:
            self._announce()
            time.sleep(1)

    def stop(self):
        self._do_poll = False


    @webframework.register_endpoint('/node/tasks')
    def _get_tasks(self, workerID, numWant=50):
        self.workerIDs.add(workerID)
        #if self._tasks.qsize() < 10:
        #    self._update_tasks()

        t_f = time.time() + WORKER_GET_TIMEOUT
        tasks = []

        try:
            tasks += [self._tasks.get(timeout=WORKER_GET_TIMEOUT)] #wait for at least 1 task
            nTasks = 1

            while (nTasks < int(numWant)) and (time.time() < t_f):
                tasks.append(self._tasks.get_nowait())
                nTasks += 1
        except Queue.Empty:
            pass

        logging.debug('Giving %d tasks to %s' % (len(tasks), workerID))

        return json.dumps({'ok': True, 'result': tasks})



    @webframework.register_endpoint('/node/handin')
    def _handin(self, taskID, status):
        self._handins.put({'taskID': taskID, 'status':status})
        return json.dumps({'ok' : True})


    def _rateTask(self, task):
        cost = 1.0
        if task['type'] == 'localization':
            filename, serverfilter = clusterIO.parseURL(task['inputs']['frames'])
            filename = '/'.join([filename.lstrip('/'), 'frame%05d.pzf' % int(task['taskdef']['frameIndex'])])

            if clusterIO.isLocal(filename, serverfilter):
                cost = .01

        elif task['type'] == 'recipe':
            for URL in task['inputs'].values():
                if clusterIO.isLocal(*clusterIO.parseURL(URL)):
                    cost *= .2


        return {'id' : task['id'], 'cost': cost}

    @webframework.register_endpoint('/node/rate')
    def _rate(self, body):
        tasks = json.loads(body)

        ratings = [self._rateTask(task) for task in tasks]
        logger.debug('Returning %d ratings ... ' % len(ratings))

        return json.dumps({'ok': True, 'result': ratings})

    @webframework.register_endpoint('/node/status')
    def _status(self):
        return json.dumps({'Polling' : self._do_poll, 'nQueued' : self._tasks.qsize()})\



class CPNodeServer(NodeServer):
    @cherrypy.expose
    def status(self):
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return self._status()

    @cherrypy.expose
    def rate(self):
        cherrypy.response.headers['Content-Type'] = 'application/json'

        body = cherrypy.request.body.read(int(cherrypy.request.headers['Content-Length']))

        return self.rate(body)

    @cherrypy.expose
    def tasks(self, workerID, numWant=50):
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return self._get_tasks(workerID, numWant)

    @cherrypy.expose
    def handin(self, taskID, status):
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return self._handin(taskID, status)



class WFNodeServer(webframework.APIHTTPServer, NodeServer):
    def __init__(self, distributor, ip_address, port, nodeID=computerName.GetComputerName()):
        NodeServer.__init__(self, distributor, ip_address, port, nodeID=computerName.GetComputerName())

        server_address = ('', port)
        webframework.APIHTTPServer.__init__(self, server_address)
        self.daemon_threads = True


def runCP(distributor, port):
    import socket
    cherrypy.config.update({'server.socket_port': port,
                            'server.socket_host': '0.0.0.0',
                            'log.screen': False,
                            'log.access_file': '',
                            'log.error_file': '',
                            'server.thread_pool': 50,
                            })

    logging.getLogger('cherrypy.access').setLevel(logging.ERROR)

    externalAddr = socket.gethostbyname(socket.gethostname())

    nodeserver = CPNodeServer('http://' + distributor + '/', port = port, ip_address=externalAddr)

    app = cherrypy.tree.mount(nodeserver, '/node/')
    app.log.access_log.setLevel(logging.ERROR)

    try:

        cherrypy.quickstart()
    finally:
        nodeserver._do_poll = False


def run(distributor, port):
    import socket

    externalAddr = socket.gethostbyname(socket.gethostname())
    nodeserver = WFNodeServer('http://' + distributor + '/', port = port, ip_address=externalAddr)

    try:
        logger.info('Starting nodeserver on %s:%d' % (externalAddr, port))
        nodeserver.serve_forever()
    finally:
        nodeserver._do_poll = False
        logger.info('Shutting down ...')
        nodeserver.shutdown()
        nodeserver.server_close()



if __name__ == '__main__':
    distributor, port = sys.argv[1:]
    run(distributor, int(port))
