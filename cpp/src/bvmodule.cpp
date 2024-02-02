#include"bvmodule.hpp"

namespace bv {
    atomic<bool> terminateThread(false);
    atomic<float> psi(19.1);
    void kbi(int signum) {
        cout << "killing program...\nSIGNAL " << signum << endl;
        terminateThread.store(true);
    }
    // void inputThread(bv::InputCallback callback, float psi) {
    //     while (!bv::terminateThread.load()) {
    //         callback(psi);
    //     }
    // }
    struct Operator {
        void operator ()(Pixel &pixel, const int *position) const {
            if (position[1] > 160) {
                int i = position[1];
                int j = position[0];
                int color = (i * 2 & (i - 255 - j));
                pixel.x = static_cast<uint8_t>(color);
                pixel.y = static_cast<uint8_t>(color>>8);
            } else {
                pixel.x = 0xe4;
                pixel.y = 0xc4;
            }
        }
    };
    BackupViewer::play(int camIndex) {
        int err_idx = 4;
        signal(SIGINT, bv::kbi);
        signal(SIGTERM, bv::kbi);
        // auto onInputReceived = [&psi](const float& input) {
        //     bv::psi.store(input)
        // };
        // thread inputHandler(update_psi, onInputReceived);
        unsigned char* fb_ptr;
        VideoCapture cap(camIndex,CAP_V4L);
        if (cap.isOpened()) {
            cout << err_idx << endl;
            err_idx--;
            int fb = open("/dev/fb0",O_RDWR);
            if (fb != -1) {
                cout << err_idx << endl;
                err_idx--;
                struct fb_var_screeninfo vinfo;
                if (!ioctl(fb, FBIOGET_VSCREENINFO, &vinfo)) {
                    cout << err_idx << endl;
                    err_idx--;
                    int width = 1600;
                    int height = 480;
                    int depth = 2;
                    fb_ptr = (unsigned char*)mmap(
                            NULL, vinfo.yres_virtual * vinfo.xres_virtual * depth, 
                            PROT_READ | PROT_WRITE, MAP_SHARED, fb, 0);
                    if (fb_ptr != MAP_FAILED) {
                        cout << err_idx << endl;
                        err_idx--;
                        Size inputSize(720, 576);
                        const int index;
                        UMat frame, undistorted, resized, middle, recolor, panelView;
                        vector<UMat> panels;
                        bv::psi.store(19.0);
                        Mat sidebar_base(480, 120, CV_8UC2, Scalar(COLOR_LOW));
                        sidebar_base.forEach<Pixel>(bv::Operator());
                        const Mat cameraMatrix = (Mat_<double>(3,3) <<
                                309.41085232860985, 0.0, 355.4094868125207,
                                0.0, 329.90981352161924, 292.2015284112677,
                                0.0, 0.0, 1.0);
                        const Mat distortionCoefficients = (Mat_<double>(4,1) <<
                                0.013301372417500422,
                                0.03857464918863361,
                                0.004117306147228716,
                                -0.008896442339724364);
                        Mat sidebar = sidebar_base.clone();
                        Mat newCameraMatrix, undistortMapX, undistortMapY, output;
                        fisheye::estimateNewCameraMatrixForUndistortRectify(
                            cameraMatrix, distortionCoefficients, inputSize, Matx33d::eye(),newCameraMatrix);
                        fisheye::initUndistortRectifyMap(
                            cameraMatrix, distortionCoefficients, Mat(), newCameraMatrix,
                            inputSize, CV_32FC1, undistortMapX, undistortMapY);
                        int capErrors = 0;
                        int pres;
                        while(!bv::terminateThread.load()) {
                            cap >> frame;
                            cout << "got frame!" << endl;
                            if (!frame.empty()) {
                                cout << "made it" << endl;
                                remap(frame, undistorted, undistortMapX, undistortMapY, INTER_CUBIC);
                                resize(undistorted.rowRange(64,556), resized, Size(960,768));
                                resize(resized(Rect(220,213,520,240)).clone(), middle, Size(1040,480));
                                panels.push_back(resized(Rect(0,8,220,480)));
                                panels.push_back(middle);
                                panels.push_back(resized(Rect(740,0,220,480)));
                                hconcat(panels,3,recolor);
                                panels.clear();
                                cvtColor(recolor,panelView,COLOR_BGR2BGR565);
                                if (bv::psi.load() != 19.1) {
                                    pres = bv::psi.load();
                                    putText(sidebar,format("{:.1f}",pres),Point(4,57),
                                            FONT_HERSHEY_SIMPLEX,1.19,Scalar(COLOR_NORMAL),3,LINE_AA);
                                    string units = "bar";
                                    if (pres > 0) { units = "PSI"; }
                                    putText(sidebar,units,Point(60,95),FONT_HERSHEY_SIMPLEX,1,
                                            Scalar(COLOR_BAD),2,LINE_AA);
                                    for (int y = 0; y < height; ++y) {
                                        memcpy(fb_ptr + (y + vinfo.yoffset) * vinfo.xres_virtual * depth + 1480,
                                                sidebar.at<uint8_t>(y), 120 * depth);
                                    }
                                    sidebar = sidebar_base.clone();
                                    psi = 19.1;
                                }
                                output = panelView.getMat(ACCESS_READ);
                                for (int y = 0; y < height; ++y) {
                                    memcpy(fb_ptr + (y + vinfo.yoffset) * vinfo.xres_virtual * depth,
                                            output.at<uint8_t>(y), 1480 * depth);
                                }
                            }
                        }
                        munmap(fb_ptr, vinfo.yres_virtual * vinfo.xres_virtual * depth);
                        ~output;
                        ~undistortMapY;
                        ~undistortMapX;
                        ~newCameraMatrix;
                        ~sidebar;
                        ~distortionCoefficients;
                        ~cameraMatrix;
                        ~sidebar_base;
                        frame.release();
                        undistorted.release();
                        resized.release();
                        middle.release();
                        recolor.release();
                        panelView.release();
                    }
                }
                close(fb);
            }
            if (cap.isOpened()) { cap.release(); }
        }
        bv::terminateThread.store(true);
        //inputHandler.join();
        cout << err_idx << endl;
        return err_idx;
    }
    BackupViewer::update_psi(float pressure) {
        bv::psi.store(pressure);
        return 0;
    }
    BackupViewer::BackupViewer() {
    }
}
