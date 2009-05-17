from wx.glcanvas import GLCanvas
import wx
#from OpenGL.GLUT import *
#from OpenGL.GLU import *
from OpenGL.GL import *
import sys,math
#import sys
import numpy
import Image
from scikits import delaunay
from PYME.Analysis.QuadTree import pointQT
import scipy
import pylab

from gen3DTriangs import gen3DTriangs, gen3DBlobs, testObj

import statusLog

name = 'ball_glut'

class cmap_mult:
    def __init__(self, gains, zeros):
        self.gains = gains
        self.zeros = zeros

    def __call__(self, cvals):
        return numpy.minimum(numpy.vstack((self.gains[0]*cvals - self.zeros[0],self.gains[1]*cvals - self.zeros[1],self.gains[2]*cvals - self.zeros[2], 1+ 0*cvals)), 1).astype('f').T

cm_hot = cmap_mult(8.0*numpy.ones(3)/3, [0, 3.0/8, 6.0/8])
cm_grey = cmap_mult(numpy.ones(3), [0, 0, 0])

class LMGLCanvas(GLCanvas):
    def __init__(self, parent):
        GLCanvas.__init__(self, parent,-1)
        wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_SIZE(self, self.OnSize)
        wx.EVT_MOUSEWHEEL(self, self.OnWheel)
        wx.EVT_LEFT_DOWN(self, self.OnLeftDown)
        wx.EVT_LEFT_UP(self, self.OnLeftUp)
        wx.EVT_MOTION(self, self.OnMouseMove)

        self.init = 0
        self.nVertices = 0
        self.IScale = [1.0, 1.0, 1.0]
        self.zeroPt = [0, 1.0/3, 2.0/3]
        self.cmap = pylab.cm.hsv
        self.clim = [0,1]
        self.alim = [0,1]

        self.parent = parent

        self.pointSize=5 #default point size = 5nm

        self.pixelsize = 5./800

        self.xmin =0
        self.xmax = self.pixelsize*self.Size[0]
        self.ymin = 0
        self.ymax = self.pixelsize*self.Size[1]

        self.scaleBarLength = 200

        self.scaleBarOffset = (20.0, 20.0) #pixels from corner
        self.scaleBarDepth = 10.0 #pixels
        self.scaleBarColour = [1,1,0]

        self.mode = 'triang'

        self.colouring = 'area'

        self.drawModes = {'triang':GL_TRIANGLES, 'quads':GL_QUADS, 'edges':GL_LINES, 'points':GL_POINTS}

        self.c = numpy.array([1,1,1])
        self.zmin = -10
        self.zmax = 10

        self.angup = 0
        self.angright = 0

        self.vecUp = numpy.array([0,1,0])
        self.vecRight = numpy.array([1,0,0])
        self.vecBack = numpy.array([0,0,1])

        self.xc = 0
        self.yc = 0
        self.zc = 0

        self.scale = 1
        
        self.dragging = False

        return

    def OnPaint(self,event):
        dc = wx.PaintDC(self)
        self.SetCurrent()
        if not self.init:
            self.InitGL()
            self.init = 1
        self.OnDraw()
        return

    def OnSize(self, event):
        glViewport(0,0, self.Size[0], self.Size[1])

        self.xmax = self.xmin + self.Size[0]*self.pixelsize
        self.ymax = self.ymin + self.Size[1]*self.pixelsize


    def OnDraw(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glLoadIdentity()
        glOrtho(-10,10,-10,10,-1000,1000)

        #glRotatef(self.angup, *self.vecUp)
        #glRotatef(self.angright, *self.vecRight)

        #glTranslatef(-self.xcc, -self.ycc, -self.zcc)

        glMultMatrixf(numpy.array([numpy.hstack((self.vecRight, 0)), numpy.hstack((self.vecUp, 0)), numpy.hstack((self.vecBack, 0)), [0,0,0, 1]]))

        glScalef(self.scale, self.scale, self.scale)

        glTranslatef(-self.xc, -self.yc, -self.zc)

        

        #glPushMatrix()
        #color = [1.0,0.,0.,1.]
        #glMaterialfv(GL_FRONT,GL_DIFFUSE,color)
        #glutSolidSphere(2,20,20)
        #glColor3f(1,0,0)

        #glBegin(GL_POLYGON)
        #glVertex2f(0, 0)
        #glVertex2f(1,0)
        #glVertex2f(1,1)
        #glVertex2f(0,1)
        #glEnd()

        

        if self.mode == 'points':
            glPointSize(self.pointSize*(float(self.Size[0])/(self.xmax - self.xmin)))

        #glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glPushMatrix ()

        glColor4f(0,0.5,0, 1)

        glDrawArrays(self.drawModes[self.mode], 0, self.nVertices)

        glPopMatrix ()
        

        glFlush()
        #glPopMatrix()
        self.SwapBuffers()
        return

    def InitGL(self):
        
        # set viewing projection
        light_diffuse = [0.5, 0.5, 0.5, 1.0]
        light_position = [20.0, 20.00, -20.0, 0.0]

        #glLightModelfv(GL_LIGHT_MODEL_AMBIENT, [0.5, 0.5, 0.5, 1.0]);
        #glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)

        glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse)
        glLightfv(GL_LIGHT0, GL_SPECULAR, [0.3,0.3,0.3,1.0])
        glLightfv(GL_LIGHT0, GL_POSITION, light_position)

        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_NORMALIZE)

        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [0.3, 0.3, 0.3, 1])
        glMaterialfv(GL_FRONT_AND_BACK, GL_SHININESS, 50)


        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glEnable(GL_COLOR_MATERIAL)

        glShadeModel(GL_SMOOTH)

        glLoadIdentity()
        glOrtho(self.xmin,self.xmax,self.ymin,self.ymax,self.zmin,self.zmax)
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClearDepth(1.0)


        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)
        glEnable (GL_BLEND)
        glBlendFunc (GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        #self.vs = glVertexPointerf(numpy.array([[5, 5],[10000, 10000], [10000, 5]]).astype('f'))
        #self.cs = glColorPointerf(numpy.ones((3,3)).astype('f'))

        #self.nVertices = 3

        self.setBlob(*testObj())

        #glMatrixMode(GL_PROJECTION)
        #glLoadIdentity()
        #gluPerspective(40.0, 1.0, 1.0, 30.0)

        #glMatrixMode(GL_MODELVIEW)
        #glLoadIdentity()
        #gluLookAt(0.0, 0.0, 10.0,
        #          0.0, 0.0, 0.0,
        #          0.0, 1.0, 0.0)
        return

    def setBlob(self, x,y,z, sizeCutoff=1000., zrescale=1):
        P, A, N = gen3DBlobs(x,y,z/zrescale, sizeCutoff)
        P[:,2] = P[:,2]*zrescale

        self.scale = 10./(x.max() - x.min())

        self.xc = x.mean()#*self.scale
        self.yc = y.mean()#*self.scale
        self.zc = z.mean()#*self.scale

        self.c = A
        vs = P
        
        self.vs_ = glVertexPointerf(vs)
        self.n_ = glNormalPointerf(N)
        
        self.mode = 'triang'

        self.nVertices = vs.shape[0]
        self.setColour(self.IScale, self.zeroPt)
        self.setCLim((self.c.min(), self.c.max()), (-1,-1))

    def setTriang(self, x,y,z, sizeCutoff=1000., zrescale=1):
        P, A, N = gen3DTriangs(x,y,z/zrescale, sizeCutoff)
        P[:,2] = P[:,2]*zrescale

        self.scale = 10./(x.max() - x.min())

        self.xc = x.mean()#*self.scale
        self.yc = y.mean()#*self.scale
        self.zc = z.mean()#*self.scale

        self.c = 1./A
        vs = P

        self.vs_ = glVertexPointerf(vs)
        self.n_ = glNormalPointerf(N)

        self.mode = 'triang'

        self.nVertices = vs.shape[0]

        self.setColour(self.IScale, self.zeroPt)
        self.setCLim((self.c.min(), self.c.max()), (0,0))

    def setPoints(self, x, y, z, c = None):
        if c == None:
            self.c = numpy.ones(x.shape).ravel()
        else:
            self.c = c

        self.xc = x.mean()#*self.scale
        self.yc = y.mean()#*self.scale
        self.zc = z.mean()#*self.scale

        vs = numpy.vstack((x.ravel(), y.ravel(), z.ravel()))
        vs = vs.T.ravel().reshape(len(x.ravel()), 3)
        self.vs_ = glVertexPointerf(vs)
        self.n_ = glNormalPointerf(0.69*numpy.ones(vs.shape))

        #cs = numpy.minimum(numpy.vstack((self.IScale[0]*c,self.IScale[1]*c,self.IScale[2]*c)), 1).astype('f')
        #cs = cs.T.ravel().reshape(len(c), 3)
        #cs_ = glColorPointerf(cs)

        self.mode = 'points'

        self.nVertices = vs.shape[0]
        self.setColour(self.IScale, self.zeroPt)
        self.setCLim((self.c.min(), self.c.max()), (0,0))


    def setTriangEdges(self, T):
        xs = T.x[T.edge_db]
        ys = T.y[T.edge_db]

        a = numpy.vstack((xs[:,0] - xs[:,1], ys[:,0] - ys[:,1])).T
        #b = numpy.vstack((xs[:,0] - xs[:,2], ys[:,0] - ys[:,2])).T

        #area of triangle
        #c = 0.5*numpy.sqrt((b*b).sum(1) - ((a*b).sum(1)**2)/(a*a).sum(1))*numpy.sqrt((a*a).sum(1))

        c = ((a*a).sum(1))

        #c_neighbours = c[T.triangle_neighbors].sum(1)
        c = 1.0/(c + 1)

        self.c = numpy.vstack((c,c)).T.ravel()

        vs = numpy.vstack((xs.ravel(), ys.ravel()))
        vs = vs.T.ravel().reshape(len(xs.ravel()), 2)
        self.vs_ = glVertexPointerf(vs)

        #cs = numpy.minimum(numpy.vstack((self.IScale[0]*c,self.IScale[1]*c,self.IScale[2]*c)), 1).astype('f')
        #cs = cs.T.ravel().reshape(len(c), 3)
        #cs_ = glColorPointerf(cs)

        self.mode = 'edges'

        self.nVertices = vs.shape[0]
        self.setColour(self.IScale, self.zeroPt)

    
    def setColour(self, IScale=None, zeroPt=None):
        #self.IScale = IScale
        #self.zeroPt = zeroPt

        #cs = numpy.minimum(numpy.vstack((IScale[0]*self.c - zeroPt[0],IScale[1]*self.c - zeroPt[1],IScale[2]*self.c - zeroPt[2])), 1).astype('f')
        cs_ = ((self.c - self.clim[0])/(self.clim[1] - self.clim[0]))
        csa_ = ((self.c - self.alim[0])/(self.alim[1] - self.alim[0]))
        cs = self.cmap(cs_)
        cs[:,3] = csa_
        #print cs.shape
        #print cs.shape
        #print cs.strides
        #cs = cs[:, :3] #if we have an alpha component chuck it
        cs = cs.ravel().reshape(len(self.c), 4)
        self.cs_ = glColorPointerf(cs)

        self.Refresh()

    def setCMap(self, cmap):
        self.cmap = cmap
        self.setColour()

    def setCLim(self, clim, alim=None):
        self.clim = clim
        if alim == None:
            self.alim = clim
        else:
            self.alim = alim
        self.setColour()


    def setView(self, xmin, xmax, ymin, ymax):
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax

        self.pixelsize = (xmax - xmin)*1./self.Size[0]

        self.Refresh()
        if 'OnGLViewChanged' in dir(self.parent):
            self.parent.OnGLViewChanged()

    def pan(self, dx, dy):
        self.setView(self.xmin + dx, self.xmax + dx, self.ymin + dy, self.ymax + dy)

    def drawScaleBar(self):
        if not self.scaleBarLength == None:
            view_size_x = self.xmax - self.xmin
            view_size_y = self.ymax - self.ymin

            sb_ur_x = self.xmax - self.scaleBarOffset[0]*view_size_x/self.Size[0]
            sb_ur_y = self.ymax - self.scaleBarOffset[1]*view_size_y/self.Size[1]
            sb_depth = self.scaleBarDepth*view_size_y/self.Size[1]

            glColor3fv(self.scaleBarColour)
            glBegin(GL_POLYGON)
            glVertex2f(sb_ur_x, sb_ur_y)
            glVertex2f(sb_ur_x, sb_ur_y - sb_depth)
            glVertex2f(sb_ur_x - self.scaleBarLength, sb_ur_y - sb_depth)
            glVertex2f(sb_ur_x - self.scaleBarLength, sb_ur_y)
            glEnd()




    def OnWheel(self, event):
        rot = event.GetWheelRotation()
        view_size_x = self.xmax - self.xmin
        view_size_y = self.ymax - self.ymin

        #get translated coordinates
        xp = 1*(event.GetX() - self.Size[0]/2)/float(self.Size[0])
        yp = 1*(self.Size[1]/2 - event.GetY())/float(self.Size[1])

        #print xp
        #print yp
        
        self.WheelZoom(rot, xp, yp)
        self.Refresh()

    

    def WheelZoom(self, rot, xp, yp):
        #print xp, yp
        #print self.xc, self.scale, self.scale*xp
        #self.xc += 20*xp/self.scale
        #self.yc += 20*yp/self.scale

        posCh = 20*xp*self.vecRight/self.scale + 20*yp*self.vecUp/self.scale

        self.xc += posCh[0]
        self.yc += posCh[1]
        self.zc -= posCh[2]

        if rot > 0:
            #zoom out
            self.scale *=2.
            #self.xc*=2
            #self.yc*=2


        if rot < 0:
            #zoom in
            self.scale /=2.
            #self.xc/=2
            #self.yc/=2
            


    def OnLeftDown(self, event):
        self.xDragStart = event.GetX()
        self.yDragStart = event.GetY()

        self.angyst = self.angup
        self.angxst = self.angright

        self.dragging = True

        event.Skip()

    def OnLeftUp(self, event):
        #x = event.GetX()
        #y = event.GetY()


        self.dragging=False
        
        
        #self.Refresh()
        event.Skip()

    def OnMouseMove(self, event):
        if self.dragging:
            x = event.GetX()
            y = event.GetY()

            #self.angup = self.angyst + x - self.xDragStart
            #self.angright = self.angxst + y - self.yDragStart

            angx = -numpy.pi*(x - self.xDragStart)/180

            vecRightN = numpy.cos(angx) * self.vecRight + numpy.sin(angx) * self.vecBack
            vecBackN = numpy.cos(angx) * self.vecBack - numpy.sin(angx) * self.vecRight

            self.vecRight = vecRightN
            self.vecBack = vecBackN

            angy = numpy.pi*(y - self.yDragStart)/180

            vecUpN = numpy.cos(angy) * self.vecUp + numpy.sin(angy) * self.vecBack
            vecBackN = numpy.cos(angy) * self.vecBack - numpy.sin(angy) * self.vecUp

            self.vecUp = vecUpN
            self.vecBack = vecBackN

            #print self.vecUp, self.vecRight, self.vecBack

            self.xDragStart = x
            self.yDragStart = y

            self.Refresh()

            event.Skip()

    def getSnapshot(self, mode = GL_LUMINANCE):
        snap =  glReadPixelsf(0,0,self.Size[0],self.Size[1], mode)

        snap.strides = (12,12*snap.shape[0], 4)

        return snap







def showGLFrame():
    f = wx.Frame(None, size=(800,800))
    c = LMGLCanvas(f)
    f.Show()
    return c





def main():
    app = wx.PySimpleApp()
    frame = wx.Frame(None,-1,'ball_wx',wx.DefaultPosition,wx.Size(800,800))
    canvas = LMGLCanvas(frame)
    frame.Show()
    app.MainLoop()

if __name__ == '__main__': main()
