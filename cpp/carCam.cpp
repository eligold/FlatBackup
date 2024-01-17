#include <opencv2/opencv.hpp>
#include <opencv2/calib3d/calib3d.hpp>
#include <OBD.h>
#include <stdio.h> // standard input / output functions
#include <string.h> // string function definitions
#include <unistd.h> // UNIX standard function definitions
#include <fcntl.h> // File control definitions
#include <errno.h> // Error number definitions
#include <termios.h> // POSIX terminal control definitionss
#include <time.h>   // time calls
#include <iostream>
#include <thread>
#include <queue>
#include <mutex>

#define FINAL_IMAGE_HEIGHT 480
#define COLOR_LOW 0xc4e4
#define COLOR_NORMAL 0x19ae

using namespace cv;
using namespace std;

atomic_bool isELMFramesAvailable = false;
queue<Mat> dataQueue;
mutex queueMutex;
Mat sidebar_base(480, 120, CV_16U, Scalar(COLOR_LOW));
for (int i = 160; i < 480; ++i) {
    for (int j = 0; j < 120; ++j) {
        sidebar_base.at<uint16_t>(i, j) = static_cast<uint16_t>(i * 2 & (i - 255 - j));
    }
}
OBD obd;
atomic_bool running = true;
thread elmThread(elm327);
filesystem::path cameraPath = 
    "/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._USB_CAMERA_SN0001-video-index0";
int camIndex;
int capErrors = 0;
if (!(filesystem::exists(cameraPath) && filesystem::is_symlink(cameraPath))) {
    // cerr << "Error: bad camera URI." << endl;
    return 1;
} else {
    string indexString = filesystem::read_symlink(cameraPath).string();
    camIndex = stoi(indexString[indexString.length()-1]);
}
VideoCapture cap(camIndex);
if (!cap.isOpened()) {
    // cerr << "Error: Couldn't open the webcam." << endl;
    return 2;
}
void kbi(int signum) {
    // cout << "killing program...\nSIGNAL " << signum << endl;
    running = false;
    if (obd.isConnected()) { obd.disconnect(); }
    if (cap.isConnected()) { cap.release(); }
    
}
int open_port(void) {
    int fd = open("/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0", O_RDWR | O_NOCTTY | O_NDELAY);
    if(fd == -1) {
        cout << "unable to open ELM port" << endl;
        return 3
    } else {
        fcntl(fd, F_SETFL, 0);
    }
    struct termios port_settings;
    cfsetispeed(&port_settings, B38400);
    cfsetospeed(&port_settings, B38400);
    port_settings.c_cflag &= ~PARENB;
    port_settings.c_cflag &= ~CSTOPB;
    port_settings.c_cflag &= ~CSIZE;
    port_settings.c_cflag |= CS8;
    tcsetattr(fd, TCSANOW, &port_settings);
}

void elm327() {
    while (running) {
        obd.connect("/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0");
        if (obd.isConnected()) {
            Mat sidebar = sidebar_base.clone()
            long rpm = obd.getRPM();
            // printf("010C\r"); // or some shit also divide by 4 for whatever reason
            long iat; // = obd.get("");//TODO HEEREEE
            printf("010F\r");
            scanf("%f",iat);
            float maf;
            // printf("010C\r"); // or some shit
            // scanf("%f",maf);
            float bps; // "0133\r"
            float mph; // "010D\r"

            cout << mph << endl;

            //calculate here
            float psi;

            putText(sidebar,to_string(psi),Point(4,57),FONT_HERSHEY_SIMPLEX,1.19,Scalar(COLOR_NORMAL),3,LINE_AA);
            lock_guard<mutex> lock(queueMutex);
            dataQueue.push(sidebar);
            isELMFrameAvailable = true;
        } else {
            // cerr << "failed to connect to OBD-II interface. retrying..." << endl;
            this_thread::sleep_for(chrono::seconds(1));
        }
        obd.disconnect()
    }
    return;
}

int main() {
    signal(SIGINT, kbi);
    
    Size inputSize(720, 576);
    Mat cameraMatrix = (Mat_<double>(3,3) << 
            309.41085232860985, 0.0, 355.4094868125207,
            0.0, 329.90981352161924, 292.2015284112677,
            0.0, 0.0, 1.0);
    Mat distortionCoefficients = (Mat_<double>(4,1) << 
            0.013301372417500422,
            0.03857464918863361,
            0.004117306147228716,
            -0.008896442339724364);
    Mat newCameraMatrix;
    fisheye::estimateNewCameraMatrixForUndistortRectify(
        cameraMatrix, distortionCoefficients, inputSize, cv::Matx33d::eye(),newCameraMatrix);
    Mat undistortMapX, undistortMapY;
    fisheye::initUndistortRectifyMap(
        cameraMatrix, distortionCoefficients, Mat(), newCameraMatrix,
        inputSize, CV_32FC1, undistortMapX, undistortMapY); // CV_16SC2?
    Mat sidebar = sidebar_base;
    Mat undistorted;
    Mat resized;
    Mat middle;
    Mat recolor;
    Mat output;
    while (true) {
        Mat frame;
        cap >> frame;
        if (frame.empty()) {
            // cerr << "Error: Couldn't capture frame." << endl;
            capErrors++;
            if (capErrors > 10) {
                return 4;
            }
        } else {
            remap(frame, undistorted, undistortMapX, undistortMapY, INTER_CUBIC);
            Rect roi(0,64,720,492);
            resize(undistorted(roi).clone(), resized, Size(960,768));
            resize(resized(Rect(220,213,520,240)).clone(), middle, Size(1040,480))
            hconcat({
                    resized(Rect(0,8,220,480)),
                    middleImage,
                    resized(Rect(740,0,220,480))
                },3,recolor
            );
            cvtColor(recolor,output,COLOR_BGR2BGR565);
        }
        if (isELMFramesAvailable) {
            lock_guard<mutex> lock(queueMutex);
            sidebar = dataQueue.front()
            dataQueue.pop();
            isELMFrameAvailable = false;
        }

        // DISPLAY 'output' on /dev/fb0
        // sidebar.at<uint16_t>(row)

    }
    elmThread.join();
    cap.release();

    // Release /dev/fb0 here

    return 0;
}