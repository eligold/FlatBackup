#include"bvmodule.hpp"

namespace bv {
    Size inputSize(720, 576);
    Mat undistorted, resized, middle, recolor;
    const Mat cameraMatrix = (Mat_<double>(3,3) << 
            309.41085232860985, 0.0, 355.4094868125207,
            0.0, 329.90981352161924, 292.2015284112677,
            0.0, 0.0, 1.0);
    const Mat distortionCoefficients = (Mat_<double>(4,1) << 
            0.013301372417500422,
            0.03857464918863361,
            0.004117306147228716,
            -0.008896442339724364);
    const Mat newCameraMatrix, undistortMapX, undistortMapY;
    void ViewBuilder::build(InputArray image, OutputArray imview) {
        remap(image, undistorted, undistortMapX, undistortMapY, INTER_CUBIC);
        Rect roi(0,64,719,492);
        resize(undistorted(roi).clone(), resized, Size(960,768));
        resize(resized(Rect(220,213,520,240)).clone(), middle, Size(1040,480));
        hconcat(new Mat[3] {
                resized(Rect(0,8,219,487)).clone(),
                middle,
                resized(Rect(740,0,959,479)).clone(),
            },3,recolor);
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