#include <opencv2/opencv.hpp>
#include <opencv2/videoio.hpp>
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
#include <sys/ioctl.h>
#include <stdlib.h>
#include <ctype.h>
#include <linux/fb.h>


#define FINAL_IMAGE_HEIGHT 480
#define COLOR_LOW 0xc4e4
#define COLOR_NORMAL 0x19ae
#define COLOR_BAD 0x8248
using namespace std;
using namespace cv;

namespace bv {
    typedef Point_<uint8_t> Pixel;
    //using InputCallback = function<void(const float&)>;
    void kbi(int);
    //void inputThread(bv::InputCallback);
    
    // CV_EXPORTS_W void play(int);
    class CV_EXPORTS_W BackupViewer {
    public:
        CV_WRAP BackupViewer();
        CV_WRAP int update_psi(float);
        CV_WRAP int play(int);
    };
}