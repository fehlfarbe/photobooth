#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QCamera>
#include <QCameraImageCapture>
#include <QMediaRecorder>
#include <QScopedPointer>
#include <QDir>
#include <QMainWindow>
#include <QThread>
#include <QtConcurrent/QtConcurrent>
#include <pigpiod_if2.h>
#include <functional>
#include <future>


enum BUTTONS {
    INFO = 21,
    PHOTO = 20,
    GIF = 19,
    PRINT = 18
};

enum OUTPUTS {
    FLASH = 13
};

namespace Ui {
class MainWindow;
}

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = 0);
    ~MainWindow();
    void pressedGPIO(int pi, unsigned user_gpio, unsigned level, uint32_t tick);
private slots:
    void setCamera(const QCameraInfo &cameraInfo);

    void startCamera();
    void stopCamera();

    void record();
    void pause();
    void stop();

    void toggleLock();
    void takeImage();
    void displayCaptureError(int, QCameraImageCapture::Error, const QString &errorString);

//    void configureCaptureSettings();
//    void configureVideoSettings();
//    void configureImageSettings();

    void displayRecorderError();
    void displayCameraError();

    void updateCameraDevice(QAction *action);

    void updateCameraState(QCamera::State);
    void updateCaptureMode();
    void updateRecorderState(QMediaRecorder::State state);
    void setExposureCompensation(int index);

    void updateRecordTime();

    void processCapturedImage(int requestId, const QImage &img);
    void updateLockStatus(QCamera::LockStatus, QCamera::LockChangeReason);

    void displayViewfinder();
    void displayCapturedImage();

    void imageCaptured(int id, const QImage &preview);
    void imageSaved(int id, const QString &fileName);

    // actions for key/buttons
    void actionPhoto();
    void actionGIF();
    void actionPrint();
    void countDownLabel();

    // flash
    void flash(bool);

signals:
    void onCountdown();
    void onActionPhoto();
    void onActionGIF();
    void onActionPrint();
    void onFlash(bool);

protected:
    void keyPressEvent(QKeyEvent *event) override;
    void keyReleaseEvent(QKeyEvent *event) override;
    void closeEvent(QCloseEvent *event) override;

private:
    Ui::MainWindow *ui;

    QScopedPointer<QCamera> m_camera;
    QScopedPointer<QCameraImageCapture> m_imageCapture;
    QScopedPointer<QMediaRecorder> m_mediaRecorder;

    QImageEncoderSettings m_imageSettings;
    QAudioEncoderSettings m_audioSettings;
    QVideoEncoderSettings m_videoSettings;
    QString m_videoContainerFormat;
    bool m_isCapturingImage = false;
    bool m_isCapturingGIF = false;
    bool m_applicationExiting = false;

    std::vector<QImage> m_gif_buffer;

    QThread m_worker;

    // buttons
    int m_pi;
    uint32_t m_last_tick = 0;
    uint32_t m_bounce_ticks = 1000000;

    // settings
    const int m_countdown_ms = 4000;
    const float m_font_mult = 400;
    QDir m_image_path;
    int m_gif_length_ms = 1000;
    int m_gif_images = 5;
    bool flip_h = true;
    bool flip_v = true;

    char m_flash_default = 100;
    char m_flash_on = 255;
};

#endif // MAINWINDOW_H
