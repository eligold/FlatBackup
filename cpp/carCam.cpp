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

#define FINAL_IMAGE_HEIGHT 480
#define COLOR_LOW 0xc4e4
#define COLOR_NORMAL 0x19ae

using namespace cv;
using namespace std;

using InputCallback = std::function<void(const std::string&)>;

// queue<Mat> dataQueue;
// mutex queueMutex;
// atomic_bool running = true;
atomic<bool> terminateThread(false);
string *psi = nullptr;

void kbi(int signum) {
    cout << "killing program...\nSIGNAL " << signum << endl;
    terminateThread.store(true);
}

void inputThread(InputCallback callback) {
    string input;
    while (!terminateThread.load()) {
        cin >> input;
        callback(input);
    }
}

int main() {
    signal(SIGINT, kbi);
    signal(SIGTERM, kbi);
    auto onInputReceived = [](const string& input) {
        psi = input;
    };
    thread inputHandler(inputThread, onInputReceived);
    
    Mat sidebar_base(480, 120, CV_16U, Scalar(COLOR_LOW));
    for (int i = 160; i < 480; ++i) {
        for (int j = 0; j < 120; ++j) {
            sidebar_base.at<uint16_t>(i, j) = static_cast<uint16_t>(i * 2 & (i - 255 - j));
        }
    }

    filesystem::path cameraPath = 
        "/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._USB_CAMERA_SN0001-video-index0";
    int camIndex;
    int capErrors = 0;
    if (!(filesystem::exists(cameraPath) && filesystem::is_symlink(cameraPath))) {
        cerr << "Error: bad camera URI." << endl;
        return 1;
    } else {
        string indexString = filesystem::read_symlink(cameraPath).string();
        camIndex = stoi(indexString[indexString.length()-1]);
    }
    VideoCapture cap(camIndex);
    if (!cap.isOpened()) {
        cerr << "Error: Couldn't open the webcam." << endl;
        return 2;
    }

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
    while (!terminateThread.load()) {
        Mat frame;
        cap >> frame;
        if (frame.empty()) {
            cerr << "Error: Couldn't capture frame." << endl;
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
        if (psi != nullptr) {
            sidebar = sidebar_base.clone()
            putText(sidebar,to_string(psi),Point(4,57),FONT_HERSHEY_SIMPLEX,1.19,Scalar(COLOR_NORMAL),3,LINE_AA);
            *psi = nullptr;
        }

        // DISPLAY 'output' on /dev/fb0
        // sidebar.at<uint16_t>(row)

    }
    terminateThread.store(true);
    if (cap.isConnected()) { cap.release(); }

    // Release /dev/fb0 here

    inputHandler.join();

    return 0;
}