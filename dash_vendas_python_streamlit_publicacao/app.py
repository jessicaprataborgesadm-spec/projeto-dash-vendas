from pathlib import Path
import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Projeto Dash Vendas — interface visual baseada na referência enviada.
# A camada visual lê somente CSVs locais; não altera fontes, SQLs ou previsões.

st.set_page_config(
    page_title="Dash Vendas | Inteligência Comercial",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
CUTOFF = pd.Timestamp("2018-08-22")

FILES = {
    "historico": "base_treinamento_faturamento_teste.csv",
    "baseline_julho": "19_previsoes_baseline_teste.csv",
    "comparacao_julho": "20_previsoes_random_forest_teste.csv",
    "validacao_temporal": "21_resultado_validacao_temporal.csv",
    "janela_recente": "22_resultado_janela_recente.csv",
    "previsao_30_dias": "23_previsao_30_dias_corte_22_08.csv",
}

# Paleta futurista em grafite, azul-marinho, lilás escuro e rosa neon.
BG = "#F1F2F6"
PANEL = "#FFFFFF"
PANEL_ALT = "#F8F5FA"
BORDER = "#E1DCE8"
PURPLE = "#7956A6"
CYAN = "#FF4F9A"
ORANGE = "#B56F9B"
PINK = "#F05A9D"
BLUE = "#263D63"
YELLOW = "#9C7DA8"
TEXT = "#292638"
MUTED = "#746D7D"
GRID = "#E7E2EC"

st.markdown(
    f"""
    <style>
      :root {{
        --bg:{BG}; --panel:{PANEL}; --panel-alt:{PANEL_ALT}; --border:{BORDER};
        --purple:{PURPLE}; --cyan:{CYAN}; --orange:{ORANGE}; --pink:{PINK};
        --text:{TEXT}; --muted:{MUTED}; --grid:{GRID};
      }}
      html, body, [class*="css"] {{ font-family: 'Inter', 'Segoe UI', system-ui, sans-serif; }}
      .stApp {{ background: var(--bg); color: var(--text); }}
      [data-testid="stHeader"] {{ background: rgba(241,242,246,.94); }}
      [data-testid="stMainBlockContainer"] {{ max-width: 1600px; padding: 1.35rem 2rem 2.4rem; }}
      h1, h2, h3 {{ color: var(--text) !important; letter-spacing: -.035em; }}
      h2 {{ font-size: 1.32rem !important; margin-top: .3rem !important; }}
      h3 {{ font-size: 1.03rem !important; }}
      p, label, li, [data-testid="stMarkdownContainer"] {{ color: var(--text); }}
      [data-testid="stMain"] {{ color: var(--text); }}
      [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #171A25 0%, #211D2B 58%, #172033 100%);
        border-right: 1px solid rgba(168,139,216,.19);
      }}
      [data-testid="stSidebar"] * {{ color: #F4EDF6; }}
      [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{ color: #B6AFC0 !important; }}
      [data-testid="stSidebar"] hr {{ border-color: rgba(168,139,216,.18); margin: 1.1rem 0; }}
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{ color: #BDB4C7; }}
      [data-testid="stSidebar"] div[role="radiogroup"] {{ gap: .45rem; }}
      [data-testid="stSidebar"] label[data-baseweb="radio"] {{
        border: 1px solid transparent; border-radius: 12px; padding: .62rem .75rem;
        background: rgba(255,255,255,.025); transition: all .15s ease;
      }}
      [data-testid="stSidebar"] label[data-baseweb="radio"]:hover {{
        background: rgba(168,139,216,.11); border-color: rgba(168,139,216,.26);
      }}
      [data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) {{
        background: linear-gradient(100deg, rgba(168,139,216,.22), rgba(255,95,162,.10));
        border-color: rgba(168,139,216,.54); box-shadow: inset 3px 0 0 var(--purple);
      }}
      [data-testid="stSidebar"] label[data-baseweb="radio"] p {{ color: #F4EDF6 !important; font-weight: 650; }}
      [data-testid="stSidebar"] .stButton button {{ background:#292436; color:#F8F1F7; border:1px solid #494054; }}
      .hero {{
        position:relative; overflow:hidden; padding:28px 31px 25px; margin-bottom:21px;
        background:linear-gradient(112deg,#1A2031 0%,#30253D 53%,#34243A 100%);
        border:1px solid rgba(168,139,216,.25); border-radius:22px;
        box-shadow:0 18px 42px rgba(0,0,0,.20);
      }}
      .hero:after {{ content:''; position:absolute; right:-65px; top:-155px; width:330px; height:330px;
        border:1px solid rgba(255,255,255,.12); border-radius:50%;
        box-shadow:0 0 0 30px rgba(255,255,255,.035),0 0 0 65px rgba(255,255,255,.025),0 0 0 100px rgba(255,255,255,.016); }}
      .eyebrow {{ text-transform:uppercase; font-size:.67rem; font-weight:800; letter-spacing:.18em; color:{CYAN}; margin-bottom:8px; }}
      .hero-title {{ font-size:clamp(1.75rem,2.9vw,2.55rem); font-weight:850; line-height:1.08; letter-spacing:-.055em; color:#FFF; margin:0 0 10px; }}
      .hero-subtitle {{ font-size:.91rem; color:#DBD2E3; max-width:900px; line-height:1.55; margin-bottom:15px; }}
      .hero-meta {{ font-size:.74rem; color:#DBD2E3; font-weight:600; }}
      .status-line {{ display:flex; flex-wrap:wrap; gap:7px; margin-top:3px; }}
      .status-chip {{ display:inline-block; border-radius:999px; padding:5px 10px; font-size:.68rem; font-weight:750;
        border:1px solid rgba(255,255,255,.17); background:rgba(255,255,255,.07); color:#FAF0F6; }}
      .section-kicker {{ color:{PURPLE}; text-transform:uppercase; font-size:.66rem; font-weight:850; letter-spacing:.14em; margin-bottom:4px; }}
      .section-title {{ font-size:1.3rem; font-weight:850; color:{TEXT}; letter-spacing:-.04em; margin-bottom:4px; }}
      .section-subtitle {{ color:{MUTED}; font-size:.83rem; margin-bottom:14px; line-height:1.5; }}
      .kpi-card {{ background:linear-gradient(145deg,#FFFFFF 0%,#F8F5FA 100%); border:1px solid {BORDER}; border-radius:16px;
        padding:17px 18px 15px; min-height:124px; height:100%; box-shadow:0 9px 24px rgba(0,0,0,.12); position:relative; overflow:hidden; }}
      .kpi-card:before {{ content:''; position:absolute; top:0; left:0; right:0; height:3px; background:linear-gradient(90deg,{PURPLE},{CYAN}); }}
      .kpi-label {{ font-size:.7rem; color:#756C80; font-weight:750; letter-spacing:.055em; margin-bottom:11px; }}
      .kpi-value {{ color:#292638; font-size:clamp(1.12rem,1.6vw,1.62rem); line-height:1.14; font-weight:850; letter-spacing:-.045em; margin-bottom:9px; overflow-wrap:anywhere; }}
      .kpi-note {{ color:#776F80; font-size:.69rem; line-height:1.4; }}
      .insight-card {{ background:linear-gradient(145deg,#FFFFFF,#F8F5FA); border:1px solid {BORDER}; border-radius:15px; padding:16px 17px; min-height:105px; }}
      .insight-title {{ color:#292638; font-weight:800; font-size:.86rem; margin-bottom:7px; }}
      .insight-text {{ color:#675F70; font-size:.78rem; line-height:1.55; }}
      .chart-shell {{ background:linear-gradient(145deg,#FFFFFF,#F8F5FA); border:1px solid {BORDER}; border-radius:16px; padding:11px 11px 3px; box-shadow:0 9px 25px rgba(0,0,0,.13); }}
      .panel {{ background:linear-gradient(145deg,#FFFFFF,#F8F5FA); border:1px solid {BORDER}; border-radius:16px; padding:17px 19px; }}
      .tiny-note {{ color:#B5AABD; font-size:.74rem; line-height:1.5; }}
      .footer {{ color:#777080; font-size:.69rem; text-align:center; padding-top:22px; line-height:1.7; }}
      div[data-testid="stMetric"] {{ background:linear-gradient(145deg,#FFFFFF,#F8F5FA); border:1px solid {BORDER}; border-radius:14px; padding:14px 16px; }}
      div[data-testid="stMetricLabel"] {{ color:#756C80; }}
      div[data-testid="stMetricValue"] {{ color:#292638; font-weight:800; }}
      [data-testid="stAlert"] {{
        background:#E5E6ED !important; color:#292638 !important;
        border:1px solid #D6D7E0 !important; border-radius:12px;
      }}
      [data-testid="stAlert"] * {{ color:#292638 !important; }}
      div[data-testid="stExpander"] {{ border:1px solid {BORDER}; border-radius:12px; background:#FFFFFF; color:#292638; }}
      div[data-testid="stExpander"] * {{ color:#292638; }}
      div[data-testid="stDataFrame"], div[data-testid="stTable"] {{
        border:1px solid #D6D7E0 !important; border-radius:12px; overflow:hidden;
        background:#E5E6ED !important;
      }}
      div[data-testid="stDataFrame"] > div, div[data-testid="stTable"] > div {{
        background:#E5E6ED !important;
      }}
      [data-testid="stDateInput"] input, [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
        background:#FFFFFF; color:#292638; border-color:{BORDER}; border-radius:9px;
      }}
      .stButton button {{ border-radius:10px; font-weight:750; }}
      @media (max-width:850px) {{ [data-testid="stMainBlockContainer"] {{ padding:1rem 1rem 2rem; }} .hero {{ padding:22px 19px; }} }}
    </style>
    """,
    unsafe_allow_html=True,
)


def load_csv(filename: str):
    path = BASE_DIR / filename
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except Exception as exc:
        st.warning(f"Não foi possível ler **{filename}**: {exc}")
        return None


def brl(value) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(value) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    return f"{float(value):.2f}%".replace(".", ",")


def number(value, digits=2) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    return f"{float(value):,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def integer(value) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    return f"{int(value):,}".replace(",", ".")


def format_table(
    df: pd.DataFrame,
    currency_columns=(),
    percentage_columns=(),
    percentage_point_columns=(),
    integer_columns=(),
):
    """Aplica formato brasileiro às unidades exibidas nas tabelas, sem alterar os dados."""
    formatters = {}

    for column in currency_columns:
        if column in df.columns:
            formatters[column] = brl

    for column in percentage_columns:
        if column in df.columns:
            formatters[column] = pct

    for column in percentage_point_columns:
        if column in df.columns:
            formatters[column] = (
                lambda value: f"{number(value)} p.p."
                if value is not None and pd.notna(value)
                else "N/D"
            )

    for column in integer_columns:
        if column in df.columns:
            formatters[column] = integer

    return df.style.format(formatters, na_rep="N/D")


def metrics_html(label: str, value: str, note: str = ""):
    note_html = f'<div class="kpi-note">{note}</div>' if note else ""
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div>{note_html}</div>',
        unsafe_allow_html=True,
    )


def section_header(kicker: str, title: str, subtitle: str = ""):
    st.markdown(
        f'<div class="section-kicker">{kicker}</div><div class="section-title">{title}</div><div class="section-subtitle">{subtitle}</div>',
        unsafe_allow_html=True,
    )


def calculate_metrics(df: pd.DataFrame, actual_col: str, forecast_col: str):
    values = df[[actual_col, forecast_col]].apply(pd.to_numeric, errors="coerce").dropna()
    if values.empty:
        return None
    actual, forecast = values[actual_col], values[forecast_col]
    abs_error = (actual - forecast).abs()
    denominator = actual.abs().sum()
    return {
        "mae": abs_error.mean(),
        "rmse": math.sqrt(((actual - forecast) ** 2).mean()),
        "wape": abs_error.sum() / denominator * 100 if denominator else float("nan"),
        "n": len(values),
    }


def style_figure(fig: go.Figure, height=365):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=16, r=18, t=20, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", size=11, color=MUTED),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11, color=TEXT)),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=BORDER, font=dict(color=TEXT, family="Inter, sans-serif")),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont=dict(color=MUTED), zeroline=False, automargin=True)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, gridwidth=1, tickfont=dict(color=MUTED), zeroline=False, automargin=True)
    return fig


def add_currency_line(fig, df, date_col, value_col, name, color, dash=None, width=2.6):
    fig.add_trace(go.Scatter(
        x=df[date_col], y=pd.to_numeric(df[value_col], errors="coerce"), mode="lines+markers", name=name,
        line=dict(color=color, width=width, dash=dash or "solid"),
        marker=dict(size=4, color=color),
        hovertemplate="%{x|%d/%m/%Y}<br>" + name + ": R$ %{y:,.2f}<extra></extra>",
    ))


def show_chart(fig: go.Figure, key: str):
    st.markdown('<div class="chart-shell">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True}, key=key, theme=None)
    st.markdown("</div>", unsafe_allow_html=True)


def insight_card(title: str, body: str):
    st.markdown(
        f'<div class="insight-card"><div class="insight-title">{title}</div><div class="insight-text">{body}</div></div>',
        unsafe_allow_html=True,
    )


# Leitura exclusivamente local dos CSVs existentes.
data = {key: load_csv(filename) for key, filename in FILES.items()}
for key in ["historico", "baseline_julho", "comparacao_julho", "janela_recente", "previsao_30_dias"]:
    df = data.get(key)
    if df is not None and "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
if data.get("validacao_temporal") is not None:
    for col in ["inicio_teste", "fim_teste"]:
        if col in data["validacao_temporal"].columns:
            data["validacao_temporal"][col] = pd.to_datetime(data["validacao_temporal"][col], errors="coerce")

missing_files = [filename for key, filename in FILES.items() if data.get(key) is None]

# Navegação lateral — sem nova biblioteca de menu.
PAGES = {
    "Visão geral": ("01 / VISÃO GERAL", "O faturamento em perspectiva", "Resumo do histórico, desempenho dos modelos e limites conhecidos."),
    "Histórico": ("02 / EXPLORAÇÃO", "Explore o histórico", "Investigue a evolução diária do valor dos itens em pedidos atualmente delivered."),
    "Desempenho dos modelos": ("03 / MODELOS", "Realizado versus previsto", "Comparação diária entre baseline e Random Forest no teste inicial de julho de 2018."),
    "Validação temporal": ("04 / ROBUSTEZ", "O desempenho se mantém no tempo?", "Cinco janelas de teste e diagnóstico separado do período recente."),
    "Previsão 30 dias": ("05 / HORIZONTE", "Previsão simulada de 30 dias", "Cenário retrospectivo iniciado após o corte provisório de 22/08/2018."),
}
NAV_SYMBOLS = {
    "Visão geral": "◈  Visão geral",
    "Histórico": "⌁  Histórico",
    "Desempenho dos modelos": "▥  Modelos",
    "Validação temporal": "◷  Validação temporal",
    "Previsão 30 dias": "↗  Previsão 30 dias",
}
with st.sidebar:
    st.markdown(
        '<div style="padding:10px 2px 17px">'
        '<div style="display:inline-block;padding:5px 9px;border:1px solid rgba(168,139,216,.40);border-radius:8px;'
        'background:rgba(168,139,216,.12);font-size:.62rem;letter-spacing:.14em;text-transform:uppercase;color:#F8A9D0;font-weight:850">DATA + IA</div>'
        '<div style="font-size:1.62rem;font-weight:900;line-height:1.02;letter-spacing:-.055em;margin-top:12px;color:#FFFFFF">DASH<br>VENDAS</div>'
        '<div style="font-size:.73rem;color:#BDB4C7;margin-top:10px;line-height:1.5">Inteligência comercial<br>Dataset público Olist</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div style="font-size:.63rem;letter-spacing:.15em;font-weight:850;color:#9A8FA8;margin:6px 0 8px">MENU PRINCIPAL</div>', unsafe_allow_html=True)
    page = st.radio(
        "Navegação principal",
        options=list(PAGES.keys()),
        format_func=lambda item: NAV_SYMBOLS[item],
        label_visibility="collapsed",
        key="dashboard_page",
    )
    st.divider()
    st.markdown('<div style="font-size:.63rem;letter-spacing:.15em;font-weight:850;color:#9A8FA8;margin-bottom:8px">ESTADO DOS ARQUIVOS</div>', unsafe_allow_html=True)
    for key, filename in FILES.items():
        ok = data.get(key) is not None
        dot_color = CYAN if ok else ORANGE
        symbol = "●" if ok else "○"
        label = filename.removesuffix(".csv")
        st.markdown(
            f'<div style="display:flex;gap:7px;align-items:flex-start;margin:7px 0;line-height:1.35">'
            f'<span style="color:{dot_color};font-size:.67rem">{symbol}</span>'
            f'<span style="font-size:.65rem;color:#CFC4D7;overflow-wrap:anywhere">{label}</span></div>',
            unsafe_allow_html=True,
        )
    st.divider()
    st.markdown(
        '<div style="font-size:.63rem;letter-spacing:.15em;font-weight:850;color:#9A8FA8;margin-bottom:7px">RECORTE ANALÍTICO</div>'
        '<div style="font-size:.75rem;color:#D8CDDE;line-height:1.7">Jan/2017 – Ago/2018<br>Corte provisório: 22/08/2018</div>',
        unsafe_allow_html=True,
    )
    st.caption("Somente leitura de CSVs locais. Esta interface não consulta nem altera o BigQuery.")

hero_kicker, hero_title, hero_subtitle = PAGES[page]
st.markdown(
    f'<div class="hero"><div class="eyebrow">{hero_kicker}</div>'
    f'<div class="hero-title">{hero_title}</div><div class="hero-subtitle">{hero_subtitle}</div>'
    '<div class="status-line"><span class="status-chip">DADOS PÚBLICOS • OLIST</span>'
    '<span class="status-chip">SQL + PYTHON + MACHINE LEARNING</span>'
    '<span class="status-chip">CORTE PROVISÓRIO · 22 AGO 2018</span></div></div>',
    unsafe_allow_html=True,
)

if missing_files:
    st.warning("Alguns CSVs não foram encontrados. Coloque-os na mesma pasta do app.py: " + ", ".join(missing_files))

# Dados de referência comuns às páginas.
hist = data.get("historico")
comp = data.get("comparacao_julho")
valid = data.get("validacao_temporal")
recent = data.get("janela_recente")
forecast = data.get("previsao_30_dias")
if hist is not None and {"data", "faturamento_diario"}.issubset(hist.columns):
    hist_cut = hist.loc[(hist["data"] <= CUTOFF), [c for c in ["data", "faturamento_diario", "qtd_pedidos_entregues", "qtd_linhas_itens_entregues"] if c in hist.columns]].copy().dropna(subset=["data"]).sort_values("data")
else:
    hist_cut = pd.DataFrame(columns=["data", "faturamento_diario"])

agg = None
windows = pd.DataFrame()
if valid is not None and "tipo_resultado" in valid.columns:
    agg_rows = valid[valid["tipo_resultado"].eq("agregado_5_janelas")]
    agg = agg_rows.iloc[0] if not agg_rows.empty else None
    windows = valid[valid["tipo_resultado"].eq("janela")].copy()

if page == "Visão geral":
    last_date = hist_cut["data"].max() if not hist_cut.empty else pd.NaT
    total_hist = pd.to_numeric(hist_cut.get("faturamento_diario", pd.Series(dtype=float)), errors="coerce").sum()
    rf_wape = float(agg["wape_random_forest_pct"]) if agg is not None else float("nan")
    base_wape = float(agg["wape_baseline_pct"]) if agg is not None else float("nan")
    diff_pp = float(agg["diferenca_wape_pontos_pct"]) if agg is not None else float("nan")
    wins = int((pd.to_numeric(windows.get("diferenca_wape_pontos_pct", pd.Series(dtype=float)), errors="coerce") < 0).sum()) if not windows.empty else 0

    section_header("PANORAMA", "Indicadores principais", "Resumo baseado nos resultados efetivamente calculados no projeto.")
    cols = st.columns(4, gap="medium")
    with cols[0]: metrics_html("FATURAMENTO HISTÓRICO", brl(total_hist), f"Até {last_date:%d/%m/%Y}" if pd.notna(last_date) else "Data indisponível")
    with cols[1]: metrics_html("WAPE · RANDOM FOREST", pct(rf_wape), "Agregado de cinco janelas")
    with cols[2]: metrics_html("WAPE · BASELINE", pct(base_wape), "Método de referência")
    with cols[3]: metrics_html("JANELAS VENCIDAS PELO RF", f"{wins}/5" if not windows.empty else "N/D", f"Diferença WAPE agregada: {number(diff_pp)} p.p.")
    st.write("")

    left, right = st.columns([1.7, 1], gap="large")
    with left:
        section_header("SÉRIE HISTÓRICA", "Faturamento diário", "Valor dos itens em pedidos atualmente delivered; recorte até 22/08/2018.")
        if not hist_cut.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=hist_cut["data"], y=pd.to_numeric(hist_cut["faturamento_diario"], errors="coerce"),
                mode="lines", name="Faturamento diário", line=dict(color=CYAN, width=2.5),
                fill="tozeroy", fillcolor="rgba(255,95,162,.09)",
                hovertemplate="%{x|%d/%m/%Y}<br>Faturamento: R$ %{y:,.2f}<extra></extra>",
            ))
            show_chart(style_figure(fig, 365), "overview_history")
        else:
            st.info("O CSV histórico não foi encontrado ou não contém as colunas esperadas.")
    with right:
        section_header("LEITURA ANALÍTICA", "O que já sabemos?", "Principais conclusões, sem tratar resultados iniciais como definitivos.")
        insight_card("01 · Melhor WAPE agregado", f"Random Forest: {pct(rf_wape)}; baseline: {pct(base_wape)} nas cinco janelas temporais.")
        st.write("")
        insight_card("02 · Desempenho varia", f"O Random Forest venceu {wins} de {len(windows)} janelas. A vantagem agregada não se repete em todos os períodos.")
        st.write("")
        insight_card("03 · Previsão simulada", "O horizonte de 23/08 a 21/09/2018 é retrospectivo e não possui faturamento realizado maduro para medir erro.")

    st.write("")
    section_header("COMPARAÇÃO DE WAPE", "Baseline x Random Forest", "Menor WAPE indica menor soma de erros absolutos em relação ao realizado.")
    if agg is not None:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=["Baseline", "Random Forest"], y=[float(agg["wape_baseline_pct"]), float(agg["wape_random_forest_pct"])],
                             marker_color=[ORANGE, PURPLE], marker_line_width=0,
                             text=[pct(agg["wape_baseline_pct"]), pct(agg["wape_random_forest_pct"])], textposition="outside",
                             hovertemplate="%{x}<br>WAPE: %{y:.2f}%<extra></extra>"))
        fig.update_layout(showlegend=False, yaxis_title="WAPE (%)", yaxis_rangemode="tozero")
        show_chart(style_figure(fig, 270), "overview_wape")
    st.warning("Definição do indicador: soma de price dos itens associados a pedidos atualmente delivered, agrupada pela data da compra. É uma aproximação operacional, não faturamento contábil reconciliado.")

elif page == "Histórico":
    section_header("EXPLORAÇÃO TEMPORAL", "Explore a série diária", "Use o filtro de datas para investigar diferentes trechos do histórico que passaram pelo corte provisório.")
    if hist is None or not {"data", "faturamento_diario"}.issubset(hist.columns) or hist_cut.empty:
        st.info("Coloque base_treinamento_faturamento_teste.csv na mesma pasta do app.py.")
    else:
        hist_work = hist_cut.copy()
        hist_work["faturamento_diario"] = pd.to_numeric(hist_work["faturamento_diario"], errors="coerce")
        hmin, hmax = hist_work["data"].min().date(), hist_work["data"].max().date()
        selection = st.date_input("Período analisado", value=(hmin, hmax), min_value=hmin, max_value=hmax, format="DD/MM/YYYY", key="history_range")
        if isinstance(selection, (tuple, list)) and len(selection) == 2:
            start_date, end_date = pd.Timestamp(selection[0]), pd.Timestamp(selection[1])
        else:
            start_date, end_date = pd.Timestamp(hmin), pd.Timestamp(hmax)
        filtered = hist_work.loc[hist_work["data"].between(start_date, end_date)].copy().sort_values("data")
        c1, c2, c3 = st.columns(3, gap="medium")
        with c1: metrics_html("FATURAMENTO DO PERÍODO", brl(filtered["faturamento_diario"].sum()), f"{len(filtered)} dias selecionados")
        with c2: metrics_html("MÉDIA DIÁRIA", brl(filtered["faturamento_diario"].mean()), "Inclui dias sem faturamento registrado")
        with c3: metrics_html("DIAS COM VALOR ZERO", str(int(filtered["faturamento_diario"].eq(0).sum())), "Zero observado na base")
        st.write("")
        fig = go.Figure()
        add_currency_line(fig, filtered, "data", "faturamento_diario", "Faturamento diário", CYAN, width=2.5)
        show_chart(style_figure(fig, 430), "history_filtered")
        with st.expander("Abrir tabela diária do período"):
            display = filtered.copy()
            display["data"] = display["data"].dt.strftime("%d/%m/%Y")
            display = display.rename(columns={"data":"Data", "faturamento_diario":"Faturamento diário", "qtd_pedidos_entregues":"Pedidos delivered", "qtd_linhas_itens_entregues":"Linhas de itens"})
            st.dataframe(
                format_table(
                    display,
                    currency_columns=["Faturamento diário"],
                    integer_columns=["Pedidos delivered", "Linhas de itens"],
                ),
                use_container_width=True,
                hide_index=True,
            )
    st.info("O histórico exibido é limitado provisoriamente a 22/08/2018 para evitar interpretar a queda no fim da série como uma queda de vendas confirmada.")

elif page == "Desempenho dos modelos":
    section_header("TESTE INICIAL", "Realizado versus previsto", "01 a 30/07/2018. Os métodos foram avaliados nas mesmas 30 datas.")
    required = {"data", "faturamento_real", "previsao_random_forest", "previsao_baseline"}
    if comp is None or not required.issubset(comp.columns):
        st.info("Coloque 20_previsoes_random_forest_teste.csv na mesma pasta do app.py.")
    else:
        comp = comp.sort_values("data").copy()
        rf_m = calculate_metrics(comp, "faturamento_real", "previsao_random_forest")
        base_m = calculate_metrics(comp, "faturamento_real", "previsao_baseline")
        c1, c2, c3, c4 = st.columns(4, gap="medium")
        with c1: metrics_html("WAPE · RANDOM FOREST", pct(rf_m["wape"]), f"MAE: {brl(rf_m['mae'])}")
        with c2: metrics_html("WAPE · BASELINE", pct(base_m["wape"]), f"MAE: {brl(base_m['mae'])}")
        with c3: metrics_html("RMSE · RANDOM FOREST", brl(rf_m["rmse"]), "Penaliza mais os erros grandes")
        with c4: metrics_html("DIFERENÇA WAPE", f"{number(rf_m['wape'] - base_m['wape'])} p.p.", "Negativo favorece RF")
        st.write("")
        fig = go.Figure()
        add_currency_line(fig, comp, "data", "faturamento_real", "Realizado", TEXT, width=2.7)
        add_currency_line(fig, comp, "data", "previsao_random_forest", "Random Forest", CYAN, width=2.5)
        add_currency_line(fig, comp, "data", "previsao_baseline", "Baseline", ORANGE, dash="dash", width=2.3)
        show_chart(style_figure(fig, 440), "july_model_comparison")
        st.caption("MAE = erro absoluto médio. WAPE = soma dos erros absolutos dividida pelo faturamento realizado total. RMSE penaliza mais fortemente erros grandes.")
        with st.expander("Ver previsões e erros por dia"):
            cols = [c for c in ["data", "faturamento_real", "previsao_random_forest", "previsao_baseline", "erro_modelo", "erro_absoluto_modelo", "erro_baseline", "erro_absoluto_baseline"] if c in comp.columns]
            display = comp[cols].copy()
            display["data"] = display["data"].dt.strftime("%d/%m/%Y")
            display = display.rename(columns={"data":"Data", "faturamento_real":"Realizado", "previsao_random_forest":"Random Forest", "previsao_baseline":"Baseline", "erro_modelo":"Erro RF", "erro_absoluto_modelo":"Erro absoluto RF", "erro_baseline":"Erro baseline", "erro_absoluto_baseline":"Erro absoluto baseline"})
            st.dataframe(
                format_table(
                    display,
                    currency_columns=[
                        "Realizado", "Random Forest", "Baseline",
                        "Erro RF", "Erro absoluto RF",
                        "Erro baseline", "Erro absoluto baseline",
                    ],
                ),
                use_container_width=True,
                hide_index=True,
            )

elif page == "Validação temporal":
    section_header("ROBUSTEZ TEMPORAL", "O desempenho se mantém no tempo?", "Cinco janelas de 30 dias. O teste inicial de julho não está incluído neste agregado.")
    if valid is None or "tipo_resultado" not in valid.columns:
        st.info("Coloque 21_resultado_validacao_temporal.csv na mesma pasta do app.py.")
    elif not windows.empty:
        windows = windows.copy().sort_values("inicio_teste")
        windows["janela"] = windows.apply(lambda r: f"{r['inicio_teste']:%d/%m}–{r['fim_teste']:%d/%m}" if pd.notna(r["inicio_teste"]) and pd.notna(r["fim_teste"]) else "Janela", axis=1)
        wins = int((pd.to_numeric(windows["diferenca_wape_pontos_pct"], errors="coerce") < 0).sum())
        c1, c2, c3 = st.columns(3, gap="medium")
        if agg is not None:
            with c1: metrics_html("WAPE AGREGADO · RF", pct(agg["wape_random_forest_pct"]), "Cinco janelas")
            with c2: metrics_html("WAPE AGREGADO · BASELINE", pct(agg["wape_baseline_pct"]), "Referência simples")
        with c3: metrics_html("JANELAS VENCIDAS PELO RF", f"{wins} de {len(windows)}", "Menor WAPE por janela")
        st.write("")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=windows["janela"], y=windows["wape_random_forest_pct"], name="Random Forest", marker_color=PURPLE, marker_line_width=0, hovertemplate="Janela %{x}<br>WAPE RF: %{y:.2f}%<extra></extra>"))
        fig.add_trace(go.Bar(x=windows["janela"], y=windows["wape_baseline_pct"], name="Baseline", marker_color=ORANGE, marker_line_width=0, hovertemplate="Janela %{x}<br>WAPE baseline: %{y:.2f}%<extra></extra>"))
        fig.update_layout(barmode="group", bargap=0.25, yaxis_title="WAPE (%)", xaxis_title="Período de teste")
        show_chart(style_figure(fig, 415), "temporal_validation")
        st.info("O Random Forest tem melhor resultado agregado, mas não vence em todas as janelas. Isso é evidência inicial, não garantia de desempenho futuro.")
        display_cols = ["janela", "linhas_treinamento", "mae_random_forest", "rmse_random_forest", "wape_random_forest_pct", "mae_baseline", "rmse_baseline", "wape_baseline_pct", "diferenca_wape_pontos_pct"]
        display = windows[[c for c in display_cols if c in windows.columns]].copy()
        display = display.rename(columns={"janela":"Janela", "linhas_treinamento":"Linhas treino", "mae_random_forest":"MAE RF", "rmse_random_forest":"RMSE RF", "wape_random_forest_pct":"WAPE RF (%)", "mae_baseline":"MAE baseline", "rmse_baseline":"RMSE baseline", "wape_baseline_pct":"WAPE baseline (%)", "diferenca_wape_pontos_pct":"Diferença WAPE (p.p.)"})
        with st.expander("Ver números de cada janela"):
            st.dataframe(
                format_table(
                    display,
                    currency_columns=["MAE RF", "RMSE RF", "MAE baseline", "RMSE baseline"],
                    percentage_columns=["WAPE RF (%)", "WAPE baseline (%)"],
                    percentage_point_columns=["Diferença WAPE (p.p.)"],
                    integer_columns=["Linhas treino"],
                ),
                use_container_width=True,
                hide_index=True,
            )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    section_header("DIAGNÓSTICO SEPARADO", "Janela recente · 31/07 a 29/08/2018", "Este diagnóstico não está incluído no agregado de cinco janelas.")
    st.warning("O valor observado de pedidos atualmente delivered cai fortemente no fim de agosto. A janela é útil como diagnóstico, mas pode refletir maturidade incompleta dos pedidos recentes.")
    if recent is not None and {"data", "faturamento_real", "previsao_random_forest", "previsao_baseline"}.issubset(recent.columns):
        recent = recent.sort_values("data")
        rm = calculate_metrics(recent, "faturamento_real", "previsao_random_forest")
        bm = calculate_metrics(recent, "faturamento_real", "previsao_baseline")
        a, b, c = st.columns(3, gap="medium")
        with a: metrics_html("WAPE RF · DIAGNÓSTICO", pct(rm["wape"]), "Janela recente")
        with b: metrics_html("WAPE BASELINE · DIAGNÓSTICO", pct(bm["wape"]), "Mesmas datas")
        with c: metrics_html("DIFERENÇA WAPE", f"{number(rm['wape']-bm['wape'])} p.p.", "Negativo favorece RF")
        fig = go.Figure()
        add_currency_line(fig, recent, "data", "faturamento_real", "Realizado observado", TEXT)
        add_currency_line(fig, recent, "data", "previsao_random_forest", "Random Forest", CYAN)
        add_currency_line(fig, recent, "data", "previsao_baseline", "Baseline", ORANGE, dash="dash")
        show_chart(style_figure(fig, 360), "recent_diagnostic")

elif page == "Previsão 30 dias":
    section_header("HORIZONTE DE PREVISÃO", "30 dias simulados", "23/08 a 21/09/2018. É uma simulação retrospectiva, não uma previsão para o mercado atual.")
    if forecast is None or not {"data", "previsao_random_forest", "previsao_baseline"}.issubset(forecast.columns):
        st.info("Coloque 23_previsao_30_dias_corte_22_08.csv na mesma pasta do app.py.")
    else:
        forecast = forecast.sort_values("data").copy()
        rf_total = pd.to_numeric(forecast["previsao_random_forest"], errors="coerce").sum()
        base_total = pd.to_numeric(forecast["previsao_baseline"], errors="coerce").sum()
        rf_avg = pd.to_numeric(forecast["previsao_random_forest"], errors="coerce").mean()
        base_avg = pd.to_numeric(forecast["previsao_baseline"], errors="coerce").mean()
        c1, c2, c3 = st.columns(3, gap="medium")
        with c1: metrics_html("TOTAL PREVISTO · RANDOM FOREST", brl(rf_total), f"Média diária: {brl(rf_avg)}")
        with c2: metrics_html("TOTAL PREVISTO · BASELINE", brl(base_total), f"Média diária: {brl(base_avg)}")
        with c3: metrics_html("DIFERENÇA RF − BASELINE", brl(rf_total-base_total), "Diferença entre previsões, não erro")
        st.write("")
        fig = go.Figure()
        add_currency_line(fig, forecast, "data", "previsao_random_forest", "Random Forest", CYAN, width=2.7)
        add_currency_line(fig, forecast, "data", "previsao_baseline", "Baseline", ORANGE, dash="dash", width=2.3)
        show_chart(style_figure(fig, 430), "forecast_horizon")
        st.warning("Esta previsão usa o corte provisório de 22/08/2018. O arquivo não contém faturamento realizado maduro para o horizonte; por isso, não há métricas de erro nesta seção.")
        with st.expander("Ver previsões diárias e features"):
            display = forecast.copy()
            display["data"] = display["data"].dt.strftime("%d/%m/%Y")
            st.dataframe(
                format_table(
                    display,
                    currency_columns=[
                        "faturamento_ano_anterior", "media_7d_usada",
                        "previsao_random_forest", "previsao_baseline",
                        "diferenca_rf_menos_baseline",
                    ],
                ),
                use_container_width=True,
                hide_index=True,
            )

st.markdown(
    '<div class="footer">PROJETO DASH VENDAS · PORTFÓLIO DE DADOS + IA · DATASET PÚBLICO OLIST<br>'
    'Indicador operacional baseado em itens de pedidos atualmente delivered. Corte em 22/08/2018 provisório.<br>'
    'Dashboard local: os dados são lidos dos CSVs na pasta da aplicação.</div>',
    unsafe_allow_html=True,
)
