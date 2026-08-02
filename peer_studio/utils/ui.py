import streamlit as st
import os


def apply_custom_theme():
    """Applies global CSS stylesheet overrides for a premium, clean dashboard aesthetic.

    Overrides typography, cards, tables, inputs, buttons, scrollbars, and
    sidebar margins.
    """
    if os.path.exists("assets/logo_horizontal.png"):
        st.logo("assets/logo_horizontal.png")

    st.markdown(
        """<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;500;600;700&family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20,400,0,0&display=swap" rel="stylesheet"><style>
    html, body, [class*="css"], .stApp, .stAppHeader, .stAppViewContainer { 
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important; 
        color: #1A1A1A !important; 
        background-color: #FFFFFF !important; 
    }
    
    /* Enforce outline icons size consistency */
    .material-symbols-outlined {
        font-size: 18px !important;
        font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 20 !important;
        vertical-align: middle !important;
    }
    
    /* 1. Spacing between major sections & 13. Page title icons sizes */
    h1, .h1-style { font-family: 'Outfit', sans-serif !important; font-size: 32px !important; font-weight: 700 !important; color: #1A1A1A !important; margin-top: 0.5rem !important; margin-bottom: 0.25rem !important; line-height: 1.2 !important; } 
    h1 .material-symbols-outlined { font-size: 28px !important; }
    h2, .h2-style { font-family: 'Outfit', sans-serif !important; font-size: 24px !important; font-weight: 600 !important; color: #1A1A1A !important; margin-top: 2rem !important; margin-bottom: 1rem !important; line-height: 1.3 !important; } 
    h3, .h3-style { font-family: 'Outfit', sans-serif !important; font-size: 20px !important; font-weight: 600 !important; color: #1A1A1A !important; margin-top: 1.5rem !important; margin-bottom: 0.75rem !important; line-height: 1.4 !important; } 
    .section-label { font-size: 16px !important; font-weight: 500 !important; color: #1A1A1A !important; margin-bottom: 0.5rem !important; } 
    
    /* 10. Paragraph and text line-height */
    p, span, label, li, td, th { font-size: 14.5px !important; font-weight: 400 !important; color: #666666 !important; line-height: 1.6 !important; } 
    
    /* FIX: Force white text & icons inside BaseWeb tags (multiselect pills) */
    div[data-baseweb="tag"], span[data-baseweb="tag"] {
        background-color: #2F7D4A !important; /* Green pill background */
    }
    div[data-baseweb="tag"] *, span[data-baseweb="tag"] * {
        color: #FFFFFF !important; /* Force white text for all child elements */
        fill: #FFFFFF !important;  /* Force white color for close 'X' icon */
    }

    .caption-text, .stMarkdown caption { font-size: 12px !important; color: #8F8F8F !important; } 
    
    /* 4. Sidebar active accent bar and grouping gap */
    [data-testid="stSidebar"] { background-color: #FAFAFA !important; border-right: 1px solid #EAEAEA !important; } 
    [data-testid="stSidebar"] * { background-color: #FAFAFA !important; } 
    /* 4. Sidebar logo sizing fix */

    [data-testid="stSidebarHeader"] {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
        height: auto !important;
        min-height: 60px !important;
    }

    [data-testid="stLogo"],
    [data-testid="stLogoContainer"],
    div[data-testid="stSidebarHeader"] > div {
        height: 60px !important;
        min-height: 60px !important;
        max-height: none !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
    }

    [data-testid="stLogo"] img,
    [data-testid="stLogoContainer"] img,
    div[data-testid="stSidebarHeader"] img {
        height: 45px !important;
        max-height: 45px !important;
        width: auto !important;
        object-fit: contain !important;
    }
    [data-testid="stSidebarNav"] { padding-top: 0.5rem !important; } 
    [data-testid="stSidebarNav"] ul { gap: 2px !important; }
    [data-testid="stSidebarNav"] div { margin-top: 0.25rem !important; margin-bottom: 0.25rem !important; }
    [data-testid="stSidebarNavItems"] li { margin-bottom: 2px !important; } 
    [data-testid="stSidebarNavItems"] li a { padding: 5px 12px !important; border-radius: 8px !important; border-left: 4px solid transparent !important; transition: all 0.2s ease !important; color: #666666 !important; font-size: 13.5px !important; font-weight: 500 !important; } 
    [data-testid="stSidebarNavItems"] li a:hover { background-color: #F5F5F5 !important; color: #1A1A1A !important; } 
    [data-testid="stSidebar"] [data-testid="stSidebarNavItems"] li a[data-selected="true"],
    [data-testid="stSidebar"] [data-testid="stSidebarNavItems"] li a[aria-current="page"] {
        background-color: #EBF7EE !important;
        color: #2F7D4A !important;
        border-left: 4px solid #2F7D4A !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] [data-testid="stSidebarNavItems"] li a[data-selected="true"] *,
    [data-testid="stSidebar"] [data-testid="stSidebarNavItems"] li a[aria-current="page"] * {
        color: #2F7D4A !important;
        background-color: #EBF7EE !important;
    }
    
    /* 5. Card soft shadows and bright borders */
    .card, .metric-card, .completed-card, .running-card, .wizard-step-body { background-color: #FFFFFF !important; border: 1px solid #EAEAEA !important; border-radius: 12px !important; padding: 20px 24px !important; margin-bottom: 20px !important; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02) !important; transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease !important; } 
    .card:hover, .metric-card:hover, .completed-card:hover, .running-card:hover { border-color: #5E3A87 !important; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important; } 
    
    /* 2. Dashboard metrics spacing */
    .metric-title { margin-bottom: 8px !important; color: #666666 !important; font-size: 13px !important; }
    .metric-value { margin-top: 6px !important; margin-bottom: 6px !important; font-size: 1.55rem !important; }
    
    /* 9. Centering the wizard number circle */
    .step-header-card { background-color: #FAFAFA !important; border: 1px solid #EAEAEA !important; border-radius: 12px !important; padding: 16px 20px !important; margin-top: 10px !important; margin-bottom: 20px !important; display: flex !important; align-items: center !important; gap: 16px !important; box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important; } 
    .step-number-circle { background-color: #5E3A87 !important; color: #FFFFFF !important; border-radius: 50% !important; width: 32px !important; height: 32px !important; display: inline-flex !important; align-items: center !important; justify-content: center !important; font-weight: 600 !important; font-size: 14px !important; line-height: 1 !important; flex-shrink: 0 !important; } 
    .step-header-content { display: flex !important; flex-direction: column !important; justify-content: center !important; } 
    .step-card-title { font-family: 'Outfit', sans-serif !important; font-size: 16px !important; font-weight: 600 !important; color: #1A1A1A !important; margin: 0 !important; line-height: 1.2 !important; } 
    .step-card-subtitle { font-size: 13px !important; color: #666666 !important; margin: 2px 0 0 0 !important; line-height: 1.2 !important; } 
    
    /* 7. Button Consistency */
    div[data-testid="stButton"] button, .stButton > button { border-radius: 8px !important; padding: 6px 16px !important; font-weight: 500 !important; font-size: 14px !important; height: 38px !important; transition: all 0.2s ease !important; } 
    div[data-testid="stButton"] button span[data-testid="stMarkdownContainer"] { display: inline-flex !important; align-items: center !important; gap: 6px !important; }
    div[data-testid="stButton"] button span[data-testid="stMarkdownContainer"] .material-symbols-outlined { font-size: 18px !important; }
    
    /* Primary Green Button */
    div[data-testid="stButton"] button[kind="primary"], .stButton > button.btn-primary { 
        background-color: #2F7D4A !important; 
        color: #FFFFFF !important; 
        border: 1px solid #2F7D4A !important; 
    } 
    div[data-testid="stButton"] button[kind="primary"] *, .stButton > button.btn-primary * { 
        color: #FFFFFF !important; 
        fill: #FFFFFF !important; 
    }
    div[data-testid="stButton"] button[kind="primary"]:hover, .stButton > button.btn-primary:hover { background-color: #27693E !important; border-color: #27693E !important; } 
    
    /* Secondary Outlined button */
    div[data-testid="stButton"] button[kind="secondary"], .stButton > button.btn-secondary { background-color: #FFFFFF !important; color: #1A1A1A !important; border: 1px solid #EAEAEA !important; } 
    div[data-testid="stButton"] button[kind="secondary"]:hover, .stButton > button.btn-secondary:hover { border-color: #666666 !important; background-color: #FAFAFA !important; } 
    
    /* 8. Input alignment & Spacing */
    label[data-testid="stWidgetLabel"] p { margin-bottom: 6px !important; font-weight: 500 !important; color: #1A1A1A !important; }
    div[data-testid="stFormHelp"] { margin-top: 4px !important; margin-bottom: 20px !important; }
    div[data-baseweb="input"], div[data-baseweb="select"], .stNumberInput input, .stTextInput input { border-radius: 8px !important; border: 1px solid #EAEAEA !important; transition: border-color 0.2s ease !important; } 
    div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within { border-color: #5E3A87 !important; } 
    
    /* 6. Table Density & spacing */
    div[data-testid="stTable"] table, div[data-testid="stDataFrame"] { border: 1px solid #EAEAEA !important; border-radius: 12px !important; overflow: hidden !important; margin-top: 20px !important; } 
    div[data-testid="stTable"] tr:nth-child(even) { background-color: #FAFAFA !important; } 
    div[data-testid="stTable"] tr:hover { background-color: #F5F5F5 !important; } 
    div[data-testid="stTable"] th { font-weight: 600 !important; color: #1A1A1A !important; background-color: #F5F5F5 !important; border-bottom: 2px solid #EAEAEA !important; } 
    div[data-testid="stTable"] td { padding: 6px 16px !important; line-height: 1.2 !important; }
    
    .badge-custom { padding: 4px 12px !important; border-radius: 999px !important; font-size: 12px !important; font-weight: 600 !important; display: inline-flex !important; align-items: center !important; line-height: 1 !important; } 
    .badge-green { background-color: #EBF7EE !important; color: #2F7D4A !important; border: 1px solid #D5EEDC !important; } 
    .badge-gold { background-color: #FEF8EC !important; color: #C48A1D !important; border: 1px solid #FDF0D5 !important; } 
    .badge-plum { background-color: #F6EFFF !important; color: #5E3A87 !important; border: 1px solid #EAD8FC !important; } 
    .badge-red { background-color: #FDF2F2 !important; color: #D12424 !important; border: 1px solid #FBD5D5 !important; } 
    .badge-gray { background-color: #F5F5F5 !important; color: #666666 !important; border: 1px solid #E7E7E7 !important; } 
    
    /* 10. Spacing between report sections & report box styling */
    .report-box { background-color: #FFFFFF !important; border: 1px solid #EAEAEA !important; border-radius: 12px !important; padding: 24px !important; margin-top: 15px !important; box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important; } 
    .report-box h1, .report-box h2, .report-box h3 { margin-top: 1.75rem !important; margin-bottom: 0.75rem !important; }
    .report-box table { margin-top: 20px !important; }
    
    /* 11. Success / Warning Messages */
    div[data-testid="stAlert"] { border-radius: 12px !important; border: 1px solid #EAEAEA !important; border-left: 3px solid #2F7D4A !important; padding: 12px 18px !important; } 
    div[data-testid="stAlert"] [data-testid="stNotificationContent"] { display: flex !important; align-items: center !important; }
    div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p { color: #1A1A1A !important; margin: 0 !important; } 
    
    .insight-box { background-color: #FEF8EC !important; border: 1px solid #FDF0D5 !important; border-left: 3px solid #C48A1D !important; border-radius: 12px !important; padding: 16px 20px !important; margin-bottom: 20px !important; } 
    .ai-banner-box { background-color: #F6EFFF !important; border: 1px solid #EAD8FC !important; border-left: 3px solid #5E3A87 !important; border-radius: 12px !important; padding: 16px 20px !important; margin-bottom: 20px !important; } 
    
    /* 14. Bottom padding */
    .page-footer-spacer { height: 80px !important; }
    </style>""",
        unsafe_allow_html=True,
    )

    import inspect
    is_create = False
    for frame_info in inspect.stack():
        if "create.py" in frame_info.filename:
            is_create = True
            break
    if not is_create:
        st.markdown(
            '<style>'
            '.floating-fab {'
            '    position: fixed !important;'
            '    bottom: 24px !important;'
            '    right: 24px !important;'
            '    background-color: #2F7D4A !important;'
            '    color: #FFFFFF !important;'
            '    padding: 12px 24px !important;'
            '    border-radius: 50px !important;'
            '    box-shadow: 0 4px 16px rgba(47, 125, 74, 0.4) !important;'
            '    text-decoration: none !important;'
            '    display: inline-flex !important;'
            '    align-items: center !important;'
            '    gap: 8px !important;'
            '    font-weight: 600 !important;'
            '    font-size: 14px !important;'
            '    z-index: 999999 !important;'
            '    transition: transform 0.2s ease, box-shadow 0.2s ease !important;'
            '    border: 1px solid #27693E !important;'
            '}'
            '.floating-fab:hover {'
            '    transform: translateY(-2.5px) !important;'
            '    box-shadow: 0 6px 20px rgba(47, 125, 74, 0.5) !important;'
            '    color: #FFFFFF !important;'
            '    background-color: #27693E !important;'
            '}'
            '.floating-fab span {'
            '    color: #FFFFFF !important;'
            '}'
            '</style>'
            '<a href="/Create_Experiment" target="_self" class="floating-fab">'
            '    <span class="material-symbols-outlined" style="color: #FFFFFF !important; margin-right: 4px;">add</span>'
            '    <span style="color: #FFFFFF !important; font-weight: 600 !important;">New Experiment</span>'
            '</a>',
            unsafe_allow_html=True
        )


def render_header(title: str, subtitle: str, icon_name: str = None):
    """Renders a unified page header with Title, Subtitle, and optional Google

    Material Symbol.
    """
    icon_html = ""
    if icon_name:
        icon_html = f'<span class="material-symbols-outlined" style="font-size: 28px; color: #5E3A87; vertical-align: middle; margin-right: 8px;">{icon_name}</span>'

    st.markdown(
        f"""
        <div style="margin-bottom: 32px;">
            <h1 style="display: flex; align-items: center; gap: 4px; margin: 0;">
                {icon_html}
                <span class="h1-style" style="vertical-align: middle;">{title}</span>
            </h1>
            <p style="margin: 4px 0 0 0; color: #666666; font-size: 14.5px;">{subtitle}</p>
        </div>
    """,
        unsafe_allow_html=True,
    )


def render_step_header(number: int, title: str, subtitle: str = None):
    """Renders a beautifully aligned wizard step header.

    Fixes the vertical alignment shifting issue.
    """
    subtitle_html = ""
    if subtitle:
        subtitle_html = f'<div class="step-card-subtitle">{subtitle}</div>'

    st.markdown(
        f"""
        <div class="step-header-card">
            <div class="step-number-circle">{number}</div>
            <div class="step-header-content">
                <div class="step-card-title">{title}</div>
                {subtitle_html}
            </div>
        </div>
    """,
        unsafe_allow_html=True,
    )


def render_empty_state(icon_name: str, title: str, description: str):
    """Renders a premium empty state container with an outline icon, title, and

    description.
    """
    st.markdown(
        f"""
        <div style="border: 1px dashed #E7E7E7; border-radius: 12px; padding: 40px 20px; text-align: center; background-color: #FAFAFA; margin: 20px 0;">
            <span class="material-symbols-outlined" style="font-size: 48px; color: #8F8F8F; margin-bottom: 12px;">{icon_name}</span>
            <h3 style="margin: 0 0 8px 0; font-size: 18px; font-weight: 600; color: #1A1A1A;">{title}</h3>
            <p style="margin: 0; color: #666666; font-size: 14px; max-width: 400px; display: inline-block;">{description}</p>
        </div>
    """,
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> str:
    """Returns the HTML string for a unified pill badge based on status."""
    s = status.strip().lower()
    if s in ["completed", "complete", "success", "pass", "active", "indexed"]:
        return f'<span class="badge-custom badge-green">{status}</span>'
    elif s in ["running", "executing", "processing"]:
        return f'<span class="badge-custom badge-plum">{status}</span>'
    elif s in ["pending", "queued", "warning", "recommendation"]:
        return f'<span class="badge-custom badge-gold">{status}</span>'
    elif s in ["failed", "fail", "error", "cancelled", "not indexed"]:
        return f'<span class="badge-custom badge-red">{status}</span>'
    else:
        return f'<span class="badge-custom badge-gray">{status}</span>'


def inject_footer_spacer():
    """Ensures that components do not touch page bottom edges."""
    st.markdown(
        '<div class="page-footer-spacer"></div>', unsafe_allow_html=True
    )