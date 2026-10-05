from __future__ import annotations
import json
from pathlib import Path
from .common import digest, finite, SafetyError, file_hash
from .features import NAMES, SCHEMA_HASH


class FrozenModel:
    def __init__(self, path):
        self.data = json.loads(Path(path).read_text(encoding='utf-8'))
        self.hash = digest(self.data)
        if self.data.get('feature_schema_hash') != SCHEMA_HASH:
            raise SafetyError('MODEL_FEATURE_SCHEMA_MISMATCH')
        if self.data.get('feature_implementation_sha256') != file_hash(Path(__file__).with_name('features.py')):
            raise SafetyError('MODEL_FEATURE_IMPLEMENTATION_CHANGED')
        if self.data.get('status') != 'EXPERIMENTAL_UNVALIDATED':
            raise SafetyError('MODEL_STATUS_INVALID')
        if self.data.get('feature_names') != list(NAMES):
            raise SafetyError('MODEL_FEATURE_ORDER_INVALID')
        if self.data.get('primary_horizon_s') != 30:
            raise SafetyError('MODEL_PRIMARY_HORIZON_INVALID')
        for name in ('means', 'scales'):
            if len(self.data[name]) != len(NAMES) or not all(finite(v) for v in self.data[name]):
                raise SafetyError('MODEL_VECTOR_INVALID')
        if not all(v > 0 for v in self.data['scales']):
            raise SafetyError('MODEL_SCALES_INVALID')
        if sorted(map(int, self.data['horizons'])) != [5, 10, 30, 60, 300]:
            raise SafetyError('MODEL_HORIZONS_INCOMPLETE')
        for row in self.data['horizons'].values():
            if len(row['weights']) != len(NAMES) or not all(finite(v) for v in row['weights']):
                raise SafetyError('MODEL_WEIGHTS_INVALID')
            for name in ('intercept_bp', 'uncertainty_bp', 'adverse_selection_bp'):
                if not finite(row.get(name)) or (name != 'intercept_bp' and row[name] < 0):
                    raise SafetyError('MODEL_ESTIMATOR_INVALID')

    def predict(self, vector):
        if len(vector) != len(NAMES) or not all(finite(v) for v in vector):
            raise SafetyError('FEATURE_VECTOR_INVALID')
        # Outside the development range, WAIT instead of extrapolating an enormous edge.
        z = [(x-m)/s for x, m, s in zip(vector, self.data['means'], self.data['scales'])]
        if max(abs(v) for v in z) > 12:
            return None
        return {h: row['intercept_bp'] + sum(w*x for w, x in zip(row['weights'], z))
                for h, row in self.data['horizons'].items()}
