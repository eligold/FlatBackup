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
    Mat undistorted, resized, middle, recolor;
    vector<Mat> panels;
    UMat umat, undistortedU, resizedU, middleU, recolorU;
    vector<UMat> panelsU;
    Size inputSize(720,576);

    void BackupViewer::buildU(InputOutputArray image) {
        try {
            if (image.isUMat()) {
                cout << "input: " << image.cols() << "x" << image.rows() << "px" << endl;
                remap(image, undistortedU, undistortMapX, undistortMapY, INTER_LINEAR);
                resize(undistortedU(Range(64,556),Range::all()), resizedU, Size(960,656));
                resize(resizedU(Rect(220,213,520,240)), middleU, Size(1040,480));
                panelsU.push_back(resizedU(Rect(0,8,220,480)));
                panelsU.push_back(middleU);
                panelsU.push_back(resizedU(Rect(740,0,220,480)));
                hconcat(panelsU,recolorU);
                panelsU.clear();
                cvtColor(recolorU,image,COLOR_BGR2BGR565);
            } else { cout << "not a UMat" << endl; }
        } 
        catch (Exception &exc) { cout << exc.what() << exc.err; }
        catch (exception &e) { cout << e.what(); }
    }
    void BackupViewer::buildMat(InputArray image, OutputArray output) {
        remap(image, undistorted, undistortMapX, undistortMapY, INTER_LINEAR);
        resize(undistorted.rowRange(64,556), resized, Size(960,656));
        resize(resized(Rect(220,213,520,240)).clone(), middle, Size(1040,480));
        panels.push_back(resized(Rect(0,8,220,480)));
        panels.push_back(middle);
        panels.push_back(resized(Rect(740,0,220,480)));
        hconcat(panels,recolor);
        panels.clear();
        cvtColor(recolor,output,COLOR_BGR2BGR565);
    }
    void BackupViewer::build(InputArray image, OutputArray output) {
        try {
            if (image.cols() == 720 && image.rows() == 576 && image.channels() == 3) {
                buildMat(image,output);
                assert(output.channels() == 2);
            } else { 
                cout << "malformed image!\ninput: " << image.cols() << "x" << image.rows() << "px" << endl;
            }
        } 
        catch (Exception &exc) { cout << exc.what() << exc.err; }
        catch (exception &e) { cout << e.what(); }
    }
    void BackupViewer::buildUMat(InputArray image, OutputArray output) {
        try {
            cout << "input: " << image.cols() << "x" << image.rows() << "px" << endl;
            UMat umat(image.getUMat());
            buildU(umat);
            output = umat.getMat(ACCESS_READ);
        } 
        catch (Exception &exc) { cout << exc.what() << exc.err; }
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
