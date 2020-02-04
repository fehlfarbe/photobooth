#include "mainwindow.h"
#include "ui_mainwindow.h"

#include <QMediaService>
#include <QMediaRecorder>
#include <QCameraViewfinder>
#include <QCameraInfo>
#include <QMediaMetaData>
#include <QVideoRendererControl>
#include <QVideoSurfaceFormat>

#include <QMessageBox>
#include <QPalette>

#include <QtWidgets>

void gpiocallback(int pi, unsigned user_gpio, unsigned level, uint32_t tick, void* wnd){
//    qDebug() << "pressed GPIO " << user_gpio << " level " << level << " tick " << tick;
    if(wnd){
        ((MainWindow*)wnd)->pressedGPIO(pi, user_gpio, level, tick);
    }
}

MainWindow::MainWindow(QWidget *parent) :
    QMainWindow(parent),
    ui(new Ui::MainWindow)
{
    ui->setupUi(this);

    //Camera devices:

    QActionGroup *videoDevicesGroup = new QActionGroup(this);
    videoDevicesGroup->setExclusive(true);
    const QList<QCameraInfo> availableCameras = QCameraInfo::availableCameras();
    for (const QCameraInfo &cameraInfo : availableCameras) {
//        QAction *videoDeviceAction = new QAction(cameraInfo.description(), videoDevicesGroup);
//        videoDeviceAction->setCheckable(true);
//        videoDeviceAction->setData(QVariant::fromValue(cameraInfo));
//        if (cameraInfo == QCameraInfo::defaultCamera())
//            videoDeviceAction->setChecked(true);

//        ui->menuDevices->addAction(videoDeviceAction);
        qDebug() << cameraInfo.deviceName();
    }

    qDebug() << "default camera: " << QCameraInfo::defaultCamera();

//    connect(videoDevicesGroup, &QActionGroup::triggered, this, &MainWindow::updateCameraDevice);
//    connect(ui->captureWidget, &QTabWidget::currentChanged, this, &MainWindow::updateCaptureMode);

    setCamera(QCameraInfo::defaultCamera());

    // init GPIO
//    gpioInitialise();
//    gpioInitialise();
//    gpioSetAlertFunc(BUTTONS::INFO, &gpiocallback);
    int pi = pigpio_start(nullptr, nullptr);
    for(size_t i=0; i<30; i++){
        switch (i) {
        case 2:
        case 3:
        case 29:
            break;
        default:
            set_mode(pi, i, PI_INPUT);
            set_pull_up_down(pi, i, PI_PUD_UP);
            callback_ex(pi, i, FALLING_EDGE, &gpiocallback, this);
            break;
        }
    }
}

MainWindow::~MainWindow()
{
    delete ui;
}


void MainWindow::setCamera(const QCameraInfo &cameraInfo)
{
    qDebug() << "Setting camera " << cameraInfo.deviceName() << " " << cameraInfo.description();
    m_camera.reset(new QCamera(cameraInfo));

    connect(m_camera.data(), &QCamera::stateChanged, this, &MainWindow::updateCameraState);
    connect(m_camera.data(), QOverload<QCamera::Error>::of(&QCamera::error), this, &MainWindow::displayCameraError);

    m_mediaRecorder.reset(new QMediaRecorder(m_camera.data()));
    connect(m_mediaRecorder.data(), &QMediaRecorder::stateChanged, this, &MainWindow::updateRecorderState);

    m_imageCapture.reset(new QCameraImageCapture(m_camera.data()));

    connect(m_mediaRecorder.data(), &QMediaRecorder::durationChanged, this, &MainWindow::updateRecordTime);
    connect(m_mediaRecorder.data(), QOverload<QMediaRecorder::Error>::of(&QMediaRecorder::error),
            this, &MainWindow::displayRecorderError);

    m_mediaRecorder->setMetaData(QMediaMetaData::Title, QVariant(QLatin1String("Test Title")));

    m_camera->setViewfinder(ui->viewfinder);

    QCameraViewfinderSettings settings;
    settings.setResolution(1920, 1088);
//    settings.setResolution(1280, 720);
    settings.setMinimumFrameRate(15.0);
    settings.setMaximumFrameRate(30.0);
    settings.setPixelFormat(QVideoFrame::PixelFormat::Format_BGR24);
    qDebug() << "resolution: " << settings.resolution() << " pixel: " << settings.pixelFormat();

    m_camera->setViewfinderSettings(settings);

    updateCameraState(m_camera->state());
    updateLockStatus(m_camera->lockStatus(), QCamera::UserRequest);
    updateRecorderState(m_mediaRecorder->state());

    connect(m_imageCapture.data(), &QCameraImageCapture::readyForCaptureChanged, this, &MainWindow::readyForCapture);
    connect(m_imageCapture.data(), &QCameraImageCapture::imageCaptured, this, &MainWindow::processCapturedImage);
    connect(m_imageCapture.data(), &QCameraImageCapture::imageSaved, this, &MainWindow::imageSaved);
    connect(m_imageCapture.data(), QOverload<int, QCameraImageCapture::Error, const QString &>::of(&QCameraImageCapture::error),
            this, &MainWindow::displayCaptureError);

    connect(m_camera.data(), QOverload<QCamera::LockStatus, QCamera::LockChangeReason>::of(&QCamera::lockStatusChanged),
            this, &MainWindow::updateLockStatus);

//    ui->viewfinder->setFullScreen(true);

//    ui->captureWidget->setTabEnabled(0, (m_camera->isCaptureModeSupported(QCamera::CaptureStillImage)));
//    ui->captureWidget->setTabEnabled(1, (m_camera->isCaptureModeSupported(QCamera::CaptureVideo)));

//    updateCaptureMode();
    m_camera->start();
}

void MainWindow::keyPressEvent(QKeyEvent * event)
{
    qDebug() << "pressed key " << event;
//    if (event->isAutoRepeat())
//        return;

//    switch (event->key()) {
//    case Qt::Key_CameraFocus:
//        displayViewfinder();
//        m_camera->searchAndLock();
//        event->accept();
//        break;
//    case Qt::Key_Camera:
//        if (m_camera->captureMode() == QCamera::CaptureStillImage) {
//            takeImage();
//        } else {
//            if (m_mediaRecorder->state() == QMediaRecorder::RecordingState)
//                stop();
//            else
//                record();
//        }
//        event->accept();
//        break;
//    default:
//        QMainWindow::keyPressEvent(event);
//    }
}

void MainWindow::keyReleaseEvent(QKeyEvent *event)
{
    qDebug() << "key release " << event;
//    if (event->isAutoRepeat())
//        return;

//    switch (event->key()) {
//    case Qt::Key_CameraFocus:
//        m_camera->unlock();
//        break;
//    default:
//        QMainWindow::keyReleaseEvent(event);
//    }
}

void MainWindow::updateRecordTime()
{
//    QString str = QString("Recorded %1 sec").arg(m_mediaRecorder->duration()/1000);
//    ui->statusbar->showMessage(str);
}

void MainWindow::processCapturedImage(int requestId, const QImage& img)
{
//    Q_UNUSED(requestId);
//    QImage scaledImage = img.scaled(ui->viewfinder->size(),
//                                    Qt::KeepAspectRatio,
//                                    Qt::SmoothTransformation);

//    ui->lastImagePreviewLabel->setPixmap(QPixmap::fromImage(scaledImage));

//    // Display captured image for 4 seconds.
//    displayCapturedImage();
//    QTimer::singleShot(4000, this, &Camera::displayViewfinder);
}

//void MainWindow::configureCaptureSettings()
//{
//    switch (m_camera->captureMode()) {
//    case QCamera::CaptureStillImage:
//        configureImageSettings();
//        break;
//    case QCamera::CaptureVideo:
//        configureVideoSettings();
//        break;
//    default:
//        break;
//    }
//}

//void MainWindow::configureVideoSettings()
//{
//    VideoSettings settingsDialog(m_mediaRecorder.data());
//    settingsDialog.setWindowFlags(settingsDialog.windowFlags() & ~Qt::WindowContextHelpButtonHint);

//    settingsDialog.setAudioSettings(m_audioSettings);
//    settingsDialog.setVideoSettings(m_videoSettings);
//    settingsDialog.setFormat(m_videoContainerFormat);

//    if (settingsDialog.exec()) {
//        m_audioSettings = settingsDialog.audioSettings();
//        m_videoSettings = settingsDialog.videoSettings();
//        m_videoContainerFormat = settingsDialog.format();

//        m_mediaRecorder->setEncodingSettings(
//                    m_audioSettings,
//                    m_videoSettings,
//                    m_videoContainerFormat);

//        m_camera->unload();
//        m_camera->start();
//    }
//}

//void MainWindow::configureImageSettings()
//{
//    ImageSettings settingsDialog(m_imageCapture.data());
//    settingsDialog.setWindowFlags(settingsDialog.windowFlags() & ~Qt::WindowContextHelpButtonHint);

//    settingsDialog.setImageSettings(m_imageSettings);

//    if (settingsDialog.exec()) {
//        m_imageSettings = settingsDialog.imageSettings();
//        m_imageCapture->setEncodingSettings(m_imageSettings);
//    }
//}

void MainWindow::record()
{
    m_mediaRecorder->record();
    updateRecordTime();
}

void MainWindow::pause()
{
    m_mediaRecorder->pause();
}

void MainWindow::stop()
{
    m_mediaRecorder->stop();
}

void MainWindow::setMuted(bool muted)
{
    m_mediaRecorder->setMuted(muted);
}

void MainWindow::toggleLock()
{
    switch (m_camera->lockStatus()) {
    case QCamera::Searching:
    case QCamera::Locked:
        m_camera->unlock();
        break;
    case QCamera::Unlocked:
        m_camera->searchAndLock();
    }
}

void MainWindow::updateLockStatus(QCamera::LockStatus status, QCamera::LockChangeReason reason)
{
//    QColor indicationColor = Qt::black;

//    switch (status) {
//    case QCamera::Searching:
//        indicationColor = Qt::yellow;
//        ui->statusbar->showMessage(tr("Focusing..."));
//        ui->lockButton->setText(tr("Focusing..."));
//        break;
//    case QCamera::Locked:
//        indicationColor = Qt::darkGreen;
//        ui->lockButton->setText(tr("Unlock"));
//        ui->statusbar->showMessage(tr("Focused"), 2000);
//        break;
//    case QCamera::Unlocked:
//        indicationColor = reason == QCamera::LockFailed ? Qt::red : Qt::black;
//        ui->lockButton->setText(tr("Focus"));
//        if (reason == QCamera::LockFailed)
//            ui->statusbar->showMessage(tr("Focus Failed"), 2000);
//    }

//    QPalette palette = ui->lockButton->palette();
//    palette.setColor(QPalette::ButtonText, indicationColor);
//    ui->lockButton->setPalette(palette);
}

void MainWindow::takeImage()
{
    m_isCapturingImage = true;
    m_imageCapture->capture();
}

void MainWindow::displayCaptureError(int id, const QCameraImageCapture::Error error, const QString &errorString)
{
    Q_UNUSED(id);
    Q_UNUSED(error);
    QMessageBox::warning(this, tr("Image Capture Error"), errorString);
    m_isCapturingImage = false;
}

void MainWindow::startCamera()
{
    m_camera->start();
}

void MainWindow::stopCamera()
{
    m_camera->stop();
}

void MainWindow::updateCaptureMode()
{
//    int tabIndex = ui->captureWidget->currentIndex();
//    QCamera::CaptureModes captureMode = tabIndex == 0 ? QCamera::CaptureStillImage : QCamera::CaptureVideo;

//    if (m_camera->isCaptureModeSupported(captureMode))
//        m_camera->setCaptureMode(captureMode);
}

void MainWindow::updateCameraState(QCamera::State state)
{
    qDebug() << state;
//    switch (state) {
//    case QCamera::ActiveState:
//        ui->actionStartCamera->setEnabled(false);
//        ui->actionStopCamera->setEnabled(true);
//        ui->captureWidget->setEnabled(true);
//        ui->actionSettings->setEnabled(true);
//        break;
//    case QCamera::UnloadedState:
//    case QCamera::LoadedState:
//        ui->actionStartCamera->setEnabled(true);
//        ui->actionStopCamera->setEnabled(false);
//        ui->captureWidget->setEnabled(false);
//        ui->actionSettings->setEnabled(false);
//    }
}

void MainWindow::updateRecorderState(QMediaRecorder::State state)
{
//    switch (state) {
//    case QMediaRecorder::StoppedState:
//        ui->recordButton->setEnabled(true);
//        ui->pauseButton->setEnabled(true);
//        ui->stopButton->setEnabled(false);
//        break;
//    case QMediaRecorder::PausedState:
//        ui->recordButton->setEnabled(true);
//        ui->pauseButton->setEnabled(false);
//        ui->stopButton->setEnabled(true);
//        break;
//    case QMediaRecorder::RecordingState:
//        ui->recordButton->setEnabled(false);
//        ui->pauseButton->setEnabled(true);
//        ui->stopButton->setEnabled(true);
//        break;
//    }
}

void MainWindow::setExposureCompensation(int index)
{
    m_camera->exposure()->setExposureCompensation(index*0.5);
}

void MainWindow::displayRecorderError()
{
    QMessageBox::warning(this, tr("Capture Error"), m_mediaRecorder->errorString());
}

void MainWindow::displayCameraError()
{
    qDebug() << m_camera->errorString();
    //    QMessageBox::warning(this, tr("Camera Error"), m_camera->errorString());
//    setCamera(QCameraInfo::defaultCamera());
}

void MainWindow::updateCameraDevice(QAction *action)
{
//    setCamera(qvariant_cast<QCameraInfo>(action->data()));
}

void MainWindow::displayViewfinder()
{
    ui->stackedWidget->setCurrentIndex(0);
}

void MainWindow::displayCapturedImage()
{
    ui->stackedWidget->setCurrentIndex(1);
}

void MainWindow::readyForCapture(bool ready)
{
//    ui->takeImageButton->setEnabled(ready);
}

void MainWindow::imageSaved(int id, const QString &fileName)
{
    Q_UNUSED(id);
//    ui->statusbar->showMessage(tr("Captured \"%1\"").arg(QDir::toNativeSeparators(fileName)));

    m_isCapturingImage = false;
    if (m_applicationExiting)
        close();
}

void MainWindow::closeEvent(QCloseEvent *event)
{
    if (m_isCapturingImage) {
        setEnabled(false);
        m_applicationExiting = true;
        event->ignore();
    } else {
        event->accept();
    }
}

void MainWindow::pressedGPIO(int pi, unsigned user_gpio, unsigned level, uint32_t tick){
//    qDebug() << "last " << m_last_tick << endl << " tick " << tick << endl << " diff " << (tick-m_last_tick);
    if(tick-m_last_tick > m_bounce_ticks){
        qDebug() << "Mainwindow pressed GPIO " << user_gpio << " level " << level << " tick " << tick;
        m_last_tick = tick;
    }
}
