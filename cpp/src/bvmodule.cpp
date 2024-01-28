#include"bvmodule.hpp"

namespace bv {
    Size inputSize(720, 576);
    UMat undistorted, resized, middle, recolor;
    UMat panels[3];
    const UMat cameraMatrix = (Mat_<double>(3,3) <<
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
        remap(image, undistorted, undistortMapX, undistortMapY, INTER_CUBIC);
        resize(undistorted.rowRange(64,556), resized, Size(960,768));
        resize(resized(Rect(220,213,520,240)).clone(), middle, Size(1040,480));
        panels[0] = resized(Rect(0,8,220,480)).clone();
        panels[1] = middle;
        panels[2] = resized(Rect(740,0,220,480)).clone();
        hconcat(panels,3,recolor);
        cvtColor(recolor,imview,COLOR_BGR2BGR565);
    }
    ViewBuilder::ViewBuilder() {
        fisheye::estimateNewCameraMatrixForUndistortRectify(
            cameraMatrix, distortionCoefficients, inputSize, Matx33d::eye(),newCameraMatrix);
        fisheye::initUndistortRectifyMap(
            cameraMatrix, distortionCoefficients, Mat(), newCameraMatrix,
            inputSize, CV_32FC1, undistortMapX, undistortMapY);
    }
}
