#scope.pa.start()

#frs.OnBStartSpoolButton(None)
import copy

l = copy.copy(l488)#get a copy of laser to resolve pyro threading issues
l.dd = copy.copy(l.dd)

time.sleep(0.1)
l.TurnOn()
time.sleep(10)

onTime = 10
#offTimes = 20*ones(10)
#offTimes = [0.2,0.5,1, 2,5, 10, 20, 50, 100, 50, 20, 10, 5, 2, 0.5, 1,0.2]
offTimes = [20, 20, 20,20,20,20,20,20,20, 20]

for offT in offTimes:
    l.TurnOff()
    time.sleep(offT)
    l.TurnOn()
    time.sleep(onTime)


l.TurnOff()
scope.pa.stop()

#frs.OnBStopSpoolingButton(None)
