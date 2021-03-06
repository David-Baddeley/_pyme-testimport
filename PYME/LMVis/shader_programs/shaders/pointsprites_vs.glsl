#version 120
//This vertex shader simply transforms the position in eye space and forwards it.
//This is one of the simplest vertex shader possible.
//It simply passes the given color to the fragment shader and
//transforms the vertex into screen space.
void main() {
    gl_PointSize = gl_Point.size;
    gl_FrontColor = gl_Color;
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
}