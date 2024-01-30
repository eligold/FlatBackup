#include <opencv2/opencv.hpp>
#include <opencv2/calib3d/calib3d.hpp>
#include <stdio.h> // standard input / output functions
#include <string.h> // string function definitions
#include <unistd.h> // UNIX standard function definitions
#include <fcntl.h> // File control definitions
#include <errno.h> // Error number definitions
#include <termios.h> // POSIX terminal control definitionss
#include <time.h>   // time calls
#include <iostream>
#include <thread>
#include <atomic>
#include <queue>
#include <mutex>
#include <csignal>
#include <sys/mman.h>

using namespace std;
using namespace cv;

namespace bv {
    class CV_EXPORTS_W ViewBuilder {
    public:
        CV_WRAP ViewBuilder();
        CV_WRAP void build(InputArray image, OutputArray imview);
    };
}