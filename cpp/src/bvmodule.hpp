#include <opencv2/opencv.hpp>
#include <opencv2/calib3d/calib3d.hpp>

using namespace std;
using namespace cv;

namespace bv {
    class CV_EXPORTS_W ViewBuilder {
    public:
        CV_WRAP ViewBuilder();
        CV_WRAP void build(InputArray image, OutputArray imview);
    };
}