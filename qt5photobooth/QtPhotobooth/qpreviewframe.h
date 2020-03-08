#ifndef QPREVIEWFRAME_H
#define QPREVIEWFRAME_H
#include <QLabel>
#include <QWidget>
#include <QImage>
#include <QPixmap>
#include <QTimer>


class QPreviewFrame : public QLabel
{
public:
    QPreviewFrame(QWidget* parent=Q_NULLPTR);
    void setPreview(QImage preview);
    void setPreview(std::vector<QImage> preview);
    void paintEvent(QPaintEvent *);
private slots:
    void incrementPreview();
private:
    void updatePixmap();

    QImage m_overlay;
    std::vector<QImage> m_preview;
    size_t m_preview_curr;
    bool m_preview_redraw = true;
    QTimer* m_timer = nullptr;
    QPixmap m_pixmap;
};

#endif // QPREVIEWFRAME_H
