#include"bvmodule.hpp"

namespace bv {
    const Mat cameraMatrix = (Mat_<double>(3,3) <<
            309.41085232860985, 0.0, 355.4094868125207,
            0.0, 329.90981352161924, 292.2015284112677,
            0.0, 0.0, 1.0);
    const Mat distortionCoefficients = (Mat_<double>(4,1) <<
            0.013301372417500422,
            0.03857464918863361,
            0.004117306147228716,
            -0.008896442339724364);
    Mat newCameraMatrix, undistortMapX, undistortMapY;
    Size inputSize(720,576);
    Size finalSize(1480,480);

    BackupViewer::buildUMat(UMat &image) {
        vector<UMat> panels;
        UMat preout(1480,480,CV_8UC3);
        remap(image, image, undistortMapX, undistortMapY, INTER_LINEAR);
        resize(image(Range(64,556),Range::all()), image, Size(960,656), 4/3, 4/3, INTER_LINEAR);
        resize(image(Rect(220,213,520,240)).clone(), preout, Size(1040,480), 2, 2, INTER_LINEAR);
        panels.push_back(image(Rect(0,8,220,480)));
        panels.push_back(preout);
        panels.push_back(image(Rect(740,0,220,480)));
        hconcat(panels,image);
        try {
            cvtColor(image,image,COLOR_BGR2BGR565,2);
        } catch (exception &e) {
            cout << e.what();
        }
    }
    BackupViewer::buildMat(Mat &image) {
        UMat frame = image.getUMat(ACCESS_RW);
        buildUMat(frame);
        image = frame.getMat(ACCESS_RW);
    }
    BackupViewer::buildNativeMat(Mat &image, OutputArray output) {
        try {
            vector<Mat> panels;
            Mat proto(960,656,CV_8UC3,Scalar::all(0));
            Mat middle(1040,480,CV_8UC3,Scalar::all(0));
            Mat panelImage(1480,480,CV_8UC3,Scalar::all(0));
            Mat left, right;
            Mat out(1480,480,CV_8UC2,Scalar::all(0));
            remap(image, image, undistortMapX, undistortMapY, INTER_LINEAR);
            resize(image.rowRange(64,556), proto, Size(960,656), 4/3, 4/3, INTER_LINEAR);
            resize(proto(Rect(220,213,520,240)), middle, Size(1040,480), 2, 2, INTER_LINEAR);
            proto(Rect(0,8,220,480)).copyTo(left);
            proto(Rect(740,0,220,480)).copyTo(right);
            panels.push_back(left);
            panels.push_back(middle);
            panels.push_back(right);
            hconcat(panels,panelImage);
            cvtColor(panelImage,output,COLOR_BGR2BGR565,2);
            ~proto;
            ~middle;
            ~panelImage;
            ~left;
            ~right;
            ~out;
        } catch (cv::Exception &exc) { cout << exc.what() << exc.err; }
        catch (exception &e) { cout << e.what(); }
    }

    BackupViewer::BackupViewer() {
        fisheye::estimateNewCameraMatrixForUndistortRectify(
            cameraMatrix, distortionCoefficients, inputSize, Matx33d::eye(), newCameraMatrix);
        fisheye::initUndistortRectifyMap(
            cameraMatrix, distortionCoefficients, Mat(), newCameraMatrix,
            inputSize, CV_32FC1, undistortMapX, undistortMapY);
    }
}
