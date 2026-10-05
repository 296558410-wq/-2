"""Frozen development-only training. Never reads the formal 2026-09-22+ test window."""
from __future__ import annotations
import argparse
import json
import datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from .common import load_config, atomic_json, digest, file_hash, SafetyError
from .features import Features, Tick, NAMES, SCHEMA_HASH

HORIZONS=(5,10,30,60,300)


def build_dataset(cfg):
    frames=[]
    sources=[]
    for path in sorted(Path(cfg['training_data_dir']).glob('ticks_*.parquet')):
        day=path.stem.split('_')[-1]
        if not (cfg['development_start']<=day<=cfg['development_end']):
            continue
        if day >= '20260922':
            raise SafetyError('FORMAL_TEST_WINDOW_REFUSED')
        frame=pd.read_parquet(path,columns=['ts_utc','bid','ask'])
        if str(frame['ts_utc'].dtype) != 'datetime64[ms, UTC]':
            raise SafetyError('TIMESTAMP_UNIT_OR_TIMEZONE_UNKNOWN')
        frame['timestamp_ms']=frame['ts_utc'].astype('int64')
        end_ms=int(dt.datetime.strptime(cfg['development_end'],'%Y%m%d').replace(tzinfo=dt.timezone.utc).timestamp()*1000)+86400000
        frame=frame[frame['timestamp_ms']<end_ms]
        frames.append(frame[['timestamp_ms','bid','ask']])
        sources.append(dict(file=str(path),sha256=file_hash(path),rows=len(frame),role='DEVELOPMENT_CONTAMINATED'))
    if not frames:
        raise SafetyError('DEVELOPMENT_DATA_MISSING')
    combined=pd.concat(frames,ignore_index=True).sort_values('timestamp_ms',kind='stable')
    combined=combined.drop_duplicates(['timestamp_ms','bid','ask'])
    features=Features()
    rows=[]
    previous_grid=-1
    segment=0
    previous_ms=None
    for ms,bid,ask in combined.itertuples(index=False,name=None):
        tick=Tick(int(ms),float(bid),float(ask))
        if previous_ms is not None and tick.timestamp_ms-previous_ms>5000:
            segment+=1
        previous_ms=tick.timestamp_ms
        if not features.add(tick):
            continue
        grid=tick.timestamp_ms//cfg['decision_grid_ms']
        if grid==previous_grid:
            continue
        previous_grid=grid
        vector=features.vector()
        if vector is not None:
            rows.append((tick.timestamp_ms,tick.bid,tick.ask,segment,*vector))
    array=np.asarray(rows,dtype=np.float64)
    if len(array)<1000:
        raise SafetyError('DEVELOPMENT_SAMPLE_INSUFFICIENT')
    return array,sources


def block_margin(residual,ts,seed=20260922):
    # Resample contiguous 300-second block means, never IID individual overlapping labels.
    blocks=ts//300000
    _,inverse=np.unique(blocks,return_inverse=True)
    sums=np.bincount(inverse,weights=residual)
    counts=np.bincount(inverse)
    valid=counts>=30
    means=sums[valid]/counts[valid]
    if len(means)<20:
        raise SafetyError('TRAINING_BLOCKS_INSUFFICIENT')
    rng=np.random.default_rng(seed)
    boot=means[rng.integers(0,len(means),size=(2000,len(means)))].mean(axis=1)
    low,high=np.quantile(boot,[.025,.975])
    return float((high-low)/2),int(len(means))


def train(root):
    root=Path(root)
    cfg=load_config(root/'config.demo.json')
    if cfg['development_end']>='20260922':
        raise SafetyError('FORMAL_TEST_WINDOW_REFUSED')
    artifact=root/cfg['model_path']
    if artifact.exists():
        raise SafetyError('FROZEN_MODEL_ALREADY_EXISTS_CREATE_A_NEW_EXPERIMENT_VERSION')
    array,sources=build_dataset(cfg)
    ts=array[:,0].astype('int64')
    bid,ask,segment=array[:,1],array[:,2],array[:,3]
    mid=(bid+ask)/2
    x=array[:,4:]
    boundary=int(dt.datetime.strptime(cfg['train_end'],'%Y%m%d').replace(tzinfo=dt.timezone.utc).timestamp()*1000)+86400000
    train_mask=ts<boundary-300000
    dev_mask=ts>=boundary+300000
    means=x[train_mask].mean(axis=0)
    scales=x[train_mask].std(axis=0)
    scales=np.where(scales>1e-10,scales,1.)
    z=(x-means)/scales
    model=dict(schema='v3-demo-ridge/1',protocol=cfg['protocol'],status='EXPERIMENTAL_UNVALIDATED',
        created_utc=dt.datetime.now(dt.timezone.utc).isoformat(),feature_schema_hash=SCHEMA_HASH,
        feature_names=list(NAMES),means=means.tolist(),scales=scales.tolist(),
        primary_horizon_s=30,model_class='Ridge',alpha=1.,horizons={},
        feature_implementation_sha256=file_hash(Path(__file__).with_name('features.py')),
        training_sources=sources,test_data_read=False,training_role='DEVELOPMENT_CONTAMINATED',
        unmodeled=['market_impact','fill_uncertainty','opportunity_cost'],
        omitted_cost_bias='expected net edge can be optimistic',formal_oos_verdict='NOT_EVALUATED')
    report=dict(protocol=cfg['protocol'],diagnostic_role='DEVELOPMENT_CONTAMINATED_NOT_OOS',
                source_rows=sum(s['rows'] for s in sources),decision_rows=len(array),horizons={})
    for horizon in HORIZONS:
        future=np.searchsorted(ts,ts+horizon*1000)
        valid=future<len(ts)
        target_idx=np.minimum(future,len(ts)-1)
        valid &= (segment[target_idx]==segment)&(ts[target_idx]-(ts+horizon*1000)<=5000)
        y=(mid[target_idx]/mid-1)*10000
        tr=valid & train_mask
        dv=valid & dev_mask
        if tr.sum()<500 or dv.sum()<100:
            raise SafetyError('HORIZON_SAMPLE_INSUFFICIENT_'+str(horizon))
        ridge=Ridge(alpha=1.).fit(z[tr],y[tr])
        pred=ridge.predict(z)
        signed_residual=np.sign(pred[tr])*(y[tr]-pred[tr])
        margin,blocks=block_margin(signed_residual,ts[tr])
        adverse=max(0.,-float(signed_residual.mean()))
        cost_price=np.maximum(cfg['round_trip_cost_floor_price'],ask-bid+.22)
        cost_bp=cost_price/mid*10000
        eligible=np.abs(pred)>cost_bp+margin+adverse
        direction=np.where(pred>=0,1.,-1.)
        # Executable quote-proxy forward result; never labelled as an actual fill/P&L.
        proxy=np.where(direction>0,bid[target_idx]-ask,bid-ask[target_idx])/mid*10000-.22/mid*10000
        sample=dv & eligible
        row=dict(weights=ridge.coef_.tolist(),intercept_bp=float(ridge.intercept_),
                 uncertainty_bp=margin,adverse_selection_bp=adverse,
                 training_rows=int(tr.sum()),training_blocks=blocks)
        model['horizons'][str(horizon)]=row
        report['horizons'][str(horizon)]=dict(train_rows=int(tr.sum()),development_rows=int(dv.sum()),
            eligible_development_rows=int(sample.sum()),uncertainty_bp=margin,adverse_selection_bp=adverse,
            mean_quote_proxy_net_bp=float(proxy[sample].mean()) if sample.any() else None,
            prediction_mae_bp=float(np.abs(y[dv]-pred[dv]).mean()),effective_independent_n='NOT_ESTABLISHED',
            development_diagnostic_only=True)
    atomic_json(artifact,model)
    report['model_hash']=digest(model)
    atomic_json(root/'artifacts'/'development_diagnostics.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',default=str(Path(__file__).resolve().parents[1]))
    args=parser.parse_args()
    train(args.root)


if __name__=='__main__':
    main()
