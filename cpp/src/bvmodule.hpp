#include <opencv2/opencv.hpp>
#include <opencv2/calib3d/calib3d.hpp>

using namespace std;
using namespace cv;

namespace bv {
    class CV_EXPORTS_W BackupViewer {
    public:
        CV_WRAP BackupViewer();
        CV_WRAP int buildMat(Mat&);
        CV_WRAP int buildUMat(UMat&);
        CV_WRAP int buildNativeMat(Mat&, OutputArray);
    };
}