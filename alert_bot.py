#!/usr/bin/env python3
import argparse
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd
import requests
import yaml
import yfinance as yf


@dataclass
class Rule:
    type: str
    params: Dict


@dataclass
class Config:
    symbol: str
    interval: str
    period: str
    polling_seconds: int
    rules: List[Rule]
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None


def load_config(path: str) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    rule_list = [Rule(type=r["type"], params=r.get("params", {})) for r in raw.get("rules", [])]
    return Config(
        symbol=raw["symbol"],
        interval=raw.get("interval", "15m"),
        period=raw.get("period", "7d"),
        polling_seconds=int(raw.get("polling_seconds", 300)),
        rules=rule_list,
        telegram_bot_token=raw.get("notifications", {}).get("telegram", {}).get("bot_token"),
        telegram_chat_id=raw.get("notifications", {}).get("telegram", {}).get("chat_id"),
    )


def compute_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def ma_cross_up(df: pd.DataFrame, short_window: int, long_window: int) -> bool:
    if len(df) < long_window + 2:
        return False

    short_ma = df["Close"].rolling(short_window).mean()
    long_ma = df["Close"].rolling(long_window).mean()

    prev = short_ma.iloc[-2] <= long_ma.iloc[-2]
    now = short_ma.iloc[-1] > long_ma.iloc[-1]
    return bool(prev and now)


def rsi_below(df: pd.DataFrame, threshold: float, window: int = 14) -> bool:
    if len(df) < window + 1:
        return False
    rsi = compute_rsi(df["Close"], window=window)
    return bool(rsi.iloc[-1] < threshold)


def breakout_high(df: pd.DataFrame, lookback: int) -> bool:
    if len(df) < lookback + 1:
        return False
    current = df["Close"].iloc[-1]
    recent_high = df["High"].iloc[-(lookback + 1) : -1].max()
    return bool(current > recent_high)


def evaluate_rule(df: pd.DataFrame, rule: Rule) -> bool:
    if rule.type == "ma_cross_up":
        return ma_cross_up(
            df,
            short_window=int(rule.params.get("short_window", 5)),
            long_window=int(rule.params.get("long_window", 20)),
        )
    if rule.type == "rsi_below":
        return rsi_below(
            df,
            threshold=float(rule.params.get("threshold", 30)),
            window=int(rule.params.get("window", 14)),
        )
    if rule.type == "breakout_high":
        return breakout_high(df, lookback=int(rule.params.get("lookback", 20)))

    raise ValueError(f"지원하지 않는 규칙 타입입니다: {rule.type}")


def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()


def run(config: Config) -> None:
    print(f"[시작] {config.symbol} 모니터링 시작 (간격: {config.polling_seconds}초)")

    while True:
        try:
            df = yf.download(
                tickers=config.symbol,
                period=config.period,
                interval=config.interval,
                progress=False,
                auto_adjust=False,
            )

            if df.empty:
                print("[경고] 데이터를 가져오지 못했습니다.")
                time.sleep(config.polling_seconds)
                continue

            matched = [rule for rule in config.rules if evaluate_rule(df, rule)]

            if matched:
                rule_names = ", ".join([r.type for r in matched])
                close = float(df["Close"].iloc[-1])
                timestamp = str(df.index[-1])
                message = (
                    f"[알림] {config.symbol} 조건 충족!\n"
                    f"- 시간: {timestamp}\n"
                    f"- 종가: {close:.2f}\n"
                    f"- 충족 규칙: {rule_names}"
                )
                print(message)

                if config.telegram_bot_token and config.telegram_chat_id:
                    send_telegram_message(config.telegram_bot_token, config.telegram_chat_id, message)

            else:
                print(f"[대기] 조건 미충족 ({config.symbol})")

        except Exception as e:
            print(f"[오류] {e}")

        time.sleep(config.polling_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="원하는 주식 차트 패턴 발생 시 알림을 보내는 봇")
    parser.add_argument("--config", default="config.yaml", help="설정 파일 경로")
    args = parser.parse_args()

    config = load_config(args.config)
    run(config)


if __name__ == "__main__":
    main()
