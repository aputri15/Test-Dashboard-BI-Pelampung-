import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ─── CONFIG HALAMAN ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BI Dashboard | Pelampung 2025",
    page_icon="🎣",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Font & background */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #0f172a; }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiselect label { color: #94a3b8 !important; font-size: 0.8rem; }

    /* KPI Cards */
    .kpi-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 20px 24px;
        color: white;
        text-align: center;
    }
    .kpi-label { font-size: 0.75rem; color: #94a3b8; font-weight: 500;
                 letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 8px; }
    .kpi-value { font-size: 1.75rem; font-weight: 700; color: #f1f5f9; line-height: 1; }
    .kpi-sub   { font-size: 0.75rem; color: #64748b; margin-top: 6px; }
    .kpi-green .kpi-value { color: #4ade80; }
    .kpi-blue  .kpi-value { color: #60a5fa; }
    .kpi-yellow.kpi-value { color: #fbbf24; }
    .kpi-red   .kpi-value { color: #f87171; }

    /* Section headers */
    .section-title {
        font-size: 1rem; font-weight: 600; color: #334155;
        border-left: 4px solid #3b82f6; padding-left: 12px;
        margin: 24px 0 16px 0;
    }

    /* Warning / info box */
    .info-box {
        background: #fef9c3; border: 1px solid #fde047;
        border-radius: 8px; padding: 10px 16px;
        font-size: 0.82rem; color: #713f12;
    }

    /* Hide streamlit branding */
    #MainMenu, footer { visibility: hidden; }
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# ─── KONEKSI DATABASE ─────────────────────────────────────────────────────────
DB_PATH = "pelampung.db"

@st.cache_data(ttl=300)
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM transaksi_analisis", conn)
    df_pelanggan = pd.read_sql("SELECT * FROM master_pelanggan", conn)
    conn.close()
    df['Tanggal_PO'] = pd.to_datetime(df['Tanggal_PO'])
    df = df[df['Wilayah'].notna()]
    return df, df_pelanggan

try:
    df_raw, df_pelanggan = load_data()
except Exception as e:
    st.error(f"❌ Database tidak ditemukan. Jalankan `python setup_db.py` terlebih dahulu.\n\nError: {e}")
    st.stop()

MONTH_ORDER = ["Januari","Februari","Maret","April","Mei","Juni",
               "Juli","Agustus","September","Oktober","November","Desember"]
WILAYAH_COLOR = {"Jawa": "#3b82f6", "Sumatera": "#f59e0b", "Kalimantan": "#10b981"}

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def fmt_idr(n):
    """Format angka menjadi format Rupiah ringkas."""
    if n >= 1_000_000_000:
        return f"Rp {n/1_000_000_000:.2f}M"
    elif n >= 1_000_000:
        return f"Rp {n/1_000_000:.1f}jt"
    elif n >= 1_000:
        return f"Rp {n/1_000:.1f}rb"
    return f"Rp {n:,.0f}"

def fmt_pct(n):
    return f"{n:.1f}%"

# ─── SIDEBAR FILTER ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎣 DASHBOARD BI RUMAH PRODUKSI PELAMPUNG 2025")
    st.markdown("---")
    st.markdown("### 🔎 Filter Data")

    # Filter Wilayah
    all_wilayah = sorted(df_raw['Wilayah'].dropna().unique().tolist())
    sel_wilayah = st.multiselect(
        "📍 Wilayah",
        options=all_wilayah,
        default=all_wilayah,
        placeholder="Pilih wilayah..."
    )

    # Filter Bulan
    all_bulan = [b for b in MONTH_ORDER if b in df_raw['Nama_Bulan'].unique()]
    sel_bulan = st.multiselect(
        "📅 Bulan",
        options=all_bulan,
        default=all_bulan,
        placeholder="Pilih bulan..."
    )

    # Filter Nama Model
    all_model = sorted(df_raw['Nama_Model'].dropna().unique().tolist())
    sel_model = st.multiselect(
        "🏷️ Model Produk",
        options=all_model,
        default=all_model,
        placeholder="Pilih model..."
    )

    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.75rem;color:#475569;text-align:center'>"
        "⚠️ <b>Catatan:</b> Kolom BOP/Listrik belum tersedia di data.<br>"
        "TLC dihitung: <i>HPP + Biaya Logistik</i>"
        "</div>", unsafe_allow_html=True
    )

# ─── TERAPKAN FILTER ─────────────────────────────────────────────────────────
df = df_raw.copy()
if sel_wilayah: df = df[df['Wilayah'].isin(sel_wilayah)]
if sel_bulan:   df = df[df['Nama_Bulan'].isin(sel_bulan)]
if sel_model:   df = df[df['Nama_Model'].isin(sel_model)]

if df.empty:
    st.warning("⚠️ Tidak ada data yang cocok dengan filter yang dipilih.")
    st.stop()

# ─── HEADER ──────────────────────────────────────────────────────────────────
st.markdown("""
<div style='margin-bottom:8px'>
    <h1 style='font-size:1.6rem;font-weight:700;color:#0f172a;margin:0'>
        📊 Dashboard Business Intelligence
    </h1>
    <p style='color:#64748b;font-size:0.9rem;margin:4px 0 0 0'>
        Analisis Profitabilitas & Product-Region Fit | Pelampung 2025
    </p>
</div>
""", unsafe_allow_html=True)

# ─── TABS NAVIGASI ───────────────────────────────────────────────────────────
tab1, tab2 = st.tabs([
    " Profitabilitas Regional",
    " Product-Region Fit"
])

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 1 ─ PROFITABILITAS REGIONAL
# ══════════════════════════════════════════════════════════════════════════════
with tab1:

    # ── KPI CARDS ─────────────────────────────────────────────────────────────
    total_revenue = df['Revenue'].sum()
    total_tlc     = df['Total_TLC'].sum()
    total_gp      = df['Gross_Profit_Total'].sum()
    avg_gpm       = df['GPM_Pct'].mean()
    total_volume  = df['Qty'].sum()
    total_po      = df['Nomor_PO'].nunique()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""<div class='kpi-card'>
            <div class='kpi-label'>Total Penjualan</div>
            <div class='kpi-value kpi-blue'>{fmt_idr(total_revenue)}</div>
            <div class='kpi-sub'>{total_po:,} Purchase Order</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class='kpi-card'>
            <div class='kpi-label'>Total TLC</div>
            <div class='kpi-value' style='color:#f97316'>{fmt_idr(total_tlc)}</div>
            <div class='kpi-sub'>HPP Produksi + Biaya Logistik</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        gp_color = "kpi-green" if total_gp >= 0 else "kpi-red"
        st.markdown(f"""<div class='kpi-card'>
            <div class='kpi-label'>Laba Kotor</div>
            <div class='kpi-value {gp_color}'>{fmt_idr(total_gp)}</div>
            <div class='kpi-sub'>Penjualan − Total Landed Cost</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        gpm_color = "#4ade80" if avg_gpm >= 30 else ("#fbbf24" if avg_gpm >= 10 else "#f87171")
        st.markdown(f"""<div class='kpi-card'>
            <div class='kpi-label'>Avg GPM</div>
            <div class='kpi-value' style='color:{gpm_color}'>{fmt_pct(avg_gpm)}</div>
            <div class='kpi-sub'>Gross Profit Margin rata-rata</div>
        </div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""<div class='kpi-card'>
            <div class='kpi-label'>Total Volume</div>
            <div class='kpi-value' style='color:#a78bfa'>{total_volume:,.0f}</div>
            <div class='kpi-sub'>Unit terjual</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── CHART 1A: Revenue vs TLC per Provinsi (Grouped Bar) ───────────────────
    st.markdown("<div class='section-title'>📊 Revenue vs Total TLC per Provinsi</div>",
                unsafe_allow_html=True)

    agg_provinsi = df.groupby(['Wilayah', 'Provinsi']).agg(
        Revenue=('Revenue', 'sum'),
        Total_TLC=('Total_TLC', 'sum'),
        Gross_Profit=('Gross_Profit_Total', 'sum'),
        Avg_GPM=('GPM_Pct', 'mean')
    ).reset_index().sort_values('Revenue', ascending=False)

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        name='💰 Total Penjualan',
        x=agg_provinsi['Provinsi'],
        y=agg_provinsi['Revenue'],
        marker_color='#3b82f6',
        text=agg_provinsi['Revenue'].apply(fmt_idr),
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Revenue: Rp %{y:,.0f}<extra></extra>'
    ))
    fig_bar.add_trace(go.Bar(
        name='📦 Total TLC',
        x=agg_provinsi['Provinsi'],
        y=agg_provinsi['Total_TLC'],
        marker_color='#f97316',
        text=agg_provinsi['Total_TLC'].apply(fmt_idr),
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>TLC: Rp %{y:,.0f}<extra></extra>'
    ))
    fig_bar.add_trace(go.Bar(
        name='✅ Gross Profit',
        x=agg_provinsi['Provinsi'],
        y=agg_provinsi['Gross_Profit'],
        marker_color='#4ade80',
        text=agg_provinsi['Gross_Profit'].apply(fmt_idr),
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Gross Profit: Rp %{y:,.0f}<extra></extra>'
    ))
    fig_bar.update_layout(
        barmode='group',
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=420,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        xaxis=dict(title='', tickfont=dict(size=12)),
        yaxis=dict(title='Nilai (Rp)', tickformat=',.0f', gridcolor='#f1f5f9'),
        margin=dict(t=40, b=20, l=20, r=20),
        font=dict(family='Inter')
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # ── CHART 1B: GPM per Wilayah + Tren Bulanan ──────────────────────────────
    col_a, col_b = st.columns([1, 1])

    with col_a:
        st.markdown("<div class='section-title'>🎯 GPM per Wilayah</div>",
                    unsafe_allow_html=True)
        agg_wil = df.groupby('Wilayah').agg(
            Revenue=('Revenue', 'sum'),
            Total_TLC=('Total_TLC', 'sum'),
            GP=('Gross_Profit_Total', 'sum'),
        ).reset_index()
        agg_wil['GPM'] = (agg_wil['GP'] / agg_wil['Revenue'] * 100).round(2)

        fig_gpm = go.Figure(go.Bar(
            x=agg_wil['Wilayah'],
            y=agg_wil['GPM'],
            marker_color=[WILAYAH_COLOR.get(w, '#94a3b8') for w in agg_wil['Wilayah']],
            text=[f"{v:.1f}%" for v in agg_wil['GPM']],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>GPM: %{y:.2f}%<extra></extra>'
        ))
        # Garis threshold 30%
        fig_gpm.add_hline(y=30, line_dash='dash', line_color='#10b981',
                          annotation_text='Target 30%', annotation_position='right')
        fig_gpm.update_layout(
            plot_bgcolor='white', paper_bgcolor='white', height=350,
            yaxis=dict(title='GPM (%)', gridcolor='#f1f5f9', range=[0, max(agg_wil['GPM'])*1.3]),
            xaxis=dict(title=''),
            margin=dict(t=20, b=20, l=20, r=40),
            font=dict(family='Inter')
        )
        st.plotly_chart(fig_gpm, use_container_width=True)

    with col_b:
        st.markdown("<div class='section-title'>📈 Tren GPM Bulanan per Wilayah</div>",
                    unsafe_allow_html=True)
        tren = df.groupby(['Wilayah', 'Bulan', 'Nama_Bulan']).agg(
            Revenue=('Revenue', 'sum'),
            GP=('Gross_Profit_Total', 'sum')
        ).reset_index()
        tren['GPM'] = (tren['GP'] / tren['Revenue'] * 100).round(2)
        tren = tren.sort_values('Bulan')

        fig_tren = go.Figure()
        for wil in tren['Wilayah'].unique():
            d = tren[tren['Wilayah'] == wil]
            fig_tren.add_trace(go.Scatter(
                x=d['Nama_Bulan'], y=d['GPM'],
                mode='lines+markers',
                name=wil,
                line=dict(color=WILAYAH_COLOR.get(wil, '#94a3b8'), width=2.5),
                marker=dict(size=7),
                hovertemplate='%{x}<br>GPM: %{y:.1f}%<extra>' + wil + '</extra>'
            ))
        fig_tren.add_hline(y=30, line_dash='dash', line_color='#94a3b8',
                           annotation_text='30%', annotation_position='right')
        fig_tren.update_layout(
            plot_bgcolor='white', paper_bgcolor='white', height=350,
            xaxis=dict(title='', categoryorder='array',
                       categoryarray=[b for b in MONTH_ORDER if b in tren['Nama_Bulan'].values]),
            yaxis=dict(title='GPM (%)', gridcolor='#f1f5f9'),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            margin=dict(t=20, b=20, l=20, r=60),
            font=dict(family='Inter')
        )
        st.plotly_chart(fig_tren, use_container_width=True)

    # ── TABEL RINGKASAN PROVINSI ───────────────────────────────────────────────
    st.markdown("<div class='section-title'>📋 Ringkasan Profitabilitas per Provinsi</div>",
                unsafe_allow_html=True)

    tbl = agg_provinsi.copy()
    tbl['GPM (%)']       = tbl['Avg_GPM'].round(2)
    tbl['Revenue']       = tbl['Revenue'].apply(fmt_idr)
    tbl['Total TLC']     = tbl['Total_TLC'].apply(fmt_idr)
    tbl['Gross Profit']  = tbl['Gross_Profit'].apply(fmt_idr)

    def color_gpm(val):
        if val >= 30: return 'color: #16a34a; font-weight:600'
        elif val >= 10: return 'color: #d97706; font-weight:600'
        return 'color: #dc2626; font-weight:600'

    st.dataframe(
        tbl[['Wilayah', 'Provinsi', 'Revenue', 'Total TLC', 'Gross Profit', 'GPM (%)']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "GPM (%)": st.column_config.NumberColumn("GPM (%)", format="%.2f %%")
        }
    )


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 2 ─ PRODUCT-REGION FIT
# ══════════════════════════════════════════════════════════════════════════════
with tab2:

    # ── SUB-FILTER WILAYAH ────────────────────────────────────────────────────
    col_f1, col_f2 = st.columns([2, 5])
    with col_f1:
        wil_options = sorted(df['Wilayah'].unique().tolist())
        sel_wil_tab2 = st.selectbox("🗺️ Fokus Wilayah:", wil_options, key='tab2_wil')
    with col_f2:
        model_options = sorted(df['Nama_Model'].unique().tolist())
        sel_model_tab2 = st.multiselect(
            "🏷️ Filter Model Produk:", model_options, default=model_options, key='tab2_model'
        )

    df2 = df[df['Wilayah'] == sel_wil_tab2]
    if sel_model_tab2:
        df2 = df2[df2['Nama_Model'].isin(sel_model_tab2)]

    if df2.empty:
        st.warning("Tidak ada data untuk filter ini.")
        st.stop()

    # ── CHART 2A: Dual-Axis — Volume (Bar) + GPM% (Line) ─────────────────────
    st.markdown(
        f"<div class='section-title'>📊 Volume vs GPM — {sel_wil_tab2} | Dual-Axis Chart</div>",
        unsafe_allow_html=True
    )

    agg_produk = df2.groupby(['Nama_Model', 'Kategori']).agg(
        Volume=('Qty', 'sum'),
        Revenue=('Revenue', 'sum'),
        GP=('Gross_Profit_Total', 'sum'),
        Avg_GPM=('GPM_Pct', 'mean'),
        Avg_TLC=('TLC', 'mean'),
        Avg_Harga=('Harga_Satuan', 'mean')
    ).reset_index()
    agg_produk['Label_Produk'] = agg_produk['Nama_Model'] + ' [' + agg_produk['Kategori'].astype(str) + ']'
    agg_produk['Total_Profit'] = agg_produk['GP']
    agg_produk = agg_produk.sort_values('Volume', ascending=False)

    fig_dual = go.Figure()
    fig_dual.add_trace(go.Bar(
        x=agg_produk['Label_Produk'],
        y=agg_produk['Volume'],
        name='📦 Volume (Unit)',
        marker_color=WILAYAH_COLOR.get(sel_wil_tab2, '#3b82f6'),
        opacity=0.8,
        yaxis='y1',
        hovertemplate='<b>%{x}</b><br>Volume: %{y:,.0f} unit<extra></extra>'
    ))
    fig_dual.add_trace(go.Scatter(
        x=agg_produk['Label_Produk'],
        y=agg_produk['Avg_GPM'],
        name='📈 GPM (%)',
        mode='lines+markers',
        line=dict(color='#f97316', width=2.5),
        marker=dict(size=8, symbol='circle'),
        yaxis='y2',
        hovertemplate='<b>%{x}</b><br>GPM: %{y:.1f}%<extra></extra>'
    ))
    fig_dual.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        height=420,
        xaxis=dict(title='', tickangle=-35, tickfont=dict(size=10)),
        yaxis=dict(title='Volume (Unit)', gridcolor='#f1f5f9', side='left'),
        yaxis2=dict(title='GPM (%)', overlaying='y', side='right',
                    showgrid=False, ticksuffix='%',
                    range=[0, max(agg_produk['Avg_GPM'])*1.4]),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(t=40, b=80, l=20, r=60),
        font=dict(family='Inter')
    )
    # Tambah garis GPM 30%
    fig_dual.add_hline(y=30, line_dash='dot', line_color='#16a34a',
                       annotation_text='GPM 30%', annotation_position='right',
                       yref='y2')
    st.plotly_chart(fig_dual, use_container_width=True)

    # ── CHART 2B & 2C ─────────────────────────────────────────────────────────
    col_c1, col_c2 = st.columns([1, 1])

    with col_c1:
        # Top 5 Produk — Horizontal Bar Chart
        st.markdown("<div class='section-title'>🏆 Top 5 Produk — Total Profit Terbesar</div>",
                    unsafe_allow_html=True)

        top5 = agg_produk.nlargest(5, 'Total_Profit').sort_values('Total_Profit')

        def color_margin(gpm):
            if gpm >= 30: return '#4ade80'
            elif gpm >= 10: return '#fbbf24'
            return '#f87171'

        colors = [color_margin(g) for g in top5['Avg_GPM']]

        fig_top5 = go.Figure(go.Bar(
            x=top5['Total_Profit'],
            y=top5['Label_Produk'],
            orientation='h',
            marker_color=colors,
            text=[f"{fmt_idr(v)}  |  GPM: {g:.1f}%"
                  for v, g in zip(top5['Total_Profit'], top5['Avg_GPM'])],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Total Profit: Rp %{x:,.0f}<extra></extra>'
        ))
        fig_top5.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            height=350,
            xaxis=dict(title='Total Profit (Rp)', tickformat=',.0f', gridcolor='#f1f5f9'),
            yaxis=dict(title=''),
            margin=dict(t=20, b=20, l=20, r=120),
            font=dict(family='Inter')
        )
        # Legend warna
        fig_top5.add_annotation(
            text="🟢 GPM>30%  🟡 10-30%  🔴 <10%",
            xref='paper', yref='paper', x=0, y=-0.15,
            showarrow=False, font=dict(size=10, color='#64748b')
        )
        st.plotly_chart(fig_top5, use_container_width=True)

    with col_c2:
        # Bubble Chart — Volume vs GPM (ukuran = Revenue)
        st.markdown("<div class='section-title'>🫧 Bubble Chart — Volume vs GPM (Ukuran = Revenue)</div>",
                    unsafe_allow_html=True)

        fig_bubble = px.scatter(
            agg_produk,
            x='Volume', y='Avg_GPM',
            size='Revenue',
            color='Nama_Model',
            text='Label_Produk',
            hover_data={
                'Label_Produk': True,
                'Volume': ':,.0f',
                'Avg_GPM': ':.1f',
                'Revenue': ':,.0f',
                'Total_Profit': ':,.0f'
            },
            size_max=50,
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        # Tambah garis kuadran
        mid_vol = agg_produk['Volume'].median()
        mid_gpm = 30  # threshold GPM
        fig_bubble.add_hline(y=mid_gpm, line_dash='dash', line_color='#94a3b8',
                             annotation_text='GPM 30%')
        fig_bubble.add_vline(x=mid_vol, line_dash='dash', line_color='#94a3b8',
                             annotation_text='Median Vol', annotation_position='top')

        # Label kuadran
        xmax = agg_produk['Volume'].max() * 1.1
        ymax = agg_produk['Avg_GPM'].max() * 1.15
        fig_bubble.add_annotation(text="⭐ High Vol<br>High Margin",
                                  x=xmax*0.85, y=ymax*0.92,
                                  showarrow=False, font=dict(size=9, color='#16a34a'),
                                  bgcolor='#f0fdf4', bordercolor='#16a34a', borderwidth=1)
        fig_bubble.add_annotation(text="⚠️ High Vol<br>Low Margin",
                                  x=xmax*0.85, y=mid_gpm * 0.5,
                                  showarrow=False, font=dict(size=9, color='#d97706'),
                                  bgcolor='#fffbeb', bordercolor='#d97706', borderwidth=1)

        fig_bubble.update_traces(textposition='top center', textfont_size=9)
        fig_bubble.update_layout(
            plot_bgcolor='white', paper_bgcolor='white', height=350,
            xaxis=dict(title='Total Volume (Unit)', gridcolor='#f1f5f9'),
            yaxis=dict(title='GPM (%)', gridcolor='#f1f5f9', ticksuffix='%'),
            legend=dict(title='Model', orientation='v'),
            margin=dict(t=20, b=20, l=20, r=20),
            font=dict(family='Inter')
        )
        st.plotly_chart(fig_bubble, use_container_width=True)

    # ── CHART 2D: Popularitas & Multi-Wilayah Comparison ─────────────────────
    st.markdown("<div class='section-title'>🌍 Perbandingan GPM Produk Antar Wilayah</div>",
                unsafe_allow_html=True)

    # Hitung popularitas per wilayah
    df_pop = df.copy()
    total_per_wilayah = df_pop.groupby('Wilayah')['Qty'].transform('sum')
    df_pop['Popularitas'] = df_pop['Qty'] / total_per_wilayah * 100

    agg_cross = df_pop.groupby(['Wilayah', 'Nama_Model']).agg(
        Total_Volume=('Qty', 'sum'),
        Avg_GPM=('GPM_Pct', 'mean'),
        Popularitas=('Popularitas', 'sum'),
        Revenue=('Revenue', 'sum')
    ).reset_index()

    fig_cross = px.bar(
        agg_cross,
        x='Nama_Model', y='Avg_GPM',
        color='Wilayah',
        barmode='group',
        color_discrete_map=WILAYAH_COLOR,
        text=agg_cross['Avg_GPM'].apply(lambda v: f"{v:.1f}%"),
        hover_data={'Total_Volume': ':,.0f', 'Popularitas': ':.1f', 'Revenue': ':,.0f'},
        labels={'Avg_GPM': 'GPM (%)', 'Nama_Model': 'Model Produk'}
    )
    fig_cross.add_hline(y=30, line_dash='dash', line_color='#94a3b8',
                        annotation_text='Target GPM 30%', annotation_position='right')
    fig_cross.update_traces(textposition='outside')
    fig_cross.update_layout(
        plot_bgcolor='white', paper_bgcolor='white', height=380,
        yaxis=dict(title='GPM (%)', gridcolor='#f1f5f9', ticksuffix='%'),
        xaxis=dict(title=''),
        legend=dict(title='Wilayah', orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(t=40, b=20, l=20, r=80),
        font=dict(family='Inter')
    )
    st.plotly_chart(fig_cross, use_container_width=True)

    # ── TABEL: Customer Loyalty per Wilayah ───────────────────────────────────
    st.markdown(
        f"<div class='section-title'>👤 Customer Terloyال di {sel_wil_tab2}</div>",
        unsafe_allow_html=True
    )

    df_loyal = df2.groupby(['ID_Pelanggan', 'Nama_Pelanggan', 'Kota']).agg(
        Jumlah_PO=('Nomor_PO', 'nunique'),
        Total_Volume=('Qty', 'sum'),
        Total_Revenue=('Revenue', 'sum'),
        Avg_GPM=('GPM_Pct', 'mean'),
        Produk_Dibeli=('Nama_Model', lambda x: ', '.join(sorted(x.unique())))
    ).reset_index().sort_values('Total_Revenue', ascending=False)

    df_loyal['Total_Revenue_fmt'] = df_loyal['Total_Revenue'].apply(fmt_idr)
    df_loyal['Total_Volume_fmt']  = df_loyal['Total_Volume'].apply(lambda v: f"{v:,.0f} unit")
    df_loyal['Avg_GPM_fmt']       = df_loyal['Avg_GPM'].apply(lambda v: f"{v:.1f}%")

    st.dataframe(
        df_loyal[['Nama_Pelanggan', 'Kota', 'Jumlah_PO',
                  'Total_Volume_fmt', 'Total_Revenue_fmt', 'Avg_GPM_fmt', 'Produk_Dibeli']].rename(
            columns={
                'Total_Volume_fmt' : 'Volume',
                'Total_Revenue_fmt': 'Revenue',
                'Avg_GPM_fmt'      : 'Avg GPM',
                'Produk_Dibeli'    : 'Model Produk'
            }
        ),
        use_container_width=True,
        hide_index=True
    )

    # ── INSIGHT BOX ───────────────────────────────────────────────────────────
    best = agg_produk.loc[agg_produk['Total_Profit'].idxmax()]
    worst = agg_produk.loc[agg_produk['Avg_GPM'].idxmin()]
    st.markdown(f"""
    <div class='info-box'>
        <b>💡 Auto-Insight untuk {sel_wil_tab2}:</b><br>
        • <b>Best performer:</b> <i>{best['Label_Produk']}</i>
          — Total Profit {fmt_idr(best['Total_Profit'])}, GPM {best['Avg_GPM']:.1f}%
          ({int(best['Volume']):,} unit terjual).<br>
        • <b>Perlu evaluasi:</b> <i>{worst['Label_Produk']}</i>
          — GPM terendah {worst['Avg_GPM']:.1f}%,
          kemungkinan beban logistik atau HPP terlalu tinggi untuk wilayah ini.
    </div>
    """, unsafe_allow_html=True)
