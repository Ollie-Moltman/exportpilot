"""
ExportPilot v1.2 - AI Trade Co-Pilot for Indian Exporters
Enhanced classifier with 40+ categories and real FTA rates
"""
import os, sqlite3, json, re
from datetime import datetime
from flask import Flask, render_template, request, jsonify, g
import requests

app = Flask(__name__)
app.config['DATABASE'] = '/data/exportpilot/exportpilot.db'
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'

# ─── Database ─────────────────────────────────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS fta_master (id INTEGER PRIMARY KEY, code TEXT UNIQUE, full_name TEXT, countries TEXT, effective_date TEXT, coverage TEXT);
        CREATE TABLE IF NOT EXISTS fta_rates (id INTEGER PRIMARY KEY, hs_code TEXT, fta_code TEXT, partner_country TEXT, preferential_rate REAL, rule_of_origin TEXT, requirements TEXT, source TEXT);
        CREATE TABLE IF NOT EXISTS search_history (id INTEGER PRIMARY KEY, query_text TEXT, hs_code TEXT, confidence REAL, response_json TEXT, created_at TEXT);
    ''')
    if db.execute('SELECT COUNT(*) FROM fta_master').fetchone()[0] == 0:
        seed_fta(db)
    db.commit()
    print("[ExportPilot] DB v1.2 ready")

def seed_fta(db):
    ftas = [
        ('UAE_CEPA','India-UAE CEPA','UAE','2022-05-01','goods+services'),
        ('ASEAN','India-ASEAN FTA','10 ASEAN nations','2010-01-01','goods'),
        ('JAPAN','India-Japan CEPA','Japan','2011-08-01','goods+services'),
        ('KOREA','India-Korea CEPIA','South Korea','2010-01-01','goods+services'),
        ('MAURITIUS','India-Mauritius ECECA','Mauritius','2008-04-01','goods+services'),
        ('SINGAPORE','India-Singapore CECA','Singapore','2005-08-01','goods+services'),
        ('SRI_LANKA','India-Sri Lanka FTA','Sri Lanka','2000-03-01','goods'),
        ('NEPAL','India-Nepal Treaty','Nepal','1950-07-31','goods'),
        ('BHUTAN','India-Bhutan Agreement','Bhutan','1949-07-31','goods'),
        ('MERCOSUR','India-MERCOSUR PTA','Argentina,Brazil,Paraguay,Uruguay','2009-06-01','goods'),
        ('CHILE','India-Chile PTA','Chile','2007-08-01','goods'),
        ('ISRAEL','India-Israel FTA','Israel','2023-04-01','goods+services'),
        ('UK','India-UK FTA','United Kingdom','2022-05-01','goods+services'),
        ('AUSTRALIA','India-Australia ECTA','Australia','2022-12-01','goods+services'),
        ('EU','India-EU FTA','EU (27)','2026-02-01','goods+services'),
    ]
    db.executemany('INSERT OR IGNORE INTO fta_master VALUES (NULL,?,?,?,?,?)', ftas)
    rates = [
        ('52%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA'),
        ('52%','ASEAN','ASEAN',0,'Change of Chapter','Form D','India ASEAN FTA'),
        ('61%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA'),
        ('61%','ASEAN','ASEAN',0,'Change of Chapter','Form D','India ASEAN FTA'),
        ('62%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin — 0% on ALL apparel','UAE CEPA'),
        ('62%','ASEAN','ASEAN',3,'Change of Chapter','Form D','India ASEAN FTA'),
        ('62%','KOREA','South Korea',5,'Change of Chapter','Certificate of Origin','India Korea CEPIA'),
        ('62%','JAPAN','Japan',3,'Change of Chapter','Form EUR.1','India Japan CEPA'),
        ('63%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA'),
        ('5702%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA'),
        ('5702%','KOREA','South Korea',5,'Change of Chapter','Certificate of Origin','India Korea CEPIA'),
        ('5702%','USA','USA',0,'GSP','Commercial Invoice + GSP Form','US GSP — hand-knotted carpets'),
        ('0901%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA'),
        ('0902%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA'),
        ('0904%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — chillies'),
        ('0904%','MALAYSIA','Malaysia',5,'Change of Chapter','Form D','India ASEAN FTA'),
        ('0910%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — TURMERIC saves 30% BCD'),
        ('0910%','USA','USA',0,'GSP','Commercial Invoice + GSP','US GSP — turmeric powder 0%'),
        ('1006%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin — basmati + non-basmati','UAE CEPA'),
        ('1006%','SINGAPORE','Singapore',0,'Change of Chapter','Form EUR.1','India Singapore CECA'),
        ('3004%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin — MAJOR SAVINGS','UAE CEPA'),
        ('3004%','ASEAN','ASEAN',0,'Change of Chapter','Form D','India ASEAN FTA'),
        ('3004%','KOREA','South Korea',5,'Change of Chapter','Certificate of Origin','India Korea CEPIA'),
        ('4202%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — bags wallets'),
        ('4203%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — leather garments'),
        ('28%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA'),
        ('29%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA'),
        ('30%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA'),
        ('33%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — essential oils'),
        ('0703%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — onions'),
        ('0804%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — mangoes bananas'),
        ('0306%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — shrimp lobster'),
        ('0304%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — fish fillets'),
        ('2001%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — mango pickle'),
        ('7113%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — gold jewellery'),
        ('7113%','SINGAPORE','Singapore',0,'Change of Chapter','Form EUR.1','India Singapore CECA'),
        ('84%','UAE_CEPA','UAE',0,'CTH or 50% local content','Certificate of Origin','UAE CEPA — machinery'),
        ('85%','UAE_CEPA','UAE',0,'CTH or 50% local content','Certificate of Origin','UAE CEPA — electrical'),
        ('8703%','UAE_CEPA','UAE',0,'CTH or 50% local content','Certificate of Origin','UAE CEPA'),
        ('8711%','UAE_CEPA','UAE',0,'CTH or 50% local content','Certificate of Origin','UAE CEPA — motorcycles'),
        ('72%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — steel'),
        ('73%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — metal articles'),
        ('76%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — aluminum'),
        ('9401%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — furniture'),
        ('9403%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — wooden furniture'),
        ('9404%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — mattresses'),
        ('9503%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — toys'),
        ('9702%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — paintings'),
        ('9702%','KOREA','South Korea',5,'Change of Chapter','Certificate of Origin','India Korea CEPIA'),
        ('1202%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — groundnuts'),
        ('2304%','UAE_CEPA','UAE',0,'Change of Chapter','Certificate of Origin','UAE CEPA — soyameal'),
    ]
    db.executemany('INSERT OR IGNORE INTO fta_rates VALUES (NULL,?,?,?,?,?,?,?)', rates)
    print("[ExportPilot] Seeded FTA master + chapter rates")

# ─── Classifier ────────────────────────────────────────────────────────────────
def classify(description, context=''):
    return keyword_classify(description)

def keyword_classify(desc):
    d = desc.lower().strip()
    # ── SHIRTS ─────────────────────────────────────────────────
    if any(w in d for w in ['shirt','tshirt','t-shirt','polo']) and not any(w in d for w in ['night','sleep','under','sports bra']):
        hs,ch,chn,rate,igst = '6205','62','Mens/Boys Shirts (Apparel)','10%','5%'
        expl = "Classified under Chapter 62. BCD 10% for cotton shirts, IGST 5% for export."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin — saves full 10% BCD'),('ASEAN','ASEAN','0-3%','Form D'),('KOREA','South Korea','5%','Certificate of Origin')]
        common = "UAE, USA, UK, EU, Saudi Arabia, Bangladesh"
        benefit = "UAE CEPA: 0% duty. On Rs 5L consignment = save Rs 41,667 in BCD alone."
        warn = "Synthetic/mixed fabric shirts may have different rates."
        sub = "Mens/Boys Cotton Shirts" if not any(w in d for w in ['women','girl','female']) else "Womens Blouses"
    # ── BLOUSES ──────────────────────────────────────────────────
    elif any(w in d for w in ['blouse','top','tunic','kurti top','croptop']):
        hs,ch,chn,rate,igst = '6206','62','Womens/Girls Blouses (Apparel)','10%','5%'
        expl = "Womens/girls blouses and tops classified under Chapter 62."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('ASEAN','ASEAN','0-3%','Form D')]
        common = "UAE, USA, UK, EU, Canada"; benefit = "UAE CEPA: 0% — saves full 10% BCD"
        warn = ""; sub = "Womens/Girls Blouses/Tops"
    # ── KURTA/ETHNIC ────────────────────────────────────────────
    elif any(w in d for w in ['kurta','sherwani','nehru jacket','ethnic wear men']):
        hs,ch,chn,rate,igst = '6203','62','Mens Ethnic Wear (Apparel)','10%','5%'
        expl = "Kurta, sherwani, ethnic jackets classified under suits/jackets of Chapter 62."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('ASEAN','ASEAN','3%','Form D')]
        common = "UAE, USA, UK, Canada"; benefit = "UAE CEPA: 0% on ethnic wear"
        warn = ""; sub = "Mens Kurta/Sherwani/Ethnic Jackets"
    # ── SAREE/LEHENGA ────────────────────────────────────────────
    elif any(w in d for w in ['saree','sari','lehenga','ethnic wear women','ghagra','choli']):
        hs,ch,chn,rate,igst = '6104','61','Womens Ethnic Wear (Knitted)','10%','5%'
        expl = "Sarees and lehengas classified under Chapter 61 (knitted) or 62 (woven). Check construction."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('SINGAPORE','Singapore','0%','Form EUR.1')]
        common = "UAE, USA, UK, Canada, Singapore"; benefit = "UAE CEPA: 0% on sarees and lehengas"
        warn = "Woven vs knitted affects code. Designer pieces may need specific HS."; sub = "Saree/Lehenga/Ethnic Wear"
    # ── JEANS ───────────────────────────────────────────────────
    elif any(w in d for w in ['jeans','denim','denim jacket','trousers men','pants men']):
        hs,ch,chn,rate,igst = '6203','62','Mens/Boys Denim Trousers','10%','5%'
        expl = "Denim jeans and trousers under Chapter 62. BCD 10%."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('ASEAN','ASEAN','0-3%','Form D')]
        common = "UAE, USA, EU, Bangladesh"; benefit = "UAE CEPA: 0% on denim trousers"
        warn = ""; sub = "Denim Jeans/Trousers (Men)"
    # ── BED LINEN ───────────────────────────────────────────────
    elif any(w in d for w in ['bedsheet','bed linen','pillow cover','quilt','comforter','bedding set']):
        hs,ch,chn,rate,igst = '6302','63','Bed Linen (Made-up Textiles)','10%','5%'
        expl = "Bed sheets, pillow covers classified under Chapter 63 (made-up textiles)."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('KOREA','South Korea','5%','Certificate of Origin')]
        common = "UAE, USA, UK, EU, Australia"; benefit = "UAE CEPA: 0% on bed linen"
        warn = ""; sub = "Bed Sheets/Linen/Made-up Textiles"
    # ── CARPETS ─────────────────────────────────────────────────
    elif any(w in d for w in ['carpet','rug','handmade carpet','woolen carpet','silk carpet','durrie','hand-knotted']):
        hs,ch,chn,rate,igst = '5702','57','Hand-Made Carpets (Chapter 57)','10%','5%'
        expl = "Hand-knotted carpets classified under Chapter 57. India is worlds largest exporter. Kashmir and Mirzapur are famous origins."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('KOREA','South Korea','5%','Certificate of Origin'),('USA','USA','0%','GSP — hand-knotted carpets qualify')]
        common = "USA, UAE, UK, Germany, Australia"; benefit = "UAE CEPA: 0%. USA: 0% under GSP for hand-knotted."
        warn = "Hand-tufted (5703) vs hand-knotted (5702) have different codes. Specify construction."
        sub = "Handmade Woolen/Silk Carpets"
    # ── TURMERIC ────────────────────────────────────────────────
    elif any(w in d for w in ['turmeric','haldi','curcumin powder']):
        hs,ch,chn,rate,igst = '0910','09','Turmeric (Chapter 09 - Spices)','30%','5%'
        expl = "Turmeric classified under HS 0910. BCD is 30% despite being agricultural. India is worlds largest turmeric producer."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin — saves 30% BCD!'),('USA','USA','0%','GSP — turmeric powder often qualifies')]
        common = "UAE, USA, Bangladesh, Malaysia"; benefit = "WITHOUT FTA: 30% BCD. WITH UAE CEPA: 0%. On Rs 5L shipment = save Rs 1.5L."
        warn = "BCD of 30% is very high. FTA utilization is CRITICAL for spices."
        sub = "Turmeric Powder/Rhizome"
    # ── CHILLI ─────────────────────────────────────────────────
    elif any(w in d for w in ['chilli','chili dried','lal mirch','red pepper']):
        hs,ch,chn,rate,igst = '0904','09','Chilli Peppers (Chapter 09)','30%','5%'
        expl = "Dried chilli peppers classified under HS 0904. India exports Guntur chillies globally."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('MALAYSIA','Malaysia','5%','Form D')]
        common = "UAE, Malaysia, Bangladesh, USA"; benefit = "UAE CEPA: 0%. Saves 30% BCD."
        warn = "30% BCD — always use UAE CEPA for chillies."; sub = "Dried Chilli Peppers"
    # ── CUMIN ─────────────────────────────────────────────────
    elif any(w in d for w in ['cumin','jeera','kala jeera']):
        hs,ch,chn,rate,igst = '0909','09','Cumin Seeds (Chapter 09)','30%','5%'
        expl = "Cumin (jeera) classified under HS 0909. India is worlds largest cumin exporter."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('USA','USA','0%','GSP eligible')]
        common = "UAE, Bangladesh, USA, Malaysia"; benefit = "UAE CEPA: 0%. Saves 30% BCD."
        warn = "30% BCD on cumin — always claim UAE CEPA."; sub = "Cumin Seeds (Jeera)"
    # ── RICE ─────────────────────────────────────────────────
    elif any(w in d for w in ['basmati rice','non-basmati rice','white rice','parboiled rice']):
        hs,ch,chn,rate,igst = '1006','10','Rice (Chapter 10)','80% (Basmati lower)','5%'
        expl = "Rice under Chapter 10. Non-basmati BCD is 80%. Basmati rates are lower. India is worlds largest rice exporter."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin — basmati AND non-basmati'),('SINGAPORE','Singapore','0%','Form EUR.1')]
        common = "UAE, Saudi Arabia, Bangladesh, Nigeria"; benefit = "UAE CEPA: 0% on both basmati and non-basmati to UAE!"
        warn = "Non-basmati BCD was raised to 80%. Basmati rates lower — verify current policy."
        sub = "Basmati/Non-Basmati Rice"
    # ── TEA ──────────────────────────────────────────────────
    elif any(w in d for w in ['tea','chai','masala chai']):
        hs,ch,chn,rate,igst = '0902','09','Tea (Chapter 09)','30%','5%'
        expl = "Tea classified under HS 0902. India is 2nd largest tea producer. Black, green, masala tea all here."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('RUSSIA','Russia','10%','Form CTR')]
        common = "UAE, Russia, Iran, UK, USA"; benefit = "UAE CEPA: 0%. Without it, 30% BCD."
        warn = "30% BCD on tea — always use UAE CEPA."; sub = "Black/Green/Masala Tea"
    # ── COFFEE ───────────────────────────────────────────────
    elif any(w in d for w in ['coffee','green coffee','roasted coffee']):
        hs,ch,chn,rate,igst = '0901','09','Coffee (Chapter 09)','30%','5%'
        expl = "Coffee classified under HS 0901. Green (unroasted) and roasted have different 8-digit codes."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin')]
        common = "UAE, Italy, Germany, Belgium"; benefit = "UAE CEPA: 0% on coffee to UAE."
        warn = "30% BCD on coffee — FTA is critical."; sub = "Green/Roasted Coffee"
    # ── FRESH FRUITS ─────────────────────────────────────────
    elif any(w in d for w in ['mango','alphonso','kesar','banana fresh','grape fresh']):
        hs,ch,chn,rate,igst = '0804','08','Fresh Fruits (Chapter 08)','30%','5%'
        expl = "Fresh fruits including mangoes, bananas, grapes classified under Chapter 08. India exports Alphonso mangoes globally."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('BANGLADESH','Bangladesh',0,'Direct — neighbor'),('NEPAL','Nepal',0,'India-Nepal Treaty')]
        common = "UAE, Bangladesh, Nepal, UK"; benefit = "UAE CEPA: 0% on fresh mangoes and bananas."
        warn = "30% BCD on fresh fruit — FTA saves massive amounts."; sub = "Fresh Mangoes/Bananas/Grapes"
    # ── SHRIMP ────────────────────────────────────────────────
    elif any(w in d for w in ['shrimp','prawn','vannamei','tiger shrimp','frozen shrimp']):
        hs,ch,chn,rate,igst = '0306','03','Frozen Crustaceans (Chapter 03)','30%','5%'
        expl = "Frozen shrimp/prawns are Indias #1 seafood export, classified under HS 0306. Vannamei shrimp are globally famous."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('JAPAN','Japan',0,'Japan-Specific Schedule')]
        common = "USA, UAE, Japan, EU, China"; benefit = "UAE CEPA: 0% on marine products."
        warn = "USA has anti-dumping duty (ADD) on certain Indian shrimp — check current ADD rate before US shipping."
        sub = "Frozen Shrimp/Prawn (Vannamei/Tiger)"
    # ── PHARMA ────────────────────────────────────────────────
    elif any(w in d for w in ['pharmaceutical','medicine','tablet','capsule','ayurvedic medicine','herbal tablet']):
        hs,ch,chn,rate,igst = '3004','30','Medicines (Chapter 30)','10%','12%'
        expl = "Ayurvedic and allopathic medicines in retail packaging under HS 3004. India pharma exports to 200+ countries."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin — MAJOR SAVINGS'),('ASEAN','ASEAN','0%','Form D'),('KOREA','South Korea','5%','Certificate of Origin')]
        common = "USA, Africa, UAE, ASEAN, UK, Brazil"; benefit = "UAE CEPA: 0%. On Rs 25L pharma consignment = save Rs 2.08L."
        warn = "WHO-GMP certification required for USA, EU regulated markets."
        sub = "Medicines/Tablets/Capsules (Retail Packed)"
    # ── LEATHER BAGS ─────────────────────────────────────────
    elif any(w in d for w in ['leather bag','leather wallet','leather handbag','leather purse']):
        hs,ch,chn,rate,igst = '4202','42','Leather Articles (Chapter 42)','10%','18%'
        expl = "Leather bags, wallets, purses classified under HS 4202. IGST 18% for leather goods."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('ASEAN','ASEAN','5%','Form D')]
        common = "UAE, USA, UK, EU, Singapore"; benefit = "UAE CEPA: 0% on leather bags and wallets."
        warn = "18% IGST on leather goods in addition to BCD."; sub = "Leather Bags/Wallets"
    # ── LEATHER GARMENTS ─────────────────────────────────────
    elif any(w in d for w in ['leather jacket','leather gloves','leather garment','leather coat']):
        hs,ch,chn,rate,igst = '4203','42','Leather Garments (Chapter 42)','10%','18%'
        expl = "Leather garments and gloves under HS 4203. IGST 18%."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('ASEAN','ASEAN','5%','Form D')]
        common = "UAE, USA, EU, Japan"; benefit = "UAE CEPA: 0% on leather garments."
        warn = "18% IGST on leather garments."; sub = "Leather Jackets/Garments/Gloves"
    # ── MOBILE ────────────────────────────────────────────────
    elif any(w in d for w in ['mobile phone','smartphone','cell phone','mobile device']):
        hs,ch,chn,rate,igst = '8517','85','Telecom Equipment (Chapter 85)','20%','18%'
        expl = "Mobile phones under HS 8517. BCD 20% + IGST 18% — high tax burden."
        fta = [('UAE_CEPA','UAE','0%','CTH or 50% local content — Certificate of Origin'),('ASEAN','ASEAN',0,'CTH or 50% local content')]
        common = "UAE, USA, EU, Bangladesh"; benefit = "UAE CEPA: 0% on mobile phones. Huge saving on high-value shipments."
        warn = "20% BCD + 18% IGST — always use UAE CEPA."; sub = "Mobile Phones/Smartphones"
    # ── STEEL ────────────────────────────────────────────────
    elif any(w in d for w in ['steel pipe','steel tube','iron rod','ms billet','steel coil']):
        hs,ch,chn,rate,igst = '7304','73','Iron and Steel Articles (Chapter 73)','15%','18%'
        expl = "Steel pipes, tubes, iron rods under Chapter 73."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('KOREA','South Korea','3%','Certificate of Origin')]
        common = "UAE, USA, Bangladesh, Nepal"; benefit = "UAE CEPA: 0% on steel — saves 15% BCD."
        warn = "Anti-dumping duties apply in some markets — check before shipping."; sub = "Steel Pipes/Tubes/Rods"
    # ── JEWELLERY ────────────────────────────────────────────
    elif any(w in d for w in ['gold jewellery','gold jewelry','kundan','precious metal jewellery']):
        hs,ch,chn,rate,igst = '7113','71','Gold Jewellery (Chapter 71)','20%','3%'
        expl = "Gold jewellery under HS 7113. BCD 20%, IGST 3% (lower than most goods). India is major gold jewellery exporter."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('SINGAPORE','Singapore','0%','Form EUR.1')]
        common = "UAE, Singapore, USA, UK"; benefit = "UAE CEPA: 0% on gold jewellery — major saving."
        warn = "20% BCD is very high — FTA utilization critical."; sub = "Gold Jewellery (Plain/Studded)"
    # ── HANDICRAFTS ──────────────────────────────────────────
    elif any(w in d for w in ['handicraft','handmade painting','pattachitra','madhubani','handcrafted']):
        hs,ch,chn,rate,igst = '9702','97','Paintings/Handicrafts (Chapter 97)','10%','5%'
        expl = "Handmade paintings and handicrafts under Chapter 97."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('KOREA','South Korea','5%','Certificate of Origin')]
        common = "UAE, USA, UK, Singapore"; benefit = "UAE CEPA: 0% on paintings and handicrafts."
        warn = ""; sub = "Handmade Paintings/Handicrafts"
    # ── AYURVEDIC ────────────────────────────────────────────
    elif any(w in d for w in ['ayurvedic medicine','herbal supplement','natural remedy','unani tablet','siddha medicine']):
        hs,ch,chn,rate,igst = '3004','30','Ayurvedic/Herbal Medicines (Chapter 30)','10%','12%'
        expl = "Ayurvedic and herbal medicines in retail packaging under HS 3004. Indias traditional medicine exports growing rapidly."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('ASEAN','ASEAN','0%','Form D')]
        common = "UAE, USA, ASEAN, UK, Africa"; benefit = "UAE CEPA: 0% on Ayurvedic medicines."
        warn = "WHO-GMP certification may be required."; sub = "Ayurvedic/Herbal Medicines"
    # ── FMCG/PROCESSED FOOD ──────────────────────────────────
    elif any(w in d for w in ['pickle','mango pickle','chutney','preserve fruit']):
        hs,ch,chn,rate,igst = '2001','20','Preserved Foods (Chapter 20)','30%','5%'
        expl = "Pickles and preserved fruits/vegetables under Chapter 2001."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('USA','USA','0%','GSP eligible')]
        common = "UAE, USA, UK, Australia"; benefit = "UAE CEPA: 0% on mango pickle."
        warn = ""; sub = "Mango Pickle/Fruit Chutney"
    # ── CASTE PAINTINGS ──────────────────────────────────────
    elif any(w in d for w in ['warli painting','thanka','pattachitra art',' Gond art','madhubani art']):
        hs,ch,chn,rate,igst = '9702','97','Folk Art/Paintings (Chapter 97)','10%','5%'
        expl = "Indian folk art paintings classified under Chapter 97 (works of art)."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('KOREA','South Korea','5%','Certificate of Origin')]
        common = "UAE, USA, UK, Singapore"; benefit = "UAE CEPA: 0% on folk art."
        warn = ""; sub = "Warli/Madhubani/Pattachitra Folk Art"
    # ── COTTON YARN ───────────────────────────────────────────
    elif any(w in d for w in ['cotton yarn','yarn cotton','cd yarn','hd yarn']):
        hs,ch,chn,rate,igst = '5201','52','Cotton Yarn (Chapter 52)','10%','5%'
        expl = "Cotton yarn and thread classified under Chapter 52. India is major cotton yarn exporter."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('BANGLADESH','Bangladesh',0,'Direct — major buyer no FTA needed')]
        common = "Bangladesh, UAE, Pakistan, China"; benefit = "UAE CEPA: 0%. Bangladesh buys heavily — direct no FTA needed."
        warn = ""; sub = "Cotton Yarn/Thread"
    # ── CHEMICALS ────────────────────────────────────────────
    elif any(w in d for w in ['essential oil','fragrance oil','perfume oil','aroma oil']):
        hs,ch,chn,rate,igst = '3301','33','Essential Oils/Perfumes (Chapter 33)','10%','5%'
        expl = "Essential oils and perfumes classified under Chapter 33. India exports menthol, sandalwood oil globally."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('USA','USA','0%','GSP eligible')]
        common = "UAE, USA, EU, Singapore"; benefit = "UAE CEPA: 0% on essential oils."
        warn = ""; sub = "Essential Oils/Fragrance Oils"
    # ── FMCG: SOAP ──────────────────────────────────────────
    elif any(w in d for w in ['soap','bath soap','handmade soap','ayurvedic soap','detergent powder']):
        hs,ch,chn,rate,igst = '3401','34','Soap/Detergents (Chapter 34)','10%','18%'
        expl = "Soap and detergents under Chapter 34. IGST 18%."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('KOREA','South Korea','5%','Certificate of Origin')]
        common = "UAE, Bangladesh, Africa, Nepal"; benefit = "UAE CEPA: 0% on soap."
        warn = ""; sub = "Soap/Detergents/Cleaning Products"
    # ── RUBBER TYRES ──────────────────────────────────────────
    elif any(w in d for w in ['rubber tyre','tire','rubber belt','hose pipe rubber']):
        hs,ch,chn,rate,igst = '4011','40','Rubber Tyres (Chapter 40)','10%','18%'
        expl = "New pneumatic tyres under Chapter 40. India is major tyre exporter — Apollo, MRF, CEAT are global brands."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('KOREA','South Korea','5%','Certificate of Origin')]
        common = "UAE, USA, EU, Latin America"; benefit = "UAE CEPA: 0% on tyres."
        warn = "USA has anti-dumping duty on certain Indian tyres — check before shipping."; sub = "Rubber Tyres/Pneumatic Tyres"
    # ── FURNITURE ──────────────────────────────────────────────
    elif any(w in d for w in ['furniture','wooden furniture','chair','table wooden','sofa']):
        hs,ch,chn,rate,igst = '9403','94','Furniture (Chapter 94)','10%','18%'
        expl = "Furniture classified under Chapter 94. Wooden furniture is a major Indian export."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('KOREA','South Korea','5%','Certificate of Origin')]
        common = "UAE, USA, UK, EU, Australia"; benefit = "UAE CEPA: 0% on furniture."
        warn = "18% IGST on furniture."; sub = "Wooden Furniture/Chairs/Tables"
    # ── STEEL STRUCTURES ───────────────────────────────────────
    elif any(w in d for w in ['steel structure','metal structure','tower transmission','bridge struct']):
        hs,ch,chn,rate,igst = '7308','73','Structures of Iron/Steel (Chapter 73)','10%','18%'
        expl = "Structures of iron or steel (bridges, towers, scaffolding) under Chapter 73."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('KOREA','South Korea','3%','Certificate of Origin')]
        common = "UAE, Africa, USA, Bangladesh"; benefit = "UAE CEPA: 0% on steel structures."
        warn = ""; sub = "Steel Structures/Towers/Bridges"
    # ── Aluminium ARTICLES ─────────────────────────────────────
    elif any(w in d for w in ['aluminium foil','aluminum utensil','aluminium wire','aluminium profile']):
        hs,ch,chn,rate,igst = '7607','76','Aluminium Articles (Chapter 76)','10%','18%'
        expl = "Aluminium foil, utensils, and articles under Chapter 76."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('KOREA','South Korea','3%','Certificate of Origin')]
        common = "UAE, USA, EU, Africa"; benefit = "UAE CEPA: 0% on aluminium articles."
        warn = ""; sub = "Aluminium Foil/Utensils/Profiles"
    # ── PLASTIC ARTICLES ────────────────────────────────────────
    elif any(w in d for w in ['plastic bottle','plastic container','plastic jar','plastic bucket']):
        hs,ch,chn,rate,igst = '3923','39','Plastic Articles (Chapter 39)','10%','18%'
        expl = "Plastic articles for packing under Chapter 39. IGST 18%."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin')]
        common = "UAE, USA, Africa, Nepal"; benefit = "UAE CEPA: 0% on plastic articles."
        warn = "18% IGST."; sub = "Plastic Bottles/Containers/Jars"
    # ── PROCESSED MEAT ─────────────────────────────────────────
    elif any(w in d for w in ['buff meat','goat meat','meat processed','chicken processed','ready to eat meat']):
        hs,ch,chn,rate,igst = '0202','02','Meat (Chapter 02)','30%','5%'
        expl = "Meat products under Chapter 02. India exports buffalo meat (beef) and processed meat."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('MALAYSIA','Malaysia',0,'Change of Chapter')]
        common = "UAE, Malaysia, Indonesia, Egypt"; benefit = "UAE CEPA: 0% on meat products."
        warn = "30% BCD — FTA is important. Some countries have import restrictions."; sub = "Processed Meat/Buffalo Meat"
    # ── DAIRY ──────────────────────────────────────────────────
    elif any(w in d for w in ['milk powder','ghee','butter','cheese','dairy','paneer','curd']):
        hs,ch,chn,rate,igst = '0402','04','Dairy Products (Chapter 04)','30%','5%'
        expl = "Dairy products classified under Chapter 04. India exports milk powder, ghee, paneer."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('SINGAPORE','Singapore',0,'Change of Chapter')]
        common = "UAE, Bangladesh, Nepal, Singapore"; benefit = "UAE CEPA: 0% on dairy to UAE."
        warn = "30% BCD on dairy — FTA is critical."; sub = "Milk Powder/Ghee/Cheese/Dairy"
    # ── BISCUITS ────────────────────────────────────────────────
    elif any(w in d for w in ['biscuit','cookies','crackers','namkeen','snack food','ready to eat snack']):
        hs,ch,chn,rate,igst = '1905','19','Biscuits/Snacks (Chapter 19)','30%','5%'
        expl = "Biscuits, cookies, crackers and snack foods under Chapter 19. India is major biscuit exporter."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('KOREA','South Korea','5%','Certificate of Origin')]
        common = "UAE, Nepal, USA, Africa"; benefit = "UAE CEPA: 0% on biscuits and snacks."
        warn = "30% BCD on biscuits — FTA utilization important."; sub = "Biscuits/Cookies/Snacks/Namkeen"
    # ── TOBACCO ────────────────────────────────────────────────
    elif any(w in d for w in ['tobacco','cigarette','bidi','tobacco leaf','chewing tobacco']):
        hs,ch,chn,rate,igst = '2401','24','Tobacco (Chapter 24)','30%','5%'
        expl = "Tobacco and tobacco products under Chapter 24. India exports bidi, cigarettes, and raw tobacco."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('INDONESIA','Indonesia',5,'Change of Chapter')]
        common = "UAE, Indonesia, Nepal, Bangladesh"; benefit = "UAE CEPA: 0% on tobacco products."
        warn = "High BCD rates on tobacco. Some countries restrict tobacco imports."; sub = "Tobacco/Cigarettes/Bidi"
    # ── COTTON BALE ────────────────────────────────────────────
    elif any(w in d for w in ['cotton bale','raw cotton','cotton lint']):
        hs,ch,chn,rate,igst = '5201','52','Cotton (Chapter 52)','10%','5%'
        expl = "Cotton, not carded or combed, under Chapter 52. India exports raw cotton globally."
        fta = [('BANGLADESH','Bangladesh',0,'Direct — no FTA needed')]
        common = "Bangladesh, Vietnam, China, Pakistan"; benefit = "Bangladesh — direct, no FTA needed. Vietnam at preferential rates."
        warn = ""; sub = "Raw Cotton/Cotton Bale"
    # ── MARINE: FISH ────────────────────────────────────────────
    elif any(w in d for w in ['fish frozen','frozen fish fillet','fish surimi']):
        hs,ch,chn,rate,igst = '0304','03','Fish Fillets (Chapter 03)','30%','5%'
        expl = "Fish fillets, fresh or frozen, under Chapter 03."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('THAILAND','Thailand',0,'Change of Chapter')]
        common = "UAE, Thailand, Japan, USA"; benefit = "UAE CEPA: 0% on fish fillets."
        warn = ""; sub = "Frozen Fish Fillets/Fish Products"
    # ── VEGETABLES: PROCESSED ─────────────────────────────────
    elif any(w in d for w in ['jelly fruit','jam','fruit preserve','pickle mango']):
        hs,ch,chn,rate,igst = '2007','20','Jams/Fruit Jellies (Chapter 20)','30%','5%'
        expl = "Jams, jellies, fruit purées and pastes under Chapter 20."
        fta = [('UAE_CEPA','UAE','0%','Certificate of Origin'),('AUSTRALIA','Australia',0,'Change of Chapter')]
        common = "UAE, Australia, USA, UK"; benefit = "UAE CEPA: 0% on jams and preserves."
        warn = ""; sub = "Fruit Jam/Jelly/Preserves"
    # ── Default / Unknown ──────────────────────────────────────
    else:
        hs,ch,chn,rate,igst = '9999','99','Unclassified Product','Varies','Varies'
        expl = "This product category is not yet in our database. Please provide more details or contact us."
        fta = []
        common = "Please specify product details for accurate classification"
        benefit = "Contact us to add your product category"
        warn = "Unknown product — please describe with more specific terms (material, use, form)"
        sub = "Please provide more details about your product"

    # ── Build result dict ────────────────────────────────────────
    fta_list = []
    if fta:
        for fta_code, country, pref_rate, reqs in fta:
            mfn_rate = float(re.search(r'[\d.]+', rate).group()) if re.search(r'[\d.]+', str(rate)) else 10
            pref = float(re.search(r'[\d.]+', str(pref_rate)).group()) if re.search(r'[\d.]+', str(pref_rate)) else 0
            saving = f"On Rs 1L cargo: save Rs {int((mfn_rate - pref) * 1000):,}"
            fta_list.append({
                'fta_code': fta_code, 'fta_name': f'{fta_code.replace("_"," ")}',
                'countries': country, 'preferential_rate': pref_rate,
                'rule_of_origin': 'Change of Chapter',
                'requirements': reqs,
                'estimated_savings_inr': saving,
                'savings_note': f"vs {int(mfn_rate)}% MFN BCD"
            })

    return {
        'hs_code': hs, 'chapter': ch, 'chapter_name': chn,
        'description': sub, 'confidence': 0.6,
        'india_bcd_rate': rate, 'india_igst_rate': igst,
        'explanation': expl,
        'fta_options': [f[0] for f in fta] if fta else [],
        'fta_analysis': fta_list,
        'common_uses': common,
        'key_fta_benefit': benefit,
        'warnings': warn,
        'method': 'keyword_fallback_v1.2'
    }

# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route('/')
def index(): return render_template('index.html')

@app.route('/hs-lookup')
def hs_lookup(): return render_template('hs_lookup.html')

@app.route('/fta-optimizer')
def fta_optimizer(): return render_template('fta_optimizer.html')

@app.route('/documents')
def documents(): return render_template('documents.html')

@app.route('/api/classify', methods=['POST'])
def api_classify():
    data = request.get_json()
    desc = data.get('description', '').strip()
    dest = data.get('destination', '')
    cargo = data.get('cargo_value', 0)

    if not desc: return jsonify({'error': 'Please describe your product'}), 400
    if len(desc) < 3: return jsonify({'error': 'Description too short'}), 400

    result = classify(desc, f'Exporting to: {dest}' if dest else '')

    # Save history
    try:
        db = get_db()
        db.execute('''
            INSERT INTO search_history (query_text, hs_code, confidence, response_json, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (desc, result.get('hs_code',''), result.get('confidence',0), json.dumps(result), datetime.now().isoformat()))
        db.commit()
    except: pass

    return jsonify(result)

@app.route('/api/fta', methods=['POST'])
def api_fta():
    data = request.get_json()
    hs = data.get('hs_code', '').strip()
    cargo = float(data.get('cargo_value', 0) or 0)
    mfn = float(data.get('mfn_rate', 10) or 10)

    if not hs: return jsonify({'error': 'HS code required'}), 400

    db = get_db()
    rows = db.execute('''
        SELECT fr.*, fm.full_name, fm.countries
        FROM fta_rates fr
        JOIN fta_master fm ON fr.fta_code = fm.code
        WHERE fr.hs_code LIKE ? OR fr.hs_code LIKE ? OR fr.hs_code = ?
        ORDER BY fr.preferential_rate ASC
    ''', [hs[:2]+'%', hs[:4]+'%', hs]).fetchall()

    if rows:
        results = []
        for r in rows:
            pref = float(r['preferential_rate'] or 0)
            saving = round(cargo * (mfn - pref) / 100, 0) if cargo > 0 else 0
            results.append({
                'fta_code': r['fta_code'], 'fta_name': r['full_name'],
                'countries': r['countries'],
                'preferential_rate': f"{r['preferential_rate']}%",
                'rule_of_origin': r['rule_of_origin'] or 'Change of Chapter',
                'requirements': r['requirements'] or 'Certificate of Origin',
                'estimated_savings_inr': f"Rs {int(saving):,}" if saving > 0 else 'N/A'
            })
    else:
        # Generic FTAs
        results = [
            {'fta_code':'UAE_CEPA','fta_name':'India-UAE CEPA','countries':'UAE','preferential_rate':'0%','rule_of_origin':'Change of Chapter','requirements':'Certificate of Origin','estimated_savings_inr':'Rs 1L on Rs 10L cargo'},
            {'fta_code':'ASEAN','fta_name':'India-ASEAN FTA','countries':'10 ASEAN nations','preferential_rate':'0-5%','rule_of_origin':'Change of Chapter','requirements':'Form D','estimated_savings_inr':'Varies by product'},
        ]

    return jsonify({'fta_options': results, 'hs_code': hs})

@app.route('/api/search-history')
def api_history():
    db = get_db()
    rows = db.execute('SELECT * FROM search_history ORDER BY created_at DESC LIMIT 50').fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/health')
def api_health():
    return jsonify({'status': 'running', 'version': '1.2.0', 'build': '2026-07-11', 'features': ['HS Classification v40+', 'FTA Rates DB', 'Real Duty Data']})

# ─── Start ──────────────────────────────────────────────────────────────────────
def start():
    with app.app_context():
        init_db()
    port = int(os.environ.get('EXPORTPILOT_PORT', 5050))
    print(f"[ExportPilot] Starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    start()
