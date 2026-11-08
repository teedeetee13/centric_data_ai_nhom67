# -*- coding: utf-8 -*-
"""
Module: app.components.auth
Cổng đăng nhập khu vực cán bộ (Bàn duyệt, Dữ liệu, nạp hàng loạt, email thử).
- Chế độ demo chưa đặt mật khẩu: mở tự do, dùng trên máy cá nhân
- Có mật khẩu hoặc chế độ production: bắt buộc đăng nhập; production thiếu mật khẩu thì khóa hẳn
"""

import hmac
import time

import streamlit as st

from src.config import is_production, officer_password

MAX_FAILURES = 5
LOCK_SECONDS = 300

# Bộ đếm dùng chung mọi phiên: mở tab mới không né được giới hạn thử mật khẩu
_failures = {'count': 0, 'locked_until': 0.0}


def auth_required():
    return is_production() or bool(officer_password())


def is_officer():
    return not auth_required() or bool(st.session_state.get('officer_authenticated'))


def _check_password(candidate):
    password = officer_password()
    if not password:
        return False
    return hmac.compare_digest(candidate.encode('utf-8'), password.encode('utf-8'))


def render_officer_gate():
    """Hiển thị form đăng nhập khi cần. Trả về True nếu được vào khu vực cán bộ."""
    if not auth_required():
        st.caption('Chế độ demo: khu vực cán bộ đang mở vì chưa đặt mật khẩu. Không dùng chế độ này trên mạng dùng chung.')
        return True
    if not officer_password():
        st.error('Khu vực cán bộ đang khóa: máy chủ chưa cấu hình EDUSUPPORT_OFFICER_PASSWORD.')
        return False
    if st.session_state.get('officer_authenticated'):
        if st.button('Đăng xuất', key='officer_logout'):
            st.session_state['officer_authenticated'] = False
            st.rerun()
        return True

    remaining = _failures['locked_until'] - time.monotonic()
    if remaining > 0:
        st.error(f'Đã nhập sai quá nhiều lần. Thử lại sau {int(remaining) + 1} giây.')
        return False

    with st.form('officer_login'):
        st.markdown('##### Đăng nhập khu vực cán bộ')
        candidate = st.text_input('Mật khẩu cán bộ', type='password', key='officer_password_input')
        submitted = st.form_submit_button('Đăng nhập', type='primary')
    if submitted:
        if _check_password(candidate):
            _failures.update(count=0, locked_until=0.0)
            st.session_state['officer_authenticated'] = True
            st.rerun()
        _failures['count'] += 1
        if _failures['count'] >= MAX_FAILURES:
            _failures.update(count=0, locked_until=time.monotonic() + LOCK_SECONDS)
        st.error('Mật khẩu không đúng.')
    return False
