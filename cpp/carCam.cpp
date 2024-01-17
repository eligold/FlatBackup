#include <opencv2/opencv.hpp>
#include <opencv2/calib3d/calib3d.hpp>

#define FINAL_IMAGE_HEIGHT 480
#define COLOR_LOW 0xc4e4
#define COLOR_NORMAL 0x19ae

namespace cv;
namespace std;

int main() {
    Size inputSize(720, 576);
    Mat sidebar_base(480, 120, CV_16U, Scalar(COLOR_LOW));
    for (int i = 160; i < 480; ++i) {
        for (int j = 0; j < 120; ++j) {
            sidebar_base.at<uint16_t>(i, j) = static_cast<uint16_t>(i * 2 & (i - 255 - j));
        }
    }
    Mat cameraMatrix = (
        Mat_<double>(3,3) << 
            309.41085232860985, 0.0, 355.4094868125207,
            0.0, 329.90981352161924, 292.2015284112677,
            0.0, 0.0, 1.0
    );
    Mat distortionCoefficients = (
        Mat_<double>(4,1) << 
            0.013301372417500422,
            0.03857464918863361,
            0.004117306147228716,
            -0.008896442339724364
    );
    Mat newCameraMatrix;
    fisheye::estimateNewCameraMatrixForUndistortRectify(cameraMatrix, distortionCoefficients, inputSize, cv::Matx33d::eye(),newCameraMatrix);
    
    // TODO get index from /dev/v4l2/by-id/
    int index = 0;
    VideoCapture cap(index);

    if (!cap.isOpened()) {
        std::cerr << "Error: Couldn't open the webcam." << endl;
        return -1;
    }
    Mat undistortMapX, undistortMapY;
    fisheye::initUndistortRectifyMap(
        cameraMatrix, distortionCoefficients, Mat(), newCameraMatrix,
        inputSize, CV_32FC1, undistortMapX, undistortMapY
    ); // CV_16SC2?
    Mat sidebar = sidebar_base.clone();
    Mat undistorted;
    Mat resized;
    Mat middle;
    Mat recolor;
    Mat output;
    while (true) {
        Mat frame;
        cap >> frame;
        if (frame.empty()) {
            std::cerr << "Error: Couldn't capture frame." << endl;
            break;
        }
        remap(frame, undistorted, undistortMapX, undistortMapY, INTER_CUBIC);
        Rect roi(0,64,720,492);
        resize(undistorted(roi).clone(), resized, Size(960,768));
        resize(resized(Rect(220,213,520,240)).clone(), middle, Size(1040,480))
        hconcat({
                resized(Rect(0,8,220,480)),
                middleImage,
                resized(Rect(740,0,220,480))
            },
            3,
            recolor
        );
        
        cvtColor(recolor,output,COLOR_BGR2BGR565);
        if (/* cin check input */) {
            sidebar = sidebar_base.clone()
            putText(sidebar,/* string text */,Point(4,57),FONT_HERSHEY_SIMPLEX,1.19,Scalar(COLOR_NORMAL),3,LINE_AA);
        }
        

        // DISPLAY 'output' on /dev/fb0

    }
    cap.release();
    // Release /dev/fb0 here
    return 0;
}