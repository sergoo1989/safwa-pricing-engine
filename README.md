# 💰 محرك تسعير صفوة - Safwa Pricing Engine

نظام تسعير محاسبي متكامل لحساب تكلفة البضاعة المباعة (COGS) والتسعير الأمثل للمنتجات والبكجات.

## 🎯 المميزات

- ✅ حساب COGS للمنتجات من المواد الخام (BOM)
- ✅ حساب COGS للبكجات (مع دعم البكجات المتداخلة)
- ✅ استخراج نسب التسويق والتشغيل من PL تلقائياً
- ✅ حساب السعر الأمثل مع هامش الربح المستهدف
- ✅ مقارنة السعر النظري مع الفعلي من طلبات سلة
- ✅ تقرير تفصيلي لمنتج واحد (جاهز للطباعة)
- ✅ واجهة Streamlit تفاعلية

## 📦 التثبيت

```bash
# Clone the repository
git clone https://github.com/sergoo1989/safwa-pricing-engine.git
cd safwa-pricing-engine

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

## 🚀 التشغيل

### واجهة Streamlit
```bash
streamlit run dashboard.py
```

### Command Line (منتج واحد)
```bash
python app.py --sku PROD001
```

### جدول تسعير كامل
```bash
python all_skus.py
```

## 📁 هيكل الملفات

```
safwa-pricing-engine/
├── data/                       # ملفات البيانات
│   ├── raw_materials_template.csv
│   ├── products_template.csv
│   ├── packages_template.csv
│   ├── pl_safwa.csv
│   └── salla_orders.csv
├── pricing_app/                # المحرك المحاسبي
│   ├── models.py              # Data models
│   ├── data_loader.py         # تحميل البيانات
│   ├── costing.py             # حساب COGS
│   ├── pricing.py             # معادلات التسعير
│   ├── fees.py                # استخراج النسب من PL
│   └── reports.py             # إنشاء التقارير
├── dashboard.py                # واجهة Streamlit
├── app.py                     # CLI لمنتج واحد
└── all_skus.py                # تقرير كامل
```

## 📊 معادلة التسعير

```
NetPriceExclVAT = COGS / (1 - fees_pct - target_margin)
PriceBeforeDiscount = NetPriceExclVAT / (1 - discount_rate)
ListPriceInclVAT = PriceBeforeDiscount × (1 + VAT)
```

## 🎓 أمثلة

### مثال 1: حساب COGS لمنتج
```python
from pricing_app.data_loader import load_cost_data
from pricing_app.costing import compute_product_costs

materials, products_df, _ = load_cost_data('data')
product_costs = compute_product_costs(products_df, materials)

print(product_costs['PROD001'])  # 82.63 SAR
```

### مثال 2: تسعير منتج
```python
from pricing_app.pricing import price_item
from pricing_app.models import ChannelFees

channel_fees = ChannelFees()
breakdown = price_item('PROD001', cogs=82.63, channel_fees=channel_fees)

print(f"List Price: {breakdown.list_price_incl_vat:.2f} SAR")
print(f"Net Margin: {breakdown.net_margin_pct:.1f}%")
```

## 📄 License

MIT License

## 👨‍💻 المطور

تم التطوير بواسطة GitHub Copilot لشركة صفوة
