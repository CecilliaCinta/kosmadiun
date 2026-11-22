import pandas as pd
import json
import matplotlib
matplotlib.use("Agg")

from matplotlib.ticker import FuncFormatter

import matplotlib.pyplot as plt
import io
import base64

from pathlib import Path
from groq import Groq

from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Kos


# ==========================================
# FUNGSI FUZZY LOGIC
# ==========================================

def fuzzy_kiri(nilai, batas_awal, batas_akhir):
    if nilai <= batas_awal:
        return 1
    elif nilai >= batas_akhir:
        return 0
    else:
        return (batas_akhir - nilai) / (batas_akhir - batas_awal)


def fuzzy_kanan(nilai, batas_awal, batas_akhir):
    if nilai <= batas_awal:
        return 0
    elif nilai >= batas_akhir:
        return 1
    else:
        return (nilai - batas_awal) / (batas_akhir - batas_awal)


def fuzzy_segitiga(nilai, batas_bawah, titik_tengah, batas_atas):
    if nilai <= batas_bawah or nilai >= batas_atas:
        return 0
    elif nilai == titik_tengah:
        return 1
    elif nilai < titik_tengah:
        return (nilai - batas_bawah) / (titik_tengah - batas_bawah)
    else:
        return (batas_atas - nilai) / (batas_atas - titik_tengah)


def hitung_fuzzy(harga, jarak, rating):

    # Fuzzy harga
    harga_murah = fuzzy_kiri(harga, 500, 800)
    harga_sedang = fuzzy_segitiga(harga, 500, 900, 1300)
    harga_mahal = fuzzy_kanan(harga, 1000, 1500)

    # Fuzzy jarak
    jarak_dekat = fuzzy_kiri(jarak, 1, 2)
    jarak_sedang = fuzzy_segitiga(jarak, 1, 3, 5)
    jarak_jauh = fuzzy_kanan(jarak, 3, 5)

    # Fuzzy rating
    rating_rendah = fuzzy_kiri(rating, 2.5, 3.5)
    rating_sedang = fuzzy_segitiga(rating, 2.5, 3.5, 4.5)
    rating_tinggi = fuzzy_kanan(rating, 3.5, 4.5)

    # Menggabungkan nilai keanggotaan
    daftar_harga = [harga_murah, harga_sedang, harga_mahal]
    daftar_jarak = [jarak_dekat, jarak_sedang, jarak_jauh]
    daftar_rating = [rating_rendah, rating_sedang, rating_tinggi]

    total_nilai = 0
    total_bobot = 0

    # Menghitung kekuatan setiap aturan Fuzzy
    for i in range(3):
        for j in range(3):
            for k in range(3):

                kekuatan = min(
                    daftar_harga[i],
                    daftar_jarak[j],
                    daftar_rating[k]
                )

                tingkat_harga = 2 - i
                tingkat_jarak = 2 - j
                tingkat_rating = k

                nilai_output = (
                    (tingkat_harga + tingkat_jarak + tingkat_rating) / 6
                ) * 100

                total_nilai += kekuatan * nilai_output
                total_bobot += kekuatan

    # Defuzzifikasi metode rata-rata terbobot
    if total_bobot == 0:
        skor = 0
    else:
        skor = total_nilai / total_bobot

    skor = round(skor, 2)

    # Menentukan kategori kelayakan
    if skor >= 70:
        kategori = "Layak"
    elif skor >= 40:
        kategori = "Cukup Layak"
    else:
        kategori = "Kurang Layak"

    return skor, kategori


# ==========================================
# HALAMAN DASHBOARD
# ==========================================



def dashboard(request):

    print("FUNGSI DASHBOARD DIJALANKAN")

    # Mengambil data kos dari database
    daftar_kos = Kos.objects.all()

    # Mengubah data database menjadi DataFrame
    df = pd.DataFrame(list(daftar_kos.values()))

    # Mengubah data database menjadi daftar
    data_kos = df.to_dict(orient="records")

    # Menghitung informasi dataset
    jumlah_kos = len(df)
    rata_rata = df["harga"].mean()
    harga_termurah = df["harga"].min()
    harga_termahal = df["harga"].max()

    # Menghitung harga dan nilai Fuzzy setiap kos
    for kos in data_kos:
        kos["harga_rupiah"] = kos["harga"] * 1000

        skor, kategori = hitung_fuzzy(
            float(kos["harga"]),
            float(kos["jarak_km"]),
            float(kos["rating"])
        )

        kos["skor_fuzzy"] = skor
        kos["kategori_fuzzy"] = kategori

    # Menyiapkan data untuk grafik Matplotlib
    nama_kos = df["nama"].tolist()
    harga_kos = (df["harga"] * 1000).tolist()

    # Membuat grafik
    plt.figure(figsize=(14, 6))
    plt.bar(nama_kos, harga_kos, color="#ec4899")

    plt.title("Perbandingan Harga Kos di Madiun")
    plt.xlabel("Nama Kos")
    plt.ylabel("Harga Kos (Rupiah)")

    plt.gca().yaxis.set_major_formatter(
    FuncFormatter(lambda x, _: "Rp " + f"{x:,.0f}".replace(",", "."))
    )

    plt.xticks(rotation=90, fontsize=8)
    plt.tight_layout()

    # Menyimpan grafik ke memori
    gambar = io.BytesIO()
    plt.savefig(gambar, format="png")
    gambar.seek(0)

    # Mengubah gambar menjadi Base64
    grafik = base64.b64encode(
        gambar.getvalue()
    ).decode("utf-8")

    print("GRAFIK BERHASIL DIBUAT:", len(grafik))

    # Membersihkan grafik
    plt.close()

    # Mengirim data ke halaman HTML
    context = {
        "data_kos": data_kos,
        "jumlah_kos": jumlah_kos,
        "rata_rata": rata_rata * 1000,
        "harga_termurah": harga_termurah * 1000,
        "harga_termahal": harga_termahal * 1000,
        "nama_kos": nama_kos,
        "harga_kos": harga_kos,
        "grafik": grafik,
    }

    return render(request, "dashboard/index.html", context)

# ==========================================
# HALAMAN REKOMENDASI FUZZY
# ==========================================

def rekomendasi(request):

    # Membaca dataset kos
    file_csv = Path(settings.BASE_DIR) / "dataset" / "kos_madiun.csv"
    df = pd.read_csv(file_csv)

    # Mengubah dataset menjadi daftar
    data_kos = df.to_dict(orient="records")

    # Mengambil input pengguna
    harga_maksimal = request.GET.get("harga", "")
    jarak_maksimal = request.GET.get("jarak", "")
    rating_minimal = request.GET.get("rating", "")

    hasil_rekomendasi = []

    # Menghitung Fuzzy untuk setiap kos
    for kos in data_kos:

        skor, kategori = hitung_fuzzy(
            float(kos["harga"]),
            float(kos["jarak_km"]),
            float(kos["rating"])
        )

        # Menambahkan hasil perhitungan
        kos["skor_fuzzy"] = skor
        kos["kategori_fuzzy"] = kategori
        kos["harga_rupiah"] = float(kos["harga"]) * 1000

        # Memeriksa filter pengguna
        if harga_maksimal and kos["harga_rupiah"] > float(harga_maksimal):
            continue

        if jarak_maksimal and float(kos["jarak_km"]) > float(jarak_maksimal):
            continue

        if rating_minimal and float(kos["rating"]) < float(rating_minimal):
            continue

        hasil_rekomendasi.append(kos)

    # Mengurutkan kos berdasarkan skor tertinggi
    hasil_rekomendasi = sorted(
        hasil_rekomendasi,
        key=lambda x: x["skor_fuzzy"],
        reverse=True
    )

    # Mengirim data ke halaman HTML
    context = {
        "hasil_rekomendasi": hasil_rekomendasi,
        "harga_maksimal": harga_maksimal,
        "jarak_maksimal": jarak_maksimal,
        "rating_minimal": rating_minimal,
    }

    return render(
        request,
        "dashboard/rekomendasi.html",
        context
    )


# ==========================================
# FUNGSI CHATBOT AI GROQ
# ==========================================

@require_POST
def chatbot(request):

    # Mengambil pesan dari pengguna
    data = json.loads(request.body)
    pesan = data.get("message", "")

    # Membaca dataset kos
    file_csv = Path(settings.BASE_DIR) / "dataset" / "kos_madiun.csv"
    df = pd.read_csv(file_csv)

    # Mengubah dataset menjadi informasi teks
    informasi_kos = df.to_string(index=False)

    # Menghubungkan ke Groq
    client = Groq(api_key=settings.GROQ_API_KEY)

    # Mengirim pertanyaan ke AI
    hasil = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": (
                    "Kamu adalah chatbot Sistem Informasi Kos Madiun. "
                    "Jawablah pertanyaan pengguna berdasarkan dataset berikut. "
                    "Gunakan bahasa Indonesia yang mudah dipahami.\n\n"
                    + informasi_kos
                )
            },
            {
                "role": "user",
                "content": pesan
            }
        ]
    )

   
    # Mengambil jawaban AI
    jawaban = hasil.choices[0].message.content

    return JsonResponse({
        "reply": jawaban
    })

    

@require_POST
def jelaskan_grafik(request):

    # Mengambil data kos dari database
    daftar_kos = Kos.objects.all()

    # Mengubah data menjadi DataFrame
    df = pd.DataFrame(list(daftar_kos.values()))

    # Menghitung informasi harga kos
    harga_tertinggi = df["harga"].max() * 1000
    harga_terendah = df["harga"].min() * 1000
    rata_rata = df["harga"].mean() * 1000

    # Mencari nama kos dengan harga tertinggi dan terendah
    kos_termahal = df.loc[df["harga"].idxmax(), "nama"]
    kos_termurah = df.loc[df["harga"].idxmin(), "nama"]

    # Menyiapkan informasi untuk AI
    informasi_grafik = f"""
    Jumlah kos: {len(df)}
    Kos termahal: {kos_termahal}
    Harga tertinggi: Rp {harga_tertinggi:,.0f}
    Kos termurah: {kos_termurah}
    Harga terendah: Rp {harga_terendah:,.0f}
    Rata-rata harga kos: Rp {rata_rata:,.0f}
    """

    # Menghubungkan ke Groq
    client = Groq(api_key=settings.GROQ_API_KEY)

    # Meminta AI menjelaskan grafik
    hasil = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": (
                    "Kamu adalah analis data Kos Madiun. "
                    "Jelaskan grafik perbandingan harga kos "
                    "berdasarkan informasi yang diberikan. "
                    "Gunakan bahasa Indonesia yang mudah dipahami. "
                    "Berikan penjelasan yang jelas dan sederhana.\n\n"
                    + informasi_grafik
                )
            },
            {
                "role": "user",
                "content": "Jelaskan grafik perbandingan harga kos tersebut."
            }
        ]
    )

    # Mengambil jawaban AI
    jawaban = hasil.choices[0].message.content

    return JsonResponse({
        "reply": jawaban
    })


# ==========================================
# HALAMAN DATA KOS
# ==========================================


def data_kos(request):

    # Mengambil seluruh data kos dari database
    daftar_kos = Kos.objects.all()

    # Mengirim data ke halaman HTML
    context = {
        "daftar_kos": daftar_kos,
    }

    return render(request, "dashboard/data_kos.html", context)


# ==========================================
# HALAMAN PENCARIAN KOS
# ==========================================

def pencarian_kos(request):

    # Membaca file CSV
    file_csv = Path(settings.BASE_DIR) / "dataset" / "kos_madiun.csv"
    df = pd.read_csv(file_csv)

    # Mengambil input pencarian dari pengguna
    nama_kos = request.GET.get("nama", "")
    harga_maksimal = request.GET.get("harga", "")
    jarak_maksimal = request.GET.get("jarak", "")
    rating_minimal = request.GET.get("rating", "")

    # Mengubah data CSV menjadi daftar
    daftar_kos = df.to_dict(orient="records")

    hasil_pencarian = []

    # Melakukan penyaringan data
    for kos in daftar_kos:

        # Mencari berdasarkan nama kos
        if nama_kos and nama_kos.lower() not in str(kos["nama"]).lower():
            continue

        # Mencari berdasarkan harga maksimal
        if harga_maksimal and float(kos["harga"]) * 1000 > float(harga_maksimal):
            continue

        # Mencari berdasarkan jarak maksimal
        if jarak_maksimal and float(kos["jarak_km"]) > float(jarak_maksimal):
            continue

        # Mencari berdasarkan rating minimal
        if rating_minimal and float(kos["rating"]) < float(rating_minimal):
            continue

        # Menambahkan kos yang sesuai kriteria
        kos["harga_rupiah"] = float(kos["harga"]) * 1000
        hasil_pencarian.append(kos)

    # Mengirim hasil pencarian ke halaman HTML
    context = {
        "hasil_pencarian": hasil_pencarian,
        "nama_kos": nama_kos,
        "harga_maksimal": harga_maksimal,
        "jarak_maksimal": jarak_maksimal,
        "rating_minimal": rating_minimal,
    }

    return render(request, "dashboard/pencarian_kos.html", context)


# ==========================================
# HALAMAN ANALISIS HARGA
# ==========================================

def analisis_harga(request):

    # Membaca file CSV
    file_csv = Path(settings.BASE_DIR) / "dataset" / "kos_madiun.csv"
    df = pd.read_csv(file_csv)

    # Mengubah harga menjadi rupiah
    df["harga_rupiah"] = df["harga"] * 1000

    # Menghitung informasi harga
    jumlah_kos = len(df)
    rata_rata = df["harga_rupiah"].mean()
    harga_termurah = df["harga_rupiah"].min()
    harga_termahal = df["harga_rupiah"].max()

    # Menyiapkan data untuk grafik
    nama_kos = df["nama"].tolist()
    harga_kos = df["harga_rupiah"].tolist()

    # Mengirim data ke halaman HTML
    context = {
        "jumlah_kos": jumlah_kos,
        "rata_rata": rata_rata,
        "harga_termurah": harga_termurah,
        "harga_termahal": harga_termahal,
        "nama_kos": json.dumps(nama_kos),
        "harga_kos": json.dumps(harga_kos),
    }

    return render(request, "dashboard/analisis_harga.html", context)


# ==========================================
# HALAMAN SEBARAN KOS
# ==========================================

def sebaran_kos(request):

    # Membaca file CSV
    file_csv = Path(settings.BASE_DIR) / "dataset" / "kos_madiun.csv"
    df = pd.read_csv(file_csv)

    # Mengubah data kos menjadi dictionary
    daftar_kos = df.to_dict(orient="records")

    # Mengirim data ke halaman HTML
    context = {
        "daftar_kos": daftar_kos,
    }

    return render(request, "dashboard/sebaran_kos.html", context)


# ==========================================
# HALAMAN CHATBOT AI
# ==========================================

def halaman_chatbot(request):

    return render(request, "dashboard/chatbot.html")




