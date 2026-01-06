# -*- coding: utf-8 -*-
"""
SIMULATION ENGINE - Queue Optimization System
Berbasis logika SimPy dari ta14_model.py
"""

import simpy
import random
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

# ===================================================================
# KONFIGURASI DEFAULT
# ===================================================================
@dataclass
class SimulationConfig:
    """Konfigurasi parameter simulasi."""
    random_seed: int = 42
    sim_time: int = 1000          # Durasi simulasi (menit)
    avg_arrival: float = 3.0      # Rata-rata kedatangan (menit per mobil)
    min_service: float = 5.0      # Minimum waktu layanan (menit)
    max_service: float = 10.0     # Maximum waktu layanan (menit)
    num_windows: int = 1          # Jumlah jendela layanan


# ===================================================================
# PROSES SIMULASI
# ===================================================================
def drive_thru_customer(
    env: simpy.Environment,
    name: str,
    windows: simpy.Resource,
    output_records: List[Dict],
    config: SimulationConfig
) -> None:
    """
    Proses pelanggan drive-thru.
    
    Args:
        env: SimPy environment
        name: Identitas pelanggan
        windows: Resource jendela layanan
        output_records: List untuk menyimpan hasil
        config: Konfigurasi simulasi
    """
    arrival_time = env.now

    # 1. Mobil meminta akses ke jendela layanan (Resource)
    with windows.request() as request:
        yield request  # Menunggu jika semua jendela penuh

        start_service = env.now
        waiting_time = start_service - arrival_time

        # 2. Proses Layanan (Distribusi Uniform)
        service_duration = random.uniform(config.min_service, config.max_service)
        yield env.timeout(service_duration)

        finish_time = env.now

        # 3. Logging: Menyimpan data ke dalam list
        output_records.append({
            "customer_id": name,
            "arrival_time": round(arrival_time, 2),
            "waiting_time": round(waiting_time, 2),
            "service_duration": round(service_duration, 2),
            "finish_time": round(finish_time, 2),
            "system_time": round(finish_time - arrival_time, 2)
        })


def customer_generator(
    env: simpy.Environment,
    windows: simpy.Resource,
    output_records: List[Dict],
    config: SimulationConfig
) -> None:
    """
    Generator kedatangan pelanggan dengan distribusi eksponensial.
    
    Args:
        env: SimPy environment
        windows: Resource jendela layanan
        output_records: List untuk menyimpan hasil
        config: Konfigurasi simulasi
    """
    i = 0
    while True:
        # Kedatangan acak (Distribusi Eksponensial)
        yield env.timeout(random.expovariate(1.0 / config.avg_arrival))
        i += 1
        env.process(drive_thru_customer(
            env, f"Mobil {i}", windows, output_records, config
        ))


# ===================================================================
# FUNGSI UTAMA SIMULASI
# ===================================================================
def run_simulation(
    num_windows: int = 1,
    avg_arrival: float = 3.0,
    sim_time: int = 1000,
    random_seed: int = 42
) -> pd.DataFrame:
    """
    Menjalankan simulasi antrian drive-thru.
    
    Args:
        num_windows: Jumlah jendela layanan (1-5)
        avg_arrival: Rata-rata waktu antar kedatangan (menit)
        sim_time: Durasi simulasi (menit)
        random_seed: Seed untuk random number generator
        
    Returns:
        DataFrame dengan hasil simulasi
    """
    # Inisialisasi konfigurasi
    config = SimulationConfig(
        random_seed=random_seed,
        sim_time=sim_time,
        avg_arrival=avg_arrival,
        num_windows=num_windows
    )
    
    # Reset random seed
    random.seed(config.random_seed)
    
    # List untuk menyimpan hasil
    records = []
    
    # Inisialisasi environment SimPy
    env = simpy.Environment()
    windows = simpy.Resource(env, capacity=config.num_windows)
    
    # Jalankan simulasi
    env.process(customer_generator(env, windows, records, config))
    env.run(until=config.sim_time)
    
    # Konversi ke DataFrame
    df = pd.DataFrame(records)
    
    if len(df) > 0:
        df['car_number'] = range(1, len(df) + 1)
    
    return df


def run_benchmark_simulations(
    avg_arrival: float = 3.0,
    sim_time: int = 1000,
    random_seed: int = 42
) -> Dict[int, pd.DataFrame]:
    """
    Menjalankan simulasi benchmark untuk 1-5 jendela.
    
    Args:
        avg_arrival: Rata-rata waktu antar kedatangan
        sim_time: Durasi simulasi
        random_seed: Seed untuk konsistensi
        
    Returns:
        Dictionary dengan DataFrame untuk setiap skenario jendela
    """
    benchmarks = {}
    
    for num_windows in range(1, 6):
        df = run_simulation(
            num_windows=num_windows,
            avg_arrival=avg_arrival,
            sim_time=sim_time,
            random_seed=random_seed
        )
        benchmarks[num_windows] = df
        
    return benchmarks


def get_simulation_stats(df: pd.DataFrame) -> Dict:
    """
    Menghitung statistik dari hasil simulasi.
    
    Args:
        df: DataFrame hasil simulasi
        
    Returns:
        Dictionary berisi statistik kunci
    """
    if len(df) == 0:
        return {
            "total_served": 0,
            "avg_wait": 0,
            "max_wait": 0,
            "min_wait": 0,
            "std_wait": 0,
            "avg_system_time": 0,
            "avg_service_time": 0,
            "throughput_per_hour": 0
        }
    
    return {
        "total_served": len(df),
        "avg_wait": round(df['waiting_time'].mean(), 2),
        "max_wait": round(df['waiting_time'].max(), 2),
        "min_wait": round(df['waiting_time'].min(), 2),
        "std_wait": round(df['waiting_time'].std(), 2),
        "avg_system_time": round(df['system_time'].mean(), 2),
        "avg_service_time": round(df['service_duration'].mean(), 2),
        "throughput_per_hour": round(len(df) / (df['finish_time'].max() / 60), 2) if df['finish_time'].max() > 0 else 0
    }


def create_summary_dataframe(
    benchmarks: Dict[int, pd.DataFrame]
) -> pd.DataFrame:
    """
    Membuat tabel ringkasan perbandingan semua skenario.
    
    Args:
        benchmarks: Dictionary hasil simulasi benchmark
        
    Returns:
        DataFrame ringkasan
    """
    summary_data = []
    
    status_map = {
        1: "🔴 Kritis - Sangat Macet",
        2: "🟡 Tidak Stabil",
        3: "🟢 Stabil & Optimal",
        4: "🟢 Sangat Optimal",
        5: "🟢 Over-capacity"
    }
    
    for num_windows, df in benchmarks.items():
        stats = get_simulation_stats(df)
        
        # Determine status based on wait time
        if stats['avg_wait'] > 60:
            status = "🔴 Kritis"
        elif stats['avg_wait'] > 15:
            status = "🟡 Tidak Stabil"
        elif stats['avg_wait'] > 5:
            status = "🟢 Stabil"
        else:
            status = "🟢 Optimal"
        
        summary_data.append({
            "Jendela": num_windows,
            "Total Mobil": stats['total_served'],
            "Rata-rata Tunggu (mnt)": stats['avg_wait'],
            "Max Tunggu (mnt)": stats['max_wait'],
            "Throughput/Jam": stats['throughput_per_hour'],
            "Status": status
        })
    
    return pd.DataFrame(summary_data)


def get_system_status(avg_wait: float) -> Tuple[str, str, str]:
    """
    Menentukan status sistem berdasarkan rata-rata waktu tunggu.
    
    Args:
        avg_wait: Rata-rata waktu tunggu dalam menit
        
    Returns:
        Tuple (status_text, status_class, status_color)
    """
    if avg_wait > 60:
        return ("BOTTLENECK KRITIS", "status-critical", "#ef4444")
    elif avg_wait > 15:
        return ("TIDAK STABIL", "status-unstable", "#facc15")
    elif avg_wait > 10:
        return ("STABIL", "status-optimal", "#22c55e")
    else:
        return ("OPTIMAL", "status-optimal", "#22c55e")


# ===================================================================
# TESTING
# ===================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("QUEUE OPTIMIZATION ENGINE - Test Run")
    print("=" * 60)
    
    # Test single simulation
    print("\n[TEST 1] Single Simulation - 2 Windows")
    df = run_simulation(num_windows=2, avg_arrival=3.0)
    stats = get_simulation_stats(df)
    print(f"Total mobil dilayani: {stats['total_served']}")
    print(f"Rata-rata waktu tunggu: {stats['avg_wait']} menit")
    print(f"Waktu tunggu maksimum: {stats['max_wait']} menit")
    
    # Test benchmark
    print("\n[TEST 2] Benchmark Simulations")
    benchmarks = run_benchmark_simulations()
    summary = create_summary_dataframe(benchmarks)
    print(summary.to_string(index=False))
    
    print("\n✅ Semua test berhasil!")
