# -*- coding: utf-8 -*-
"""
Kịch bản Kiểm thử & Trình diễn Thực tế Hệ thống EduSupportAI
Data-Centric AI kết hợp Human-in-the-Loop
Không sử dụng emoji - Số liệu tính toán trực tiếp từ dữ liệu thực tế
"""

import os
import sys
import time
import pandas as pd
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.cleaner import clean_text_single, get_canonical_hash
from src.model import EduSupportClassifier
from src.faq_engine import FAQEngine
from src.database import init_db, sync_kb_from_csv, get_connection, log_review_action
from src.quality_profiler import profile_dataset

def print_separator(title=""):
    print("\n" + "=" * 70)
    if title:
        print(f" {title.upper()} ")
        print("=" * 70)

def run_live_demo():
    print_separator("KHOI CHAY DEMO THUC TE HE THONG EDUSUPPORTAI")
    print("Moi truong: Python, scikit-learn, SQLite, Streamlit")
    print("Dinh huong: Data-Centric AI (DCAI) ket hop Human-in-the-Loop")

    # 1. Khoi tao CSDL va Engine
    print("\n[BUOC 1] Khoi tao He thong & Nap Kho Tri thuc Quy che...")
    init_db()
    sync_kb_from_csv()
    
    model_path = "models/best_classifier.joblib"
    if not os.path.exists(model_path):
        from src.model import train_and_save_production_model
        clf = train_and_save_production_model()
    else:
        clf = EduSupportClassifier().load(model_path)
    
    faq_engine = FAQEngine()
    print("[OK] Kho tri thuc va Model san sang.")

    # 2. Tinh huong 1: Phan anh khan cap & chua thong tin ca nhan (PII)
    print_separator("TINH HUONG 1: PHAN ANH KHAN CAP & CHUA THONG TIN CA NHAN (PII)")
    raw_query_1 = (
        "Da em chao thay co, em nop tien hoc phi 8.500.000d qua Vietcombank hom qua "
        "nhung cong van bao no, sdt em 0987654321, mssv 2022601234 cuu em voi khong bi cam thi a!"
    )
    print(f"Van ban dau vao (raw_text):\n  \"{raw_query_1}\"")

    clean_res_1 = clean_text_single(raw_query_1)
    print(f"\n1. Sau Pipeline Lam sach & Che PII:\n  \"{clean_res_1['clean_text']}\"")
    print(f"   Co phat hien: {clean_res_1['quality_flags']}")

    pred_res_1 = clf.predict_single(clean_res_1['clean_text'])
    print(f"\n2. Ket qua Phan loai AI:")
    print(f"   - Chuyen mon du doan: {pred_res_1['predicted_topic']}")
    print(f"   - Do tu tin (Confidence): {pred_res_1['confidence_score'] * 100:.2f}%")
    print(f"   - Muc do uu tien: {pred_res_1['priority_level']}")

    draft_res_1 = faq_engine.generate_draft_response(clean_res_1['clean_text'], predicted_topic=pred_res_1['predicted_topic'])
    print(f"\n3. Tra cuu Quy che EAUT & Sinh Ban nhap:")
    print(f"   - Dieu khoan quy che khop: {draft_res_1['matched_kb_id']}")
    print(f"   - Don vi tiep nhan: {draft_res_1['department']}")
    print(f"   - Ban nhap tu dong:\n---\n{draft_res_1['draft_text']}\n---")

    # 3. Tinh huong 2: Loc phan anh qua ngan / tin rac (Data-Centric Quality Filter)
    print_separator("TINH HUONG 2: LOC PHAN ANH QUA NGAN / TIN RAC (DATA-CENTRIC FILTER)")
    raw_query_2 = "Hoc phi"
    print(f"Van ban dau vao: \"{raw_query_2}\" (do dai: {len(raw_query_2)} ky tu)")
    
    clean_res_2 = clean_text_single(raw_query_2)
    print(f"Ket qua kiem tra: is_usable = {clean_res_2['is_usable']}, co: {clean_res_2['quality_flags']}")
    if not clean_res_2['is_usable']:
        print("-> He thong tu dong CHAN khong chuyen vao mo hinh de tranh gay nhieu du lieu.")

    # 4. Tinh huong 3: Phat hien phan anh trung lap (Deduplication)
    print_separator("TINH HUONG 3: PHAT HIEN PHAN ANH TRUNG LAP DO GUI NHIEU LAN")
    text_a = "Thua thay co, phong 402 nha B khoa cua khong vao hoc duoc."
    text_b = "Thua thay co, phong 402 nha B khoa cua khong vao hoc duoc."
    hash_a = get_canonical_hash(text_a)
    hash_b = get_canonical_hash(text_b)
    print(f"Phan anh A: \"{text_a}\" -> Hash: {hash_a}")
    print(f"Phan anh B: \"{text_b}\" -> Hash: {hash_b}")
    print(f"Trunh khop Hash 100%: {hash_a == hash_b} -> Chi giu lai 1 ban ghi dai dien.")

    # 5. Tinh huong 4: Kiem duyet Cán bo & Ghi vet Kiem toan SQLite (Human-in-the-Loop)
    print_separator("TINH HUONG 4: KIEM DUYET CAN BO & GHI VET KIEM TOAN SQLITE")
    test_record_id = f"REC_DEMO_{int(time.time())}"
    print(f"Gia lap Can bo phe duyet phan anh: {test_record_id}")
    
    log_review_action(
        record_id=test_record_id,
        officer_action="approve",
        original_topic="Hoc_phi",
        final_topic="Hoc_phi",
        final_response=draft_res_1['draft_text'],
        notes="Da kiem tra bien lai thanh toan, xac nhan hop le."
    )
    print(f"[OK] Da ghi nhan hanh dong phe duyet vao bang 'review_logs' cua SQLite.")
    
    conn = get_connection()
    df_logs = pd.read_sql_query(
        "SELECT record_id, officer_action, final_topic, officer_notes, reviewed_at FROM review_logs ORDER BY id DESC LIMIT 1",
        conn
    )
    conn.close()
    print("Du lieu ghi vet thuc te trong CSDL:")
    print(df_logs.to_string(index=False))

    # 6. Tinh huong 5: Quet thong ke chat luong tren tap du lieu thuc te
    print_separator("TINH HUONG 5: QUET THONG KE CHAT LUONG TREN TAP DU LIEU THUC TE")
    real_csv_path = "data/mau_phan_anh_thuc_te_eaut.csv"
    if os.path.exists(real_csv_path):
        df_real = pd.read_csv(real_csv_path)
        print(f"Doc tap du lieu thuc te: {real_csv_path} ({len(df_real)} ban ghi)")
        
        report = profile_dataset(df_real)
        print("\nKet qua phan tich chat luong thuc te (Khong so lieu bia):")
        print(f"  - Tong so ban ghi tiep nhan: {report['total_records']}")
        print(f"  - So ban ghi hop le: {report['usable_records']} ({report['usable_ratio']}%)")
        print(f"  - So ban ghi qua ngan (< 12 ky tu): {report['short_records']} ({report['short_ratio']}%)")
        print(f"  - So ban ghi trung lap: {report['exact_duplicates']} ({report['exact_duplicate_ratio']}%)")
        print(f"  - So ca phat hien thong tin ca nhan (PII): {report['pii_stats']['total_pii']}")
        print(f"    + So dien thoai: {report['pii_stats']['phone_count']}")
        print(f"    + Email: {report['pii_stats']['email_count']}")
        print(f"    + Ma sinh vien: {report['pii_stats']['mssv_count']}")
        print(f"  - Diem suc khoe du lieu (Data Health Score): {report['health_score']}/100")

    print_separator("HOAN TAT DEMO THUC TE")
    print("Giao dien truc quan: Mo trinh duyet tai http://localhost:8501 de tuong tac.")

if __name__ == "__main__":
    run_live_demo()
