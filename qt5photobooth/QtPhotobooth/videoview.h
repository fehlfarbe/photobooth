#ifndef VIDEOVIEW_H
#define VIDEOVIEW_H
#include <QCameraViewfinder>
#include <QPainter>
#include <QPaintEvent>
#include <QDebug>


class VideoView : public QCameraViewfinder
{
public:
    VideoView();
    VideoView(QWidget*);

protected:
    void paintEvent(QPaintEvent *event) override;
};

#endif // VIDEOVIEW_H
