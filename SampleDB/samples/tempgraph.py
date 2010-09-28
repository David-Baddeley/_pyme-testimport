from django.http import HttpResponse
from django.shortcuts import render_to_response
from SampleDB.samples.models import *
import matplotlib
matplotlib.use('Agg')
from pylab import *
import numpy as np
import time
from PYME.misc import tempDB
from datetime import datetime

def temprecord(request):
    numhours = 24
    if 'numhours' in request.REQUEST:
        numhours = int(request.REQUEST['numhours'])

    #print files

    return render_to_response('samples/temperature_record.html', {'numhours':numhours,})

def tempgraph(request, numhours):
    response = HttpResponse(mimetype="image/png")

    #nbins= 800


    #print start_date, end_date
    nhours = int(numhours)
    endtime= time.time()
    starttime = endtime - 3600*nhours

    times_1, temps_1 = tempDB.getEntries(starttime, endtime, 1)

    mask = (temps_1 < 0)
    mask[:-1] += (diff(times_1) > 20)

    temps_1 = np.ma.masked_array(temps_1, mask)

    times_2, temps_2 = tempDB.getEntries(starttime, endtime, 2)

    mask = (temps_2 < 0)
    mask[:-1] += (diff(times_2) > 20)

    temps_2 = np.ma.masked_array(temps_2, mask)

    times_3, temps_3 = tempDB.getEntries(starttime, endtime, 3)

    mask = (temps_3 < 0)
    mask[:-1] += (diff(times_3) > 20)

    temps_3 = np.ma.masked_array(temps_3, mask)

    dpi=100.
    f = figure(figsize=(1000/dpi, 600/dpi))
    #axes((.05, .05, .9, .9))


    plot(times_1, temps_1)
    plot(times_2, temps_2)
    plot(times_3, temps_3)
    xlabel('Time')
    ylabel('Temperature')
    legend(['Instrument Frame', 'Optical Table', 'AC control'], loc=2)
    title('Last %d hours' % nhours)
    
    #xlim(bins[0], bins[-1])

    xt = xticks()[0]

    #xt = linspace(dates[0], dates[-1], 5)
    #print xt

    if nhours < 24:
        dateform = '%H:%M'
    elif nhours < 72:
        dateform = '%H:%M %d/%m'
    else:
        dateform = '%d/%m'

    xticks(xt, [time.strftime(dateform, datetime.fromtimestamp(t).timetuple()) for t in xt])


    #box(False)

    f.savefig(response, dpi=dpi, format='png')
    return response
    
