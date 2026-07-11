"""
ExportPilot - AI Trade Co-Pilot for Indian Exporters
Phase 1 MVP: HS Code Classifier + FTA Duty Optimizer

Build: 2026-07-11
"""

import os
import sqlite3
import json
import re
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, jsonify, g
import requests

app = Flask(__name__)
app.config['DATABASE'] = '/data/exportpilot/exportpilot.db'

# ─── OpenRouter Config ────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'

# ─── Database ─────────────────────────────────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Create tables if they don't exist."""
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS hs_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,       -- e.g. '6204' or '6204.62'
            chapter TEXT NOT NULL,           -- e.g. '62'
            description TEXT NOT NULL,
            level INTEGER DEFAULT 6,          -- 2,4,6,8 digit level
            parent_code TEXT
        );

        CREATE TABLE IF NOT EXISTS india_tariff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hs_code TEXT NOT NULL,
            bcd_rate REAL,                   -- Basic Customs Duty %
            igst_rate REAL,                  -- Integrated GST %
            social_welfare_cess REAL,        -- SWS %
            applied_from TEXT,
            fta_eligible INTEGER DEFAULT 0,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS fta_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hs_code TEXT NOT NULL,
            fta_code TEXT NOT NULL,         -- 'UAE_CEPA', 'ASEAN', 'JAPAN', etc.
            partner_country TEXT NOT NULL,
            preferential_rate REAL,           -- Preferential duty %
            rule_of_origin TEXT,              -- e.g. 'Change of Chapter' or '50% local content'
            requirements TEXT,                -- Free text on documentation needed
            source TEXT
        );

        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_text TEXT NOT NULL,
            hs_code TEXT,
            confidence REAL,
            response_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS fta_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,       -- 'UAE_CEPA', 'ASEAN', etc.
            full_name TEXT NOT NULL,
            countries TEXT NOT NULL,          -- comma-separated
            effective_date TEXT,
            coverage TEXT                     -- goods/services/both
        );
    ''')
    
    # Seed FTA master data if empty
    cur = db.execute('SELECT COUNT(*) FROM fta_master')
    if cur.fetchone()[0] == 0:
        seed_fta_master(db)
    
    db.commit()
    print("[ExportPilot] Database initialized")

def seed_fta_master(db):
    """Seed India's active FTAs."""
    ftas = [
        ('UAE_CEPA', 'India-UAE CEPA', 'UAE', '2022-05-01', 'goods_services'),
        ('ASEAN', 'India-ASEAN FTA', 'Brunei, Cambodia, Indonesia, Laos, Malaysia, Myanmar, Philippines, Singapore, Thailand, Vietnam', '2010-01-01', 'goods'),
        ('JAPAN', 'India-Japan CEPA', 'Japan', '2011-08-01', 'goods_services'),
        ('KOREA', 'India-Korea CEPIA', 'South Korea', '2010-01-01', 'goods_services'),
        ('MAURITIUS', 'India-Mauritius ECECA', 'Mauritius', '2008-04-01', 'goods_services'),
        ('SINGAPORE', 'India-Singapore CECA', 'Singapore', '2005-08-01', 'goods_services'),
        ('SRI_LANKA', 'India-Sri Lanka FTA', 'Sri Lanka', '2000-03-01', 'goods'),
        ('NEPAL', 'India-Nepal Treaty', 'Nepal', '1950-07-31', 'goods'),
        ('BHUTAN', 'India-Bhutan Agreement', 'Bhutan', '1949-07-31', 'goods'),
        ('MERCOSUR', 'India-MERCOSUR PTA', 'Argentina, Brazil, Paraguay, Uruguay', '2009-06-01', 'goods'),
        ('CHILE', 'India-Chile PTA', 'Chile', '2007-08-01', 'goods'),
        ('ISRAEL', 'India-Israel FTA', 'Israel', '2023-04-01', 'goods_services'),
        ('UK', 'India-UK FTA', 'United Kingdom', '2022-05-01', 'goods_services'),
        ('AUSTRALIA', 'India-Australia ECTA', 'Australia', '2022-12-01', 'goods_services'),
        ('EU', 'India-EU FTA', 'EU (27 countries)', '2026-02-01', 'goods_services'),
    ]
    db.executemany('''
        INSERT OR IGNORE INTO fta_master (code, full_name, countries, effective_date, coverage)
        VALUES (?, ?, ?, ?, ?)
    ''', ftas)
    print("[ExportPilot] FTA master seeded")

# ─── AI Classification ─────────────────────────────────────────────────────────
def classify_with_ai(product_description: str, context: str = '') -> dict:
    """
    Use OpenRouter LLM to classify HS code from product description.
    Falls back to keyword matching if no API key.
    """
    if OPENROUTER_API_KEY:
        system_prompt = """You are an expert Indian customs and trade specialist.
Given a product description, you MUST return a JSON object with:
{
  "hs_code": "XXXX.XX" (6-digit HS code, or 8-digit Indian tariff line if confident),
  "chapter": "XX",
  "chapter_name": "Chapter name",
  "description": "Concise product description",
  "confidence": 0.0-1.0,
  "india_bcd_rate": "X%",
  "india_igst_rate": "X%",
  "explanation": "Why this HS code is correct",
  "fta_options": ["UAE", "ASEAN", etc. - any FTAs where this product gets preferential rates],
  "common_uses": "Where this product is typically exported from India",
  "warnings": "Any classification pitfalls or similar products to distinguish from"
}
Return ONLY valid JSON. No markdown, no explanation outside the JSON."""

        try:
            headers = {
                'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://exportpilot.in',
                'X-Title': 'ExportPilot'
            }
            payload = {
                'model': 'openrouter/auto',
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': f'Classify this Indian export product:\n\n{product_description}\n\nContext: {context}'}
                ],
                'temperature': 0.3,
                'max_tokens': 800
            }
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            content = data['choices'][0]['message']['content'].strip()
            # Extract JSON from response
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]
            content = content.strip()
            return json.loads(content)
        except Exception as e:
            print(f"[ExportPilot] AI classification failed: {e}")
            return keyword_classify(product_description)
    else:
        return keyword_classify(product_description)

def keyword_classify(description: str) -> dict:
    """Fallback keyword-based HS code classifier for Phase 1."""
    desc = description.lower()
    
    # Textile & Apparel patterns
    if any(w in desc for w in ['shirt', 'tshirt', 't-shirt', 'top', 'blouse', 'kurta', 'suit']):
        chapter = '62'; ch_name = 'Articles of apparel and clothing accessories, not knitted or crocheted'
        hs6 = '6205'; rate = '10%'; igst = '5%'
        if 'men' in desc or 'boy' in desc: hs6 = '6205'; sub = 'Mens/boys shirts'
        elif 'women' in desc or 'girl' in desc or 'blouse' in desc: hs6 = '6206'; sub = 'Womens/girls blouses'
        elif 'kurta' in desc: hs6 = '6203'; sub = 'Mens/boys suits, jackets'
        else: sub = 'Mens/boys shirts, of cotton'
    elif any(w in desc for w in ['saree', 'sari', 'dress', 'ethnic']):
        chapter = '62'; ch_name = 'Articles of apparel'; hs6 = '6208'; rate = '10%'; igst = '5%'
        sub = 'Womens/girls singlets and other vests'
    elif any(w in desc for w in ['cotton', 'fabric', 'textile', 'woven fabric', 'grey cloth']):
        chapter = '52'; ch_name = 'Cotton'; hs6 = '5208'; rate = '10%'; igst = '5%'
        sub = 'Woven fabrics of cotton'
    elif any(w in desc for w in ['carpet', 'rug', 'handmade carpet', 'woolen carpet', 'silk carpet']):
        chapter = '57'; ch_name = 'Carpets and textile floor coverings'; hs6 = '5702'; rate = '10%'; igst = '5%'
        sub = 'Carpets, hand-made'
    elif any(w in desc for w in ['spice', 'turmeric', 'chilli', 'cumin', 'coriander', 'pepper', 'masala']):
        chapter = '09'; ch_name = 'Coffee, tea, mate and spices'; hs6 = '0910'; rate = '30%'; igst = '5%'
        sub = 'Ginger, saffron, turmeric, thyme, bay leaves, curry'
    elif any(w in desc for w in ['rice', 'basmati', 'non-basmati', 'white rice']):
        chapter = '10'; ch_name = 'Cereals'; hs6 = '1006'; rate = '80% (free for some)' ; igst = '5%'
        sub = 'Rice'
    elif any(w in desc for w in ['pharmaceutical', 'medicine', 'tablet', 'capsule', 'drug', 'ayurvedic', 'herbal medicine']):
        chapter = '30'; ch_name = 'Pharmaceutical products'; hs6 = '3004'; rate = '10%'; igst = '12%'
        sub = 'Medicaments, retail packed'
    elif any(w in desc for w in ['leather', 'leather bag', 'leather wallet', 'leather shoe', 'leather jacket']):
        chapter = '42'; ch_name = 'Leather articles'; hs6 = '4202'; rate = '10%'; igst = '18%'
        sub = 'Trunks, suit-cases, handbags'
    elif any(w in desc for w in ['mobile', 'phone', 'smartphone', 'cell phone']):
        chapter = '85'; ch_name = 'Electrical machinery'; hs6 = '8517'; rate = '20%'; igst = '18%'
        sub = 'Telephone sets, smartphones'
    elif any(w in desc for w in ['software', 'saas', 'cloud service', 'it service', 'consulting service']):
        chapter = 'S'; ch_name = 'Services (GTA exemption)'; hs6 = 'SVC'; rate = '0%'; igst = '18%'
        sub = 'Software/IT Services export'
    elif any(w in desc for w in ['tea', 'coffee']):
        chapter = '09'; ch_name = 'Coffee, tea, mate and spices'
        if 'tea' in desc: hs6 = '0902'; sub = 'Tea'
        else: hs6 = '0901'; sub = 'Coffee'
        rate = '30%'; igst = '5%'
    elif any(w in desc for w in ['diamond', 'gem', 'jewellery', 'jewelry', 'gold', 'silver', 'platinum']):
        chapter = '71'; ch_name = 'Natural/Cultured pearls, precious metals'
        hs6 = '7113'; rate = '20%'; igst = '3%'
        sub = 'Gold jewellery'
    elif any(w in desc for w in ['steel', 'iron', 'metal', 'aluminum']):
        chapter = '72'; ch_name = 'Iron and steel'; hs6 = '7204'; rate = '15%'; igst = '18%'
        sub = 'Ferrous waste and scrap'
    elif any(w in desc for w in ['plastic', 'polymer', 'pet bottle', 'packaging']):
        chapter = '39'; ch_name = 'Plastics and articles thereof'; hs6 = '3923'; rate = '10%'; igst = '18%'
        sub = 'Containers, plastic'
    elif any(w in desc for w in ['handicraft', 'handicraft item', 'artisan', 'handmade']):
        chapter = '97'; ch_name = 'Works of art, collectors pieces'; hs6 = '9702'; rate = '10%'; igst = '5%'
        sub = 'Handmade paintings'
    elif any(w in desc for w in ['basil', 'herbs', 'medicinal plant', 'ayurvedic raw']):
        chapter = '12'; ch_name = 'Oil seeds, medicinal plants'; hs6 = '1211'; rate = '10%'; igst = '5%'
        sub = 'Plants and parts of plants for perfumery/pharmacy'
    else:
        chapter = '99'; ch_name = 'Miscellaneous manufactured articles'; hs6 = '9999'; rate = 'varies'; igst = 'varies'
        sub = 'Please provide more details for precise classification'

    return {
        'hs_code': hs6,
        'chapter': chapter,
        'chapter_name': ch_name,
        'description': sub if 'sub' in dir() else description,
        'confidence': 0.5,
        'india_bcd_rate': rate,
        'india_igst_rate': igst,
        'explanation': f'Classified based on keyword matching for: {description}',
        'fta_options': ['UAE_CEPA', 'ASEAN', 'KOREA', 'JAPAN'],
        'common_uses': 'Commonly exported from India to UAE, USA, EU, Bangladesh',
        'warnings': 'Verify with a customs broker for exact 8-digit Indian tariff line',
        'method': 'keyword_fallback'
    }

# ─── FTA Optimization ─────────────────────────────────────────────────────────
def get_fta_rates(hs_code: str, product_desc: str = '') -> list:
    """
    Return applicable FTA rates for a HS code.
    In production this would query actual FTA tariff schedules.
    For MVP we return known FTA preferential rates for common HS chapters.
    """
    db = get_db()
    results = db.execute('''
        SELECT f.code, f.full_name, f.countries, f.effective_date,
               fr.preferential_rate, fr.rule_of_origin, fr.requirements
        FROM fta_rates fr
        JOIN fta_master f ON fr.fta_code = f.code
        WHERE fr.hs_code = ? OR fr.hs_code = ? OR fr.hs_code = ?
        ORDER BY fr.preferential_rate ASC
    ''', [hs_code[:4] + '%', hs_code[:2] + '%', hs_code]).fetchall()
    
    if not results:
        # Return generic FTA info for the chapter
        fta_info = db.execute('''
            SELECT code, full_name, countries, effective_date FROM fta_master
        ''').fetchall()
        return [
            {
                'fta_code': f['code'],
                'fta_name': f['full_name'],
                'countries': f['countries'],
                'preferential_rate': '0-5% (varies by product)',
                'rule_of_origin': 'Typically Change of Chapter or 35-50% local content',
                'requirements': 'Certificate of Origin (Form D/Form EUR1/etc.)',
                'estimated_savings': '2-10% of cargo value depending on product'
            }
            for f in fta_info
        ]
    
    return [dict(r) for r in results]

# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/hs-lookup')
def hs_lookup():
    return render_template('hs_lookup.html')

@app.route('/fta-optimizer')
def fta_optimizer():
    return render_template('fta_optimizer.html')

@app.route('/documents')
def documents():
    return render_template('documents.html')

@app.route('/api/classify', methods=['POST'])
def api_classify():
    data = request.get_json()
    description = data.get('description', '').strip()
    destination = data.get('destination', '')
    
    if not description:
        return jsonify({'error': 'Please provide a product description'}), 400
    
    if len(description) < 3:
        return jsonify({'error': 'Description too short. Please describe your product in more detail.'}), 400
    
    # Run AI classification
    result = classify_with_ai(description, f'Exporting to: {destination}' if destination else 'Domestic or export')
    
    if not result:
        return jsonify({'error': 'Classification service temporarily unavailable. Please try again.'}), 500
    
    # Save to history
    db = get_db()
    db.execute('''
        INSERT INTO search_history (query_text, hs_code, confidence, response_json)
        VALUES (?, ?, ?, ?)
    ''', (description, result.get('hs_code',''), result.get('confidence',0), json.dumps(result)))
    db.commit()
    
    # Get FTA options
    hs_code = result.get('hs_code', '')
    if hs_code and hs_code != 'SVC':
        fta_options = get_fta_rates(hs_code, description)
        result['fta_analysis'] = fta_options
    
    return jsonify(result)

@app.route('/api/fta', methods=['POST'])
def api_fta():
    data = request.get_json()
    hs_code = data.get('hs_code', '').strip()
    product_desc = data.get('description', '')
    cargo_value = float(data.get('cargo_value', 0))
    destination = data.get('destination', '')
    
    if not hs_code:
        return jsonify({'error': 'HS code required'}), 400
    
    fta_results = get_fta_rates(hs_code, product_desc)
    
    # Calculate savings estimates
    for fta in fta_results:
        rate_str = fta.get('preferential_rate', '0%')
        try:
            pref_rate = float(re.search(r'[\d.]+', str(rate_str)).group()) if re.search(r'[\d.]+', str(rate_str)) else 0
            mfn_rate = float(re.search(r'[\d.]+', str(data.get('mfn_rate', '10%'))).group()) if re.search(r'[\d.]+', str(data.get('mfn_rate', '10%'))) else 10
        except:
            pref_rate = 5; mfn_rate = 10
        
        savings = cargo_value * (mfn_rate - pref_rate) / 100
        fta['estimated_savings_inr'] = round(savings, 2) if cargo_value > 0 else 'Varies by cargo value'
    
    return jsonify({'fta_options': fta_results, 'hs_code': hs_code})

@app.route('/api/search-history')
def api_history():
    db = get_db()
    rows = db.execute('''
        SELECT * FROM search_history ORDER BY created_at DESC LIMIT 50
    ''').fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/validate-hs', methods=['POST'])
def api_validate_hs():
    """Validate if an HS code is valid for India."""
    data = request.get_json()
    hs_code = data.get('hs_code', '').strip().replace('.', '').replace(' ', '')
    
    # Basic validation
    if not hs_code.isdigit():
        return jsonify({'valid': False, 'error': 'HS code must contain only digits'})
    
    if len(hs_code) not in [2, 4, 6, 8]:
        return jsonify({'valid': False, 'error': 'HS code must be 2, 4, 6, or 8 digits'})
    
    return jsonify({'valid': True, 'hs_code': hs_code, 'normalized': True})

@app.route('/api/health')
def api_health():
    return jsonify({
        'status': 'running',
        'version': '1.0.0-MVP',
        'build': '2026-07-11',
        'features': ['HS Classification', 'FTA Optimization', 'Document Templates']
    })

# ─── Startup ──────────────────────────────────────────────────────────────────
def start_app():
    with app.app_context():
        init_db()
    port = int(os.environ.get('EXPORTPILOT_PORT', 5050))
    print(f"[ExportPilot] Starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    start_app()
