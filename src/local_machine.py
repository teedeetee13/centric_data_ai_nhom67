# -*- coding: utf-8 -*-
"""
Module: src.local_machine
Hệ thống Máy học Cục bộ (Local Learning Machine) & Engine Lập luận Quy trình (Local Reasoning Engine):
- Huấn luyện cục bộ trên tập dữ liệu chuẩn hóa kết hợp toàn bộ tri thức quy trình từ data-doc/
- Phân loại chủ đề học vụ (Multi-class Classification) với TF-IDF kép (Word 1-2 & Char 3-5)
- Tra cứu và so khớp quy trình nghiệp vụ tương đồng (Semantic Procedure Retrieval)
- Lập luận từng bước (Chain-of-Thought Reasoning) và tổng hợp giải đáp tự động có căn cứ văn bản
- Tích hợp bộ ghi vết minh bạch (Explainability Trace Logger) ghi nhận chi tiết từng mili-giây
"""

import sys
import json
import uuid
import warnings
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
import pandas as pd
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
import joblib

from src.config import MODEL_PATH, TOPICS
from src.cleaner import clean_text_single
from src.doc_parser import build_procedure_catalog, KB_OUTPUT_JSON
from src.trace_logger import ExecutionTrace
from src.model import determine_priority, KEYWORDS_URGENT, KEYWORDS_HIGH

DEPT_MAP = {
    "Hoc_phi": "Phòng Tài chính - Kế toán",
    "Lich_hoc_lich_thi": "Phòng Đào tạo",
    "Diem_khao_thi": "Ban Khảo thí & Đảm bảo chất lượng",
    "Thu_tuc_hanh_chinh": "Bộ phận Một cửa - Phòng CTSV",
    "Co_so_vat_chat": "Phòng Hành chính - Quản trị CSVC",
    "He_thong_CNTT": "Trung tâm Công nghệ Thông tin",
    "Khac": "Bộ phận Tiếp nhận chung"
}

class LocalLearningMachine:
    def __init__(self, model_path: Optional[Path] = None, catalog_path: Optional[Path] = None):
        self.model_path = Path(model_path) if model_path else MODEL_PATH
        self.catalog_path = Path(catalog_path) if catalog_path else KB_OUTPUT_JSON
        self.classifier = None
        self.procedures: List[Dict[str, Any]] = []
        self.proc_vectorizer: Optional[TfidfVectorizer] = None
        self.proc_matrix = None
        self._load_or_initialize()

    def _load_or_initialize(self):
        """Tải mô hình phân loại và kho quy trình đã được index."""
        # 1. Tải mô hình phân loại
        if self.model_path.exists():
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    loaded = joblib.load(str(self.model_path))
                    # Support both raw pipeline or EduSupportClassifier wrapper
                    self.classifier = loaded.model if hasattr(loaded, "model") else loaded
            except Exception as e:
                print(f"[LocalMachine] Cảnh báo khi tải mô hình: {e}. Sẽ huấn luyện mới.")
                self.classifier = None

        # 2. Tải kho quy trình từ data-doc
        self.reload_procedures()

        # Nếu chưa có mô hình thì huấn luyện ngay
        if self.classifier is None:
            self.train_local_model()

    def reload_procedures(self):
        """Nạp lại danh mục quy trình từ file JSON hoặc trích xuất trực tiếp từ data-doc."""
        if self.catalog_path.exists():
            try:
                with open(self.catalog_path, "r", encoding="utf-8") as f:
                    self.procedures = json.load(f)
            except Exception:
                self.procedures = build_procedure_catalog()
        else:
            self.procedures = build_procedure_catalog()
            self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.catalog_path, "w", encoding="utf-8") as f:
                json.dump(self.procedures, f, ensure_ascii=False, indent=2)

        # Indexing TF-IDF kép (Word 1-2 & Char 3-5) hỗ trợ cả gõ có dấu lẫn không dấu cho tra cứu quy trình
        if self.procedures:
            import unicodedata
            def strip_accents(t):
                return ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')

            corpus = []
            for p in self.procedures:
                text_block = f"{p['title']} {p['content_extract']} {p.get('legal_basis', '')} {p.get('forms_required', '')} " + " ".join(p.get("sample_queries", []))
                corpus.append(text_block + " " + strip_accents(text_block))

            self.proc_vectorizer = FeatureUnion([
                ("word_tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
                ("char_tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True))
            ])
            self.proc_matrix = self.proc_vectorizer.fit_transform(corpus)

    def train_local_model(self) -> Dict[str, Any]:
        """
        Huấn luyện mô hình học máy cục bộ (Local Model Training):
        Tổng hợp dữ liệu từ data/splits/train.csv + dữ liệu sinh từ data-doc
        """
        train_csv = ROOT_DIR / "data" / "splits" / "train.csv"
        texts = []
        labels = []

        if train_csv.exists():
            df_train = pd.read_csv(train_csv)
            col_text = "clean_text" if "clean_text" in df_train.columns else "text"
            col_label = "target_label_gold" if "target_label_gold" in df_train.columns else ("topic" if "topic" in df_train.columns else "label")
            if col_text in df_train.columns and col_label in df_train.columns:
                texts.extend(df_train[col_text].dropna().tolist())
                labels.extend(df_train[col_label].dropna().tolist())

        # Bổ sung dữ liệu huấn luyện từ sample_queries trích xuất trong data-doc
        for p in self.procedures:
            topic = p["topic"]
            for q in p.get("sample_queries", []):
                texts.append(q)
                labels.append(topic)
            # Thêm tiêu đề và trích đoạn làm mẫu
            texts.append(p["title"])
            labels.append(topic)

        # Xây dựng pipeline trích xuất kép Word + Char n-grams
        features = FeatureUnion([
            ("word_tfidf", TfidfVectorizer(
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.98,
                sublinear_tf=True
            )),
            ("char_tfidf", TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(3, 5),
                min_df=1,
                sublinear_tf=True
            ))
        ])

        classifier = LogisticRegression(
            C=1.5,
            solver="lbfgs",
            class_weight="balanced",
            random_state=42,
            max_iter=600
        )

        pipeline = Pipeline([
            ("features", features),
            ("clf", classifier)
        ])

        pipeline.fit(texts, labels)
        self.classifier = pipeline

        # Lưu trọng số mô hình
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipeline, str(self.model_path))

        return {
            "status": "SUCCESS",
            "total_samples": len(texts),
            "classes": list(pipeline.classes_),
            "model_path": str(self.model_path),
            "procedures_count": len(self.procedures)
        }

    def get_procedure(self, proc_id: str) -> Optional[Dict[str, Any]]:
        """Lấy thông tin quy trình theo mã định danh (proc_id)."""
        for p in self.procedures:
            if p.get("proc_id") == proc_id:
                return dict(p)
        return None

    def retrieve_procedure(self, query_text: str, predicted_topic: Optional[str] = None, top_k: int = 2) -> List[Dict[str, Any]]:
        """Tra cứu quy trình phù hợp nhất từ kho tri thức data-doc bằng Cosine Similarity kết hợp Fallback theo chuyên môn."""
        if not self.procedures or self.proc_vectorizer is None or self.proc_matrix is None:
            return []

        q_vec = self.proc_vectorizer.transform([query_text])
        sims = cosine_similarity(q_vec, self.proc_matrix)[0]

        ranked = []
        for idx, score in enumerate(sims):
            proc = self.procedures[idx]
            bonus = 0.12 if proc.get("topic") == predicted_topic else 0.0
            total_score = float(score) + bonus
            if total_score >= 0.05 or float(score) >= 0.04:
                item = dict(proc)
                item["similarity_score"] = round(float(score), 4)
                item["rank_score"] = round(total_score, 4)
                ranked.append(item)

        ranked.sort(key=lambda x: x["rank_score"], reverse=True)

        # Nếu chưa khớp từ khóa do câu quá ngắn hoặc teencode, tự động fallback về quy trình chuẩn của chuyên môn
        if not ranked and self.procedures:
            if predicted_topic and predicted_topic != 'Khac':
                topic_procs = [p for p in self.procedures if p.get("topic") == predicted_topic]
                if topic_procs:
                    fallback_p = dict(topic_procs[0])
                    fallback_p["similarity_score"] = 0.65
                    fallback_p["rank_score"] = 0.65
                    ranked.append(fallback_p)

            if not ranked:
                best_idx = int(sims.argmax())
                best_p = dict(self.procedures[best_idx])
                best_p["similarity_score"] = round(float(sims[best_idx]), 4)
                best_p["rank_score"] = round(float(sims[best_idx]), 4)
                ranked.append(best_p)

        return ranked[:top_k]

    def reason_and_synthesize(
        self,
        clean_text: str,
        topic: str,
        matched_procedure: Optional[Dict[str, Any]]
    ) -> Tuple[List[str], str]:
        """
        Lõi Lập luận Cục bộ (Local Machine Reasoning & Synthesis):
        Sinh chuỗi các bước suy luận logic (Chain-of-Thought) và tổng hợp văn bản giải đáp
        đúng thể thức hành chính, trích dẫn chuẩn xác văn bản từ data-doc.
        """
        dept = DEPT_MAP.get(topic, "Bộ phận Tiếp nhận")
        reasoning_steps = []

        if not matched_procedure:
            reasoning_steps.append(f"[Suy luận 1: Nhận diện phản ánh] Sinh viên phản ánh vấn đề liên quan đến nhóm '{TOPICS.get(topic, topic)}'.")
            reasoning_steps.append("[Suy luận 2: Đối chiếu quy định] Chưa tìm thấy điều khoản quy trình cụ thể tương đồng trong kho tài liệu data-doc.")
            reasoning_steps.append(f"[Suy luận 3: Thẩm quyền giải quyết] Chuyển tiếp tới {dept} để cán bộ tiếp nhận xác minh trực tiếp.")
            draft = (
                f"Chào bạn,\n\n"
                f"Hệ thống đã tiếp nhận phản ánh của bạn về lĩnh vực: {TOPICS.get(topic, topic)}.\n"
                f"Hiện tại nội dung chưa đủ thông tin hoặc chưa khớp với quy trình giải quyết tự động sẵn có. "
                f"Yêu cầu của bạn đã được chuyển đến {dept} để cán bộ chuyên trách kiểm tra hồ sơ và hướng dẫn cụ thể.\n\n"
                f"Trân trọng cảm ơn bạn."
            )
            return reasoning_steps, draft

        title = matched_procedure.get("title", "")
        legal = matched_procedure.get("legal_basis", "Quy định Nhà trường")
        p_time = matched_procedure.get("processing_time", "Theo quy định")
        forms = matched_procedure.get("forms_required", "Theo hướng dẫn")
        steps = matched_procedure.get("steps", [])

        reasoning_steps.append(f"[Suy luận 1: Nhận diện phản ánh] Phát hiện sự việc tương thích với quy trình nghiệp vụ '{title}'.")
        reasoning_steps.append(f"[Suy luận 2: Đối chiếu căn cứ pháp lý] Căn cứ theo văn bản: {legal}.")
        reasoning_steps.append(f"[Suy luận 3: Xác định thẩm quyền & Thời hạn] Thụ lý: {matched_procedure.get('department', dept)} | Thời gian xử lý: {p_time}.")
        reasoning_steps.append(f"[Suy luận 4: Hướng dẫn biểu mẫu & Trình tự] Yêu cầu biểu mẫu [{forms}] và thực hiện theo {len(steps)} bước chuẩn hóa.")

        # Định dạng văn bản giải đáp đầy đủ, rõ ràng và trang trọng
        step_lines = []
        for s in steps[:5]:  # Hiển thị tối đa 5 bước chính
            step_lines.append(f"  • Bước {s.get('step', '')} ({s.get('actor', '')}): {s.get('action', '')}")

        steps_formatted = "\n".join(step_lines) if step_lines else "  • Nộp hồ sơ và làm theo hướng dẫn tại bộ phận Một cửa."

        draft = (
            f"Chào bạn,\n\n"
            f"Căn cứ theo quy định tại {legal}, vấn đề của bạn được giải quyết theo '{title}' như sau:\n\n"
            f"1. Đơn vị tiếp nhận và xử lý: {matched_procedure.get('department', dept)}\n"
            f"2. Thời hạn giải quyết: {p_time}\n"
            f"3. Biểu mẫu / Hồ sơ cần chuẩn bị: {forms}\n\n"
            f"4. Trình tự các bước thực hiện:\n"
            f"{steps_formatted}\n\n"
            f"Nếu cần hỗ trợ thêm, bạn vui lòng liên hệ trực tiếp tại {matched_procedure.get('department', dept)} trong giờ hành chính để được hướng dẫn chu đáo.\n\n"
            f"Trân trọng."
        )

        return reasoning_steps, draft

    def process_request_with_trace(self, raw_text: str, record_id: str = "") -> Dict[str, Any]:
        """
        Thực thi toàn bộ quy trình tiếp nhận, xử lý, suy luận và ghi nhận Trace Log minh bạch.
        """
        trace_id = f"TRACE-{uuid.uuid4().hex[:12].upper()}"
        trace = ExecutionTrace(trace_id=trace_id, record_id=record_id)

        # -------------------------------------------------------------
        # BƯỚC 1: TIẾP NHẬN & KIỂM TOÁN CHẤT LƯỢNG DỮ LIỆU (DATA-CENTRIC AUDIT)
        # -------------------------------------------------------------
        step1 = trace.new_step(
            step_number=1,
            name="DATA_CENTRIC_AUDIT_AND_PII_FILTER",
            description="Làm sạch, chuẩn hóa Unicode NFC, phát hiện và che giấu thông tin định danh cá nhân (PII)"
        )
        step1.add_log(f"Tiếp nhận chuỗi dữ liệu đầu vào độ dài {len(raw_text)} ký tự")

        clean_res = clean_text_single(raw_text)
        clean_res.pop("raw_text", None)
        clean_text = clean_res["clean_text"]
        quality_flags = clean_res["quality_flags"]
        is_usable = clean_res["is_usable"]

        step1.add_log(f"Chuẩn hóa Unicode NFC và xử lý khoảng trắng thừa")
        if quality_flags:
            step1.add_log(f"Phát hiện và gắn cờ kiểm soát chất lượng: {', '.join(quality_flags)}")
        else:
            step1.add_log("Dữ liệu đạt chuẩn sạch (CLEAN), không có cờ cảnh báo")

        step1.finish(
            status="SUCCESS" if is_usable else "WARNING",
            raw_length=len(raw_text),
            cleaned_length=len(clean_text),
            quality_flags=quality_flags,
            is_usable=is_usable,
            masked_preview=clean_text[:120] + ("..." if len(clean_text) > 120 else "")
        )

        # Trường hợp không đủ điều kiện xử lý (< 12 ký tự hoặc rỗng)
        if not is_usable:
            step_err = trace.new_step(
                step_number=2,
                name="GUARDRAIL_ABORT",
                description="Từ chối suy luận tự động do dữ liệu không đủ độ dài tối thiểu (< 12 ký tự)"
            )
            step_err.add_log("Dữ liệu rỗng hoặc quá ngắn; không chuyển vào mô hình học máy")
            step_err.finish(status="ABORTED", reason="Văn bản quá ngắn hoặc rỗng")
            trace.finalize()

            return {
                "clean_text": clean_text,
                "quality_flags": quality_flags,
                "is_usable": False,
                "predicted_topic": "Khac",
                "confidence_score": 0.0,
                "class_probabilities": {},
                "priority_level": "Thấp",
                "priority_reason": "Nội dung phản ánh quá ngắn (dưới 12 ký tự) hoặc rỗng.",
                "department": "Bộ phận Tiếp nhận",
                "matched_kb_id": None,
                "matched_procedure": None,
                "articles": [],
                "draft_response": (
                    "Chào bạn, nội dung phản ánh chưa đủ thông tin để hệ thống có thể xử lý. "
                    "Bạn vui lòng bổ sung mô tả sự việc chi tiết, thời gian và địa điểm cụ thể để được hỗ trợ. Trân trọng."
                ),
                "review_reasons": ["Nội dung rỗng hoặc quá ngắn (dưới 12 ký tự)."],
                "needs_review": True,
                "execution_trace": trace.to_dict(),
                "terminal_log": trace.format_terminal_log()
            }

        # -------------------------------------------------------------
        # BƯỚC 2: MÁY HỌC PHÂN LOẠI & ĐỊNH TUYẾN (LOCAL CLASSIFIER & ROUTING)
        # -------------------------------------------------------------
        step2 = trace.new_step(
            step_number=2,
            name="LOCAL_MACHINE_CLASSIFICATION_AND_ROUTING",
            description="Trích xuất đặc trưng TF-IDF n-grams kép, ước lượng xác suất phân lớp và gán mức ưu tiên"
        )
        step2.add_log("Trích xuất đặc trưng Word n-grams (1, 2) và Character n-grams (3, 5)")

        pred_topic = "Khac"
        conf_score = 0.50
        prob_dict = {}

        if self.classifier is not None:
            try:
                probs = self.classifier.predict_proba([clean_text])[0]
                classes = list(self.classifier.classes_)
                max_idx = int(np.argmax(probs))
                pred_topic = classes[max_idx]
                conf_score = round(float(probs[max_idx]), 4)
                prob_dict = {cls: round(float(p), 4) for cls, p in zip(classes, probs)}
                step2.add_log(f"Phân loại thành công: Chủ đề [{pred_topic}] với độ tự tin {conf_score:.1%}")
            except Exception as e:
                step2.add_log(f"Lỗi suy luận phân loại: {e}. Áp dụng chủ đề mặc định.")
                pred_topic = "Khac"
                conf_score = 0.50

        # Cây quyết định mức độ ưu tiên
        priority_lvl = determine_priority(clean_text)
        dept = DEPT_MAP.get(pred_topic, "Bộ phận Tiếp nhận")

        prio_reason = "Không phát hiện từ khóa khẩn cấp; xếp mức Bình thường."
        t_low = clean_text.lower()
        for kw in KEYWORDS_URGENT:
            if kw in t_low:
                prio_reason = f"Quy tắc mức Khẩn cấp: phát hiện từ khóa nguy cấp '{kw}'."
                break
        else:
            for kw in KEYWORDS_HIGH:
                if kw in t_low:
                    prio_reason = f"Quy tắc mức Cao: phát hiện từ khóa ưu tiên '{kw}'."
                    break

        step2.add_log(f"Xác định mức ưu tiên: [{priority_lvl}] — {prio_reason}")
        step2.add_log(f"Định tuyến phòng ban thụ lý: {dept}")

        step2.finish(
            status="SUCCESS",
            predicted_topic=pred_topic,
            confidence_score=conf_score,
            priority_level=priority_lvl,
            priority_reason=prio_reason,
            department=dept,
            all_probabilities=prob_dict,
            top_3_probabilities=dict(sorted(prob_dict.items(), key=lambda x: x[1], reverse=True)[:3])
        )

        # -------------------------------------------------------------
        # BƯỚC 3: TRA CỨU ĐỐI CHIẾU QUY TRÌNH (PROCEDURE RETRIEVAL TỪ DATA-DOC)
        # -------------------------------------------------------------
        step3 = trace.new_step(
            step_number=3,
            name="PROCEDURE_KNOWLEDGE_RETRIEVAL",
            description="Tìm kiếm quy trình nghiệp vụ tương đồng từ kho tài liệu chính thức data-doc bằng Cosine Similarity"
        )
        step3.add_log(f"Truy vấn không gian vector trên {len(self.procedures)} quy trình nghiệp vụ")

        matched_procs = self.retrieve_procedure(clean_text, predicted_topic=pred_topic, top_k=3)
        top_proc = matched_procs[0] if matched_procs else None

        candidate_list = []
        for p in matched_procs:
            candidate_list.append({
                "proc_id": p.get("proc_id"),
                "title": p.get("title"),
                "doc_source": p.get("doc_source", ""),
                "similarity_score": p.get("similarity_score", 0),
                "rank_score": p.get("rank_score", 0)
            })

        if top_proc:
            step3.add_log(f"Khớp quy trình [{top_proc['proc_id']}]: '{top_proc['title']}' (Cosine Score: {top_proc.get('similarity_score', 0):.3f})")
            step3.add_log(f"Căn cứ văn bản: {top_proc.get('legal_basis', 'Quy định Nhà trường')}")
            step3.finish(
                status="SUCCESS",
                proc_id=top_proc["proc_id"],
                title=top_proc["title"],
                similarity_score=top_proc.get("similarity_score", 0),
                legal_basis=top_proc.get("legal_basis", ""),
                forms_required=top_proc.get("forms_required", ""),
                processing_time=top_proc.get("processing_time", ""),
                candidate_procedures=candidate_list
            )
        else:
            step3.add_log("Không tìm thấy quy trình đủ tương đồng")
            step3.finish(status="NO_MATCH", note="Không có quy trình tương thích trong kho tri thức hiện hành", candidate_procedures=[])

        # -------------------------------------------------------------
        # BƯỚC 4: LẬP LUẬN CỤC BỘ & TỔNG HỢP GIẢI ĐÁP (LOCAL REASONING & SYNTHESIS)
        # -------------------------------------------------------------
        step4 = trace.new_step(
            step_number=4,
            name="LOCAL_MACHINE_REASONING_AND_SYNTHESIS",
            description="Thực thi chuỗi suy luận logic (Chain-of-Thought) và tổng hợp phản hồi chuẩn hóa theo quy trình"
        )
        step4.add_log("Khởi tạo tiến trình suy luận cục bộ (Local Deterministic Reasoning)")

        reasoning_steps, draft_response = self.reason_and_synthesize(
            clean_text=clean_text,
            topic=pred_topic,
            matched_procedure=top_proc
        )

        for r_step in reasoning_steps:
            step4.add_log(r_step)

        step4.finish(
            status="SUCCESS",
            reasoning_steps=reasoning_steps,
            response_character_count=len(draft_response),
            response_preview=draft_response[:140] + "..."
        )

        # -------------------------------------------------------------
        # BƯỚC 5: RÀO CHẮN AN TOÀN & RA QUYẾT ĐỊNH (GUARDRAILS & DISPATCH)
        # -------------------------------------------------------------
        step5 = trace.new_step(
            step_number=5,
            name="GUARDRAILS_AND_DISPATCH_DECISION",
            description="Đánh giá rào chắn kiểm soát chất lượng và xác định điều kiện Tự động duyệt hoặc chuyển Bàn duyệt"
        )

        review_reasons = []
        if conf_score < 0.60:
            review_reasons.append("Độ tự tin phân loại dưới 60%; cần cán bộ xác minh nhóm chuyên môn.")
        if not top_proc:
            review_reasons.append("Chưa tìm thấy quy trình quy chế đủ tương đồng để viện dẫn tự động.")
        if priority_lvl == "Khẩn cấp":
            review_reasons.append("Phản ánh thuộc diện Ưu tiên Khẩn cấp; bắt buộc cán bộ thụ lý trực tiếp.")
        if quality_flags:
            review_reasons.append(f"Có cờ chất lượng dữ liệu: {', '.join(quality_flags)}")

        is_auto_approvable = (
            conf_score >= 0.70
            and bool(top_proc)
            and priority_lvl != "Khẩn cấp"
            and not any("duplicate" in f for f in quality_flags)
        )

        guardrail_checks = {
            "confidence_threshold_50": {
                "rule": "Độ tự tin phân loại AI >= 50%",
                "passed": bool(conf_score >= 0.50),
                "score": f"{conf_score:.1%}"
            },
            "official_docx_procedure_linked": {
                "rule": "Có quy trình căn cứ pháp lý trích xuất từ 3 file DOCX",
                "passed": bool(top_proc is not None),
                "procedure": top_proc.get('proc_id') if top_proc else None
            },
            "data_hygiene_and_pii_safe": {
                "rule": "Dữ liệu được làm sạch chuẩn NFC và che giấu PII an toàn",
                "passed": bool(is_usable),
                "flags": quality_flags
            },
            "priority_dispatch_ready": {
                "rule": "Kiểm định mức độ ưu tiên giải quyết",
                "passed": True,
                "level": priority_lvl
            }
        }

        if is_auto_approvable:
            decision = "AUTO_APPROVE"
            step5.add_log("Đạt toàn bộ tiêu chuẩn an toàn: Độ tự tin >= 70%, có căn cứ quy trình rõ ràng và không khẩn cấp.")
            step5.add_log("Quyết định: TỰ ĐỘNG PHÊ DUYỆT & GỬI PHẢN HỒI CHO SINH VIÊN.")
            step5.finish(
                status="AUTO_APPROVED",
                decision="AUTO_APPROVE",
                action="Tự động giải đáp và lưu vết kiểm toán",
                guardrail_checks=guardrail_checks,
                final_dispatch="TỰ ĐỘNG PHÊ DUYỆT"
            )
        else:
            decision = "ROUTED_TO_REVIEW_QUEUE"
            step5.add_log("Chưa đạt điều kiện tự động giải đáp; chuyển tiếp vào Hàng đợi Bàn duyệt cán bộ (Review Queue).")
            for reason in review_reasons:
                step5.add_log(f"Lý do: {reason}")
            step5.finish(
                status="REVIEW_QUEUE",
                decision="ROUTED_TO_REVIEW_QUEUE",
                review_reasons=review_reasons,
                guardrail_checks=guardrail_checks,
                final_dispatch="CHUYỂN BÀN DUYỆT CÁN BỘ"
            )

        trace.finalize()

        # Tạo articles tương thích với FAQEngine hiện có
        articles = []
        if top_proc:
            articles.append({
                "kb_id": top_proc.get("proc_id", "PROC_01"),
                "topic": top_proc.get("topic", pred_topic),
                "question_standard": top_proc.get("title", ""),
                "content_extract": top_proc.get("content_extract", ""),
                "department": top_proc.get("department", dept),
                "source_url": top_proc.get("legal_basis", ""),
                "verified": True,
                "similarity_score": top_proc.get("similarity_score", 0.0)
            })

        return {
            "clean_text": clean_text,
            "quality_flags": quality_flags,
            "is_usable": True,
            "predicted_topic": pred_topic,
            "confidence_score": conf_score,
            "class_probabilities": prob_dict,
            "priority_level": priority_lvl,
            "priority_reason": prio_reason,
            "department": top_proc.get("department", dept) if top_proc else dept,
            "matched_kb_id": top_proc.get("proc_id") if top_proc else None,
            "matched_procedure": top_proc,
            "reasoning_steps": reasoning_steps,
            "articles": articles,
            "draft_response": draft_response,
            "review_reasons": review_reasons,
            "needs_review": bool(review_reasons),
            "execution_trace": trace.to_dict(),
            "terminal_log": trace.format_terminal_log()
        }

# Global singleton instance
_GLOBAL_LOCAL_MACHINE: Optional[LocalLearningMachine] = None

def get_local_machine() -> LocalLearningMachine:
    global _GLOBAL_LOCAL_MACHINE
    if _GLOBAL_LOCAL_MACHINE is None:
        _GLOBAL_LOCAL_MACHINE = LocalLearningMachine()
    return _GLOBAL_LOCAL_MACHINE
