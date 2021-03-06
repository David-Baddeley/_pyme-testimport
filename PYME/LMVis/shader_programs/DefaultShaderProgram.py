#!/usr/bin/python

# DefaultShaderProgram.py
#
# Copyright Michael Graff
#   graff@hm.edu
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
import os

from PYME.LMVis.shader_programs.GLProgram import GLProgram, GL_VERTEX_SHADER, GL_FRAGMENT_SHADER, glUseProgram, \
    glPolygonMode, GL_FILL, GL_FRONT_AND_BACK, glEnable, GL_BLEND, GL_SRC_ALPHA, GL_DST_ALPHA, glBlendFunc, \
    glBlendEquation, GL_FUNC_ADD, GL_DEPTH_TEST, glDepthFunc, GL_LEQUAL, GL_POINT_SMOOTH, GL_ONE_MINUS_SRC_ALPHA, \
    GL_TRUE, glDepthMask, glClearDepth, glClear, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, glDisable, GL_ONE, GL_ZERO
from PYME.LMVis.shader_programs.shader_program import ShaderProgram


class DefaultShaderProgram(GLProgram):

    def __init__(self):
        GLProgram.__init__(self)
        shader_path = os.path.join(os.path.dirname(__file__), "shaders")
        _shader_program = ShaderProgram(shader_path)
        _shader_program.add_shader("default_vs.glsl", GL_VERTEX_SHADER)
        _shader_program.add_shader("default_fs.glsl", GL_FRAGMENT_SHADER)
        _shader_program.link()
        self.set_shader_program(_shader_program)

    def __enter__(self):
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_BLEND)
        glDepthMask(GL_TRUE)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_POINT_SMOOTH)
        self.get_shader_program().use()
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    def __exit__(self, exc_type, exc_val, exc_tb):
        glUseProgram(0)
        glDisable(GL_BLEND)
        glClearDepth(1.0)
        glClear(GL_DEPTH_BUFFER_BIT)
        pass


