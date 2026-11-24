"""Run manually or via Windows Task Scheduler to save an auditable price snapshot.

Read-only market data retrieval. No broker connections, orders or credentials.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from quantlab.market_data import download_prices
from quantlab.quality import price_quality_report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--tickers',default='SPY,QQQ,IWM,DIA,XLK,XLF,XLE,TLT,GLD,EEM')
    ap.add_argument('--period',default='5y',choices=['1y','2y','5y','10y'])
    ap.add_argument('--out-dir',type=Path,default=Path('local_data'))
    args=ap.parse_args()
    now=dt.datetime.now(dt.timezone.utc)
    prices=download_prices(args.tickers.split(','),args.period)
    quality=price_quality_report(prices,min(63,len(prices)-1))
    args.out_dir.mkdir(parents=True,exist_ok=True)
    # Date-stamped exports; older files are not overwritten or silently deleted.
    stem=now.strftime('%Y%m%dT%H%M%SZ')
    prices.to_csv(args.out_dir/f'prices_{stem}.csv',index_label='Date')
    quality.to_csv(args.out_dir/f'quality_{stem}.csv')
    metadata={'retrieved_at_utc':now.isoformat(),'provider':'Yahoo Finance via yfinance',
              'kind':'historical adjusted closes, NOT a live/exchange-certified feed',
              'date_min':str(prices.index.min().date()),'date_max':str(prices.index.max().date()),
              'tickers':list(prices.columns),'rows':len(prices),'quality_status':quality['Status'].to_dict()}
    (args.out_dir/f'metadata_{stem}.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print(json.dumps(metadata,indent=2))

if __name__=='__main__':
    main()
