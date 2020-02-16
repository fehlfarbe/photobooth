#include "qcountdownlabel.h"
#include <QPropertyAnimation>
#include <QDateTime>
#include <QDebug>
#include <QTimer>

QCountdownLabel::QCountdownLabel(QWidget *parent) : QLabel(parent)
{
//    this->setText("Label");
    this->setFont(QFont("Colibri", 25));
//    this->setCursor(Qt::PointingHandCursor);
//    qRegisterAnimationInterpolator<QFont>(&QCountdownLabel::fontInterpolator);
//    qRegisterAnimationInterpolator<int>(&QCountdownLabel::textInterpolator);

    QPalette pal;
    pal.setColor(QPalette::ButtonText,Qt::white);
    this->setPalette(pal);
}

//QVariant QCountdownLabel::fontInterpolator(const QFont &start, const QFont &end, qreal progress)
//{
//    int a = std::min(start.pixelSize(), end.pixelSize());
//    int b = std::max(start.pixelSize(), end.pixelSize());
//    int c = (1-progress)*a + progress*b;
//    QFont rt(start);
//    rt.setPointSize(c);
//    qDebug() << "progress" << progress << "a " << a << " b " << b << " c " << c;
//    return (rt);
//}

//QVariant QCountdownLabel::textInterpolator(const int &start, const int &end, qreal progress)
//{
//    return QString::number((end-start)*progress + start);
//}

void QCountdownLabel::startCountdown(qint64 ms){
    m_countdown_start = QDateTime::currentMSecsSinceEpoch();
    m_countdown_duration = ms;
    setVisible(true);
}

void QCountdownLabel::flash(qint64 ms)
{
    qDebug() << "enable flash";
    m_flash = true;
    QPixmap pmap;
    if(pixmap() == nullptr){
        pmap = QPixmap(size());
    } else {
        pmap = QPixmap(pixmap()->size());
    }
    qDebug() << "pixmap size " << pmap.size();

    pmap.fill(Qt::white);
    setPixmap(pmap);
    setVisible(true);
    emit paintEvent(nullptr);

    QTimer::singleShot(ms, this, &QCountdownLabel::disableFlash);
}

void QCountdownLabel::paintEvent(QPaintEvent * event){
    qint64 current = QDateTime::currentMSecsSinceEpoch();
    QPalette palette = this->palette();
    qDebug() << "countdownlabel paint";
    if(m_flash){
//        setText("-");
        qDebug() << "flash";
//        setStyleSheet("background-color: #fff;");
//        palette.setColor(backgroundRole(), Qt::white);
//        palette.setColor(foregroundRole(), Qt::white);
//        setVisible(true);
    } else {
        qDebug() << "QCountdownLabel paint() " << current-m_countdown_start << " " << m_countdown_duration;
        if(current-m_countdown_start > m_countdown_duration){
            setVisible(false);
        } else {
            setStyleSheet("background-color: transparent;");
            palette.setColor(backgroundRole(), Qt::transparent);
            palette.setColor(foregroundRole(), Qt::white);

            qint64 delta = (int)(current-m_countdown_start);
//            qDebug() << "countdown..." << delta << "ms " << (t_current-t_start);
            qint64 remaining = m_countdown_duration - delta;
            float deltaS = delta/1000.;
            QFont f = font();
            f.setBold(true);
            f.setPixelSize(30);
            f.setPixelSize(std::max(10, (int)((deltaS-(int)deltaS)*m_font_mult)));
            setFont(f);
            setText(QString::number((int)(remaining/1000.)));
        }
    }
    setPalette(palette);

    QLabel::paintEvent(event);
}

void QCountdownLabel::disableFlash()
{
    m_flash = false;
}
