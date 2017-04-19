#!/usr/bin/python

##################
# gl_render3D.py
#
# Copyright Michael Graff
# graff@hm.edu
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
from math import floor

import numpy
import numpy as np
import wx
import wx.glcanvas
from OpenGL.GL import *
from OpenGL.GLU import *

from PYME.LMVis.layers import AxesOverlayLayer, LUTOverlayLayer, Point3DRenderLayer, PointSpritesRenderLayer, \
    QuadTreeRenderLayer, RenderLayer, ScaleBarOverlayLayer, SelectionOverlayLayer, ShadedPointRenderLayer, \
    TriangleRenderLayer

from PYME.LMVis.gl_offScreenHandler import OffScreenHandler
from wx.glcanvas import GLCanvas

from PYME.LMVis.views import View

try:
    from PYME.Analysis.points.gen3DTriangs import gen3DTriangs, gen3DBlobs
except:
    pass

try:
    # location in Python 2.7 and 3.1
    from weakref import WeakSet
except ImportError:
    # separately installed py 2.6 compatibility
    from weakrefset import WeakSet

# import time

import sys

if sys.platform == 'darwin':
    # osx gives us LOTS of scroll events
    # ajust the mag in smaller increments
    ZOOM_FACTOR = 1.1
else:
    ZOOM_FACTOR = 2.0

# import statusLog

name = 'ball_glut'


class SelectionSettings(object):
    def __init__(self):
        self.start = (0, 0)
        self.finish = (0, 0)
        self.colour = [1, 1, 0]
        self.show = False


class LMGLShaderCanvas(GLCanvas):
    LUTOverlayLayer = None
    AxesOverlayLayer = None
    ScaleBarOverlayLayer = None
    _is_initialized = False

    def __init__(self, parent):
        print("New Canvas")
        attribute_list = [wx.glcanvas.WX_GL_RGBA, wx.glcanvas.WX_GL_STENCIL_SIZE, 8, wx.glcanvas.WX_GL_DOUBLEBUFFER, 16]
        GLCanvas.__init__(self, parent, -1, attribList=attribute_list)
        wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_SIZE(self, self.OnSize)
        wx.EVT_MOUSEWHEEL(self, self.OnWheel)
        wx.EVT_LEFT_DOWN(self, self.OnLeftDown)
        wx.EVT_LEFT_UP(self, self.OnLeftUp)
        wx.EVT_MIDDLE_DOWN(self, self.OnMiddleDown)
        wx.EVT_MIDDLE_UP(self, self.OnMiddleUp)
        wx.EVT_RIGHT_DOWN(self, self.OnMiddleDown)
        wx.EVT_RIGHT_UP(self, self.OnMiddleUp)
        wx.EVT_MOTION(self, self.OnMouseMove)
        wx.EVT_KEY_DOWN(self, self.OnKeyPress)
        # wx.EVT_MOVE(self, self.OnMove)
        self.gl_context = wx.glcanvas.GLContext(self)

        self.nVertices = 0
        self.IScale = [1.0, 1.0, 1.0]
        self.zeroPt = [0, 1.0 / 3, 2.0 / 3]
        self.cmap = None
        self.clim = [0, 1]
        self.alim = [0, 1]

        self.displayMode = '2D'  # 3DPersp' #one of 3DPersp, 3DOrtho, 2D

        self.wireframe = False

        self.parent = parent

        self.pointSize = 5  # default point size = 5nm

        self._scaleBarLength = 1000

        self.centreCross = False

        self.LUTDraw = True

        self.c = numpy.array([1, 1, 1])
        self.a = numpy.array([1, 1, 1])
        self.zmin = -10
        self.zmax = 10

        self.angup = 0
        self.angright = 0

        self.vecUp = numpy.array([0, 1, 0])
        self.vecRight = numpy.array([1, 0, 0])
        self.vecBack = numpy.array([0, 0, 1])

        self.xc = 0
        self.yc = 0
        self.zc = 0

        self.zc_o = 0

        self.sx = 100
        self.sy = 100

        self.scale = 1
        self.stereo = False

        self.eye_dist = .01

        self.dragging = False
        self.panning = False

        self.edgeThreshold = 20

        self.selectionSettings = SelectionSettings()
        self.selectionDragging = False

        self.layers = []
        self.overlays = []

        self.wantViewChangeNotification = WeakSet()
        self.pointSelectionCallbacks = []

        self.on_screen = True
        self.view_port_size = (self.Size[0], self.Size[1])

        return

    @property
    def scaleBarLength(self):
        return self._scaleBarLength

    @scaleBarLength.setter
    def scaleBarLength(self, value):
        self._scaleBarLength = value
        self.ScaleBarOverlayLayer.set_scale_bar_length(value)

    def OnPaint(self, events):
        if not self.IsShown():
            print('ns')
            return
        wx.PaintDC(self)
        # print self.GetContext()
        self.gl_context.SetCurrent(self)
        self.SetCurrent()

        if not self._is_initialized:
            self.initialize()
        else:
            self.OnDraw()
        return

    def initialize(self):
        self.InitGL()
        self.ScaleBarOverlayLayer = ScaleBarOverlayLayer()
        self.LUTOverlayLayer = LUTOverlayLayer()
        self.AxesOverlayLayer = AxesOverlayLayer()
        self.overlays.append(SelectionOverlayLayer(self.selectionSettings))

        self._is_initialized = True

    def OnSize(self, event):
        self.view_port_size = (self.Size[0], self.Size[1])
        if self._is_initialized:
            self.OnDraw()
        self.Refresh()

        # self.interlace_stencil()

    def OnMove(self, event):
        self.Refresh()

    def setOverlayMessage(self, message=''):
        # self.messageOverlay.set_message(message)
        # if self._is_initialized:
        #     self.Refresh()
        pass

    def interlace_stencil(self):
        window_width = self.view_port_size[0]
        window_height = self.view_port_size[1]
        # setting screen-corresponding geometry
        glViewport(0, 0, window_width, window_height)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0.0, window_width - 1, 0.0, window_height - 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # clearing and configuring stencil drawing
        if self.on_screen:
            glDrawBuffer(GL_BACK)
        glEnable(GL_STENCIL_TEST)
        glClearStencil(0)
        glClear(GL_STENCIL_BUFFER_BIT)
        glStencilOp(GL_REPLACE, GL_REPLACE, GL_REPLACE)  # colorbuffer is copied to stencil
        glDisable(GL_DEPTH_TEST)
        glStencilFunc(GL_ALWAYS, 1, 1)  # to avoid interaction with stencil content

        # drawing stencil pattern
        glColor4f(1, 1, 1, 0)  # alfa is 0 not to interfere with alpha tests

        start = self.ScreenPosition[1] % 2
        # print start

        for y in range(start, window_height, 2):
            glLineWidth(1)
            glBegin(GL_LINES)
            glVertex2f(0, y)
            glVertex2f(window_width, y)
            glEnd()

        glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP)  # // disabling changes in stencil buffer
        glFlush()

        # print 'is'

    def OnDraw(self):
        self.interlace_stencil()
        glEnable(GL_DEPTH_TEST)
        glClear(GL_COLOR_BUFFER_BIT)

        # print 'od'

        if self.displayMode == '2D':
            views = ['2D']
        elif self.stereo:
            views = ['left', 'right']
        else:
            views = ['centre']

        for view in views:
            if view == 'left':
                eye = -self.eye_dist
                glStencilFunc(GL_NOTEQUAL, 1, 1)
            elif view == 'right':
                eye = +self.eye_dist
                glStencilFunc(GL_EQUAL, 1, 1)
            else:
                eye = 0

            glClear(GL_DEPTH_BUFFER_BIT)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()

            ys = float(self.view_port_size[1]) / float(self.view_port_size[0])

            if self.displayMode == '3DPersp':
                glFrustum(-1 + eye, 1 + eye, -ys, ys, 8.5, 11.5)
            else:
                glOrtho(-1, 1, -ys, ys, -1000, 1000)

            glMatrixMode(GL_MODELVIEW)
            glTranslatef(eye, 0.0, 0.0)

            glTranslatef(0, 0, -10)

            if not self.displayMode == '2D':
                self.AxesOverlayLayer.render(self)

            glScalef(self.scale, self.scale, self.scale)

            glPushMatrix()
            # rotate object
            glMultMatrixf(self.object_rotation_matrix)

            glTranslatef(-self.xc, -self.yc, -self.zc)

            for l in self.layers:
                l.render(self)

            for o in self.overlays:
                o.render(self)

            glPopMatrix()

            self.ScaleBarOverlayLayer.render(self)
            self.LUTOverlayLayer.render(self)

        glFlush()

        self.SwapBuffers()

        return

    @property
    def object_rotation_matrix(self):
        """
        The transformation matrix used to map coordinates in real space to our 3D view space. Currently implements
        rotation, defined by 3 vectors (up, right, and back). Does not include scaling or projection.
        
        Returns
        -------
        a 4x4 matrix describing the rotation of the pints within our 3D world
        
        """
        if not self.displayMode == '2D':
            return numpy.array(
                [numpy.hstack((self.vecRight, 0)), numpy.hstack((self.vecUp, 0)), numpy.hstack((self.vecBack, 0)),
                 [0, 0, 0, 1]])
        else:
            return numpy.eye(4)

    def InitGL(self):
        print('OpenGL - Version: {}'.format(glGetString(GL_VERSION)))
        print('Shader - Version: {}'.format(glGetString(GL_SHADING_LANGUAGE_VERSION)))
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_NORMALIZE)

        glLoadIdentity()
        glOrtho(self.xmin, self.xmax, self.ymin, self.ymax, self.zmin, self.zmax)
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClearDepth(1.0)

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_POINT_SMOOTH)

        self.ResetView()

        return

    def setTriang3D(self, x, y, z, c=None, sizeCutoff=1000., zrescale=1, internalCull=True, wireframe=False, alpha=1,
                    recenter=True):

        if recenter:
            self.recenter(x, y)
        self.layers.append(TriangleRenderLayer(x, y, z, c, self.cmap, sizeCutoff,
                                               internalCull, zrescale, alpha, is_wire_frame=wireframe))
        self.Refresh()

    def setTriang(self, T, c=None, sizeCutoff=1000., zrescale=1, internalCull=True, alpha=1,
                  recenter=True):
        # center data
        x = T.x
        y = T.y
        xs = x[T.triangle_nodes]
        ys = y[T.triangle_nodes]
        zs = np.zeros_like(xs)  # - z.mean()

        if recenter:
            self.recenter(x, y)

        if c is None:
            a = numpy.vstack((xs[:, 0] - xs[:, 1], ys[:, 0] - ys[:, 1])).T
            b = numpy.vstack((xs[:, 0] - xs[:, 2], ys[:, 0] - ys[:, 2])).T
            b2 = numpy.vstack((xs[:, 1] - xs[:, 2], ys[:, 1] - ys[:, 2])).T

            c = numpy.median([(b * b).sum(1), (a * a).sum(1), (b2 * b2).sum(1)], 0)
            c = 1.0 / (c + 1)

        self.c = numpy.vstack((c, c, c)).T.ravel()

        self.vecUp = numpy.array([0, 1, 0])
        self.vecRight = numpy.array([1, 0, 0])
        self.vecBack = numpy.array([0, 0, 1])

        self.SetCurrent()

        self.layers.append(
            RenderLayer(T.x[T.triangle_nodes], T.y[T.triangle_nodes], 0 * (T.x[T.triangle_nodes]), self.c,
                        self.cmap, self.clim, alpha))
        self.Refresh()

    def setTriangEdges(self, T):
        self.setTriang(T)

    def setPoints3D(self, x, y, z, c=None, a=None, recenter=False, alpha=1.0, mode='points',
                    normal_x = None, normal_y = None, normal_z = None):  # , clim=None):
        # center data
        x = x  # - x.mean()
        y = y  # - y.mean()
        z = z  # - z.mean()

        if recenter:
            self.recenter(x, y)

        self.zc = z.mean()
        self.zc_o = 1.0 * self.zc

        if c is None:
            self.c = numpy.ones(x.shape).ravel()
        else:
            self.c = c

        if a:
            self.a = a
        else:
            self.a = numpy.ones(x.shape).ravel()

        self.sx = x.max() - x.min()
        self.sy = y.max() - y.min()
        self.sz = z.max() - z.min()

        self.SetCurrent()

        if mode is 'pointsprites':
            self.layers.append(PointSpritesRenderLayer(x, y, z, self.c, self.cmap, self.clim, alpha, self.pointSize))
        elif mode is 'shadedpoints':
            self.layers.append(ShadedPointRenderLayer(x, y, z, normal_x, normal_y, normal_z, self.c, self.cmap,
                                                      self.clim, alpha=alpha, point_size=self.pointSize))
        else:
            self.layers.append(Point3DRenderLayer(x, y, z, self.c, self.cmap, self.clim,
                                                  alpha=alpha, point_size=self.pointSize))
        self.Refresh()

    def setPoints(self, x, y, c=None, a=None, recenter=True, alpha=1.0):
        """Set 2D points"""
        self.setPoints3D(x, y, 0 * x, c, a, recenter, alpha)

    def setQuads(self, qt, max_depth=100, md_scale=False):
        lvs = qt.getLeaves(max_depth)

        xs = numpy.zeros((len(lvs), 4))
        ys = numpy.zeros((len(lvs), 4))
        c = numpy.zeros(len(lvs))

        i = 0

        real_max_depth = 0
        for l in lvs:
            xs[i, :] = [l.x0, l.x1, l.x1, l.x0]
            ys[i, :] = [l.y0, l.y0, l.y1, l.y1]
            c[i] = float(l.numRecords) * 2 ** (2 * l.depth)
            i += 1
            real_max_depth = max(real_max_depth, l.depth)

        if not md_scale:
            c /= 2 ** (2 * real_max_depth)

        self.c = numpy.vstack((c, c, c, c)).T.ravel()

        self.SetCurrent()
        self.layers.append(QuadTreeRenderLayer(xs.ravel(), ys.ravel(), 0 * xs.ravel(),
                                               self.c, self.cmap, self.clim, alpha=1))
        self.Refresh()

    def ResetView(self):

        self.vecUp = numpy.array([0, 1, 0])
        self.vecRight = numpy.array([1, 0, 0])
        self.vecBack = numpy.array([0, 0, 1])

        self.Refresh()

    def setColour(self, IScale=None, zeroPt=None):
        self.Refresh()

    def setCMap(self, cmap):
        self.cmap = cmap
        if self.LUTOverlayLayer:
            self.LUTOverlayLayer.set_color_map(cmap)
        self.setColour()

    def setCLim(self, clim, alim=None):
        self.clim = clim
        if alim is None:
            self.alim = clim
        else:
            self.alim = alim
        self.setColour()

    @property
    def xmin(self):
        return self.xc - 0.5 * self.pixelsize * self.view_port_size[0]

    @property
    def xmax(self):
        return self.xc + 0.5 * self.pixelsize * self.view_port_size[0]

    @property
    def ymin(self):
        return self.yc - 0.5 * self.pixelsize * self.view_port_size[1]

    @property
    def ymax(self):
        return self.yc + 0.5 * self.pixelsize * self.view_port_size[1]

    @property
    def pixelsize(self):
        return 2. / (self.scale * self.view_port_size[0])

    def setView(self, xmin, xmax, ymin, ymax):

        self.xc = (xmin + xmax) / 2.0
        self.yc = (ymin + ymax) / 2.0
        self.zc = self.zc_o  # 0#z.mean()

        self.scale = 2. / (xmax - xmin)

        self.Refresh()
        if 'OnGLViewChanged' in dir(self.parent):
            self.parent.OnGLViewChanged()

        for callback in self.wantViewChangeNotification:
            callback.Refresh()

    def moveView(self, dx, dy, dz=0):
        return self.pan(dx, dy, dz)

    def pan(self, dx, dy, dz=0):
        # self.setView(self.xmin + dx, self.xmax + dx, self.ymin + dy, self.ymax + dy)
        self.xc += dx
        self.yc += dy
        self.zc += dz

        self.Refresh()

        for callback in self.wantViewChangeNotification:
            callback.Refresh()

    def OnWheel(self, event):
        rot = event.GetWheelRotation()
        xp, yp = self._ScreenCoordinatesToNm(event.GetX(), event.GetY())

        dx, dy = (xp - self.xc), (yp - self.yc)

        dx_, dy_, dz_, c_ = numpy.dot(self.object_rotation_matrix, [dx, dy, 0, 0])

        xp_, yp_, zp_ = (self.xc + dx_), (self.yc + dy_), (self.zc + dz_)

        # print xp
        # print yp
        if event.MiddleIsDown():
            self.WheelFocus(rot, xp_, yp_, zp_)
        else:
            self.WheelZoom(rot, xp_, yp_, zp_)

    def WheelZoom(self, rot, xp, yp, zp=0):
        dx = xp - self.xc
        dy = yp - self.yc
        dz = zp - self.zc

        if rot > 0:
            # zoom out
            self.scale *= ZOOM_FACTOR

            self.xc += dx * (1. - 1. / ZOOM_FACTOR)
            self.yc += dy * (1. - 1. / ZOOM_FACTOR)
            self.zc += dz * (1. - 1. / ZOOM_FACTOR)

        if rot < 0:
            # zoom in
            self.scale /= ZOOM_FACTOR

            self.xc += dx * (1. - ZOOM_FACTOR)
            self.yc += dy * (1. - ZOOM_FACTOR)
            self.zc += dz * (1. - ZOOM_FACTOR)

        self.Refresh()

        for callback in self.wantViewChangeNotification:
            callback.Refresh()

    def WheelFocus(self, rot, xp, yp, zp=0):
        if rot > 0:
            # zoom out
            self.zc -= 1.

        if rot < 0:
            # zoom in
            self.zc += 1.

        self.Refresh()

        for callback in self.wantViewChangeNotification:
            callback.Refresh()

    def OnLeftDown(self, event):
        if not self.displayMode == '2D':
            # dragging the mouse rotates the object
            self.xDragStart = event.GetX()
            self.yDragStart = event.GetY()

            self.angyst = self.angup
            self.angxst = self.angright

            self.dragging = True
        else:  # 2D
            # dragging the mouse sets an ROI
            xp, yp = self._ScreenCoordinatesToNm(event.GetX(), event.GetY())

            self.selectionDragging = True
            self.selectionSettings.show = True

            self.selectionSettings.start = (xp, yp)
            self.selectionSettings.finish = (xp, yp)

        event.Skip()

    def OnLeftUp(self, event):
        self.dragging = False

        if self.selectionDragging:
            xp, yp = self._ScreenCoordinatesToNm(event.GetX(), event.GetY())

            self.selectionSettings.finish = (xp, yp)
            self.selectionDragging = False

            self.Refresh()
            self.Update()

        event.Skip()

    def OnMiddleDown(self, event):
        self.xDragStart = event.GetX()
        self.yDragStart = event.GetY()

        self.panning = True
        event.Skip()

    def OnMiddleUp(self, event):
        self.panning = False
        event.Skip()

    def _ScreenCoordinatesToNm(self, x, y):
        # FIXME!!!
        x_ = self.pixelsize * (x - 0.5 * float(self.view_port_size[0])) + self.xc
        y_ = -self.pixelsize * (y - 0.5 * float(self.view_port_size[1])) + self.yc
        # print x_, y_
        return x_, y_

    def OnMouseMove(self, event):
        x = event.GetX()
        y = event.GetY()

        if self.selectionDragging:
            self.selectionSettings.finish = self._ScreenCoordinatesToNm(x, y)

            self.Refresh()
            event.Skip()

        elif self.dragging:

            angx = numpy.pi * (x - self.xDragStart) / 180
            angy = -numpy.pi * (y - self.yDragStart) / 180

            rMat1 = numpy.matrix(
                [[numpy.cos(angx), 0, numpy.sin(angx)], [0, 1, 0], [-numpy.sin(angx), 0, numpy.cos(angx)]])
            rMat = rMat1 * numpy.matrix(
                [[1, 0, 0], [0, numpy.cos(angy), numpy.sin(angy)], [0, -numpy.sin(angy), numpy.cos(angy)]])

            vecRightN = numpy.array(rMat * numpy.matrix(self.vecRight).T).squeeze()
            vecUpN = numpy.array(rMat * numpy.matrix(self.vecUp).T).squeeze()
            vecBackN = numpy.array(rMat * numpy.matrix(self.vecBack).T).squeeze()

            self.vecRight = vecRightN

            self.vecUp = vecUpN
            self.vecBack = vecBackN

            self.xDragStart = x
            self.yDragStart = y

            self.Refresh()
            event.Skip()

        elif self.panning:

            dx = self.pixelsize * (x - self.xDragStart)
            dy = -self.pixelsize * (y - self.yDragStart)

            # print dx

            dx_, dy_, dz_, c_ = numpy.dot(self.object_rotation_matrix, [dx, dy, 0, 0])

            self.xDragStart = x
            self.yDragStart = y

            self.pan(-dx_, -dy_, -dz_)

            event.Skip()

    def OnKeyPress(self, event):
        # print event.GetKeyCode()
        if event.GetKeyCode() == 83:  # S - toggle stereo
            self.stereo = not self.stereo
            self.Refresh()
        elif event.GetKeyCode() == 67:  # C - centre
            self.xc = self.sx / 2
            self.yc = self.sy / 2
            self.zc = self.sz / 2
            self.Refresh()

        elif event.GetKeyCode() == 91:  # [ decrease eye separation
            self.eye_dist /= 1.5
            self.Refresh()

        elif event.GetKeyCode() == 93:  # ] increase eye separation
            self.eye_dist *= 1.5
            self.Refresh()

        elif event.GetKeyCode() == 82:  # R reset view
            self.ResetView()
            self.Refresh()

        elif event.GetKeyCode() == 314:  # left
            pos = numpy.array([self.xc, self.yc, self.zc], 'f')
            pos -= 300 * self.vecRight
            self.xc, self.yc, self.zc = pos
            # print 'l'
            self.Refresh()

        elif event.GetKeyCode() == 315:  # up
            pos = numpy.array([self.xc, self.yc, self.zc])
            pos -= 300 * self.vecBack
            self.xc, self.yc, self.zc = pos
            self.Refresh()

        elif event.GetKeyCode() == 316:  # right
            pos = numpy.array([self.xc, self.yc, self.zc])
            pos += 300 * self.vecRight
            self.xc, self.yc, self.zc = pos
            self.Refresh()

        elif event.GetKeyCode() == 317:  # down
            pos = numpy.array([self.xc, self.yc, self.zc])
            pos += 300 * self.vecBack
            self.xc, self.yc, self.zc = pos
            self.Refresh()

        else:
            event.Skip()

    def getSnapshot(self, mode=GL_RGB):

        # glBindFramebuffer(GL_READ_FRAMEBUFFER, 0)
        # width, height = self.view_port_size[0], self.view_port_size[1]
        # snap = glReadPixelsf(0, 0, width, height, mode)
        # snap = snap.ravel().reshape(width, height, -1, order='F')
        #
        # if mode == GL_LUMINANCE:
        #     # snap.strides = (4, 4 * snap.shape[0])
        #     pass
        # elif mode == GL_RGB:
        #     snap.strides = (12, 12 * snap.shape[0], 4)
        # else:
        #     raise RuntimeError('{} is not a supported format.'.format(mode))
        # img.show()
        self.on_screen = False
        off_screen_handler = OffScreenHandler(self.view_port_size, mode)
        with off_screen_handler:
            self.OnDraw()
        snap = off_screen_handler.get_snap()
        self.on_screen = True
        return snap

    def getIm(self, pixel_size=None, mode=GL_RGB):

        if pixel_size is None or abs(1 - pixel_size) < 0.001:  # use current pixel size
            return self.getSnapshot(mode=mode)
        else:
            self.view_port_size = (int(round(self.Size[0] * pixel_size)), int(round(self.Size[1] * pixel_size)))
            snap = self.getSnapshot(mode=mode)
            self.view_port_size = self.Size
            return snap

    def recenter(self, x, y):
        self.xc = x.mean()
        self.yc = y.mean()
        self.zc = 0  # z.mean()

        self.sx = x.max() - x.min()
        self.sy = y.max() - y.min()
        self.sz = 0  # z.max() - z.min()

        self.scale = 2. / (max(self.sx, self.sy))

    def set_view(self, view):
        self.vecBack = view.vec_back
        self.vecRight = view.vec_right
        self.vecUp = view.vec_up
        self.xc = view.translation[0]
        self.yc = view.translation[1]
        self.zc = view.translation[2]
        self.scale = view.zoom
        self.Refresh()

    def get_view(self, view_id='id'):
        view = View(view_id,
                    self.vecUp,
                    self.vecBack,
                    self.vecRight,
                    np.array([self.xc, self.yc, self.zc]),
                    self.scale)
        return view


def showGLFrame():
    f = wx.Frame(None, size=(800, 800))
    c = LMGLShaderCanvas(f)
    f.Show()
    return c
