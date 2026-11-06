"""Đánh giá định tuyến ticket theo quy trình trên tập câu hỏi diễn đạt lại (data/kb/procedure_eval.csv).

Các câu trong tập đánh giá không trùng với câu hỏi mẫu (aliases) trong kho quy trình.
Đo hai mặt: ghép đúng quy trình (trong phạm vi) và từ chối đúng (ngoài phạm vi, không có quy trình).
Tập nhỏ, do nhóm tự viết; không đại diện cho câu hỏi thực tế của sinh viên.
"""
import json

import pandas as pd

from src.config import ROOT
from src.procedure_engine import ProcedureEngine


def run(path=ROOT / 'data' / 'kb' / 'procedure_eval.csv'):
    engine = ProcedureEngine()
    frame = pd.read_csv(path, keep_default_na=False)
    rows = []
    for _, row in frame.iterrows():
        found = engine.match(row['text'], top_k=1)
        got = found[0]['procedure']['id'] if found else ''
        rows.append({'text': row['text'], 'expected': row['expected'], 'got': got,
                     'score': found[0]['score'] if found else 0.0, 'correct': got == row['expected']})
    result = pd.DataFrame(rows)
    in_scope = result[result['expected'] != '']
    out_scope = result[result['expected'] == '']
    report = {
        'n_in_scope': int(len(in_scope)),
        'routing_accuracy_in_scope': round(float(in_scope['correct'].mean()), 4),
        'n_out_of_scope': int(len(out_scope)),
        'rejection_accuracy_out_of_scope': round(float(out_scope['correct'].mean()), 4),
        'errors': result[~result['correct']][['text', 'expected', 'got', 'score']].to_dict('records'),
    }
    out = ROOT / 'experiments' / 'procedure_routing_report.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == '__main__':
    run()
