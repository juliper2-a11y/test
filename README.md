# Stock Pattern Alert Bot

원하는 주식 차트 조건이 발생하면 콘솔/텔레그램으로 알림을 보내는 간단한 파이썬 프로그램입니다.

## 지원 조건

- `ma_cross_up`: 단기 이동평균선이 장기 이동평균선을 상향 돌파
- `rsi_below`: RSI가 특정 값 아래
- `breakout_high`: 최근 N개 봉의 고점을 현재 종가가 돌파

## 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 설정

```bash
cp config.example.yaml config.yaml
```

`config.yaml`을 수정해 종목, 주기, 조건, 텔레그램 정보를 입력하세요.

## 실행

```bash
python alert_bot.py --config config.yaml
```

## 참고

- 텔레그램 설정이 없으면 콘솔에만 출력됩니다.
- 투자 책임은 사용자 본인에게 있습니다.
