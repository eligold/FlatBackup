#include"bvmodule.hpp"

namespace bv {
    void ViewBuilder::build(InputArray image, OutputArray imview) {
        remap(image, undistorted, undistortMapX, undistortMapY, INTER_CUBIC);
        Rect roi(0,64,719,492);
        resize(undistorted(roi).clone(), resized, Size(960,768));
        resize(resized(Rect(220,213,520,240)).clone(), middle, Size(1040,480));
        hconcat(new Mat[] {
                resized(Rect(0,8,219,487)),
                middle,
                resized(Rect(740,0,959,479)),
            },recolor);
        cvtColor(recolor,imview,COLOR_BGR2BGR565);
    }
    ViewBuilder::ViewBuilder() {
        fisheye::estimateNewCameraMatrixForUndistortRectify(
            cameraMatrix, distortionCoefficients, inputSize, Matx33d::eye(),newCameraMatrix);
        fisheye::initUndistortRectifyMap(
            cameraMatrix, distortionCoefficients, Mat(), newCameraMatrix,
            inputSize, CV_32FC1, undistortMapX, undistortMapY); // CV_16SC2?
    }
}