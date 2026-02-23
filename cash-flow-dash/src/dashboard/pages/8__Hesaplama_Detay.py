"""
🧮 Hesaplama Detay - Tüm sütun formüllerinin açıklaması

Tüm bankalarda kullanılan hesaplama formüllerini Türkçe metin olarak gösterir.

© 2026 Kariyer.net Finans Ekibi
"""

import streamlit as st
import sys
from pathlib import Path

# Proje yolunu ekle
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from auth import check_password

# Sayfa yapılandırması
st.set_page_config(
    page_title="Hesaplama Detay - POS Komisyon",
    page_icon="🧮",
    layout="wide"
)

# Kimlik doğrulama
if not check_password():
    st.stop()

st.title("🧮 Hesaplama Detay")
st.markdown("**Tüm bankalarda kullanılan sütun hesaplama formüllerinin Türkçe açıklaması**")
st.markdown("---")

# ═══════════════════════════════════════════════════════
# 1. TEMEL SÜTUNLAR
# ═══════════════════════════════════════════════════════
st.header("1️⃣ Temel Sütunlar (Dosyadan Okunan)")

st.markdown("""
Bu sütunlar banka ekstre dosyalarından (Excel/CSV) doğrudan okunur ve herhangi bir hesaplama yapılmaz.

| Sütun | Açıklama |
|-------|----------|
| **`bank_name`** | Banka adı — dosya adından veya içerikten otomatik tespit edilir. |
| **`transaction_date`** | İşlem tarihi — POS cihazında satışın yapıldığı tarih. |
| **`settlement_date`** | Valor / hesaba geçiş tarihi — tutarın banka hesabına yansıdığı tarih. |
| **`gross_amount`** | Brüt tutar — müşterinin ödediği toplam tutar (₺). |
| **`commission_rate`** | Bankanın uyguladığı komisyon oranı — ondalık olarak (örn. 0.0336 = %3,36). |
| **`commission_amount`** | Bankanın kestiği komisyon tutarı (₺). |
| **`net_amount`** | Banka hesabına yansıyan net tutar (₺). |
| **`installment_count`** | Taksit sayısı — 1 = Peşin, 2-12 = Taksitli. |
| **`transaction_type`** | İşlem tipi — "Satış", "Peşin Satış", "Taksit", "TEK", "TKS" vb. |
| **`card_type`** | Kart tipi — Kredi, Debit vb. |
| **`card_brand`** | Kart markası — VISA, Mastercard, TROY. |
""")

# ═══════════════════════════════════════════════════════
# 2. HESAPLANAN SÜTUNLAR
# ═══════════════════════════════════════════════════════
st.markdown("---")
st.header("2️⃣ Hesaplanan Sütunlar")

st.subheader("🔹 Net Tutar Hesabı")
st.info("**Formül:** `Net Tutar = Brüt Tutar − Komisyon Tutarı`")
st.markdown("""
```
net_amount = gross_amount − commission_amount
```

**Açıklama:**  
Müşterinin ödediği brüt tutardan bankanın kestiği komisyon çıkarılarak 
hesaba geçen net tutar bulunur.

**Örnek:**  
- Brüt Tutar = ₺5.038,80  
- Komisyon Tutarı = ₺1.206,80  
- **Net Tutar = ₺5.038,80 − ₺1.206,80 = ₺3.832,00**
""")

st.subheader("🔹 Komisyon Tutarı Hesabı (Oran Üzerinden)")
st.info("**Formül:** `Komisyon Tutarı = Brüt Tutar × Komisyon Oranı`")
st.markdown("""
```
commission_amount = gross_amount × commission_rate
```

**Açıklama:**  
Bazı banka dosyalarında komisyon tutarı doğrudan verilmeyip oran verilir. 
Bu durumda komisyon tutarı, brüt tutarın komisyon oranıyla çarpılmasıyla hesaplanır.

**Örnek:**  
- Brüt Tutar = ₺10.000,00  
- Komisyon Oranı = 0,0336 (%3,36)  
- **Komisyon Tutarı = ₺10.000,00 × 0,0336 = ₺336,00**
""")

st.subheader("🔹 Komisyon Yüzdesi")
st.info("**Formül:** `Komisyon Yüzdesi = (Komisyon Tutarı ÷ Brüt Tutar) × 100`")
st.markdown("""
```
commission_pct = (commission_amount / gross_amount) × 100
```

**Açıklama:**  
Belirli bir banka, taksit grubu veya dönem için ağırlıklı ortalama komisyon oranını yüzde olarak gösterir.

**Örnek:**  
- Komisyon Tutarı = ₺336,00  
- Brüt Tutar = ₺10.000,00  
- **Komisyon Yüzdesi = (₺336 ÷ ₺10.000) × 100 = %3,36**
""")

# ═══════════════════════════════════════════════════════
# 3. KOMİSYON KONTROL SÜTUNLARı
# ═══════════════════════════════════════════════════════
st.markdown("---")
st.header("3️⃣ Komisyon Kontrol Sütunları")
st.markdown("""
Bu sütunlar, bankanın uyguladığı oranın sözleşmedeki oranla eşleşip eşleşmediğini kontrol eder.  
Sözleşme oranları `config/commission_rates.yaml` dosyasından yüklenir.
""")

st.subheader("🔹 Beklenen Oran (Sözleşme Oranı)")
st.info("**Kaynak:** `commission_rates.yaml` → Banka + Taksit Sayısına göre eşleşme")
st.markdown("""
```
rate_expected = commission_rates[banka_adı][taksit_sayısı]
```

**Açıklama:**  
Her banka ve taksit sayısı kombinasyonu için sözleşmede tanımlanan oran.  
Örneğin Vakıfbank Peşin = 0,0336, 12 Taksit = 0,2395.

**Eşleşme Mantığı:**  
1. Önce banka adı birebir eşleştirilir  
2. Bulunamazsa kısmi eşleşme denenir (örn. "VAKIF" → "Vakıfbank")  
3. Taksit = 0 veya 1 ise "Peşin" oranı kullanılır
""")

st.subheader("🔹 Beklenen Komisyon Tutarı")
st.info("**Formül:** `Beklenen Komisyon = Brüt Tutar × Sözleşme Oranı`")
st.markdown("""
```
commission_expected = gross_amount × rate_expected
```

**Açıklama:**  
Sözleşme oranı kullanılarak hesaplanan "olması gereken" komisyon tutarı.  
Gerçek komisyonla karşılaştırılarak fark bulunur.

**Örnek:**  
- Brüt Tutar = ₺5.038,80  
- Sözleşme Oranı (12 Taksit) = 0,2395  
- **Beklenen Komisyon = ₺5.038,80 × 0,2395 = ₺1.206,79**
""")

st.subheader("🔹 Oran Farkı")
st.info("**Formül:** `Oran Farkı = |Uygulanan Oran − Sözleşme Oranı|`")
st.markdown("""
```
rate_diff = |commission_rate − rate_expected|
```

**Açıklama:**  
Bankanın dosyada belirttiği oranla sözleşmedeki oran arasındaki mutlak fark.  
Tolerans değeri: **%0,5 (0,005)** — bu değerin altındaki farklar "uyumlu" kabul edilir.
""")

st.subheader("🔹 Komisyon Farkı (₺)")
st.info("**Formül:** `Komisyon Farkı = Gerçek Komisyon − Beklenen Komisyon`")
st.markdown("""
```
commission_diff = commission_amount − commission_expected
```

**Açıklama:**  
Bankanın gerçekte kestiği komisyon ile sözleşme oranından hesaplanan beklenen komisyon 
arasındaki tutar farkı.

- **Pozitif fark** → Banka sözleşmeden **fazla** kesmiş  
- **Negatif fark** → Banka sözleşmeden **az** kesmiş  
- **Sıfır** → Oran tolerans dahilindeyse fark sıfır olarak atanır

**Tolerans Kuralı:**  
Oran farkı < %0,5 ise → `commission_diff = 0` (fark yok sayılır)
""")

st.subheader("🔹 Oran Eşleşmesi")
st.info("**Formül:** `Eşleşme = Oran Farkı < 0,005`")
st.markdown("""
```
rate_match = |commission_rate − rate_expected| < 0.005
```

**Değerler:**
- ✅ `True` → Oran sözleşmeyle uyumlu (%0,5 tolerans dahilinde)  
- ❌ `False` → Oran sözleşmeyle uyumsuz

**Durum Etiketleri:**
| Durum | Anlamı |
|-------|--------|
| ✅ Uyumlu | Fark < %0,5 |
| 🔴 Fazla | Uygulanan oran > Sözleşme oranı |
| 🟢 Az | Uygulanan oran < Sözleşme oranı |
| ⚪ Veri Yok | İşlem verisi bulunamadı |
| ⚠️ Oran Tanımsız | Sözleşmede bu taksit oranı yok |
""")

st.subheader("🔹 Tutar Doğrulaması")
st.info("**Formül:** `Tutar Eşleşmesi = |Gerçek Komisyon − (Brüt × Oran)| / Gerçek Komisyon < %1`")
st.markdown("""
```
commission_calculated = gross_amount × commission_rate
amount_diff = |commission_amount − commission_calculated|
amount_diff_pct = (amount_diff / commission_amount) × 100
amount_match = amount_diff_pct < 1.0
```

**Açıklama:**  
Dosyada verilen komisyon tutarının, yine dosyada verilen oranla hesaplanan tutarla 
tutarlı olup olmadığını kontrol eder. %1'den fazla fark varsa bayrak koyar.
""")

# ═══════════════════════════════════════════════════════
# 4. FİLTRELEME KURALLARI
# ═══════════════════════════════════════════════════════
st.markdown("---")
st.header("4️⃣ İşlem Filtreleme Kuralları")

st.markdown("""
Veri yüklendikten sonra aşağıdaki filtreleme kuralları uygulanır:

### Dahil Edilen İşlem Tipleri
Sadece başarılı satış işlemleri analize dahil edilir:
- `Satış`, `SATIŞ`, `Peşin Satış`, `Taksit`, `Tek Çekim`, `TKS`, `TEK`

### Hariç Tutulan İşlem Tipleri
Aşağıdaki işlem tipleri **otomatik olarak hariç tutulur**:
- `İPTAL` / `IPTAL` — İptal edilen işlemler
- `BAŞARISIZ` — Başarısız işlemler

### İade İşlemleri
- İade (İADE) satırları **hariç tutulmaz**
- İade işlemleri negatif tutara sahiptir
- Toplam hesaplamalarında doğal olarak düşülür (brütten çıkarılır)

### Özel Kategoriler (Garanti BBVA)
- `PNLT` — Ceza/Ödül iadesi → Kategorize edilir, hariç tutulmaz
- `PUCRT` — Hizmet ücreti → Kategorize edilir, hariç tutulmaz
""")

# ═══════════════════════════════════════════════════════
# 5. TOPLAM (AGGREGATE) HESAPLAMALARI
# ═══════════════════════════════════════════════════════
st.markdown("---")
st.header("5️⃣ Toplam ve Gruplama Hesaplamaları")

st.subheader("🔹 Banka Bazlı Toplam")
st.markdown("""
```
Toplam Brüt      = SUM(gross_amount)        — tüm satırlar (pozitif + negatif)
Toplam Komisyon   = SUM(commission_amount)   — tüm satırlar
Toplam Net        = Toplam Brüt − Toplam Komisyon
İşlem Sayısı      = COUNT(*)
Ortalama Oran (%) = (Toplam Komisyon / Toplam Brüt) × 100
```

**Önemli Not:**  
Negatif tutarlı satırlar (iade / chargeback) toplamdan **otomatik olarak düşülür**.  
Ayrı bir "iade çıkar" işlemi yapılmaz — SUM doğal olarak negatif değerleri düşürür.
""")

st.subheader("🔹 Taksit Bazlı Toplam")
st.markdown("""
```
Her taksit sayısı için:
  Tutar     = SUM(gross_amount)
  Komisyon  = SUM(commission_amount)
  Oran (%)  = (Komisyon / Tutar) × 100
  İşlem     = COUNT(*)
```

**Taksit Sınıflandırması:**
| Taksit Sayısı | Etiket |
|---------------|--------|
| 0 veya 1 | Peşin |
| 2 | 2 Taksit |
| 3 | 3 Taksit |
| ... | ... |
| 12 | 12 Taksit |
""")

st.subheader("🔹 Aylık Toplam")
st.markdown("""
```
Her ay (YYYY-MM) için:
  Brüt Tutar = SUM(gross_amount)
  Komisyon   = SUM(commission_amount)
  İşlem      = COUNT(*)
```

**Tarih Seçimi Önceliği:**
1. `settlement_date` (valor / hesaba geçiş tarihi) — öncelikli  
2. `transaction_date` (işlem tarihi) — settlement_date yoksa  

Ay filtreleme, seçilen ayın 1. gününden son gününe kadar olan aralığı kapsar.
""")

st.subheader("🔹 Peşin vs Taksitli Karşılaştırma")
st.markdown("""
```
Peşin İşlemler:
  installment_count ∈ {0, 1, "Peşin", "TEK"}
  Tutar   = SUM(gross_amount)   [peşin satırlar]
  Komis.  = SUM(commission_amount)
  Net     = Tutar − Komisyon
  Oran(%) = (Komisyon / Tutar) × 100

Taksitli İşlemler:
  installment_count ∉ {0, 1, "Peşin", "TEK"}
  Tutar   = SUM(gross_amount)   [taksitli satırlar]
  Komis.  = SUM(commission_amount)
  Net     = Tutar − Komisyon
  Oran(%) = (Komisyon / Tutar) × 100
```

**Not:** Sadece POS işlemleri dahil edilir (PNLT/PUCRT hariç).
""")

# ═══════════════════════════════════════════════════════
# 6. SÖZLEŞME VS UYGULANAN ORAN KARŞILAŞTIRMASI
# ═══════════════════════════════════════════════════════
st.markdown("---")
st.header("6️⃣ Sözleşme vs Uygulanan Oran Karşılaştırması")

st.markdown("""
Her taksit sayısı için sözleşme oranı ile gerçekte uygulanan oran karşılaştırılır.

```
Her taksit grubu için:
  Sözleşme Oranı  = commission_rates.yaml'dan okunan oran
  Uygulanan Oran  = SUM(komisyon [pozitif satırlar]) / SUM(brüt [pozitif satırlar])
  Oran Farkı      = Uygulanan Oran − Sözleşme Oranı
  Oran Farkı (bps)= Oran Farkı × 10.000  (basis point)

  Beklenen Komisyon (₺) = Brüt Tutar × Sözleşme Oranı
  Gerçek Komisyon (₺)   = SUM(commission_amount)
  Komisyon Farkı (₺)    = Gerçek Komisyon − Beklenen Komisyon
```

**Oran Kontrolü İçin Önemli Not:**  
Uygulanan oran hesaplanırken **sadece pozitif (satış) işlemler** kullanılır.  
Negatif (iade) işlemler dahil edilirse ortalama oran bozulur.  
Ancak komisyon tutarı karşılaştırmasında tüm işlemler (pozitif + negatif) dahildir.

**Durum Değerlendirmesi:**

| Koşul | Durum |
|-------|-------|
| |Oran Farkı| < 0,005 | ✅ Uyumlu |
| Oran Farkı > 0 | 🔴 Fazla (banka fazla kesmiş) |
| Oran Farkı < 0 | 🟢 Az (banka az kesmiş) |
| İşlem sayısı = 0 | ⚪ Veri Yok |
| Sözleşme oranı tanımsız | ⚠️ Oran Tanımsız |
""")

# ═══════════════════════════════════════════════════════
# 7. GELECEK DEĞER HESAPLAMALARI
# ═══════════════════════════════════════════════════════
st.markdown("---")
st.header("7️⃣ Gelecek Değer (Yatırım) Hesaplamaları")

st.subheader("🔹 Basit Faiz")
st.info("**Formül:** `Gelecek Değer = Anapara + (Anapara × Yıllık Oran × Süre/12)`")
st.markdown("""
```
faiz       = anapara × yıllık_oran × (ay / 12)
gelecek_değer = anapara + faiz
efektif_oran  = faiz / anapara
```

**Örnek:**  
- Anapara = ₺1.000.000  
- Yıllık Oran = %42  
- Süre = 3 ay  
- Faiz = ₺1.000.000 × 0,42 × (3/12) = **₺105.000**  
- Gelecek Değer = ₺1.000.000 + ₺105.000 = **₺1.105.000**
""")

st.subheader("🔹 Bileşik Faiz")
st.info("**Formül:** `Gelecek Değer = Anapara × (1 + Oran/n)^(n × Süre)`")
st.markdown("""
```
n             = bileşik dönem sayısı (genellikle 12 — aylık)
gelecek_değer = anapara × (1 + yıllık_oran / n) ^ (n × yıl)
faiz          = gelecek_değer − anapara
efektif_oran  = faiz / anapara
```

**Örnek:**  
- Anapara = ₺1.000.000  
- Yıllık Oran = %42  
- Süre = 12 ay, aylık bileşik  
- Gelecek Değer = ₺1.000.000 × (1 + 0,42/12)^12 = **₺1.511.068,96**
""")

st.subheader("🔹 Aylık Nakit Akışı Projeksiyon")
st.markdown("""
```
Her aylık yatırım (deposit) için:
  kalan_ay      = toplam_süre − yatırım_sırası
  gelecek_değer = yatırım_tutarı × (1 + aylık_oran) ^ kalan_ay
  faiz          = gelecek_değer − yatırım_tutarı

Toplam:
  toplam_anapara     = SUM(yatırım_tutarları)
  toplam_gelecek     = SUM(gelecek_değerler)
  toplam_faiz_geliri = toplam_gelecek − toplam_anapara
```

**Açıklama:**  
Her ayın net tutarı bankaya yatırılsa, süre sonunda toplam ne kadar olacağını gösterir.  
Erken yatırılan tutarlar daha uzun süre faiz kazanır.
""")

# ═══════════════════════════════════════════════════════
# 8. KONTROL BAYRAKLARI
# ═══════════════════════════════════════════════════════
st.markdown("---")
st.header("8️⃣ Kontrol Bayrakları (Flags)")

st.markdown("""
Her işlem satırı için aşağıdaki kontrol bayrakları otomatik olarak atanır:

| Bayrak | Anlamı | Koşul |
|--------|--------|-------|
| `✓ OK` | Tüm kontroller geçti | Hiçbir sorun yok |
| `ORAN_FARK:X%` | Oran farkı var | \|Uygulanan − Sözleşme\| ≥ %0,5 |
| `TUTAR_FARK:X₺(Y%)` | Tutar tutarsızlığı | \|Gerçek − Hesaplanan\| ≥ %1 |
| `ORAN_HESAPLANDI` | Oran dosyada yoktu | Oran = Komisyon ÷ Brüt olarak hesaplandı |
| `TABLO_YOK` | Sözleşme oranı bulunamadı | Banka+taksit YAML'da tanımlı değil |
""")

# ═══════════════════════════════════════════════════════
# 9. YAPI KREDİ (YKB) KOMİSYON HESAPLAMASI
# ═══════════════════════════════════════════════════════
st.markdown("---")
st.header("9️⃣ Yapı Kredi (YKB) Komisyon Hesaplaması")

st.markdown("""
Yapı Kredi dosyalarında komisyon tutarı doğrudan bir sütunda verilmez.  
Komisyon, iki ayrı sütunun toplanmasıyla hesaplanır:

```
commission_amount = Taksitli İşlem Komisyonu + Katkı Payı TL
```

| Kaynak Sütun | Eşleşme | Açıklama |
|-------------|---------|----------|
| **Taksitli İşlem Komisyonu** | `commission_taksitli` | Taksitli işlemler için banka komisyonu |
| **Katkı Payı TL** | `katki_payi_tl` | Banka katkı payı (ek komisyon) |

**Önemli Notlar:**
- Komisyon tutarı **artı veya eksi** olabilir — iade işlemlerinde negatif değer alır
- `Peşin İşlem Komisyonu` sütunu hesaplamaya **dahil edilmez**
- Net tutar her zaman `Brüt − Komisyon` formülüyle hesaplanır
- Komisyon oranı = `commission_amount / gross_amount` (işaret korunur)

**YKB Sütun Eşleştirmeleri:**

| Dosya Sütunu | Standart Sütun | Açıklama |
|-------------|---------------|----------|
| Yükleme Tarihi | `transaction_date` | İşlem günü |
| Ödeme Tarihi | `settlement_date` | Valor (hesaba geçiş) |
| İşlem Tutarı | `gross_amount` | Brüt tutar |
| Taksitli İşlem Komisyonu | `commission_taksitli` | Komisyon bileşeni 1 |
| Katkı Payı TL | `katki_payi_tl` | Komisyon bileşeni 2 |
| Net Tutar / Net | `net_amount` | Net tutar |
| Taksit Sayısı | `installment_count` | "3/3" formatında olabilir |
""")

# ═══════════════════════════════════════════════════════
# 10. EK KESİNTİLER (GARANTİ BBVA)
# ═══════════════════════════════════════════════════════
st.markdown("---")
st.header("🔟 Ek Kesintiler (Garanti BBVA)")

st.markdown("""
Garanti BBVA dosyalarında standart komisyon dışında ek kesintiler bulunabilir:

| Sütun | Açıklama |
|-------|----------|
| **`reward_deduction`** | Ödül programı kesintisi — müşteri puan/mil kazanımı karşılığı |
| **`service_deduction`** | Servis/hizmet ücreti kesintisi |
| **`transaction_category`** | İşlem kategorisi: "POS İşlemi", "PNLT" (ödül), "PUCRT" (servis) |

**Önemli:**  
Bu ek kesintiler NET tutar hesabına **dahil değildir**.  
Net tutar her zaman `Brüt − Komisyon` formülüyle hesaplanır.  
Ek kesintiler sadece bilgi amaçlı gösterilir.
""")

# ═══════════════════════════════════════════════════════
# 11. GÖSTERIM FORMATLARI
# ═══════════════════════════════════════════════════════
st.markdown("---")
st.header("1️⃣1️⃣ Gösterim Formatları")

st.markdown("""
Dashboard'da kullanılan sayı formatları:

| Format | Açıklama | Örnek |
|--------|----------|-------|
| Tam Tutar | Türk Lirası, binlik nokta, ondalık virgül | ₺1.234.567,89 |
| Kısa Tutar (K) | 10.000₺ üzeri bin kısaltması | ₺123,5K |
| Kısa Tutar (M) | 1.000.000₺ üzeri milyon kısaltması | ₺1,23M |
| Oran | Yüzde formatı, iki ondalık | %3,36 |
| Oran (Ondalık) | Dört ondalık basamak | 0,0336 |
| Oran Farkı (bps) | Basis point cinsinden | +12,5 bps |
""")

# ═══════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; font-size: 0.85em;">
    📋 Bu sayfa tüm bankalarda kullanılan hesaplama formüllerinin referans dokümantasyonudur.<br>
    Sözleşme oranları <code>config/commission_rates.yaml</code> dosyasından yüklenir.<br>
    Filtreleme kuralları <code>config/settings.yaml</code> dosyasından yüklenir.<br><br>
    © 2026 Kariyer.net Finans Ekibi
</div>
""", unsafe_allow_html=True)
