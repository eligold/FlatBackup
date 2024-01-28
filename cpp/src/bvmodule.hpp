#include <opencv2/opencv.hpp>
#include <opencv2/calib3d/calib3d.hpp>

using namespace std;
using namespace cv;

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
    class CV_EXPORTS_W ViewBuilder {
    public:
        CV_WRAP ViewBuilder();
        CV_WRAP void build(InputArray image, OutputArray imview);
    };
}