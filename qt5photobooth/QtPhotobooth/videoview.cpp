#include "videoview.h"

#include <QVideoRendererControl>
#include <QVideoSurfaceFormat>
#include <QAbstractVideoSurface>


VideoView::VideoView() : QCameraViewfinder()
{

}

VideoView::VideoView(QWidget *parent) : QCameraViewfinder(parent)
{
    qDebug() << "VideoView initialized";
}


void VideoView::paintEvent(QPaintEvent *event)
{
//    qDebug() << "paint";
    this->QCameraViewfinder::paintEvent(event);
//    mediaObject()->service()->
//    QPainter painter(this);
//    painter.rotate(180);
}
