#ifndef QCOUNTDOWNLABEL_H
#define QCOUNTDOWNLABEL_H
#include <QLabel>
#include <QVariant>
#include <QFont>


class QCountdownLabel : public QLabel
{
public:
    QCountdownLabel(QWidget *parent = Q_NULLPTR);

    void startCountdown(qint64 ms);
    void flash(qint64 ms);

    void paintEvent(QPaintEvent * event);
private:
    void disableFlash();
//    static QVariant fontInterpolator(const QFont &start, const QFont &end, qreal progress);
//    static QVariant textInterpolator(const int &start, const int &end, qreal progress);

    qint64 m_countdown_start;
    qint64 m_countdown_duration = 0;
    float m_font_mult = 400;

    bool m_flash = false;
};

#endif // QCOUNTDOWNLABEL_H
