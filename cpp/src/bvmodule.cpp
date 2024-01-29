#include"bvmodule.hpp"

#define COLOR_LOW 0xc4e4

namespace bv {
    filesystem::path cameraPath = 
            "/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._USB_CAMERA_SN0001-video-index0";
    Size inputSize(720, 576);
    VideoCapture cap;
    const int index;
    Mat frame, undistorted, resized, middle, recolor;
    Mat panels[3];
    Mat sidebar_base(480, 120, CV_16U, Scalar(COLOR_LOW));
    const Mat cameraMatrix = (Mat_<double>(3,3) <<
            309.41085232860985, 0.0, 355.4094868125207,
            0.0, 329.90981352161924, 292.2015284112677,
            0.0, 0.0, 1.0);
    const UMat distortionCoefficients = (Mat_<double>(4,1) <<
            0.013301372417500422,
            0.03857464918863361,
            0.004117306147228716,
            -0.008896442339724364);
    UMat newCameraMatrix, undistortMapX, undistortMapY;
    void ViewBuilder::build(InputArray image, OutputArray imview) {
        remap(image, this.undistorted, this.undistortMapX, this.undistortMapY, INTER_CUBIC);
        resize(undistorted.rowRange(64,556), this.resized, Size(960,768));
        resize(resized(Rect(220,213,520,240)).clone(), this.middle, Size(1040,480));
        panels[0] = resized(Rect(0,8,220,480)).clone();
        panels[1] = this.middle;
        panels[2] = resized(Rect(740,0,220,480)).clone();
        hconcat(panels,3,recolor);
        cvtColor(recolor,imview,COLOR_BGR2BGR565);
    }
    void ViewBuilder::start() {
        while(True)
        cap >> frame;
    }
    ViewBuilder::ViewBuilder() {
        fisheye::estimateNewCameraMatrixForUndistortRectify(
            cameraMatrix, distortionCoefficients, inputSize, Matx33d::eye(),newCameraMatrix);
        fisheye::initUndistortRectifyMap(
            cameraMatrix, distortionCoefficients, Mat(), newCameraMatrix,
            inputSize, CV_32FC1, undistortMapX, undistortMapY);
        for (int i = 160; i < 480; ++i) {
            for (int j = 0; j < 120; ++j) {
                sidebar_base.at<uint16_t>(i, j) = static_cast<uint16_t>(i * 2 & (i - 255 - j));
            }
        }
        int camIndex;
        int capErrors = 0;
        if (!(filesystem::exists(cameraPath) && filesystem::is_symlink(cameraPath))) {
            cerr << "Error: bad camera URI." << endl;
        } else {
            string indexString = filesystem::read_symlink(cameraPath).string();
            camIndex = stoi(indexString[indexString.length()-1]);
            this.cap = new VideoCapture(camIndex);
            if (!cap.isOpened()) {
                cerr << "Error: Couldn't open the webcam." << endl;
                return 2;
            }
        }
        
    }
}
