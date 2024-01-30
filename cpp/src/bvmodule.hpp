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

#define FINAL_IMAGE_HEIGHT 480
#define COLOR_LOW 0xc4e4
#define COLOR_NORMAL 0x19ae
#define COLOR_BAD 0x8248
using namespace std;
using namespace cv;

namespace bv {
    class CV_EXPORTS_W ViewBuilder {
    public:
        CV_WRAP ViewBuilder();
        CV_WRAP void build(InputArray image, OutputArray imview);
    };
}