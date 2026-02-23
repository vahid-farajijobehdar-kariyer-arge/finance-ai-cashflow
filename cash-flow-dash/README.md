# Banka Ekstreleri – Kolon Sözlüğü (Data Dictionary)

Bu doküman; **Ziraat, Akbank, Garanti, Halkbank, QNB, Finansbank, YKB (Yapı Kredi), İşbank, Vakıfbank** ekstreleri ve raporlarında yer alan kolon adlarını ve **Türkçe açıklamalarını** içerir.

> **Not**: Tüm parasal değerler Türkçe formatta gösterilir: `₺1.234.567,89`  
> Formatlama: `format_utils.py` → `tl()`, `_tl()`, `_tl0()`

---

## 📋 İşlem Kategorisi & Sınıflandırma

| Kolon Adı | Açıklama |
|---|---|
| transaction_category | POS İşlemi veya İade sınıflandırması (iade filtreleme için kritik) |
| card_type | Kart tipi (Kredi Kartı, Banka Kartı, Prepaid vb.) |

---

## 🧾 İşlem & Zaman Bilgileri

| Kolon Adı | Açıklama |
|---|---|
| İşlem Tarihi | Kart işleminin gerçekleştiği tarih |
| Gün Sonu Tarihi | Banka tarafından işlemin muhasebeleştirildiği tarih |
| Valor Tarihi | İşlemin finansal olarak geçerli olduğu tarih |
| Bloke Tarihi | Tutarın bloke edildiği tarih |
| Bloke Çözüm Tarihi | Blokenin kaldırıldığı tarih |
| Hesaba Geçiş Tarihi | Tutarın hesaba geçtiği tarih |
| Vade Tarihi | Taksitli işlemlerde ödeme vade tarihi |
| Ay | İşlemin ait olduğu ay |
| Sezon | Kampanya / dönem bilgisi |

---

## 💳 Kart & Ödeme Bilgileri

| Kolon Adı | Açıklama |
|---|---|
| Kart No | Maskelenmiş kredi/banka kartı numarası |
| Kart Tipi | Kredi Kartı / Banka Kartı |
| Kart Markası | Visa, Mastercard, Troy vb. |
| Kartın Bankası | Kartın ait olduğu banka |
| Ana Kart Tipi | Ana kart segmenti |
| Alt Kart Tipi | Alt kart / ürün tipi |
| Para Birimi | TRY, USD, EUR vb. |
| Döviz Kodu | Para birimi kodu |
| Kur | Döviz kuru |

---

## 🏪 Üye İşyeri (Merchant) Bilgileri

| Kolon Adı | Açıklama |
|---|---|
| Üye İşyeri No | Banka sistemindeki üye işyeri numarası |
| Üye İşyeri Adı | Firma / mağaza adı |
| Üye Grup No | Üye işyerinin bağlı olduğu grup |
| Zincir No | Zincir mağaza kodu |
| Ana Bayi Üye İşyeri No | Üst bayiye ait numara |
| Şube No / Şube Kodu | Banka şube bilgisi |
| Terminal No | POS terminal numarası |
| Batch No | Günlük işlem paketi numarası |

---

## 💰 Tutar & Finansal Alanlar

| Kolon Adı | Açıklama |
|---|---|
| Tutar | İşlemin brüt tutarı |
| Brüt Tutar | Komisyon öncesi toplam tutar |
| Net Tutar | Komisyonlar düşüldükten sonra kalan tutar |
| Hesaba Geçen Net Tutar | Banka tarafından ödenecek net tutar |
| Bekleyen Alacak Tutarı | Henüz tahsil edilmemiş alacak |
| Bekleyen Borç Tutarı | Henüz tahsil edilmemiş borç |
| Çözümlenmiş Alacak Tutarı | Tahsil edilmiş alacak |
| Çözümlenmiş Borç Tutarı | Tahsil edilmiş borç |
| Kar | İşlemden elde edilen kazanç |
| Net Gelir | Kar – cezalar sonrası net kazanç |
| Ceza Tutarı | Banka/servis kaynaklı kesinti |
| Fark Oranı | Beklenen–gerçekleşen fark yüzdesi |

---

## 🧮 Komisyon & Kesintiler

| Kolon Adı | Açıklama |
|---|---|
| Komisyon Oranı (%) | Bankanın uyguladığı komisyon oranı |
| Kesilen Komisyon Tutarı | Banka tarafından kesilen tutar |
| Kendi Bankası Komisyonu | Kartın ait olduğu bankanın komisyonu |
| Ziraat Komisyonu | Ziraat Bankası’na ait komisyon |
| Hizmet Komisyon Tutarı | Ek servis bedeli |
| Marka Servis Komisyonu | Visa/Mastercard/Troy komisyonu |
| BSMV Tutarı | Banka ve Sigorta Muameleleri Vergisi |
| IKP Tutarı | İlave komisyon / kampanya kesintisi |

---

## 🔁 Taksit & Kampanya Alanları

| Kolon Adı | Açıklama |
|---|---|
| İşlem Tipi | Satış, İade, Peşin, Taksitli |
| Taksit Sayısı | Toplam taksit adedi |
| Taksit Sıra | İlgili taksitin sıra numarası |
| Taksit Tipi | Peşin / Çok taksitli |
| Öteleme Durumu | Taksit erteleme bilgisi |
| Artı Taksit Durumu | Kampanyalı ekstra taksit |
| Kampanyasız Komisyon | Kampanya hariç komisyon |

---

## 🧾 Teknik & Sistem Alanları

| Kolon Adı | Açıklama |
|---|---|
| Provizyon Kodu | Banka onay kodu |
| Banka RRN | Referans numarası |
| Banka STAN | İşlem takip numarası |
| Host Cevap | Banka işlem sonucu |
| Servis Kodu | POS / sanal POS servis kodu |
| Servis Açıklaması | Servis türü açıklaması |
| İşlemi Yapan Kullanıcı | API / kullanıcı bilgisi |

---

## 📊 Özet & Raporlama Alanları

| Kolon Adı | Açıklama |
|---|---|
| Toplam Çekim Tutarı | Belirli dönem toplam hacim |
| Tek Çekim Tutarı | Peşin işlemler toplamı |
| Tek Çekim Oranı | Peşin işlemlerin oranı |
| Kar Oranı | Karlılık yüzdesi |
| Genel Toplam | Tüm dönemlerin toplamı |

---

## 🏦 YKB (Yapı Kredi) Özel Kolon Eşleştirmesi

YKB iki farklı Excel formatını destekler (yeni → eski fallback):

| Kaynak Kolon (Yeni Format) | Hedef Alan | Açıklama |
|---|---|---|
| Yükleme Tarihi | transaction_date | İşlem günü |
| Ödeme Tarihi | settlement_date | Valor / ödeme tarihi |
| Brüt Tutar | gross_amount | Komisyon öncesi tutar |
| Toplam (Taksitli İşlem Komisyonu+Katkı Payı TL) | commission_amount | Toplam komisyon |
| *hesaplanan* | net_amount | Brüt - Komisyon |

| Kaynak Kolon (Eski Format) | Hedef Alan | Açıklama |
|---|---|---|
| İşlem Günü | transaction_date | İşlem tarihi |
| Valor | settlement_date | Ödeme tarihi |
| Peşin Komisyon+Katkı Payı TL + Taksitli İşlem Komisyonu+Katkı Payı TL | commission_amount | Toplam (iki kolon toplamı) |

---

## 🔄 Ziraat Özel İşlem Ayrımı

Ziraat bankası `transaction_category` alanını işlem tipi kolonundan türetir:
- İşlem açıklamasında "ade" geçen satırlar → **İade**
- Diğer satırlar → **POS İşlemi**

Bu ayrım, iade işlemlerinin komisyon oranı metriklerini bozmasını engeller.
