#ifndef QPREVIEWFRAME_H
#define QPREVIEWFRAME_H
#include <QLabel>
#include <QWidget>
#include <QImage>
#include <QPixmap>


class QPreviewFrame : public QLabel
{
public:
    QPreviewFrame(QWidget* parent=Q_NULLPTR);
    void setPreview(QImage preview);
    void paintEvent(QPaintEvent *);
private:
    void updatePixmap();

    QImage m_overlay;
    QImage m_preview;
    QPixmap m_pixmap;
};

#endif // QPREVIEWFRAME_H
