"""
dashboard.py — Streamlit dashboard for the Finance Credit Follow-Up Email Agent.

Run with: streamlit run dashboard.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import streamlit as st
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# Page config (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Finance Email Agent | Dashboard",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS — Premium dark theme
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
  }

  /* Dark background */
  .stApp {
    background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #0d1117 100%);
    color: #e6edf3;
  }

  /* Hide Streamlit branding */
  #MainMenu, footer, header { visibility: hidden; }

  /* Metric cards */
  .metric-card {
    background: linear-gradient(145deg, #1c2128, #21262d);
    border: 1px solid #30363d;
    border-radius: 16px;
    padding: 24px 20px;
    text-align: center;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }
  .metric-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.4);
  }
  .metric-number {
    font-size: 2.8rem;
    font-weight: 700;
    margin: 0;
    background: linear-gradient(135deg, #58a6ff, #79c0ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .metric-label {
    font-size: 0.85rem;
    color: #8b949e;
    margin-top: 4px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .metric-icon { font-size: 1.8rem; margin-bottom: 8px; }

  /* Stage badges */
  .stage-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.03em;
  }
  .badge-stage1 { background: rgba(63,185,80,0.15); color: #3fb950; border: 1px solid #3fb950; }
  .badge-stage2 { background: rgba(210,153,34,0.15); color: #d2972a; border: 1px solid #d2972a; }
  .badge-stage3 { background: rgba(248,81,73,0.15); color: #f85149; border: 1px solid #f85149; }
  .badge-stage4 { background: rgba(147,51,234,0.15); color: #a371f7; border: 1px solid #a371f7; }
  .badge-escalated { background: rgba(255,255,255,0.1); color: #e6edf3; border: 1px solid #6e7681; }

  /* Section headers */
  .section-title {
    font-size: 1.2rem;
    font-weight: 600;
    color: #58a6ff;
    border-bottom: 1px solid #21262d;
    padding-bottom: 8px;
    margin-bottom: 20px;
  }

  /* Email preview card */
  .email-preview {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 20px;
    font-family: monospace;
    font-size: 0.87rem;
    line-height: 1.7;
    white-space: pre-wrap;
    color: #c9d1d9;
    max-height: 400px;
    overflow-y: auto;
  }

  /* Status pill */
  .pill-sent { color: #3fb950; font-weight: 600; }
  .pill-dryrun { color: #58a6ff; font-weight: 600; }
  .pill-escalated { color: #d29922; font-weight: 600; }
  .pill-error { color: #f85149; font-weight: 600; }

  /* Run button */
  div.stButton > button {
    background: linear-gradient(135deg, #238636, #2ea043);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 28px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    width: 100%;
  }
  div.stButton > button:hover {
    background: linear-gradient(135deg, #2ea043, #3fb950);
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(46,160,67,0.4);
  }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: #161b22;
    border-right: 1px solid #21262d;
  }

  /* Info box */
  .info-box {
    background: rgba(31,111,235,0.1);
    border: 1px solid rgba(31,111,235,0.3);
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 0.87rem;
    color: #79c0ff;
  }

  /* Warning box */
  .warn-box {
    background: rgba(210,153,34,0.1);
    border: 1px solid rgba(210,153,34,0.3);
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 0.87rem;
    color: #e3b341;
  }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: transparent;
  }
  .stTabs [data-baseweb="tab"] {
    background: #21262d;
    border-radius: 8px;
    color: #8b949e;
    border: 1px solid #30363d;
  }
  .stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #1f6feb, #388bfd) !important;
    color: white !important;
    border-color: transparent !important;
  }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def stage_badge(stage: int) -> str:
    labels = {
        1: ("1st Follow-Up", "stage1"),
        2: ("2nd Follow-Up", "stage2"),
        3: ("3rd Follow-Up", "stage3"),
        4: ("4th Follow-Up", "stage4"),
        5: ("⚠️ Escalated", "escalated"),
    }
    label, cls = labels.get(stage, ("Unknown", "escalated"))
    return f'<span class="stage-badge badge-{cls}">{label}</span>'


def status_pill(status: str) -> str:
    mapping = {
        "sent": ("✅ Sent", "sent"),
        "dry_run": ("🧪 Dry Run", "dryrun"),
        "escalated": ("⚠️ Escalated", "escalated"),
        "error": ("❌ Error", "error"),
    }
    label, cls = mapping.get(status, (status, ""))
    return f'<span class="pill-{cls}">{label}</span>'


def metric_card(icon: str, number: str | int, label: str) -> str:
    return f"""
    <div class="metric-card">
      <div class="metric-icon">{icon}</div>
      <div class="metric-number">{number}</div>
      <div class="metric-label">{label}</div>
    </div>"""


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 💼 Finance Email Agent")
    st.markdown("---")

    # Config check
    try:
        from src.config import Config
        config_ok = True
    except Exception as e:
        config_ok = False
        st.error(f"Config error: {e}")

    if config_ok:
        mode_color = "🧪" if Config.DRY_RUN else "🚀"
        st.markdown(f"**Mode:** {mode_color} {'Dry Run' if Config.DRY_RUN else 'LIVE'}")
        st.markdown(f"**LLM:** `{Config.LLM_PROVIDER.upper()} / {Config.LLM_MODEL}`")
        st.markdown("---")

    st.markdown("### ⚙️ Run Options")
    data_file = st.text_input("Data File", value="data/invoices.csv")
    specific_invoices = st.text_area(
        "Filter Invoices (one per line, blank = all)",
        placeholder="INV-2024-001\nINV-2024-003",
    )
    force_dry_run = st.checkbox("Force Dry Run", value=True)

    st.markdown("---")
    run_clicked = st.button("▶ Run Agent Now", use_container_width=True)
    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.78rem; color: #6e7681; line-height:1.6;">
    <b>Quick links:</b><br>
    📋 <a href="https://github.com" style="color:#58a6ff;">GitHub Repo</a><br>
    📄 <a href="audit/audit_trail.db" style="color:#58a6ff;">Audit DB</a>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Main header
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<h1 style="
  font-size: 2rem;
  font-weight: 700;
  background: linear-gradient(135deg, #58a6ff 0%, #79c0ff 50%, #a371f7 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 4px;
">💼 Finance Credit Follow-Up Email Agent</h1>
<p style="color: #8b949e; margin-bottom: 32px;">
  Automate overdue invoice follow-ups · Escalate intelligently · Audit everything
</p>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Run Agent on button click
# ─────────────────────────────────────────────────────────────────────────────

if run_clicked:
    import os
    if force_dry_run:
        os.environ["DRY_RUN"] = "true"

    invoice_filter = None
    if specific_invoices.strip():
        invoice_filter = [
            line.strip()
            for line in specific_invoices.strip().splitlines()
            if line.strip()
        ]

    with st.spinner("🤖 Agent running — generating emails with LLM..."):
        try:
            from src.agent import FinanceEmailAgent
            agent = FinanceEmailAgent()
            result = agent.run(data_file=data_file, invoice_filter=invoice_filter)
            st.session_state["last_result"] = result
            st.success(f"✅ Agent completed! {result.emails_generated} emails generated, {result.escalated} escalated.")
        except Exception as e:
            st.error(f"❌ Agent error: {e}")
            st.exception(e)

# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard", "📋 Invoice Queue", "📧 Email Previews", "🔍 Audit Trail"
])


# ── Tab 1: Dashboard ──────────────────────────────────────────────────────────
with tab1:
    try:
        from src.audit import AuditDB
        from src.config import Config
        audit = AuditDB(Config.AUDIT_DB_PATH)
        stats = audit.get_stats()
    except Exception:
        stats = {"total": 0, "sent": 0, "dry_run": 0, "escalated": 0, "errors": 0}

    col1, col2, col3, col4, col5 = st.columns(5)
    cards = [
        (col1, "📨", stats["total"], "Total Processed"),
        (col2, "✅", stats["sent"], "Emails Sent"),
        (col3, "🧪", stats["dry_run"], "Dry Runs"),
        (col4, "⚠️", stats["escalated"], "Escalated"),
        (col5, "❌", stats["errors"], "Errors"),
    ]
    for col, icon, num, label in cards:
        with col:
            st.markdown(metric_card(icon, num, label), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Escalation stage breakdown chart
    try:
        entries = audit.get_all()
        if entries:
            stage_counts = pd.DataFrame([
                {"Stage": f"Stage {e.escalation_stage}", "Count": 1}
                for e in entries
            ]).groupby("Stage").sum().reset_index()

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown('<div class="section-title">📊 Stage Distribution</div>', unsafe_allow_html=True)
                st.bar_chart(stage_counts.set_index("Stage"))

            with col_b:
                st.markdown('<div class="section-title">📈 Recent Activity</div>', unsafe_allow_html=True)
                recent_df = pd.DataFrame([
                    {
                        "Invoice": e.invoice_no,
                        "Client": e.client_name,
                        "Status": e.send_status,
                        "Tone": e.tone_used[:30],
                        "When": e.timestamp.strftime("%m/%d %H:%M"),
                    }
                    for e in entries[:10]
                ])
                st.dataframe(recent_df, use_container_width=True, hide_index=True)
        else:
            st.markdown("""
            <div class="info-box">
              📭 No audit records yet. Click <b>▶ Run Agent Now</b> to process your invoices.
            </div>""", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Could not load chart data: {e}")


# ── Tab 2: Invoice Queue ──────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-title">📋 Overdue Invoice Queue</div>', unsafe_allow_html=True)
    try:
        from src.data_loader import load_invoices
        from src.models import STAGE_META

        records, errors = load_invoices(data_file)
        overdue = [r for r in records if r.days_overdue > 0]

        if overdue:
            rows = []
            for r in overdue:
                meta = STAGE_META[r.escalation_stage]
                rows.append({
                    "Invoice #": r.invoice_no,
                    "Client": r.client_name,
                    "Company": r.company_name,
                    "Amount": r.amount_formatted,
                    "Due Date": r.due_date_formatted,
                    "Days Overdue": r.days_overdue,
                    "Stage": int(r.escalation_stage),
                    "Tone": meta["tone"],
                    "Follow-ups Sent": r.follow_up_count,
                })

            df = pd.DataFrame(rows)

            # Colour-coded stage column
            def colour_stage(val):
                colours = {1: "#3fb950", 2: "#d2972a", 3: "#f85149", 4: "#a371f7", 5: "#6e7681"}
                c = colours.get(val, "#6e7681")
                return f"background-color: {c}20; color: {c}; font-weight: 600;"

            styled = df.style.map(colour_stage, subset=["Stage"])
            st.dataframe(styled, use_container_width=True, hide_index=True)

            # Summary
            total_amt = sum(r.amount for r in overdue)
            st.markdown(f"""
            <div class="info-box">
              💰 <b>{len(overdue)} overdue invoices</b> totalling
              <b>₹{total_amt:,.0f}</b> require follow-up action.
            </div>""", unsafe_allow_html=True)
        else:
            st.success("🎉 No overdue invoices — all payments are current!")

        if errors:
            st.warning(f"⚠️ {len(errors)} rows had validation errors and were skipped.")
    except FileNotFoundError:
        st.error(f"Data file not found: `{data_file}`. Check the sidebar path.")
    except Exception as e:
        st.error(f"Error loading invoices: {e}")


# ── Tab 3: Email Previews ─────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-title">📧 Last Run — Generated Emails</div>', unsafe_allow_html=True)

    last_result = st.session_state.get("last_result")
    if last_result and last_result.audit_entries:
        entries_with_body = [
            e for e in last_result.audit_entries
            if e.email_body and e.send_status != "error"
        ]
        if entries_with_body:
            selected = st.selectbox(
                "Select invoice to preview:",
                options=[e.invoice_no for e in entries_with_body],
                format_func=lambda inv: next(
                    (f"{e.invoice_no} — {e.client_name} ({e.tone_used})"
                     for e in entries_with_body if e.invoice_no == inv), inv
                ),
            )
            chosen = next((e for e in entries_with_body if e.invoice_no == selected), None)
            if chosen:
                col_left, col_right = st.columns([3, 1])
                with col_left:
                    st.markdown(f"**Subject:** {chosen.email_subject}")
                with col_right:
                    st.markdown(f"**Status:** {status_pill(chosen.send_status)}", unsafe_allow_html=True)

                st.markdown(
                    f'<div class="email-preview">{chosen.email_body}</div>',
                    unsafe_allow_html=True
                )
    else:
        st.markdown("""
        <div class="info-box">
          🔄 Run the agent first to preview generated emails here.
          Click <b>▶ Run Agent Now</b> in the sidebar.
        </div>""", unsafe_allow_html=True)

        # Show sample templates
        st.markdown("### 📚 Sample Email Formats by Stage")
        samples = {
            "Stage 1 — Warm & Friendly": """Subject: Quick Reminder – Invoice #INV-2024-001 | ₹45,000 Due

Hi Rajesh,

I hope you're doing well! This is a friendly reminder that Invoice #INV-2024-001 for ₹45,000 was due on 20 Apr 2025.

If you have already processed this, please disregard. Otherwise, you can use the payment link below to complete the transaction at your convenience.

Payment Link: https://pay.yourcompany.com/invoice/INV-2024-001

Thank you for your continued partnership!

Warm regards,
Finance Team""",
            "Stage 3 — Formal & Serious": """Subject: IMPORTANT: Outstanding Payment – Invoice #INV-2024-001 (15 Days Overdue)

Dear Mr. Kapoor,

Despite our previous reminders, Invoice #INV-2024-001 (₹45,000) remains unpaid as of today, now 15 days overdue.

We request your immediate attention to this matter. Continued non-payment may impact your credit terms with us.

Please respond within 48 hours confirming payment or providing a payment schedule.

Regards,
Finance Team""",
            "Stage 4 — Stern & Urgent": """Subject: FINAL NOTICE – Invoice #INV-2024-001 – Immediate Action Required

Dear Mr. Kapoor,

This is our final reminder. Invoice #INV-2024-001 (₹45,000) is now 28 days overdue.

Failure to remit payment within 24 hours will result in escalation to our legal and recovery team.

Please act immediately. Contact us on +91-XXXXXXXXXX if you need to discuss payment arrangements.

Finance Team""",
        }
        for title, body in samples.items():
            with st.expander(title):
                st.markdown(f'<div class="email-preview">{body}</div>', unsafe_allow_html=True)


# ── Tab 4: Audit Trail ────────────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="section-title">🔍 Full Audit Trail</div>', unsafe_allow_html=True)
    try:
        from src.audit import AuditDB
        from src.config import Config
        audit = AuditDB(Config.AUDIT_DB_PATH)
        all_entries = audit.get_all()

        if all_entries:
            df = pd.DataFrame([
                {
                    "ID": e.id,
                    "Timestamp": e.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "Invoice": e.invoice_no,
                    "Client": e.client_name,
                    "Amount": f"₹{e.amount:,.0f}",
                    "Days OD": e.days_overdue,
                    "Stage": e.escalation_stage,
                    "Tone": e.tone_used[:30],
                    "Status": e.send_status,
                    "Dry Run": "✓" if e.dry_run else "✗",
                    "Subject": e.email_subject[:50],
                }
                for e in all_entries
            ])

            # Filter
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                status_filter = st.multiselect(
                    "Filter by Status",
                    ["sent", "dry_run", "escalated", "error"],
                    default=["sent", "dry_run", "escalated", "error"],
                )
            with col_f2:
                stage_filter = st.multiselect(
                    "Filter by Stage",
                    [1, 2, 3, 4, 5],
                    default=[1, 2, 3, 4, 5],
                )

            filtered = df[
                df["Status"].isin(status_filter) &
                df["Stage"].isin(stage_filter)
            ]
            st.dataframe(filtered, use_container_width=True, hide_index=True)

            # Download
            csv = filtered.to_csv(index=False)
            st.download_button(
                "⬇️ Download Audit CSV",
                data=csv,
                file_name=f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )
        else:
            st.markdown("""
            <div class="info-box">
              📭 Audit trail is empty. Run the agent to populate it.
            </div>""", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Could not load audit trail: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<p style="text-align:center; color: #6e7681; font-size: 0.8rem;">
  Finance Credit Follow-Up Email Agent · Built for AI Enablement Internship Task 2 ·
  <a href="https://github.com" style="color:#58a6ff;">GitHub</a>
</p>""", unsafe_allow_html=True)
