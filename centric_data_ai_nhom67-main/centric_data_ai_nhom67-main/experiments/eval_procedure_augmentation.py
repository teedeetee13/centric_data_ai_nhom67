"""Thực nghiệm data-centric: bổ sung câu hỏi mẫu từ kho quy trình vào tập huấn luyện.

Giữ nguyên thuật toán (TF-IDF từ + ký tự, Logistic Regression C=1.5, class_weight balanced),
chỉ thay dữ liệu huấn luyện, rồi so sánh trên ba tập không dùng để huấn luyện:
- test_sealed: 70 câu niêm phong của bộ dữ liệu mô phỏng
- mau_thuc_te: 50 phản ánh mẫu viết theo văn phong thực tế (data/mau_phan_anh_thuc_te_eaut.csv)
- procedure_eval: 30 câu diễn đạt lại thuộc quy trình (nhãn = chủ đề của quy trình đúng)
"""
import json

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

from src.cleaner import clean_text_single
from src.config import PROCEDURE_KB_PATH, ROOT
from src.model import EduSupportClassifier, procedure_training_rows


def _clean(texts):
    return [clean_text_single(t)['clean_text'] for t in texts]


def eval_sets():
    sealed = pd.read_csv(ROOT / 'data' / 'splits' / 'test_sealed.csv')
    real = pd.read_csv(ROOT / 'data' / 'mau_phan_anh_thuc_te_eaut.csv')
    real = real[[clean_text_single(t)['is_usable'] for t in real['raw_text']]]
    topics = {p['id']: p['topic'] for p in json.loads(PROCEDURE_KB_PATH.read_text(encoding='utf-8'))['procedures']}
    proc = pd.read_csv(ROOT / 'data' / 'kb' / 'procedure_eval.csv', keep_default_na=False)
    proc = proc[proc['expected'] != '']
    return {
        'test_sealed': (list(sealed['clean_text']), list(sealed['target_label_gold'])),
        'mau_thuc_te': (_clean(real['raw_text']), list(real['target_label_gold'])),
        'procedure_eval': (_clean(proc['text']), [topics[e] for e in proc['expected']]),
    }


def score(clf, texts, labels):
    probs = clf.model.predict_proba(texts)
    pred = [clf.classes_[i] for i in probs.argmax(axis=1)]
    return {
        'macro_f1': round(float(f1_score(labels, pred, average='macro', zero_division=0)), 4),
        'accuracy': round(float(accuracy_score(labels, pred)), 4),
        'mean_confidence': round(float(np.mean(probs.max(axis=1))), 4),
        'share_confidence_below_0_60': round(float(np.mean(probs.max(axis=1) < 0.60)), 4),
    }


def run():
    train = pd.read_csv(ROOT / 'data' / 'splits' / 'train.csv')[['clean_text', 'target_label_gold']]
    extra = procedure_training_rows()
    sets = eval_sets()
    report = {'n_train_base': len(train), 'n_train_extra': len(extra), 'results': {}}
    for name, frame in [('A_base', train), ('B_base_plus_procedures', pd.concat([train, extra], ignore_index=True))]:
        clf = EduSupportClassifier(c_val=1.5, class_weight='balanced').train(frame['clean_text'], frame['target_label_gold'])
        report['results'][name] = {k: score(clf, *v) for k, v in sets.items()}
    out = ROOT / 'experiments' / 'procedure_augmentation_report.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == '__main__':
    run()
