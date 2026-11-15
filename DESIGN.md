# EduSupportAI — Design System & Visual Specification (Operate Mode)

## 1. Product & Surface Mode
* **Surface Mode:** `Operate` (High-density, scan-friendly, mission-critical academic student service desk).
* **Primary Objective:** Empower university officers (Phòng Đào tạo, Khảo thí, CTSV, CSVC, CNTT, Kế toán) to review, verify, and resolve student inquiries in under 30 seconds with zero visual fatigue.
* **Aesthetic Identity:** **EAUT Sapphire Slate & Academic Pro** — Deep sapphire university navy, crisp slate neutrals, soft pastel semantic pills, and subtle elevation cards.

---

## 2. Color Tokens & Palette
* **Brand / University Blue:**
  * `--brand-navy`: `#1e3a8a` (Deep academic sapphire for navbar, brand badges)
  * `--brand-primary`: `#2563eb` (Action buttons, active tabs, focused inputs)
  * `--brand-primary-hover`: `#1d4ed8`
  * `--brand-subtle`: `#eff6ff` (Soft selection background)
* **Neutral Slate Scale:**
  * `--bg-app`: `#f8fafc` (Canvas background)
  * `--bg-surface`: `#ffffff` (Cards, drawers, modal panes)
  * `--border-subtle`: `#e2e8f0` (Card borders, dividers)
  * `--border-strong`: `#cbd5e1` (Input borders)
  * `--text-primary`: `#0f172a` (Headings, ticket codes, active items)
  * `--text-secondary`: `#475569` (Body text, email text)
  * `--text-muted`: `#64748b` (Timestamps, captions, metadata labels)
* **Semantic Accents:**
  * **Urgent / Danger:** Text `#b91c1c`, Background `#fef2f2`, Border `#fecaca`
  * **High / Warning:** Text `#c2410c`, Background `#fff7ed`, Border `#ffedd5`
  * **Success / Auto-Approved:** Text `#15803d`, Background `#f0fdf4`, Border `#bbf7d0`
  * **AI Copilot Indigo:** Text `#4338ca`, Background `#eef2ff`, Border `#c7d2fe`

---

## 3. Typography & Hierarchy
* **Font Family:** `Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`
* **App Bar Brand:** `18px`, Weight 700, Letter spacing `-0.02em`
* **Card Titles:** `14px - 15px`, Weight 600, Color `#0f172a`
* **Ticket Monospace Code:** `13px`, Weight 700, Monospace / Tabular numbers
* **Body Text:** `13.5px`, Line-height `1.55`, Weight 400 - 500
* **Meta & Badges:** `11px - 12px`, Weight 600, Uppercase / Semi-bold

---

## 4. Component Patterns
1. **Top Application Bar:**
   * University Crest + System Logo.
   * Status Pill (`● Sẵn sàng phục vụ`).
   * Active Term / Academic Year badge.
   * Active Officer Profile Chip (`👤 Cán bộ trực ban`).
2. **Tabbed Navigation:**
   * Modern rounded pill or clean underline tabs with badge counters.
3. **Master-Detail Ticket Workspace:**
   * **Left Panel (Ticket Queue):** Quick filter pills, search input, modern ticket feed with hover highlight, urgency indicator, student code, department badge, and clean message excerpt.
   * **Right Panel (Detail & Action Studio):**
     * Ticket Header Bar: Code, SLA timer, status, officer assignment.
     * Student Message Bubble: Styled like a modern messaging app conversation bubble with student avatar, timestamp, contact tags, and clean text.
     * AI Copilot Box: Purple/indigo glowing accent, confidence gauge, official regulation reference, and direct resolution draft.
     * Officer Action Bar: Category selector, response editor, recipient email, and primary action buttons.
