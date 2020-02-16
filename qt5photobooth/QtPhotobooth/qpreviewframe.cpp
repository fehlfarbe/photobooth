#include "qpreviewframe.h"
#include <QPainter>
#include <QDebug>

QPreviewFrame::QPreviewFrame(QWidget *parent) : QLabel(parent)
{
    if(!m_overlay.load(":/images/photo_frame.png")){
        qDebug() << "cannot load photo frame";
    };
//    qDebug() << "overlay has alpha channel " << m_overlay.hasAlphaChannel();
//    updatePixmap();
}

void QPreviewFrame::setPreview(QImage preview)
{
    qDebug() << "set preview image with size " << preview.size();
    m_preview = preview;
    updatePixmap();
}

void QPreviewFrame::paintEvent(QPaintEvent *event)
{
    qDebug() << "QPreviewFrame paintEvent...pixmap: " << pixmap();
//    if(pixmap() == nullptr){
//        updatePixmap();
//        qDebug() << "QPreviewFrame paintEvent, pixmap size: " << pixmap()->size();
//    }
    QLabel::paintEvent(event);
}

void QPreviewFrame::updatePixmap()
{
    qDebug() << "update pixmap";
    QSize size;
    if(m_preview.isNull()){
        qDebug() << "preview image is null...return";
        return;
    }
    size = m_preview.size();

    if(pixmap() == nullptr){
        qDebug() << "pixmap is null";
        m_pixmap = QPixmap(size);
    } else {
        qDebug() << "pixmap size " << pixmap()->size();
        m_pixmap = QPixmap(pixmap()->size());
    }

//    qDebug() << "fill pixmap of size" << m_preview.size() << " black";
//    m_preview.fill(Qt::black);

    qDebug() << "create painter from pixmap";
    QPainter p(&m_pixmap);

    if(!m_preview.isNull()){
        qDebug() << "set mode";
        p.setCompositionMode(QPainter::CompositionMode_Source);
        qDebug() << "draw image";
        p.drawImage(0, 0, m_preview);
    }
//    p.fillRect(QRect(0, 0, 100, 100), Qt::white);

    if(!m_overlay.isNull()){
        if(m_overlay.size() != m_preview.size())        {
            qDebug() << "resizing overlay from " << m_overlay.size() <<
                       "to " << m_preview.size() << " to fit preview image";
            m_overlay = m_overlay.scaled(m_preview.size(), Qt::IgnoreAspectRatio, Qt::SmoothTransformation);
        }
        qDebug() << "draw overlay";
        p.setCompositionMode(QPainter::CompositionMode_Lighten);
        p.drawImage(0, 0, m_overlay);
    }
    qDebug() << "paint end";
    p.end();

    qDebug() << "set pixmap";
    setPixmap(m_pixmap);
}
