"""
ExportPilot Part 2 - Remaining classifier + Routes
"""
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
