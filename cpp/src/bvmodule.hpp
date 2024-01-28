#include <opencv2/opencv.hpp>
#include <opencv2/calib3d/calib3d.hpp>

using namespace std;
using namespace cv;

namespace bv {
	CV_EXPORTS_W void buildView(InputArray image, OutputArray imview);
    CV_EXPORTS_W void init();
}