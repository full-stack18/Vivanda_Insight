import base64
from pathlib import Path

import streamlit as st


def aplicar_marca_vivanda():
    """Aplica una identidad visual inspirada en los tonos frescos de Vivanda."""
    logo_path = Path(__file__).parent / "assets" / "logo_vivanda.png"
    if not logo_path.exists():
        st.error(
            "No encontré el logo oficial. Guarda el archivo como "
            "vivanda_insight/assets/logo_vivanda.png."
        )
        st.stop()

    logo_base64 = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    st.markdown(
        """
        <style>
        :root {
            --vivanda-green: #83bd91;
            --vivanda-deep-green: #183b2c;
            --vivanda-coral: #e98982;
            --vivanda-cream: #f4f2e9;
        }

        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(ellipse at 4% 0%, rgba(91, 139, 101, .16), transparent 34%),
                #111713;
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #18231d 0%, #151b17 100%);
            border-right: 1px solid rgba(131, 189, 145, .22);
        }

        .vivanda-brandbar {
            display: flex;
            align-items: center;
            gap: 1.1rem;
            padding: 1.15rem 1.4rem;
            margin: .2rem 0 1.1rem 0;
            border: 1px solid rgba(131, 189, 145, .25);
            border-radius: 18px;
            background: linear-gradient(105deg, #203a2c 0%, #1b2921 58%, #242722 100%);
            box-shadow: 0 12px 32px rgba(0, 0, 0, .18);
        }

        .vivanda-official-logo {
            display: block;
            flex: 0 0 auto;
            width: 205px;
            height: 76px;
            padding: 8px 13px;
            box-sizing: border-box;
            object-fit: contain;
            border-radius: 13px;
            background: #f4f2e9;
        }

        .vivanda-brand-name {
            color: var(--vivanda-cream);
            font-size: 1.65rem;
            font-weight: 750;
            letter-spacing: .01em;
            line-height: 1.1;
        }

        .vivanda-brand-name span {
            color: #a7d2ad;
            font-weight: 500;
        }

        .vivanda-brand-subtitle {
            color: #c9d4ca;
            font-size: .88rem;
            margin-top: .3rem;
        }

        .vivanda-brand-chip {
            margin-left: auto;
            padding: .48rem .75rem;
            border: 1px solid rgba(233, 137, 130, .52);
            border-radius: 999px;
            color: #f3c3bd;
            font-size: .72rem;
            font-weight: 650;
            letter-spacing: .07em;
            white-space: nowrap;
        }

        [data-testid="stMetric"] {
            padding: 1rem 1.1rem;
            border: 1px solid #303c33;
            border-top: 3px solid var(--vivanda-green);
            border-radius: 15px;
            background: linear-gradient(145deg, #1d2721, #191f1b);
        }

        [data-testid="stMetricLabel"] {
            color: #cbd5cc;
        }

        [data-testid="stMetricValue"] {
            color: #f4f2e9;
        }

        [data-testid="stAlert"] {
            border-color: rgba(131, 189, 145, .38);
            background: rgba(43, 77, 54, .25);
        }

        .stButton > button {
            border-color: rgba(131, 189, 145, .42);
            border-radius: 10px;
            transition: border-color .15s ease, background .15s ease;
        }

        .stButton > button:hover {
            border-color: var(--vivanda-coral);
            color: #f4f2e9;
        }

        @media (max-width: 700px) {
            .vivanda-brandbar { padding: .9rem; }
            .vivanda-official-logo { width: 155px; height: 62px; }
            .vivanda-brand-name { font-size: 1.35rem; }
            .vivanda-brand-chip { display: none; }
        }
        </style>

        <div class="vivanda-brandbar">
            <img class="vivanda-official-logo"
                 src="data:image/png;base64,__LOGO_BASE64__"
                 alt="Logo oficial de Vivanda">
            <div class="vivanda-brand-copy">
                <div class="vivanda-brand-name"><span>INSIGHT</span></div>
                <div class="vivanda-brand-subtitle">Inteligencia comercial · Piensa fresco</div>
            </div>
            <div class="vivanda-brand-chip">DEMO ACADÉMICA</div>
        </div>
        """.replace("__LOGO_BASE64__", logo_base64),
        unsafe_allow_html=True,
    )
