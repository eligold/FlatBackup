
# OpenCV C++ python module build notes
This directory contains my efforts to build a python module in C++ that will undistort an input backup camera image and convert it into the panelized output displayed on screen. Turns out replicating python code based on C++ under the hood in C++ isn't actually any faster but at least I learned something.
1. ] https://docs.opencv.org/4.x/da/d49/tutorial_py_bindings_basics.html
    Limited guidance from the OpenCV documentation
1. ] https://learnopencv.com/how-to-convert-your-opencv-c-code-into-a-python-module/
    This page is the tutorial for using code available at both of the below  listed repositories. The module name is changed in [3] but it is otherwise functionally identical
1. ] https://github.com/TracelessLe/cv2_gen_python_bindings/
1. ] https://github.com/spmallick/learnopencv/tree/master/pymodule
    In order to get the above example to work, I had to make the changes indicated in the `diff` patch below. I might have broken UMat functionality but in doing so I was able to get the example to compile. Despite my experience with arduino code, my knowledge of pure C++ is limited. I attempted to implement the entire script in a module using these guides but couldn't get it to work. I was successful in building a module that puts an input image through the same OpenCV manipulations I was doing in python but in testing it actually turned out to be about 1ms slower than just keeping everything within a python context. I think the benefits of a custom module come from implementing much more complex logic than I am working with in this project. Since the same tutorial code appears in two different github repos and wasn't functional with modern versions of OpenCV as instructed I decided to document my changes here in case anybody else runs into the same issues I did.
    ```
    diff ../../learnopencv/pymodule/bv.cpp ./bv.cpp
    187c187
    <     UMatData* allocate(int dims0, const int* sizes, int type, void* data, size_t* step, int flags, UMatUsageFlags usageFlags) const
    ---
    >     UMatData* allocate(int dims0, const int* sizes, int type, void* data, size_t* step, AccessFlag flags, UMatUsageFlags usageFlags) const
    216c216
    <     bool allocate(UMatData* u, int accessFlags, UMatUsageFlags usageFlags) const
    ---
    >     bool allocate(UMatData* u, AccessFlag accessFlags, UMatUsageFlags usageFlags) const
    589c589
    <     int accessFlags;
    ---
    >     AccessFlag accessFlags;
    ```
    In step 5 from the tutorial linked in [[2](#opencv-c-python-module-build-notes)] above, the command to compile the module also required slight tweaking. the `pkg-config` command failed referring to `opencv`, I had to point it to `opencv4` instead to resolve the dependency flags correctly with my environment and installed version of OpenCV:
    <br>
    g++ -shared -rdynamic -g -O3 -Wall -fPIC \\
    bv.cpp src/bvmodule.cpp \\
    -DMODULE_STR=bv -DMODULE_PREFIX=pybv \\
    -DNDEBUG -DPY_MAJOR_VERSION=3 \\
    \`pkg-config --cflags --libs opencv**4**\` \\
    \`python3-config --includes --ldflags\` \\
    -I . -I/usr/local/lib/python3.5/dist-packages/numpy/core/include \\
    -o build/bv.so