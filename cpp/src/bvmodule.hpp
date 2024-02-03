#include <opencv2/opencv.hpp>
#include <opencv2/calib3d/calib3d.hpp>

using namespace std;
using namespace cv;

namespace bv {
    class CV_EXPORTS_W BackupViewer {
    public:
        CV_WRAP BackupViewer();
        CV_WRAP void build(InputArray image, OutputArray output);
        CV_WRAP void buildU(InputOutputArray image);
        CV_WRAP void buildMat(InputArray image, OutputArray output);
        CV_WRAP void buildUMat(InputArray image, OutputArray output);
    };
}