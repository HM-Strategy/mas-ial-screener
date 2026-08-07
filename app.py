import streamlit as st
import pandas as pd
import hmac
from datetime import datetime
from scraper import scrape_mas_ial
from matcher import match_batch, match_single
from report import generate_screening_report, generate_single_search_report
from recipients import load_recipients, push_recipients_to_github, EMAIL_RE

st.set_page_config(
    page_title="HM Strategy - MAS Screening",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)


def _check_password() -> bool:
    if st.session_state.get("pw_ok", False):
        return True

    expected = st.secrets.get("app_password", "")
    if not expected:
        st.error("App password is not configured.")
        return False

    st.markdown(
        "<div style='height:24px'></div>"
        "<div style='background:#132852;color:#FFFFFF;font-weight:bold;"
        "font-size:22px;padding:14px 0;text-align:center;border-radius:6px'>"
        "HM Strategy | MAS Screening</div>"
        "<div style='text-align:center;color:#666666;margin-top:10px'>"
        "Restricted access &middot; enter the password to continue</div>",
        unsafe_allow_html=True,
    )

    with st.form("app_gate"):
        st.text_input(
            "Password",
            type="password",
            key="pw",
            placeholder="Password",
        )
        submitted = st.form_submit_button("Enter", type="primary", use_container_width=True)

    if submitted:
        if hmac.compare_digest(st.session_state.get("pw", ""), expected):
            st.session_state["pw_ok"] = True
            st.rerun()
        st.error("Incorrect password")
    return False


if not _check_password():
    st.stop()

_CUSTOM_CSS = """
<style>
    .stApp { background-color: #F8FAFC; }
    .main > div { padding: 0 0.5rem 0.5rem !important; }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1A366D 0%, #132852 100%);
        padding: 0.75rem 0;
    }
    section[data-testid="stSidebar"] .stMarkdown p { color: #FFFFFF !important; }
    section[data-testid="stSidebar"] .stCaption { color: #CBD5E1 !important; }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 { color: #FFFFFF !important; }
    section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.1); margin: 0.75rem 0; }
    section[data-testid="stSidebar"] .stButton button {
        background: rgba(255,255,255,0.1);
        border: 1px solid rgba(255,255,255,0.2);
        color: #FFFFFF !important;
        border-radius: 8px;
        width: 100%;
        font-weight: 500;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background: rgba(255,255,255,0.2);
    }
    section[data-testid="stSidebar"] .st-b7 { color: #FFFFFF !important; }

    .hm-header {
        background: linear-gradient(135deg, #132852 0%, #1A366D 100%);
        padding: 0.75rem 1.5rem;
        margin: 0 -0.5rem 1rem -0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .hm-header .hm-title {
        color: #FFFFFF !important;
        font-size: 1.4rem;
        font-weight: 700;
        letter-spacing: 0.03em;
    }
    .hm-header .hm-subtitle {
        color: rgba(255,255,255,0.7) !important;
        font-size: 0.8rem;
        margin-left: auto;
    }

    .stButton button[kind="primary"],
    .stButton button[data-testid="baseButton-primary"] {
        background: #3B82F6;
        border: none;
        border-radius: 8px;
        padding: 0.4rem 1.5rem;
        font-weight: 600;
    }
    .stButton button[kind="primary"]:hover {
        background: #2563EB;
        box-shadow: 0 4px 12px rgba(59,130,246,0.3);
    }

    .stTabs [data-baseweb="tab"] {
        padding: 0.4rem 1.25rem;
        font-weight: 500;
        font-size: 0.9rem;
        color: #475569;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: #3B82F6;
        color: #FFFFFF !important;
    }
    .stTabs [data-baseweb="tab"]:hover:not([aria-selected="true"]) {
        background: #F1F5F9;
        color: #1A366D;
    }

    [data-testid="stFileUploader"] {
        background: #FFFFFF;
        border-radius: 12px;
        border: 2px dashed #CBD5E1;
        padding: 1rem;
    }
    [data-testid="stFileUploader"]:hover { border-color: #3B82F6; }

    [data-testid="stDataFrame"] { border-radius: 8px; border: 1px solid #E2E8F0; }

    div[data-testid="stTextInput"] { max-width: 500px; }
    div[data-testid="stTextInput"] label { color: #1A366D !important; font-weight: 500; }
    div[data-testid="stTextInput"] input {
        background: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 8px;
        color: #0F172A !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #3B82F6;
        box-shadow: 0 0 0 2px rgba(59,130,246,0.2);
    }

    [data-testid="stMetricValue"] { color: #1A366D; font-weight: 700; }
    [data-testid="stMetricLabel"] { color: #64748B; }
    section[data-testid="stSidebar"] [data-testid="stMetricValue"] { color: #FFFFFF !important; }
    section[data-testid="stSidebar"] [data-testid="stMetricLabel"] { color: #CBD5E1 !important; }

    .hm-footer {
        margin-top: 2rem;
        padding: 0.75rem 0;
        border-top: 1px solid #E2E8F0;
        text-align: center;
        font-size: 0.75rem;
        color: #94A3B8;
    }

    div[data-testid="stSelectbox"] { max-width: 500px; }
    div[data-testid="stSelectbox"] label { color: #1A366D !important; font-weight: 500; }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        background: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 8px;
        color: #0F172A !important;
    }
    div[data-testid="stSelectbox"] ul[role="listbox"] li {
        color: #0F172A !important;
        background: #FFFFFF !important;
    }
    div[data-testid="stSelectbox"] ul[role="listbox"] li:hover {
        background: #F1F5F9 !important;
    }
    div[data-testid="stSelectbox"] ul[role="listbox"] li[aria-selected="true"] {
        background: #3B82F6 !important;
        color: #FFFFFF !important;
    }

</style>
"""

st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

st.markdown("""
<script>
(function() {
    function bindEnter() {
        var btn = document.querySelector('button[kind="primary"]');
        var fields = document.querySelectorAll(
            'div[data-testid="stTextInput"] input, '+
            'div[data-testid="stSelectbox"] input'
        );
        if (!btn) return;
        fields.forEach(function(f) {
            if (f && !f._eb) {
                f._eb = true;
                f.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        var pop = document.querySelector('[data-baseweb="popover"]');
                        if (!pop) btn.click();
                    }
                });
            }
        });
    }
    setInterval(bindEnter, 400);
})();
</script>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hm-header">
    <div class="hm-title">HM Strategy | MAS Investor Alert List Screening</div>
    <div class="hm-subtitle">Powered by MAS API</div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### HM Strategy")
    st.markdown("MAS Screening Tool")
    st.markdown("---")

    if "ial_data" not in st.session_state:
        with st.spinner("Loading MAS data..."):
            st.session_state.ial_data = scrape_mas_ial()
            st.session_state.last_refresh = datetime.now()
            st.session_state.ial_source = "fallback"

    st.metric("IAL Entries", len(st.session_state.ial_data))

    if st.button("Refresh Data"):
        with st.spinner("Refreshing..."):
            st.session_state.ial_data = scrape_mas_ial()
            st.session_state.last_refresh = datetime.now()
            st.rerun()

    st.markdown("---")
    st.caption("Powered by [MAS Investor Alert List](https://www.mas.gov.sg/investor-alert-list)")

if st.session_state.get("_search_result") is not None:
    st.session_state["_skip_bulk"] = True

tab1, tab2, tab3 = st.tabs(["Bulk Client Screening", "Individual Name Search", "Email Recipients"])

with tab1:
    skip_bulk = st.session_state.pop("_skip_bulk", False)
    uploaded_file = st.file_uploader(
        "Upload client list", key="bulk_upload",
        type=["csv", "xlsx", "xls", "json"],
        help="Accepted: CSV, Excel (.xlsx/.xls), JSON. Must have a column with entity/individual names.",
    )

    if uploaded_file is not None and not skip_bulk:
        filename = uploaded_file.name.lower()
        try:
            if filename.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            elif filename.endswith((".xlsx", ".xls")):
                df = pd.read_excel(uploaded_file)
            elif filename.endswith(".json"):
                df = pd.read_json(uploaded_file)
            else:
                st.error("Unsupported file format.")
                st.stop()
        except Exception as e:
            st.error(f"Failed to read file: {e}")
            st.stop()

        name_keywords = ["name", "client", "company", "entity", "organisation", "organization"]
        assoc_keywords = ["associate", "related", "linked", "alias", "connected"]

        name_col = next(
            (col for col in df.columns if any(kw in col.lower() for kw in name_keywords)),
            df.columns[0],
        )
        assoc_col = next(
            (col for col in df.columns if any(kw in col.lower() for kw in assoc_keywords)),
            None,
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Rows Loaded", len(df))
        c2.metric("Name Column", name_col[:12])
        if assoc_col:
            c3.metric("Associates", assoc_col[:12])

        with st.expander("Preview data"):
            st.dataframe(df.head(10), use_container_width=True)

        if st.button("Run Screening", type="primary"):
            client_names = df[name_col].dropna().astype(str).tolist()
            all_names = list(client_names)
            if assoc_col:
                assoc_names = df[assoc_col].dropna().astype(str).tolist()
                all_names.extend(assoc_names)

            with st.spinner(f"Screening {len(all_names)} names..."):
                matches = match_batch(all_names, st.session_state.ial_data)

            st.markdown("---")

            if not matches:
                st.markdown(
                    '<div style="background:#ECFDF5;border:1px solid #A7F3D0;border-radius:8px;padding:1.5rem;text-align:center;">'
                    "<strong>No matches found</strong> - all names are clear.</div>",
                    unsafe_allow_html=True,
                )
            else:
                flag_color = "#FEF2F2" if any(m["confidence"] == 100 for m in matches) else "#FFFBEB"
                flag_border = "#FECACA" if any(m["confidence"] == 100 for m in matches) else "#FDE68A"
                st.markdown(
                    f'<div style="background:{flag_color};border:1px solid {flag_border};border-radius:8px;padding:1.5rem;text-align:center;">'
                    f"<strong>{len(matches)} potential match(es)</strong> found. Review flagged names below.</div>",
                    unsafe_allow_html=True,
                )

                rows = []
                for m in matches:
                    entry = m["matched_entry"]
                    rows.append({
                        "Client Name": m["client_name"],
                        "Matched Alert": entry["name"],
                        "Confidence": m["confidence"],
                        "Match Type": m["match_type"].upper(),
                        "Alert Type": entry["type"],
                        "Date Added": entry["date_added"],
                    })

                results_df = pd.DataFrame(rows)

                def color_row(row):
                    if row["Confidence"] == 100:
                        return ["background-color: #C8E6C9"] * len(row)
                    elif row["Confidence"] >= 90:
                        return ["background-color: #FFF9C4"] * len(row)
                    else:
                        return ["background-color: #FFE0B2"] * len(row)

                st.dataframe(
                    results_df.style.apply(color_row, axis=1),
                    use_container_width=True,
                    hide_index=True,
                )

            st.markdown("---")
            pdf_bytes = generate_screening_report(matches, len(client_names))
            st.download_button(
                label="Download PDF Report",
                data=pdf_bytes,
                file_name=f"HM_Screening_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
            )

with tab2:
    if "suggestions" not in st.session_state:
        st.session_state.suggestions = []

    def _on_type():
        txt = st.session_state.si.strip()
        if len(txt) >= 2:
            st.session_state.suggestions = [
                e["name"] for e in st.session_state.ial_data
                if txt.lower() in e["name"].lower()
                or any(txt.lower() in a.lower() for a in e.get("aliases", []))
            ][:15]
        else:
            st.session_state.suggestions = []

    st.text_input("Entity name:", placeholder="Type at least 2 characters...",
                  key="si", on_change=_on_type)

    sel = st.selectbox(
        "Suggestions",
        [""] + st.session_state.suggestions,
        label_visibility="collapsed",
    )

    searched = st.button("Search", type="primary")

    _prev_result = st.session_state.pop("_search_result", None)
    result_to_show = None
    result_name = None

    if searched:
        st.session_state["_skip_bulk"] = True
        name = sel if sel else st.session_state.si.strip()
        if len(name) >= 2:
            with st.spinner("Searching..."):
                result_to_show = match_single(name, st.session_state.ial_data)
            result_name = name
            st.session_state["_search_result"] = (name, result_to_show)

    elif _prev_result is not None:
        result_name, result_to_show = _prev_result

    if result_to_show is not None:
        st.markdown("---")
        if result_to_show is None:
            st.markdown(
                '<div style="background:#ECFDF5;border:1px solid #A7F3D0;border-radius:12px;padding:2rem;text-align:center;">'
                f"<strong style='font-size:1.1rem;'>{result_name}</strong>"
                "<br>is <strong>NOT</strong> on the MAS Investor Alert List.</div>",
                unsafe_allow_html=True,
            )
            clean_result = {
                "match": False,
                "client_name": result_name,
                "matched_entry": None,
                "confidence": 0,
                "match_type": "none",
            }
            pdf_bytes = generate_single_search_report(clean_result)
            st.download_button(
                label="Download Search Report",
                data=pdf_bytes,
                file_name=f"HM_Search_{result_name[:30]}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
            )
        else:
            entry = result_to_show["matched_entry"]
            confidence = result_to_show["confidence"]

            if confidence == 100:
                bg = "#FEF2F2"
                border = "#FECACA"
                label = "IS FLAGGED"
            elif confidence >= 90:
                bg = "#FFFBEB"
                border = "#FDE68A"
                label = "HIGH-CONFIDENCE MATCH"
            else:
                bg = "#FFF7ED"
                border = "#FED7AA"
                label = "MEDIUM-CONFIDENCE MATCH"

            extra_row = ""
            if entry.get("description"):
                extra_row = (
                    '<tr><td style="padding:0.5rem;color:#64748B;">Description</td>'
                    f'<td style="padding:0.5rem;font-weight:600;">{entry["description"]}</td></tr>'
                )

            st.markdown(
                f'<div style="background:{bg};border:1px solid {border};border-radius:12px;padding:1.5rem;margin-bottom:1rem;">'
                f'<div style="margin-bottom:1rem;">'
                f'<strong style="font-size:1.1rem;color:#991B1B;">{result_name} - {label}</strong>'
                f"</div>"
                f'<table style="width:100%;border-collapse:collapse;">'
                f'<tr><td style="padding:0.5rem;color:#64748B;">Matched Alert</td><td style="padding:0.5rem;font-weight:600;">{entry["name"]}</td></tr>'
                f'<tr><td style="padding:0.5rem;color:#64748B;">Confidence</td><td style="padding:0.5rem;font-weight:600;">{confidence}% ({result_to_show["match_type"].upper()})</td></tr>'
                f'<tr><td style="padding:0.5rem;color:#64748B;">Type</td><td style="padding:0.5rem;font-weight:600;">{entry["type"]}</td></tr>'
                f'<tr><td style="padding:0.5rem;color:#64748B;">Date Added</td><td style="padding:0.5rem;font-weight:600;">{entry["date_added"]}</td></tr>'
                f'{extra_row}'
                f'<tr><td style="padding:0.5rem;color:#64748B;">Aliases</td><td style="padding:0.5rem;font-weight:600;">{(', '.join(entry["aliases"]) if entry["aliases"] else "None")}</td></tr>'
                f"</table></div>",
                unsafe_allow_html=True,
            )

            pdf_bytes = generate_single_search_report(result_to_show)
            st.download_button(
                label="Download Search Report",
                data=pdf_bytes,
                file_name=f"HM_Search_{result_name[:30]}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
            )

with tab3:
    st.markdown("### Email Recipients")
    st.caption("Who receives the automated MAS IAL notification email on each run.")

    current = load_recipients()
    st.session_state.setdefault("recipients_text", "\n".join(current))

    st.text_area(
        "Recipients (one email per line)",
        key="recipients_text",
        height=200,
        help="One email address per line. Lines starting with # are ignored.",
    )

    def _parse_emails(text: str) -> tuple[list[str], list[str]]:
        valid, invalid = [], []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            stripped = stripped.split("#")[0].strip()
            if not stripped:
                continue
            if EMAIL_RE.match(stripped):
                if stripped not in valid:
                    valid.append(stripped)
            else:
                invalid.append(stripped)
        return valid, invalid

    if st.button("Save to repository", type="primary"):
        valid, invalid = _parse_emails(st.session_state.recipients_text)
        if not valid:
            st.error("Enter at least one valid email address.")
        else:
            if invalid:
                st.warning(f"Ignoring invalid line(s): {', '.join(invalid)}")
            ok, msg = push_recipients_to_github(valid)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    with st.expander("How this works"):
        st.markdown(
            "Recipients are stored in `data/recipients.txt` in the repository. "
            "The GitHub Actions workflow reads this file each run and emails every address listed. "
            "Saving here writes the file and pushes it to the repository."
        )

st.markdown('<div class="hm-footer">This tool screens names against the MAS Investor Alert List. Results are preliminary and do not constitute legal or compliance advice. Human verification is recommended for all flagged matches.</div>', unsafe_allow_html=True)
