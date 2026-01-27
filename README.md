# Cash Flow Dashboard / Nakit Akışı Takip Paneli

An AI-powered cash flow analysis and management system for credit card commission tracking.



### Özellikler

- **Ekstre Analizi**: Ham banka ekstreleri üzerinde otomatik komisyon hesaplama
- **Tek Çekim / Taksitli Ayrımı**: İşlemleri peşin ve taksitli olarak sınıflandırma
- **Banka Bazlı Komisyon Oranları**: Her banka ve taksit sayısı için doğru oran uygulaması
- **Kontrol Mekanizması**: Hesaplanan değerlerin doğruluğunu kontrol eden sistem
- **Dosya Yönetimi**: Excel dosyaları için metadata takibi ve cache sistemi
- **Gelecek Değer Hesabı**: Mevduat faiz oranlarıyla yatırım projeksiyonu


---

### Project Structure

```
ai-transformation/cash-flow-dash/
├── config/
│   └── banks.yaml           # Bank configuration and column mappings
├── data/
│   ├── raw/                  # Raw Excel files from banks
│   ├── metadata/             # JSON metadata for uploaded files
│   └── uploads/              # Cached uploaded files
├── spec/
│   └── specification.md      # Project specification
└── src/
    ├── dashboard/
    │   ├── app.py            # Main Streamlit dashboard
    │   └── pages/            # Multi-page app pages
    │       ├── 1_📤_Upload.py    # File upload page
    │       └── 2_💰_Future_Value.py  # Future value calculator
    ├── ingestion/            # Data loading modules
    ├── processing/           # Data processing & calculations
    ├── storage/              # File cache & metadata management
    └── validation/           # Data validation modules
```

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run dashboard
cd ai-transformation/cash-flow-dash
streamlit run src/dashboard/app.py
```

### Usage

1. **Upload Files**: Navigate to "📤 Upload" page to upload Excel bank statements
2. **View Dashboard**: Main page shows commission analysis with Tek Çekim/Taksitli breakdown
3. **Future Value**: Calculate investment projections on "💰 Future Value" page

### Data Format

Expected Excel columns (Turkish):
- `İşlem Tarihi` - Transaction Date
- `Brüt Tutar` / `İşlem Tutarı` - Gross Amount
- `Komisyon Tutarı` - Commission Amount  
- `Taksit Sayısı` - Installment Count
- `Banka` - Bank Name (optional)

### Key Terms (Turkish → English)

| Turkish | English |
|---------|---------|
| Tek Çekim | Single Payment / Cash |
| Taksitli | Installment |
| Komisyon | Commission |
| Brüt Tutar | Gross Amount |
| Net Tutar | Net Amount |
| Ekstre | Statement |

### Technology Stack

- **Python 3.13+**
- **Streamlit** - Dashboard UI
- **Pandas** - Data processing
- **Plotly** - Interactive charts
- **OpenPyXL** - Excel file handling
- **Pydantic** - Data validation

### License

Private - Internal Use Only

---

## Configuration

### Banks Configuration (`config/banks.yaml`)

Configure bank-specific column mappings and commission rates:

```yaml
banks:
  - name: "ZIRAAT"
    source_type: "excel"
    columns:
      date: "İşlem Tarihi"
      gross_amount: "Brüt Tutar"
      commission: "Komisyon Tutarı"
      installment: "Taksit Sayısı"
```

