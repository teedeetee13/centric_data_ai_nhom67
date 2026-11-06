"""Compare data interventions with a fixed model and template-group holdout.

This evaluator is specifically for the bundled controlled synthetic dataset.
It does not claim performance on real student questions.
"""
import hashlib
import json
import random
import re
from pathlib import Path
import difflib
import pandas as pd
from sklearn.metrics import f1_score,accuracy_score
from src.config import ROOT,RAW_DEMO_PATH
from src.cleaner import clean_text_single,clean_dataframe
from src.data_generator import BASE_TEMPLATES
from src.model import EduSupportClassifier

def canonical(text):
    return re.sub(r'[^\w\s]','',clean_text_single(text)['clean_text'].lower()).strip()

def prepare_groups(frame):
    patterns=[]
    for topic,templates in BASE_TEMPLATES.items():
        for text,_ in templates:
            text=text.replace('{mssv}','20991234').replace('{phone}','0912345678').replace('{email}','demo@example.org')
            normalized=canonical(text)
            gid=topic+'_'+hashlib.sha256(normalized.encode()).hexdigest()[:12]
            patterns.append((normalized,gid,topic,len(text)>=12))
    patterns.sort(key=lambda p:len(p[0]),reverse=True)
    groups=[]
    eligible={}
    for text in frame['raw_text'].fillna(''):
        norm=canonical(text)
        match=next((p for p in patterns if p[0] in norm),None)
        if match is None:
            raise ValueError('Có câu không khớp mẫu sinh ban đầu; evaluator này chỉ dành cho dữ liệu mô phỏng kèm repo.')
        groups.append(match[1])
        eligible[match[1]]=match[3]
    result=frame.copy()
    result['template_group']=groups
    rng=random.Random(42)
    test_groups,val_groups=set(),set()
    for topic,part in result.groupby('target_label_gold'):
        candidates=sorted(g for g in part['template_group'].unique() if eligible[g])
        if len(candidates)<3:
            raise ValueError('Mỗi nhãn cần ít nhất ba nhóm mẫu để tách train/validation/test.')
        rng.shuffle(candidates)
        test_groups.add(candidates[0])
        val_groups.add(candidates[1])
    result['split']=result['template_group'].map(
        lambda g:'test' if g in test_groups else ('val' if g in val_groups else 'train'))
    return result

def cleaned_subset(frame):
    clean=clean_dataframe(frame,'raw_text')
    clean['target_label_gold']=frame['target_label_gold'].to_numpy()
    clean['record_id']=frame['record_id'].to_numpy()
    clean['template_group']=frame['template_group'].to_numpy()
    return clean

def run_all_experiments(output_json=None,**unused):
    raw=pd.read_csv(RAW_DEMO_PATH)
    if set(raw['source_type'].dropna())!={'controlled_demo'}:
        raise ValueError('Không dùng evaluator mẫu cho dữ liệu vận hành.')
    grouped=prepare_groups(raw)
    train=grouped[grouped['split']=='train'].copy()
    val=grouped[grouped['split']=='val'].copy()
    test=cleaned_subset(grouped[grouped['split']=='test'].copy())
    test=test[test['is_usable']].copy()
    clean_train=cleaned_subset(train)
    variants={
      'E0':('Thô, giữ cấu hình mô hình cố định',train['raw_text'].fillna(''),train['target_label_gold']),
      'E1':('Chuẩn hóa, che PII và loại trùng hoàn toàn',
            clean_train.loc[~clean_train['quality_flags'].str.contains('exact_duplicate|empty'),'clean_text'],
            clean_train.loc[~clean_train['quality_flags'].str.contains('exact_duplicate|empty'),'target_label_gold']),
      'E2':('Thêm lọc ngắn và gần trùng',
            clean_train.loc[clean_train['is_usable'],'clean_text'],
            clean_train.loc[clean_train['is_usable'],'target_label_gold']),
    }
    report={'dataset_type':'controlled_demo','real_world_accuracy_established':False,
      'method':'Split by original template family before cleaning. Same model configuration for every experiment.',
      'model':{'features':'word TF-IDF 1-2 + char TF-IDF 3-5','C':1.5,'class_weight':'balanced','random_state':42,'max_iter':500},
      'counts':{'raw':len(raw),'train_raw':len(train),'validation_raw':len(val),'test_usable':len(test)},
      'train_test_group_overlap':len(set(train['template_group'])&set(test['template_group'])),
      'experiments':{}}
    for key,(name,texts,labels) in variants.items():
        clf=EduSupportClassifier(c_val=1.5,class_weight='balanced').train(texts,labels)
        predicted=clf.model.predict(test['clean_text'])
        report['experiments'][key]={'name':name,'train_samples':len(texts),
            'macro_f1':round(float(f1_score(test['target_label_gold'],predicted,average='macro',zero_division=0)),4),
            'accuracy':round(float(accuracy_score(test['target_label_gold'],predicted)),4),
            'errors':[{'record_id':str(row['record_id']),'clean_text':row['clean_text'],
                       'gold_label':row['target_label_gold'],'predicted_label':str(pred)}
                      for (_,row),pred in zip(test.iterrows(),predicted) if row['target_label_gold']!=pred]}
    train_clean=clean_train.loc[clean_train['is_usable'],'clean_text'].tolist()
    report['test_near_train_ge_093']=sum(
        any(difflib.SequenceMatcher(None,t.lower(),tr.lower()).ratio()>=.93 for tr in train_clean)
        for t in test['clean_text'])
    report['limitations']=[
       'Synthetic templates; small held-out set, not a measurement on real school data.',
       'Retrieval threshold 0.15 and confidence threshold 0.60 are provisional.',
       'The app artifact is not overwritten by this evaluation.',
       'Data interventions may reduce classification scores; report the observed results.']
    path=Path(output_json) if output_json else ROOT/'experiments'/'group_holdout_results.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    grouped[['record_id','template_group','split']].to_csv(path.with_name('group_holdout_split_manifest.csv'),index=False)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return report

if __name__=='__main__':
    run_all_experiments()
