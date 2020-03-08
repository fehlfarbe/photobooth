#include "mainwindow.h"
#include "ui_mainwindow.h"

#include <QMediaService>
#include <QMediaRecorder>
#include <QCameraViewfinder>
#include <QCameraInfo>
#include <QCameraImageCapture>
#include <QMediaMetaData>
#include <QVideoRendererControl>
#include <QVideoSurfaceFormat>
#include <QTemporaryDir>

#include <QMessageBox>
#include <QPalette>
#include <QFont>

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

    // UI stuff
    ui->viewfinderLabel->setVisible(false);
    ui->stackedWidget->setCurrentIndex(0);

    // load settings
    QFile checkSettings("settings.ini");
    if(!checkSettings.exists()){
        qDebug() << "No settings file at " << checkSettings.fileName() << " found";
        this->close();
        return;
    }
    m_settings = new QSettings(checkSettings.fileName(), QSettings::Format::IniFormat);

    //Camera devices:
    QActionGroup *videoDevicesGroup = new QActionGroup(this);
    videoDevicesGroup->setExclusive(true);
    const QList<QCameraInfo> availableCameras = QCameraInfo::availableCameras();
    for (const QCameraInfo &cameraInfo : availableCameras) {
        qDebug() << cameraInfo.deviceName();
    }
    qDebug() << "default camera: " << QCameraInfo::defaultCamera();

//    connect(videoDevicesGroup, &QActionGroup::triggered, this, &MainWindow::updateCameraDevice);
//    connect(ui->captureWidget, &QTabWidget::currentChanged, this, &MainWindow::updateCaptureMode);

    setCamera(QCameraInfo::defaultCamera());

    // init signals
    connect(this, &MainWindow::onCountdown, this, &MainWindow::countDownLabel);
    connect(this, &MainWindow::onActionPhoto, this, &MainWindow::actionPhoto);
    connect(this, &MainWindow::onActionGIF, this, &MainWindow::actionGIF);
    connect(this, &MainWindow::onActionPrint, this, &MainWindow::actionPrint);
    connect(this, &MainWindow::onFlash, this, &MainWindow::flash);

    // init GPIO
    m_pi = pigpio_start(nullptr, nullptr);
//    for(size_t i=0; i<30; i++){
//        switch (i) {
//        case BUTTONS::INFO:
//        case BUTTONS::PHOTO:
//        case BUTTONS::GIF:
//        case BUTTONS::PRINT:
//            set_mode(m_pi, i, PI_INPUT);
//            set_pull_up_down(m_pi, i, PI_PUD_UP);
//            callback_ex(m_pi, i, FALLING_EDGE, &gpiocallback, this);
//            break;
//        case OUTPUTS::FLASH:
//            set_mode(m_pi, i, PI_OUTPUT);
//            set_PWM_dutycycle(m_pi, i, 100);
//            break;
//        default:
//            break;
//        }
//    }

    // setup buttons
    const QStringList buttons {"info", "photo", "gif", "print"};
    for(auto& key : buttons){
        int i = getGPIO(key);
        set_mode(m_pi, i, PI_INPUT);
        set_pull_up_down(m_pi, i, PI_PUD_UP);
        callback_ex(m_pi, i, FALLING_EDGE, &gpiocallback, this);
    }

    // setup flash
    int flash = getGPIO("flash");
    set_mode(m_pi, flash, PI_OUTPUT);
    set_PWM_dutycycle(m_pi, flash, readSettings("main", "flash_default", 100).toInt());
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

    // image capture
    m_imageCapture.reset(new QCameraImageCapture(m_camera.data()));
//    QCameraImageCapture::CaptureDestinations dest;
//    m_imageCapture->setCaptureDestination();

    // media recorder
    m_mediaRecorder.reset(new QMediaRecorder(m_camera.data()));
    connect(m_mediaRecorder.data(), &QMediaRecorder::stateChanged, this, &MainWindow::updateRecorderState);
    connect(m_mediaRecorder.data(), &QMediaRecorder::durationChanged, this, &MainWindow::updateRecordTime);
    connect(m_mediaRecorder.data(), QOverload<QMediaRecorder::Error>::of(&QMediaRecorder::error),
            this, &MainWindow::displayRecorderError);
    m_mediaRecorder->setMetaData(QMediaMetaData::Title, QVariant(QLatin1String("Photobooth")));
//    m_mediaRecorder->setContainerFormat("mp4");
//    m_mediaRecorder->setVideoSettings(vid);
//    qDebug() << "supported containers: " << m_mediaRecorder->supportedContainers();
//    qDebug() << "supported fps: " << m_mediaRecorder->supportedFrameRates();
//    qDebug() << "supported codecs: " << m_mediaRecorder->supportedVideoCodecs();
    m_mediaRecorder->setMuted(true);
    m_videoContainerFormat.append("video/webm");
    m_videoSettings.setCodec("video/x-vp8") ;
//    m_videoSettings.setFrameRate(1.0);
    m_mediaRecorder->setContainerFormat(m_videoContainerFormat);
    m_mediaRecorder->setVideoSettings(m_videoSettings);
    qDebug() << m_mediaRecorder->videoSettings().codec() << " " << m_mediaRecorder->containerFormat();

    // camera liveview
    m_camera->setViewfinder(ui->viewfinder);

    QCameraViewfinderSettings settings;
    settings.setResolution(1920, 1088);
//    settings.setResolution(1280, 720);
    settings.setMinimumFrameRate(1.0);
    settings.setMaximumFrameRate(30.0);
    settings.setPixelFormat(QVideoFrame::PixelFormat::Format_BGR24);
    qDebug() << "resolution: " << settings.resolution() << " pixel: " << settings.pixelFormat();

    m_camera->setViewfinderSettings(settings);

//    updateCameraState(m_camera->state());
//    updateLockStatus(m_camera->lockStatus(), QCamera::UserRequest);
    updateRecorderState(m_mediaRecorder->state());

//    connect(m_imageCapture.data(), &QCameraImageCapture::readyForCaptureChanged, this, &MainWindow::readyForCapture);
    connect(m_imageCapture.data(), &QCameraImageCapture::imageCaptured, this, &MainWindow::processCapturedImage);
    connect(m_imageCapture.data(), &QCameraImageCapture::imageSaved, this, &MainWindow::imageSaved);
    connect(m_imageCapture.data(), QOverload<int, QCameraImageCapture::Error, const QString &>::of(&QCameraImageCapture::error),
            this, &MainWindow::displayCaptureError);

    connect(m_camera.data(), QOverload<QCamera::LockStatus, QCamera::LockChangeReason>::of(&QCamera::lockStatusChanged),
            this, &MainWindow::updateLockStatus);

//    ui->viewfinder->setFullScreen(true);

//    ui->captureWidget->setTabEnabled(0, (m_camera->isCaptureModeSupported(QCamera::CaptureStillImage)));
//    ui->captureWidget->setTabEnabled(1, (m_camera->isCaptureModeSupported(QCamera::CaptureVideo)));

    // V4L settings
    QString args(QString("v4l2-ctl --set-ctrl=horizontal_flip=")
                 + QString::number(readSettings("main", "flip_h", false).toBool())
                 + " --set-ctrl=vertical_flip="
                 + QString::number(readSettings("main", "flip_v", false).toBool()));
    QProcess::execute(args);

//    updateCaptureMode();
//    m_camera->setCaptureMode(QCamera::CaptureVideo);
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
    if (event->isAutoRepeat())
        return;

    switch (event->key()) {
    case Qt::Key_Space:
        emit onActionPhoto();
        break;
    case Qt::Key_Right:
        emit displayCapturedImage();
        break;
    case Qt::Key_Left:
        emit displayViewfinder();
        break;
    case Qt::Key_Escape:
        emit close();
        break;
    default:
        QMainWindow::keyReleaseEvent(event);
    }
}

void MainWindow::actionPhoto(){
    if(m_isCapturingImage || m_isCapturingGIF){
        return;
    }
    qDebug() << "start countdown and take photo";

    emit onCountdown();
    emit onFlash(true);
    QTimer::singleShot(readSettings("main", "countdown", 3000).toInt(), this, &MainWindow::takeImage);
}

void MainWindow::actionGIF(){
    if(m_isCapturingImage || m_isCapturingGIF){
        return;
    }
    qDebug() << "start countdown and take GIF";
    emit onCountdown();
    emit onFlash(true);
    QTimer::singleShot(readSettings("main", "countdown", 3000).toInt(), this, &MainWindow::record);
}

void MainWindow::actionPrint(){
    if(m_last_image.isEmpty()){
        qDebug() << "no image to print...";
        return;
    }

    // check if print is already running
    QProcess process;
    process.start("lpstat");
    process.waitForFinished();
    QString output = process.readAllStandardOutput();
    qDebug() << output;
    if(output.size() > 0){
        qDebug() << "Printer is still printing...";
        return;
    }

    qDebug() << "printing last photo: " << m_last_image;

    // copy last image to temporary directory so it can't be deleted and modified
//    QTemporaryDir path("/dev/shm/");
    QString tmp = "/dev/shm/print.jpg";
    QFile::copy(m_last_image, tmp);

    // flip image
    if(readSettings("main", "printer_flip_v", false).toBool()){
        qDebug() << "flip image before printing";
        QImage img(tmp);
        img = img.mirrored(false, true);
        img.save(tmp);
    }
    QProcess::startDetached(QString("lpr -o fit-to-page %1").arg(tmp));
}

void MainWindow::countDownLabel(){
    ui->viewfinderLabel->startCountdown(readSettings("main", "countdown", 3000).toInt());
}

void MainWindow::updateRecordTime()
{
    qDebug() << QString("Recorded %1 ms").arg(m_mediaRecorder->duration());
}

void MainWindow::processCapturedImage(int requestId, const QImage& img)
{
    if(m_isCapturingGIF){
        m_gif_buffer.push_back(img);
        if(m_gif_buffer.size() >= readSettings("main", "gif_frames", 3).toInt()){
            qDebug() << "GIF buffer full";
            m_isCapturingGIF = false;
            emit onFlash(false);
            qDebug() << "save and show GIF buffer";
//            saveGIF(m_gif_buffer, 3.0);
            QtConcurrent::run(this, &MainWindow::saveGIF, std::move(m_gif_buffer), readSettings("main", "gif_fps", 3).toFloat());
            // show GIF
            for(auto& img : m_gif_buffer){
                img = img.scaled(ui->viewfinder->size(),
                                 Qt::KeepAspectRatio,
                                 Qt::SmoothTransformation);
            }
            ui->preview->setPreview(m_gif_buffer);
            displayCapturedImage();
            QTimer::singleShot(8000, this, &MainWindow::displayViewfinder);
            // clear GIF buffer
            m_gif_buffer.clear();
        } else {
            qDebug() << "take next GIF frame in " << readSettings("main", "gif_pause", 1000).toInt() << "ms";
            QTimer::singleShot(readSettings("main", "gif_pause", 1000).toInt(), this, &MainWindow::takeImage);
        }
    } else {
        Q_UNUSED(requestId);
        QImage scaledImage = img.scaled(ui->viewfinder->size(),
                                        Qt::KeepAspectRatio,
                                        Qt::SmoothTransformation);
        ui->preview->setPreview(scaledImage);

        // Display captured image for 4 seconds.
        displayCapturedImage();
        emit onFlash(false);
        QTimer::singleShot(4000, this, &MainWindow::displayViewfinder);
    }
}

void MainWindow::record()
{
    qDebug() << "Started GIF record";
    m_isCapturingGIF = true;

//    m_mediaRecorder->record();
//    QTimer::singleShot(m_gif_length_ms, this, &MainWindow::stop);
////    updateRecordTime();
    takeImage();
}

void MainWindow::pause()
{
    qDebug() << "Pause GIF record";
    m_mediaRecorder->pause();
}

void MainWindow::stop()
{
    qDebug() << "Stop GIF record";
    m_mediaRecorder->stop();
    m_isCapturingGIF = false;
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
    qDebug() << "update lock status: " << status << " because " << reason;
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
//    m_camera->setCaptureMode(QCamera::CaptureStillImage);
    m_isCapturingImage = true;
    ui->viewfinderLabel->flash(100);
    m_imageCapture->capture();
}

void MainWindow::displayCaptureError(int id, const QCameraImageCapture::Error error, const QString &errorString)
{
    Q_UNUSED(id);
    Q_UNUSED(error);
    qDebug() << "Image Capture Error" << errorString;
    m_isCapturingImage = false;
    emit onFlash(false);
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
    qDebug() << "new camera state: " << state;
    switch (state) {
    case QCamera::ActiveState:
        m_isCapturingImage = false;
        emit onFlash(false);
        break;
    default:
        break;
    }
}

void MainWindow::updateRecorderState(QMediaRecorder::State state)
{
    switch (state) {
    case QMediaRecorder::StoppedState:
        qDebug() << "record stopped";
        break;
    case QMediaRecorder::PausedState:
        qDebug() << "record paused";
        break;
    case QMediaRecorder::RecordingState:
        qDebug() << "record started";
        break;
    }
}

void MainWindow::setExposureCompensation(int index)
{
    m_camera->exposure()->setExposureCompensation(index*0.5);
}

void MainWindow::displayRecorderError()
{
    qDebug() << "Capture error: " << m_mediaRecorder->errorString();
//    QMessageBox::warning(this, tr("Capture Error"), m_mediaRecorder->errorString());
}

void MainWindow::displayCameraError()
{
    qDebug() << "camera Error: " << m_camera->errorString();
    emit close();
    //    QMessageBox::warning(this, tr("Camera Error"), m_camera->errorString());
//    setCamera(QCameraInfo::defaultCamera());
}

void MainWindow::updateCameraDevice(QAction *action)
{
//    setCamera(qvariant_cast<QCameraInfo>(action->data()));
    qDebug() << "update camera device";
}

void MainWindow::displayViewfinder()
{
    m_camera->start();
    ui->preview->clear();
    ui->stackedWidget->setCurrentIndex(0);
}

void MainWindow::displayCapturedImage()
{
    m_camera->stop();
    ui->stackedWidget->setCurrentIndex(1);
}

void MainWindow::imageCaptured(int id, const QImage &preview){
    if(m_isCapturingGIF){
        return;
    }
    qDebug() << "got image with ID " << id;
    QString full, thumb;
    full.asprintf("image_%05d.jpg", id);
    QString full_path = readSettings("main", "image_dir", "~").toString() + full;
    preview.save(full_path);
}

void MainWindow::imageSaved(int id, const QString &fileName)
{
    Q_UNUSED(id);
    qDebug() << "saved image to " << fileName;
    m_last_image = fileName;

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
        emit onFlash(false);
    }
}

void MainWindow::saveGIF(std::vector<QImage> &images, float fps)
{
    // save all images to temporary memory
    QTemporaryDir path("/dev/shm/");
    for(size_t i=0; i<images.size(); i++){
        QString filename = path.filePath(QString("%1").arg(i, 2, 10, QChar('0')) + ".jpg");
        qDebug() << "Saving to " << filename;
        images[i].save(filename);
    }

    // create animated GIF with ffmpeg
    QString args(QString("ffmpeg -r %3 -i %1/%2 -c:v libvpx -vf \"scale=800:-1\" -crf 10 -b:v 1M %4/%5.webm").arg(
                     path.path(),
                     "%02d.jpg",
                     QString::number(fps),
                     readSettings("main", "image_dir", "~").toString(),
                     QDateTime::currentDateTime().toString("yyyy-MM-dd_hh-mm-ss")));
    qDebug() << args;
    QProcess::execute(args);
}

int MainWindow::getGPIO(QString name)
{
    return readSettings("gpio", name, -1).toInt();
}

QVariant MainWindow::readSettings(QString group, QString key, QVariant val_default)
{
    m_settings->beginGroup(group);
    qDebug() << "readSettings: " << m_settings->group() << " " << m_settings->childKeys();
    QVariant value = m_settings->value(key, val_default);
    m_settings->endGroup();
    return value;
}

void MainWindow::pressedGPIO(int pi, unsigned user_gpio, unsigned level, uint32_t tick){
//    qDebug() << "last " << m_last_tick << endl << " tick " << tick << endl << " diff " << (tick-m_last_tick);
    if(tick-m_last_tick > m_bounce_ticks){
        m_last_tick = tick;
        if(user_gpio == getGPIO("photo")){
            emit onActionPhoto();
        } else if(user_gpio == getGPIO("gif")){
            emit onActionGIF();
        } else if(user_gpio == getGPIO("print")){
            emit onActionPrint();
        } else {
            qDebug() << "No handler for GPIO " << user_gpio;
        }
    }
}

void MainWindow::flash(bool on){
    set_PWM_dutycycle(m_pi, getGPIO("flash"),
                      on ? readSettings("main", "flash_on", 255).toInt() : readSettings("main", "flash_default", 100).toInt());
}
