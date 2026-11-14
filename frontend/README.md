# FireSync — Vanilla Frontend 🗺️🔥

**Different sensors. One common view.**

واجهة تفاعلية (Map UI + Calendar) لعرض الـ hotspots، متوصّلة مباشرة بـ **FireSync API الحقيقي** (`api.py` بتاع الفريق)، ومبنية بـ **Vanilla JS بدون أي build tools** (من غير React/Vite) عشان يكون سهل التعديل والتشغيل والتجربة بسرعة.

---

## ⚡ التشغيل — أسرع طريقة (بدون أي تنصيب)

افتح `index.html` بمتصفح Chrome/Edge — هتشتغل فورًا على البيانات التجريبية (محتاج إنترنت بس لأن بلاطات الخريطة من CDN). أول ما سيرفر الـ API يشتغل، الواجهة **بتحوّل نفسها تلقائيًا** للداتا الحقيقية.

لو المتصفح منع الفتح المباشر، شغّل سيرفر محلي بسيط:

```bash
# من جوه مجلد المشروع
python -m http.server 8080
# افتح: http://localhost:8080
```

## ❗ سؤال شائع: `npm install` بيدي ENOENT / Could not read package.json

**ده متوقّع ومش خطأ عندك.** المشروع ده Vanilla JS بدون build tools — مفيهوش `package.json` أصلًا (أو كان، قبل الإصدار ده) ومفيش أي حاجات تتثبت بـ npm. مكتبة الخرايط (MapLibre) بتيجي من CDN، والـ API سيرفر بتاعكم **Python/FastAPI** مش Node.

لو حابب تعمل كل حاجة بأسلوب npm، أضفنا `package.json` اختياري في الإصدار ده (من غير أي dependencies — يعني `npm install` هي نجاح فاضي):

```bash
npm install        # مش ضروري — مفيش dependencies، بس هي النجاح لو حبيت
npm start          # يشغّل سيرفر محلي للواجهة على http://localhost:8080 (بيستخدم python)
npm run api        # يشغّل FireSync API (server/api.py) على http://localhost:8000
npm run install:api # يعمل pip install لمتطلبات الـ API
```

> ملاحظة: السكريبتات دي بتنادي `python` — لازم يكون متثبت وعلى الـ PATH (وده موجود عندكم لأن الـ API أصلًا Python).

## 🔌 التوصيل بـ FireSync API الحقيقي (api.py)

ملف `server/api.py` ده **نفس ملف الـ API بتاع الفريق** بدون أي تعديل. الـ API بيقرأ ملفات الـ output بتاعة الـ pipeline (`observations_indexed.csv` وغيرها من `pipeline.py` + `harmonization.py`).

```bash
# 1) جهّز ملفات الـ output بتاعة الـ pipeline في مجلد output/ جنب api.py
#    (نفس الطريقة اللي بتشغّل بيها api.py عادي)
pip install -r server/requirements.txt

# 2) شغّل السيرفر
python server/api.py
# → http://localhost:8000  (افتح /docs لكل الـ endpoints)
```

بعدها:

- افتح `index.html` — شارة الحالة فوق هتتغير من **demo data** لـ **live API** تلقائيًا.
- الواجهة بتستخدم الـ endpoints دي من `api.py`:
  - `GET /api/overview` → الملخص + date range + الـ disclaimer
  - `GET /api/hotspots/geojson?limit=20000` → GeoJSON جاهز للرسم على الخريطة
  - `GET /api/observations` → لـ pagination تلقائي لو الداتا أكتر من 20,000 ملاحظة
- لو السيرفر مش شغال أو مفيش ملفات `output/` (يعني `/api/overview` رجّع 0 ملاحظات)، الواجهة ترجع **تلقائيًا** للبيانات التجريبية المدمجة (`js/demo-data.js`) وعليها شارة demo بوضوح.
- رابط السيرفر بيتغير من `js/config.js` (`apiBaseUrl`) — الافتراضي `http://localhost:8000`.

## 🗺️ صفحة الخريطة (`index.html`) — الرئيسية

- **MapLibre GL JS** (نفس مكتبة الخرايط المكتوبة في معمارية الباوربوينت) + خلفية داكنة.
- **النقط الملونة** بطريقتين (زي slide 14):
  - **Mode A · Color by platform:** كل منصة بلون (ألوان المنصات بتتبني **ديناميكيًا** من الداتا الراجعة من الـ API — أي منصة جديدة هتاخد لون تلقائي).
  - **Mode B · Color by FRP:** الـ bins المكتوبة في الباوربوينت: `<1 / 1–3 / 3–10 / ≥10 MW` (بيجيب "قوة الإشارة"). ده threshold للعرض بس، مش تصنيف رسمي من NASA.
- **Panel صغيرة فوق الخريطة في الجمب** فيها: تبديل الـ Mode، تشغيل/إطفاء أي منصة، فلتر اليوم، وعدّاد الملاحظات الظاهرة لكل منصة.
- **كليك على أي نقطة** → كارت تفاصيل من الداتا الحقيقية: sensor، satellite، الوقت UTC، FRP، الـ confidence الأصلي (بدون تحويل — زي مبدأ الحفاظ على القيم الأصلية)، brightness، day/night، رقم الـ grid cell (1 km · EPSG:6933)، والإحداثيات.

## 📅 صفحة التقويم (`calendar.html`) — منفصلة عن الخريطة

- تقويم شهري (يبدأ من السبت) بيعرض **عدد الـ hotspots الماخودة من الـ API** لكل يوم، والتلوين حسب شدة اليوم.
- كليك على أي يوم → ملخص **لكل منصة على حدة** (عدد الملاحظات + median FRP + قيم confidence الأصلية — من غير دمج بين الحساسات، زي مبدأ FireSync) + لستة الملاحظات نفسها.
- زرار **"Open this day on the map →"** يفتح الخريطة على نفس اليوم (بـ `?date=YYYY-MM-DD`).

---

## 📁 الملفات

```
├── index.html          ← صفحة الخريطة (الأساسية)
├── calendar.html       ← صفحة التقويم (منفصلة عن الخريطة)
├── package.json        ← اختياري: npm scripts (start / api) — من غير أي dependencies
├── css/style.css       ← ستايل مشترك
├── js/
│   ├── config.js       ← إعدادات: رابط الـ API ووقت الانتظار
│   ├── api.js          ← طبقة الربط بالـ API (overview + geojson + pagination + demo fallback)
│   ├── demo-data.js    ← البيانات التجريبية المدمجة (بنفس schema الـ API الحقيقي)
│   ├── map.js          ← منطق الخريطة
│   └── calendar.js     ← منطق التقويم
└── server/
    ├── api.py          ← FireSync API الحقيقي بتاع الفريق (نفس الملف بدون تعديل)
    └── requirements.txt
```

## 🎨 تعديلات سريعة

- **ألوان المنصات المعروفة / الـ FRP bins:** في `js/api.js` (`KNOWN_COLORS`) وأول `js/map.js` (`FRP_STEPS`) + متغيرات الألوان في `css/style.css`.
- **رابط الـ API ووقت الانتظار:** `js/config.js`.
- **مركز الخريطة والزوم:** `js/config.js` تحت `map`.

## ⚠️ ملاحظات علمية (زي ما الباوربوينت بيصرّح)

- النقطة الواحدة = رصد حراري واحد (hotspot)، مش محيط حريق.
- الـ FRP bins للعرض البصري فقط، مش تصنيفات رسمية للشدة.
- تشترك نقطتين في نفس الخلية/اليوم = **co-occurrence** ومش دليل إنهم نفس الحريق.
- الـ FRP عمره ما بيتجمع بين الحساسات، وقيم confidence أصلية وغير قابلة للمقارنة بين MODIS و VIIRS.
- مشروع طلبة مستقل، غير تابع لـ NASA ولا معتمد منها. المصدر: NASA FIRMS.
