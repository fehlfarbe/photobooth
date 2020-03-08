#include "qpreviewframe.h"
#include <QPainter>
#include <QDebug>

QPreviewFrame::QPreviewFrame(QWidget *parent) : QLabel(parent)
{
    if(!m_overlay.load(":/images/photo_frame.png")){
        qDebug() << "cannot load photo frame";
    };

    // timer for GIF animation
    m_timer = new QTimer(this);
    connect(m_timer, &QTimer::timeout, this, &QPreviewFrame::incrementPreview);
    m_timer->start(300);
}

void QPreviewFrame::setPreview(QImage preview)
{
    qDebug() << "set preview image with size " << preview.size();
    m_preview.clear();
    m_preview.emplace_back(preview);
    m_preview_curr = 0;
    updatePixmap();
}

void QPreviewFrame::setPreview(std::vector<QImage> preview)
{
    m_preview.clear();
    m_preview = std::move(preview);
    m_preview_curr = 0;
    updatePixmap();
}

void QPreviewFrame::paintEvent(QPaintEvent *event)
{
    qDebug() << "QPreviewFrame paintEvent...pixmap: " << pixmap();
    if(m_preview_redraw){
        updatePixmap();
    }

    QLabel::paintEvent(event);
}

void QPreviewFrame::updatePixmap()
{
    size_t idx = m_preview_curr%m_preview.size();
    qDebug() << "update pixmap";
    QSize size;
    if(m_preview.empty()){
        qDebug() << "preview image is null...return";
        return;
    }
    size = m_preview[idx].size();

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

    qDebug() << "set mode";
    p.setCompositionMode(QPainter::CompositionMode_Source);
    qDebug() << "draw image";
    p.drawImage(0, 0, m_preview[idx]);
//    p.fillRect(QRect(0, 0, 100, 100), Qt::white);

    if(!m_overlay.isNull()){
        if(m_overlay.size() != m_preview[idx].size())        {
            qDebug() << "resizing overlay from " << m_overlay.size() <<
                       "to " << m_preview[idx].size() << " to fit preview image";
            m_overlay = m_overlay.scaled(m_preview[idx].size(), Qt::IgnoreAspectRatio, Qt::SmoothTransformation);
        }
        qDebug() << "draw overlay";
        p.setCompositionMode(QPainter::CompositionMode_Lighten);
        p.drawImage(0, 0, m_overlay);
    }
    qDebug() << "paint end";
    p.end();

    qDebug() << "set pixmap";
    setPixmap(m_pixmap);

    m_preview_redraw = false;
}

void QPreviewFrame::incrementPreview()
{
    m_preview_curr = (m_preview_curr+1) % m_preview.size();
    m_preview_redraw = true;

    // if widget is visible, emit paint event to update pixmap
    if(isVisible()){
        emit paintEvent(nullptr);
    }
}
