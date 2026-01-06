# -*- coding: utf-8 -*-
"""
QUEUE OPTIMIZATION ENGINE
Aplikasi Streamlit dengan UI Ethereal Glassmorphism
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from pathlib import Path

# Import modul simulasi
from simulation import (
    run_simulation,
    run_benchmark_simulations,
    get_simulation_stats,
    create_summary_dataframe,
    get_system_status
)

# ===================================================================
# KONFIGURASI HALAMAN
# ===================================================================
st.set_page_config(
    page_title="Queue Optimizer System",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ===================================================================
# LOAD CSS
# ===================================================================
def load_css():
    """Memuat custom CSS dari file."""
    css_path = Path(__file__).parent / "static" / "style.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        # Fallback CSS jika file tidak ditemukan
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Orbitron:wght@400;500;600;700;800;900&display=swap');
        
        #MainMenu {visibility: hidden !important;}
        footer {visibility: hidden !important;}
        header {visibility: hidden !important;}
        
        .stApp {
            background: #050505 !important;
        }
        </style>
        """, unsafe_allow_html=True)

load_css()

# ===================================================================
# SESSION STATE INITIALIZATION
# ===================================================================
if 'page' not in st.session_state:
    st.session_state.page = 'dashboard'

# Backward-compat (some parts of the app still reference `current_page`)
if 'current_page' not in st.session_state:
    st.session_state.current_page = st.session_state.page

if 'simulation_results' not in st.session_state:
    st.session_state.simulation_results = None

if 'benchmark_data' not in st.session_state:
    st.session_state.benchmark_data = None

# ===================================================================
# CUSTOM NAVIGATION
# ===================================================================
def _set_page(page: str):
    st.session_state.page = page
    st.session_state.current_page = page

def render_navbar():
    """Render floating navbar dengan HTML/CSS."""
    nav_html = f"""
    <div class="floating-navbar">
        <div style="display: flex; align-items: center; gap: 0.5rem; margin-right: 2rem;">
            <span style="font-size: 1.5rem;">🚀</span>
            <span style="font-family: 'Orbitron', monospace; font-weight: 700; color: #00d4ff; font-size: 0.9rem;">QOS</span>
        </div>
        <button class="nav-item {'active' if st.session_state.page == 'dashboard' else ''}">
            📊 Dashboard
        </button>
        <button class="nav-item {'active' if st.session_state.page == 'analysis' else ''}">
            📈 Analisis Historis
        </button>
        <button class="nav-item {'active' if st.session_state.page == 'about' else ''}">
            ℹ️ Tentang
        </button>
    </div>
    """
    st.markdown(nav_html, unsafe_allow_html=True)

    # Click bridge (SPA): invisible Streamlit buttons positioned on top of the HTML navbar.
    # Important: we must not change CSS files/templates, so we inject minimal CSS here.
    st.markdown(
        """
        <style>
        /* Ensure overlay does not occupy layout space and never shows visible buttons */
        .nav-overlay-root {
            position: fixed;
            top: 1rem;
            left: 50%;
            transform: translateX(-50%);
            z-index: 10000;
            width: fit-content;
            height: 0;
            pointer-events: none;
        }

        .nav-overlay-root * {
            pointer-events: auto;
        }

        /* Force the Streamlit button visuals to be fully transparent in the overlay */
        .nav-overlay-root .stButton > button,
        .nav-overlay-root [data-testid="stButton"] > button {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: transparent !important;
            padding: 0.5rem 1.5rem !important;
            border-radius: 25px !important;
            min-height: 2.3rem !important;
            height: 2.3rem !important;
        }

        .nav-overlay-root .stButton > button:hover,
        .nav-overlay-root [data-testid="stButton"] > button:hover {
            background: transparent !important;
        }

        /* Remove any margins/gaps so overlay doesn't push content */
        .nav-overlay-root [data-testid="stHorizontalBlock"] {
            gap: 0 !important;
        }
        .nav-overlay-root [data-testid="column"] {
            padding: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Render overlay in a zero-height container, fixed-positioned.
    overlay = st.container()
    with overlay:
        st.markdown('<div class="nav-overlay-root">', unsafe_allow_html=True)
        cols = st.columns([2.2, 1, 1.2, 0.8], gap="small")
        with cols[0]:
            st.markdown("", unsafe_allow_html=True)
        with cols[1]:
            st.button("\u200b", key="nav_spa_dashboard", on_click=_set_page, args=("dashboard",))
        with cols[2]:
            st.button("\u200b", key="nav_spa_analysis", on_click=_set_page, args=("analysis",))
        with cols[3]:
            st.button("\u200b", key="nav_spa_about", on_click=_set_page, args=("about",))
        st.markdown("</div>", unsafe_allow_html=True)

# Spacer untuk navbar
st.markdown("<div style='height: 80px;'></div>", unsafe_allow_html=True)

# ===================================================================
# HERO SECTION
# ===================================================================
def render_hero(status_text: str, status_class: str):
    """Render hero section dengan status dinamis."""
    hero_html = f"""
    <div class="hero-section">
        <h1 class="hero-title">Queue Optimizer System</h1>
        <p class="hero-subtitle">Simulasi & Optimasi Antrian Drive-Thru Berbasis SimPy</p>
        <div class="status-indicator {status_class}">
            <span class="status-dot"></span>
            <span>{status_text}</span>
        </div>
    </div>
    """
    st.markdown(hero_html, unsafe_allow_html=True)

# ===================================================================
# METRIC CARDS
# ===================================================================
def render_metric_card(label: str, value: str, unit: str = "", color_class: str = ""):
    """Render single metric card."""
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {color_class}">{value}</div>
        <div class="metric-unit">{unit}</div>
    </div>
    """

def render_metrics_row(stats: dict, avg_wait: float):
    """Render baris metric cards."""
    # Tentukan warna berdasarkan performa
    if avg_wait > 60:
        wait_color = "danger"
    elif avg_wait > 15:
        wait_color = "warning"
    else:
        wait_color = "success"
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(render_metric_card(
            "Total Throughput",
            str(stats['total_served']),
            "mobil dilayani",
            "success"
        ), unsafe_allow_html=True)
    
    with col2:
        st.markdown(render_metric_card(
            "Rata-rata Tunggu",
            f"{stats['avg_wait']:.1f}",
            "menit",
            wait_color
        ), unsafe_allow_html=True)
    
    with col3:
        st.markdown(render_metric_card(
            "Waktu Tunggu Maks",
            f"{stats['max_wait']:.1f}",
            "menit",
            "warning" if stats['max_wait'] > 30 else ""
        ), unsafe_allow_html=True)
    
    with col4:
        st.markdown(render_metric_card(
            "Throughput/Jam",
            f"{stats['throughput_per_hour']:.1f}",
            "mobil/jam",
            ""
        ), unsafe_allow_html=True)

# ===================================================================
# PLOTLY CHARTS
# ===================================================================
def create_wait_time_chart(df: pd.DataFrame, benchmarks: dict = None) -> go.Figure:
    """Membuat chart waktu tunggu dengan style cyberpunk."""
    fig = go.Figure()
    
    # Plot data simulasi saat ini
    fig.add_trace(go.Scatter(
        x=df['car_number'] if 'car_number' in df.columns else list(range(1, len(df) + 1)),
        y=df['waiting_time'],
        mode='lines',
        name='Simulasi Saat Ini',
        line=dict(color='#00d4ff', width=2),
        fill='tozeroy',
        fillcolor='rgba(0, 212, 255, 0.1)'
    ))
    
    # Tambahkan benchmark jika ada
    if benchmarks:
        colors = {
            1: 'rgba(239, 68, 68, 0.5)',   # Red
            2: 'rgba(250, 204, 21, 0.5)',   # Yellow
        }
        
        for windows, bench_df in benchmarks.items():
            if windows in [1, 2] and len(bench_df) > 0:
                fig.add_trace(go.Scatter(
                    x=list(range(1, len(bench_df) + 1)),
                    y=bench_df['waiting_time'],
                    mode='lines',
                    name=f'Benchmark {windows} Jendela',
                    line=dict(color=colors.get(windows, '#ffffff'), width=1, dash='dot'),
                    opacity=0.6
                ))
    
    # Layout styling
    fig.update_layout(
        title=dict(
            text='📈 Tren Waktu Tunggu per Mobil',
            font=dict(family='Orbitron', size=18, color='#f0f0f0')
        ),
        xaxis=dict(
            title=dict(text='Urutan Mobil Datang', font=dict(family='Inter', size=12, color='#a0a0a0')),
            tickfont=dict(family='Inter', size=10, color='#808080'),
            gridcolor='rgba(255, 255, 255, 0.05)',
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            title=dict(text='Waktu Tunggu (menit)', font=dict(family='Inter', size=12, color='#a0a0a0')),
            tickfont=dict(family='Inter', size=10, color='#808080'),
            gridcolor='rgba(255, 255, 255, 0.05)',
            showgrid=True,
            zeroline=False
        ),
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        legend=dict(
            font=dict(family='Inter', size=11, color='#a0a0a0'),
            bgcolor='rgba(15, 15, 25, 0.8)',
            bordercolor='rgba(255, 255, 255, 0.1)',
            borderwidth=1
        ),
        margin=dict(l=50, r=30, t=60, b=50),
        hovermode='x unified'
    )
    
    return fig


def create_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """Membuat histogram distribusi waktu tunggu."""
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=df['waiting_time'],
        nbinsx=25,
        marker=dict(
            color='rgba(168, 85, 247, 0.6)',
            line=dict(color='#a855f7', width=1)
        ),
        name='Distribusi'
    ))
    
    # Tambahkan garis rata-rata
    avg_wait = df['waiting_time'].mean()
    fig.add_vline(
        x=avg_wait,
        line=dict(color='#00d4ff', width=2, dash='dash'),
        annotation=dict(
            text=f'Rata-rata: {avg_wait:.1f} mnt',
            font=dict(color='#00d4ff', family='Inter'),
            bgcolor='rgba(0, 0, 0, 0.7)'
        )
    )
    
    fig.update_layout(
        title=dict(
            text='📊 Distribusi Waktu Tunggu',
            font=dict(family='Orbitron', size=18, color='#f0f0f0')
        ),
        xaxis=dict(
            title=dict(text='Waktu Tunggu (menit)', font=dict(family='Inter', size=12, color='#a0a0a0')),
            tickfont=dict(family='Inter', size=10, color='#808080'),
            gridcolor='rgba(255, 255, 255, 0.05)'
        ),
        yaxis=dict(
            title=dict(text='Frekuensi', font=dict(family='Inter', size=12, color='#a0a0a0')),
            tickfont=dict(family='Inter', size=10, color='#808080'),
            gridcolor='rgba(255, 255, 255, 0.05)'
        ),
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        bargap=0.1,
        margin=dict(l=50, r=30, t=60, b=50)
    )
    
    return fig


def create_comparison_chart(summary_df: pd.DataFrame) -> go.Figure:
    """Membuat chart perbandingan antar skenario."""
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=['Rata-rata Waktu Tunggu', 'Total Throughput'],
        specs=[[{"type": "bar"}, {"type": "bar"}]]
    )
    
    # Bar chart waktu tunggu
    colors = ['#ef4444' if x > 60 else '#facc15' if x > 15 else '#22c55e' 
              for x in summary_df['Rata-rata Tunggu (mnt)']]
    
    fig.add_trace(
        go.Bar(
            x=[f"{j} Jendela" for j in summary_df['Jendela']],
            y=summary_df['Rata-rata Tunggu (mnt)'],
            marker_color=colors,
            name='Waktu Tunggu',
            text=[f"{v:.1f}" for v in summary_df['Rata-rata Tunggu (mnt)']],
            textposition='outside',
            textfont=dict(color='#f0f0f0', family='Orbitron')
        ),
        row=1, col=1
    )
    
    # Bar chart throughput
    fig.add_trace(
        go.Bar(
            x=[f"{j} Jendela" for j in summary_df['Jendela']],
            y=summary_df['Total Mobil'],
            marker_color='#00d4ff',
            name='Throughput',
            text=summary_df['Total Mobil'],
            textposition='outside',
            textfont=dict(color='#f0f0f0', family='Orbitron')
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        title=dict(
            text='🔄 Perbandingan Performa Antar Skenario',
            font=dict(family='Orbitron', size=18, color='#f0f0f0')
        ),
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        showlegend=False,
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    fig.update_xaxes(
        tickfont=dict(family='Inter', size=10, color='#808080'),
        gridcolor='rgba(255, 255, 255, 0.05)'
    )
    fig.update_yaxes(
        tickfont=dict(family='Inter', size=10, color='#808080'),
        gridcolor='rgba(255, 255, 255, 0.05)'
    )
    
    # Update subplot titles
    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(family='Inter', size=14, color='#a0a0a0')
    
    return fig

# ===================================================================
# HALAMAN: DASHBOARD
# ===================================================================
def render_dashboard():
    """Render halaman dashboard utama."""
    
    # Control Panel
    st.markdown("""
    <div class="control-panel">
        <div class="control-title">Panel Kontrol Simulasi</div>
    </div>
    """, unsafe_allow_html=True)
    
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 2, 1])
    
    with col_ctrl1:
        avg_arrival = st.slider(
            "⏱️ Rata-rata Kedatangan (menit/mobil)",
            min_value=1.0,
            max_value=10.0,
            value=3.0,
            step=0.5,
            help="Semakin kecil nilai = semakin padat kedatangan"
        )
    
    with col_ctrl2:
        num_windows = st.slider(
            "🪟 Jumlah Jendela Layanan",
            min_value=1,
            max_value=5,
            value=2,
            step=1,
            help="Jumlah counter/jendela yang melayani pelanggan"
        )
    
    with col_ctrl3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        run_benchmark = st.checkbox("🔄 Tampilkan Benchmark", value=True)
    
    # Jalankan simulasi
    with st.spinner("⚡ Menjalankan simulasi..."):
        df = run_simulation(
            num_windows=num_windows,
            avg_arrival=avg_arrival,
            sim_time=1000
        )
        
        benchmarks = None
        if run_benchmark:
            benchmarks = {
                1: run_simulation(num_windows=1, avg_arrival=avg_arrival),
                2: run_simulation(num_windows=2, avg_arrival=avg_arrival)
            }
        
        stats = get_simulation_stats(df)
        status_text, status_class, status_color = get_system_status(stats['avg_wait'])
    
    # Hero Section dengan status
    render_hero(status_text, status_class)
    
    # Divider
    st.markdown('<div class="neon-divider"></div>', unsafe_allow_html=True)
    
    # Metrics Row
    st.markdown("""
    <div class="section-header">Metrik Performa Real-time</div>
    """, unsafe_allow_html=True)
    render_metrics_row(stats, stats['avg_wait'])
    
    # Spacer
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    
    # Charts
    col_chart1, col_chart2 = st.columns([3, 2])
    
    with col_chart1:
        fig_trend = create_wait_time_chart(df, benchmarks)
        st.plotly_chart(fig_trend, use_container_width=True)
    
    with col_chart2:
        fig_dist = create_distribution_chart(df)
        st.plotly_chart(fig_dist, use_container_width=True)
    
    # Tabel Summary jika benchmark aktif
    if run_benchmark:
        st.markdown('<div class="neon-divider"></div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="section-header">Tabel Perbandingan Skenario</div>
        """, unsafe_allow_html=True)
        
        all_benchmarks = run_benchmark_simulations(avg_arrival=avg_arrival)
        summary_df = create_summary_dataframe(all_benchmarks)
        
        # Styled dataframe
        def color_wait_time(val):
            if isinstance(val, (int, float)):
                if val > 60:
                    return 'background: linear-gradient(90deg, rgba(239, 68, 68, 0.3), transparent); color: #ef4444;'
                elif val > 15:
                    return 'background: linear-gradient(90deg, rgba(250, 204, 21, 0.3), transparent); color: #facc15;'
                else:
                    return 'background: linear-gradient(90deg, rgba(34, 197, 94, 0.3), transparent); color: #22c55e;'
            return ''
        
        styled_df = summary_df.style.applymap(
            color_wait_time,
            subset=['Rata-rata Tunggu (mnt)', 'Max Tunggu (mnt)']
        ).format({
            'Rata-rata Tunggu (mnt)': '{:.2f}',
            'Max Tunggu (mnt)': '{:.2f}',
            'Throughput/Jam': '{:.1f}'
        })
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # Comparison Chart
        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
        fig_comparison = create_comparison_chart(summary_df)
        st.plotly_chart(fig_comparison, use_container_width=True)

# ===================================================================
# HALAMAN: ANALISIS HISTORIS
# ===================================================================
def render_analysis():
    """Render halaman analisis historis."""
    
    st.markdown("""
    <div class="hero-section">
        <h1 class="hero-title">Analisis Historis</h1>
        <p class="hero-subtitle">Analisis mendalam performa sistem antrian</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="neon-divider"></div>', unsafe_allow_html=True)
    
    # Parameter untuk analisis
    st.markdown("""
    <div class="section-header">Parameter Analisis</div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        sim_duration = st.selectbox(
            "📅 Durasi Simulasi",
            options=[500, 1000, 2000, 5000],
            index=1,
            format_func=lambda x: f"{x} menit ({x/60:.1f} jam)"
        )
    
    with col2:
        arrival_rate = st.selectbox(
            "🚗 Tingkat Kedatangan",
            options=[1.5, 2.0, 3.0, 4.0, 5.0],
            index=2,
            format_func=lambda x: f"1 mobil per {x} menit"
        )
    
    # Jalankan semua benchmark
    if st.button("🔬 Jalankan Analisis Lengkap", use_container_width=True):
        with st.spinner("⚡ Menganalisis semua skenario..."):
            benchmarks = run_benchmark_simulations(
                avg_arrival=arrival_rate,
                sim_time=sim_duration
            )
            
            st.session_state.benchmark_data = benchmarks
    
    # Tampilkan hasil jika ada
    if st.session_state.benchmark_data:
        benchmarks = st.session_state.benchmark_data
        
        st.markdown('<div class="neon-divider"></div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="section-header">Hasil Analisis Lengkap</div>
        """, unsafe_allow_html=True)
        
        # Tabs untuk setiap skenario
        tabs = st.tabs([f"🪟 {i} Jendela" for i in range(1, 6)])
        
        for idx, (num_windows, df) in enumerate(benchmarks.items()):
            with tabs[idx]:
                stats = get_simulation_stats(df)
                status_text, status_class, _ = get_system_status(stats['avg_wait'])
                
                # Mini metrics
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric("Total Dilayani", f"{stats['total_served']} mobil")
                with m2:
                    st.metric("Rata-rata Tunggu", f"{stats['avg_wait']:.1f} menit")
                with m3:
                    st.metric("Max Tunggu", f"{stats['max_wait']:.1f} menit")
                with m4:
                    st.metric("Status", status_text)
                
                # Chart
                fig = create_wait_time_chart(df)
                st.plotly_chart(fig, use_container_width=True)
                
                # Detail stats dalam expander
                with st.expander("📊 Statistik Detail"):
                    st.json(stats)

# ===================================================================
# HALAMAN: TENTANG
# ===================================================================
def render_about():
    """Render halaman tentang."""
    
    st.markdown("""
    <div class="hero-section">
        <h1 class="hero-title">Tentang Sistem</h1>
        <p class="hero-subtitle">Queue Optimization Engine v1.0</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="neon-divider"></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="glass-card">
            <h3 style="color: #00d4ff; font-family: 'Orbitron', monospace;">🎯 Tujuan Sistem</h3>
            <p style="color: #a0a0a0; font-family: 'Inter', sans-serif; line-height: 1.8;">
                Queue Optimization Engine adalah aplikasi simulasi berbasis SimPy yang dirancang 
                untuk menganalisis dan mengoptimalkan sistem antrian drive-thru. Sistem ini 
                memungkinkan pengguna untuk bereksperimen dengan berbagai konfigurasi 
                jendela layanan dan tingkat kedatangan pelanggan.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="glass-card" style="margin-top: 1rem;">
            <h3 style="color: #a855f7; font-family: 'Orbitron', monospace;">⚙️ Teknologi</h3>
            <ul style="color: #a0a0a0; font-family: 'Inter', sans-serif; line-height: 2;">
                <li><strong>SimPy</strong> - Discrete Event Simulation</li>
                <li><strong>Streamlit</strong> - Web Application Framework</li>
                <li><strong>Plotly</strong> - Interactive Visualizations</li>
                <li><strong>Pandas</strong> - Data Analysis</li>
                <li><strong>NumPy</strong> - Numerical Computing</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="glass-card">
            <h3 style="color: #22c55e; font-family: 'Orbitron', monospace;">📐 Model Simulasi</h3>
            <p style="color: #a0a0a0; font-family: 'Inter', sans-serif; line-height: 1.8;">
                <strong>Distribusi Kedatangan:</strong> Eksponensial<br>
                <strong>Distribusi Layanan:</strong> Uniform (5-10 menit)<br>
                <strong>Tipe Antrian:</strong> FIFO (First In First Out)<br>
                <strong>Durasi Default:</strong> 1000 menit simulasi
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="glass-card" style="margin-top: 1rem;">
            <h3 style="color: #facc15; font-family: 'Orbitron', monospace;">📊 Indikator Status</h3>
            <p style="color: #a0a0a0; font-family: 'Inter', sans-serif; line-height: 2;">
                🟢 <strong style="color: #22c55e;">OPTIMAL</strong> - Waktu tunggu < 10 menit<br>
                🟡 <strong style="color: #facc15;">TIDAK STABIL</strong> - Waktu tunggu 15-60 menit<br>
                🔴 <strong style="color: #ef4444;">KRITIS</strong> - Waktu tunggu > 60 menit
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
    <div class="custom-footer">
        <p>Dibuat dengan ❤️ menggunakan Streamlit | TA-14 Pemodelan & Simulasi</p>
        <p style="font-size: 0.75rem; margin-top: 0.5rem;">© 2026 Queue Optimization Engine</p>
    </div>
    """, unsafe_allow_html=True)

# ===================================================================
# ROUTING & MAIN
# ===================================================================
def main():
    """Fungsi utama aplikasi."""
    
    # Check URL params untuk navigasi
    query_params = st.query_params
    if 'page' in query_params:
        page_param = query_params.get('page')
        if isinstance(page_param, list):
            page_param = page_param[0] if page_param else None
        _set_page(page_param)

    render_navbar()
    
    # Sidebar untuk mobile navigation
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <span style="font-size: 2rem;">🚀</span>
            <h2 style="color: #00d4ff; font-family: 'Orbitron', monospace; margin-top: 0.5rem;">QOS</h2>
            <p style="color: #a0a0a0; font-size: 0.8rem;">Queue Optimizer System</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.button("📊 Dashboard", use_container_width=True):
            _set_page('dashboard')
            st.rerun()
        
        if st.button("📈 Analisis Historis", use_container_width=True):
            _set_page('analysis')
            st.rerun()
        
        if st.button("ℹ️ Tentang", use_container_width=True):
            _set_page('about')
            st.rerun()
    
    # Render halaman berdasarkan state
    if st.session_state.page == 'dashboard':
        render_dashboard()
    elif st.session_state.page == 'analysis':
        render_analysis()
    elif st.session_state.page == 'about':
        render_about()
    else:
        render_dashboard()

if __name__ == "__main__":
    main()
