#include"bvmodule.hpp"

#define COLOR_LOW 0xc4e4

namespace bv {
    atomic<bool> terminateThread(false);
    string *psi = "19.1";
    int err_idx = 5;
    void kbi(int signum) {
        cout << "killing program...\nSIGNAL " << signum << endl;
        terminateThread.store(true);
        cout << err_idx << endl;
    }
    void inputThread(InputCallback callback) {
        string input;
        while (!terminateThread.load()) {
            cin >> input;
            callback(input);
        }
    }
    void BackupViewer::run() {
        signal(SIGINT, kbi);
        signal(SIGTERM, kbi);
        auto onInputReceived = [](const string& input) {
            psi = input;
        };
        thread inputHandler(inputThread, onInputReceived);
        filesystem::path cameraPath = 
                "/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._USB_CAMERA_SN0001-video-index0";
        Size inputSize(720, 576);
        const int index;
        UMat frame, undistorted, resized, middle, recolor, panelView;
        UMat panels[3];
        UMat sidebar_base(480, 120, CV_16U, Scalar(COLOR_LOW));
        const Mat cameraMatrix = (Mat_<double>(3,3) <<
                309.41085232860985, 0.0, 355.4094868125207,
                0.0, 329.90981352161924, 292.2015284112677,
                0.0, 0.0, 1.0);
        const Mat distortionCoefficients = (Mat_<double>(4,1) <<
                0.013301372417500422,
                0.03857464918863361,
                0.004117306147228716,
                -0.008896442339724364);
        UMat newCameraMatrix, undistortMapX, undistortMapY;
        fisheye::estimateNewCameraMatrixForUndistortRectify(
            cameraMatrix, distortionCoefficients, inputSize, Matx33d::eye(),newCameraMatrix);
        fisheye::initUndistortRectifyMap(
            cameraMatrix, distortionCoefficients, Mat(), newCameraMatrix,
            inputSize, CV_32FC1, undistortMapX, undistortMapY);
        for (int i = 160; i < 480; ++i) {
            for (int j = 0; j < 120; ++j) {
                sidebar_base.at<uint16_t>(i, j) = static_cast<uint16_t>(i * 2 & (i - 255 - j));
            }
        }
        int camIndex;
        int capErrors = 0;
        if (filesystem::exists(cameraPath) && filesystem::is_symlink(cameraPath)) {
            err_idx--;
            string indexString = filesystem::read_symlink(cameraPath).string();
            camIndex = stoi(indexString[indexString.length()-1]);
            VideoCapture cap = new VideoCapture(camIndex,CAP_V4L);
            if (cap.isOpened()) {
                err_idx--;
                UMat sidebar = sidebar_base.clone();
                int fb = open("/dev/fb0",O_RDWR);
                if (fb != -1) {
                    err_idx--;
                    struct fb_var_screeninfo vinfo;
                    if (!ioctl(fb, FBIOGET_VSCREENINFO, &vinfo)) {
                        err_idx--;
                        int width = 1600;
                        int height = 480;
                        int depth = 2;
                        unsigned char* fb_ptr = (unsigned char*)mmap(
                                NULL, vinfo.yres_virtual * vinfo.width_virtual * depth, 
                                PROT_READ | PROT_WRITE, MAP_SHARED, fb, 0);
                        if (fb_ptr != MAP_FAILED) {
                            err_idx--;
                            UMat output = UMat(480, 1600, 2, CV_8U, Scalar(0));
                            while(!terminateThread.load()) {
                                cap >> frame;
                                if (!frame.empty()) {
                                    remap(frame, undistorted, undistortMapX, undistortMapY, INTER_CUBIC);
                                    resize(undistorted.rowRange(64,556), resized, Size(960,768));
                                    resize(resized(Rect(220,213,520,240)).clone(), middle, Size(1040,480));
                                    panels[0] = resized(Rect(0,8,220,480)).clone();
                                    panels[1] = middle;
                                    panels[2] = resized(Rect(740,0,220,480)).clone();
                                    hconcat(panels,3,recolor);
                                    cvtColor(recolor,panelView,COLOR_BGR2BGR565);
                                    
                                    if (psi != nullptr) {
                                        putText(sidebar,psi,Point(4,57),FONT_HERSHEY_SIMPLEX,1.19,
                                                Scalar(COLOR_NORMAL),3,LINE_AA);
                                        string units = "bar";
                                        if (stoi(psi) > 0) { units = "PSI" }
                                        putText(sidebar,units,Point(60,95),FONT_HERSHEY_SIMPLEX,1,
                                                Scalar(COLOR_BAD),2,LINE_AA);
                                        for (int z = 0; z < height; ++z) {
                                            memcpy(fb_ptr + (y + vinfo.yoffset) * vinfo.width_virtual * depth + 1480,
                                                    sidebar.ptr(y, 1480), 120);
                                        }
                                        sidebar = sidebar_base.clone();
                                        *psi = nullptr;
                                    }
                                    for (int y = 0; y < height; ++y) {
                                        memcpy(fb_ptr + (y + vinfo.yoffset) * vinfo.width_virtual * depth,
                                                panelView.ptr(y), 1480 * depth);
                                    }
                                }
                            }
                        }
                    }
                }
                
            }
        }
        terminateThread.store(true);
        inputHandler.join();
        if (cap.isConnected()) { cap.release(); }
        munmap(fb_ptr, vinfo.yres_virtual * vinfo.width_virtual * depth);
        close(fb);

    }
    ViewBuilder::ViewBuilder() {
    }
}
