"""Demo data seeder — Metso Outotec / Nordea / Wärtsilä."""
import uuid
from datetime import datetime, timezone, timedelta

from core import db, hash_password, logger
from models import Role, SignalStatus
from services.embedding import semantic_embed, sector_hash
from services.swarm import update_clusters


async def seed_demo():
    default_tenants = [
        {"id": "default-tenant", "name": "Metso Outotec", "sector": "Manufacturing"},
        {"id": "tenant-nordea", "name": "Nordea", "sector": "Financial Services"},
        {"id": "tenant-wartsila", "name": "Wärtsilä", "sector": "Energy & Marine"},
    ]
    for t in default_tenants:
        if not await db.tenants.find_one({"id": t["id"]}):
            await db.tenants.insert_one({
                "id": t["id"], "name": t["name"], "sector": t["sector"],
                "sector_hash": sector_hash(t["sector"]),
                "description": f"{t['name']} — Suvereeniteettianalyysi tenant",
                "created_at": datetime.now(timezone.utc),
                "active": True,
            })
        else:
            await db.tenants.update_one({"id": t["id"]}, {"$set": {
                "name": t["name"], "sector": t["sector"], "sector_hash": sector_hash(t["sector"])
            }})

    users_seed = [
        {"email": "admin@talktoplus.io", "password": "Admin!2026", "full_name": "Anna Tunnuslause", "role": Role.SUPER_ADMIN.value, "tenant_id": "default-tenant"},
        {"email": "facilitator@talktoplus.io", "password": "Facil!2026", "full_name": "Matti Korhonen", "role": Role.FACILITATOR.value, "tenant_id": "default-tenant"},
        {"email": "exec@talktoplus.io", "password": "Exec!2026", "full_name": "Anna Virtanen", "role": Role.EXECUTIVE.value, "tenant_id": "default-tenant"},
    ]
    for u in users_seed:
        if not await db.users.find_one({"email": u["email"]}):
            await db.users.insert_one({
                "id": str(uuid.uuid4()),
                "email": u["email"], "full_name": u["full_name"],
                "password_hash": hash_password(u["password"]),
                "role": u["role"], "tenant_id": u["tenant_id"],
                "locale": "fi",
                "created_at": datetime.now(timezone.utc),
            })

    if await db.strategy_docs.count_documents({"tenant_id": "default-tenant"}) == 0:
        txt = (
            "Metso Outotec strategia 2026: kestävän kaivosteollisuuden kärkitoimittajaksi. "
            "Painopisteet: digitaalinen huolto-alusta, alihankkijoiden laatuauditit, "
            "Q3 ERP-migraatio, henkilöstön sitouttaminen muutoshankkeisiin. "
            "Kriittiset kyvykkyydet: insinöörikapasiteetti, datapohjainen päätöksenteko, "
            "alihankkijaverkoston laadunhallinta."
        )
        vec = semantic_embed(txt)
        await db.strategy_docs.insert_one({
            "id": str(uuid.uuid4()), "tenant_id": "default-tenant",
            "title": "Metso Outotec — Strategia 2026",
            "content": txt, "chunks": 4,
            "uploaded_by": "Anna Tunnuslause",
            "created_at": datetime.now(timezone.utc), "vector": vec,
        })

    if await db.signals.count_documents({}) < 12 or not await db.signals.find_one({"content": {"$regex": "Q3-projektin"}}):
        await db.signals.delete_many({})
        await db.action_cards.delete_many({})
        await db.swarm_fragments.delete_many({})
        await db.universal_bottlenecks.delete_many({})

        FACILITATORS = ["Matti Korhonen", "Anna Virtanen", "Jukka Mäkinen"]

        demo_signals = [
            {"t": "default-tenant", "bu": "Engineering", "rl": "HIGH", "cat": "resources", "age_d": 7,
             "content": "Resurssipula hidastaa Q3-projektin toimitusta — 3 insinööriä puuttuu tiimistä."},
            {"t": "default-tenant", "bu": "Quality", "rl": "CRITICAL", "cat": "process", "age_d": 2,
             "content": "Laadunvalvontaprosessi ei kata alihankkijatasoa — löytöjä auditissa."},
            {"t": "default-tenant", "bu": "IT", "rl": "MODERATE", "cat": "process", "age_d": 12,
             "content": "Uusi ERP-järjestelmä aiheuttaa katkoksia tilausten käsittelyssä."},
            {"t": "default-tenant", "bu": "HR", "rl": "HIGH", "cat": "engagement", "age_d": 5,
             "content": "Henkilöstön sitoutuminen Q2 muutoshankkeeseen alle tavoitetason (42%)."},
            {"t": "tenant-nordea", "bu": "Compliance", "rl": "HIGH", "cat": "resources", "age_d": 3,
             "content": "Compliance-tiimi ylikuormittunut — uusi regulaatio vaatii 200h lisäkapasiteettia."},
            {"t": "tenant-nordea", "bu": "Customer Service", "rl": "MODERATE", "cat": "process", "age_d": 9,
             "content": "Asiakaspalvelun vasteaika kasvanut 34% — syy tuntematon."},
            {"t": "tenant-nordea", "bu": "Strategy", "rl": "LOW", "cat": "engagement", "age_d": 18,
             "content": "Strateginen kumppanuusneuvottelu jumissa — päätöksentekijä ei vastaa."},
            {"t": "tenant-nordea", "bu": "IT", "rl": "MODERATE", "cat": "capabilities", "age_d": 6,
             "content": "IT-infrastruktuuri ei tue hybridityömallia — 40% etätyöntekijöistä raportoi ongelmia."},
            {"t": "tenant-wartsila", "bu": "Supply Chain", "rl": "CRITICAL", "cat": "resources", "age_d": 1,
             "content": "Toimitusketjun häiriö — kriittinen komponentti viivästyy 6 viikkoa."},
            {"t": "tenant-wartsila", "bu": "Strategy", "rl": "HIGH", "cat": "engagement", "age_d": 4,
             "content": "Johdon ja operatiivisen tason strategiaymmärrys eroaa merkittävästi."},
            {"t": "tenant-wartsila", "bu": "Digital", "rl": "HIGH", "cat": "process", "age_d": 8,
             "content": "Uusi digitalisaatiohanke ilman selkeää omistajuutta — 3 tiimiä, 0 vastuuhenkilöä."},
            {"t": "tenant-wartsila", "bu": "HR", "rl": "CRITICAL", "cat": "capabilities", "age_d": 2,
             "content": "Henkilöstövaihtuvuus kasvanut 28% — exit-haastattelut viittaavat johtamisongelmiin."},
        ]

        IMPACT_SCORES = [6, 8, 9, 4, 7, 9, 8, 5, 7, 6, 8, 9]
        CARD_STATUSES = ["pending_validation", "validated", "in_progress", "pending_validation",
                         "in_progress", "validated", "pending_validation", "dismissed",
                         "in_progress", "validated", "pending_validation", "in_progress"]
        SWARM_VERIFIED_FLAGS = [True, False, True, False, True, False, False, True, True, False, False, True]

        gaps_by_cat = {
            "resources": ["Kapasiteettilisäys ei toteutunut sovitussa aikataulussa", "Resurssien priorisointi epäselvä", "Tiimin ylikuormitus näkyy mittareissa"],
            "capabilities": ["Osaamiskartoitus puuttuu", "Koulutusbudjetti alimitoitettu", "Senior-tason siirtyminen ei johda osaamisen siirtoon"],
            "engagement": ["Sisäinen viestintä katkonaista", "Town hall -käytänteet eivät toteudu", "Palautteenkeruu puuttuu"],
            "process": ["Vastuuhenkilö epäselvä", "Mittareita ei seurata viikkotasolla", "Standardiprosessi puuttuu kriittisessä vaiheessa"],
        }
        questions = [
            "Kuka omistaa tämän seuraavat 2 viikkoa?",
            "Mitä konkreettista tukea tarvitaan 48h sisällä?",
            "Mihin strategiseen tavoitteeseen tämä vaikuttaa eniten?",
        ]

        CARD_TITLES_PLAYBOOKS = {
            0: ("Insinöörikapasiteetin pikalisäys Q3-toimitukseen",
                "Kohdennetaan 3 insinööriä ulkoisilta kumppaneilta 14 päivän sisällä ja varmistetaan tiedonsiirto kahden viikon yhteistyöjaksolla. Vältetään toimitusriskin eskaloituminen, joka vaarantaisi 18 M€ Q3-arvon.",
                ["1. Aktivoi raamisopimus 2 päivän sisällä Tieto Engineering -kumppanin kanssa",
                 "2. Allokoi 10 päivän knowledge transfer ennen kriittistä faasia",
                 "3. Päivitä Q3-toimitusgantt ja viesti asiakkaalle proaktiivisesti",
                 "4. Aseta viikoittainen burn-down -mittari ohjausryhmään",
                 "5. Päätöspiste 4 vk: jatka vai eskaloi C-tasolle"]),
            1: ("Alihankkijatason laatuauditit 30 päivässä",
                "Käynnistetään top-10 alihankkijan laatuauditit ja luodaan jatkuva valvontamalli, jolla estetään löytöjen toistuminen tulevissa audiointiin. Painopiste kriittisessä jäähdytyskomponenttilinjassa.",
                ["1. Listaa top-10 alihankkijaa volyymin ja kriittisyyden perusteella",
                 "2. Suorita on-site -audit jokaiselle 30 vk:n aikana",
                 "3. Implementoi yhteinen laatu-KPI -raportointi (kuukausittain)",
                 "4. Sopimusrikkomus-eskalaatiomalli alihankkijoille",
                 "5. Q1-2027 katselmus: vähennä laatuvirheet -50%"]),
            2: ("ERP-katkojen pikadiagnoosi ja stabilointi",
                "Perustetaan ERP War Room 48 tunnin sisällä, identifioidaan 3 suurinta katkoslähdettä ja stabiloidaan tilaustenkäsittely. Tilausvolyymin liiketoimintavaikutus on 4 M€ kuukaudessa.",
                ["1. Kokoa War Room: IT lead + ERP vendor + Operations lead",
                 "2. Diagnosoi top-3 katkos-juurisyyt 5 päivässä",
                 "3. Hot-fix priorisointi: tilausreititys ensin",
                 "4. Daily stand-up viikon ajan, kunnes vakaa",
                 "5. Post-mortem ja preventiivinen toimenpidelista"]),
            3: ("Sitoutumisen nostaminen Q2-muutoshankkeessa",
                "Käynnistetään fokusryhmäkierros 3 yksikössä viikon sisällä, identifoidaan 5 keskeisintä huolta ja vastataan niihin avoimella town hall -formaatilla. Tavoite 65% sitoutuminen Q3-mittauksessa.",
                ["1. Pulse-kysely 200 työntekijälle 3 päivän sisällä",
                 "2. 6 fokusryhmää: 3 yksikköä × 2 ryhmää",
                 "3. Top-5 huolen julkinen vastausnäyttö",
                 "4. Town Hall livestreamilla Q&A:llä",
                 "5. Q3 sitoutumismittaus + raportti henkilöstöjohdolle"]),
            4: ("Compliance-kapasiteetin nopea skaalaus",
                "Hankitaan 200h ulkoinen compliance-kapasiteetti seuraaviksi 2 kuukaudeksi ja samalla automatisoidaan 30% tarkistustyöstä RegTech-työkalulla. Riski regulaattorin sanktiosta vältetään.",
                ["1. RFP-kierros 3 compliance-vendorille viikon sisällä",
                 "2. Allekirjoita 8 viikon kapasiteettisopimus 200h:lle",
                 "3. Pilotoi Workiva/MetricStream automaatio top-3 prosessissa",
                 "4. Mittari: compliance-läpimenoaika -40%",
                 "5. Päätöspiste: ostetaanko vendor-tool pysyvästi Q4:llä"]),
            5: ("Asiakaspalvelun juurisyyanalyysi vasteajan kasvuun",
                "Suoritetaan kanavakohtainen analyysi 7 päivässä, kohdennetaan resurssit ruuhkahuippuihin ja otetaan käyttöön self-service-pilotti TOP-5 kysymystyypille. Tavoite -20% vasteaika 30 päivässä.",
                ["1. Kanava-data-pull viim. 90 pv: chat / puhelu / email",
                 "2. Identifioi 3 ruuhka-aikaa ja 5 toistuvaa kysymystä",
                 "3. Self-service pilotti chatbotilla top-5 kysymyksiin",
                 "4. Roster-optimointi ruuhka-aikoina",
                 "5. KPI-mittaus 30 vk:n jälkeen"]),
            6: ("Strategisen kumppaneiden eskalaatiomalli",
                "Luodaan 2-tason eskalaatiomalli kumppanuusneuvotteluihin: 7 päivää ilman vastausta → tason 2 yhteyshenkilö, 14 päivää → C-tason eskalaatio. Estetään strategisten projektien jumiutuminen.",
                ["1. Mallinna eskalaatiopolku: päivät 0-7-14",
                 "2. Nimeä C-tason sponsor jokaiselle TOP-10 kumppanille",
                 "3. Kvartaalitarkastelu sponsoreille",
                 "4. SLA kirjaus partner-sopimuksiin",
                 "5. Päivitä CRM eskalaatiotrigger-säännöillä"]),
            7: ("Hybridityömallin IT-tukikuilun sulkeminen",
                "Suoritetaan hybridityö-IT-auditti 14 päivässä, priorisoidaan VPN/wifi/laitteistovaivat ja toteutetaan korjaukset vaiheessa 1 (30 päivää). Tavoite: ongelmat raportointi alle 10%.",
                ["1. Hybridi-IT pulssi-kysely 500 etätyöntekijälle",
                 "2. Top-3 ongelman priorisointi (VPN / Wifi / Endpoint)",
                 "3. Vaihe 1: pikakorjaukset 30 vk:n sisällä",
                 "4. Vaihe 2: laitteistopäivityskierros budjetoitu",
                 "5. Mittaus: tikettilaadun lasku -50%"]),
            8: ("Kriittisen komponentin toimitusketjun risk-mitigaatio",
                "Aktivoidaan secondary supplier 7 päivässä, varastoidaan 12 viikon turvavarasto kriittisille tuotteille ja neuvotellaan toimituksen siirtohinta minimiin. Tavoite: 0 viivettä asiakassuorituksiin.",
                ["1. Secondary supplier -aktivointi: tilaus + ekspressitoimitus",
                 "2. 12 vk:n turvavarasto kriittisille SKU:ille",
                 "3. Asiakasviestintä proaktiivisesti TOP-20",
                 "4. Vaihtoehtoisen reitityksen logistiikka",
                 "5. Q4 supplier-diversifikaatiostrategia"]),
            9: ("Strategian operationalisointi: johdon ja operatiivisen tason yhteinen kieli",
                "Pidetään kahden päivän strategia-alignment -työpaja johdolle ja operatiivisille esimiehille, luodaan 5 selkeää OKR:ää kvartaalille. Mitataan ymmärrystä OKR-pulssikyselyllä 30 päivän välein.",
                ["1. 2 pv strategia-alignment offsite (CEO + 30 esimiestä)",
                 "2. Yhteiset 5 Q4 OKR:ää, mitattavat",
                 "3. OKR-pulssi joka 30 vk: ymmärrysprosentti tavoite >85%",
                 "4. Esimiesten cascade-vastuu omaan tiimiin",
                 "5. Q1-2027 katselmus + säätö"]),
            10: ("Digitalisaatiohankkeen omistajuusmalli",
                 "Nimetään yksi C-tason sponsori ja yksi product owner 3 päivässä, perustetaan steering group ja siirretään kolmen tiimin työ yhteen backlogiin. Estetään 6 kk hukkainvestointi.",
                 ["1. C-tason sponsoripäätös 3 päivässä",
                  "2. Product Owner -roolitus, raamisopimus",
                  "3. Steering group: 5 jäsentä, kahden viikon välein",
                  "4. Yhteinen backlog Jiraan, kolmen tiimin yhdistäminen",
                  "5. 30 vk:n re-baselining päätös"]),
            11: ("Henkilöstövaihtuvuuden pysäyttäminen — johtamiskvaliteettiprojekti",
                 "Käynnistetään 360°-arvioinnit johtoryhmälle, allokoidaan 1 coach per esimies seuraaviksi 6 kk. Mitataan eNPS:ä kuukausittain, tavoite vaihtuvuus alle 12% Q4-Q1.",
                 ["1. 360° kierros TOP-30 esimiehelle 30 vk:n sisällä",
                  "2. Executive coach -ohjelma 6 kk",
                  "3. eNPS kuukausittain (anonymously)",
                  "4. Exit-data deep-dive: 3 toistuvaa juurisyytä",
                  "5. Henkilöstöjohdon kvartaaliraportti hallitukselle"]),
        }

        now = datetime.now(timezone.utc)
        for i, s in enumerate(demo_signals):
            t_ago = now - timedelta(days=s["age_d"])
            sid = str(uuid.uuid4())
            vec = semantic_embed(s["content"])
            summary = f"Toimeenpanoriski tasolla {s['rl']} kategoriassa {s['cat']}: {s['content'][:80]}"
            facilitator = FACILITATORS[i % 3]
            doc = {
                "id": sid, "tenant_id": s["t"],
                "content": s["content"], "source": "manual",
                "business_unit": s["bu"], "author": facilitator,
                "submitted_at": t_ago,
                "status": SignalStatus.VALIDATED.value,
                "risk_level": s["rl"],
                "confidence": round(0.72 + (0.20 if s["rl"] == "CRITICAL" else 0.10 if s["rl"] == "HIGH" else 0.05), 2),
                "summary": summary,
                "execution_gaps": gaps_by_cat[s["cat"]],
                "hidden_assumptions": ["Oletetaan nykyinen kapasiteetti riittää", "Vastuunjako ymmärretään yhtenäisesti"],
                "facilitator_questions": questions,
                "category": s["cat"],
                "semantic_vector": vec,
                "validated_by": facilitator,
                "validated_at": t_ago + timedelta(minutes=22),
                "validation_note": "Verifioitu strategiaa vasten",
                "override_risk_level": None,
                "swarm_fragment_id": None, "action_card_id": None,
            }
            await db.signals.insert_one(doc.copy())

            tenant = await db.tenants.find_one({"id": s["t"]}, {"_id": 0})
            frag_id = str(uuid.uuid4())
            await db.swarm_fragments.insert_one({
                "id": frag_id, "sector_hash": tenant["sector_hash"],
                "sector_display": tenant["sector"],
                "risk_level": s["rl"], "confidence": doc["confidence"],
                "category": s["cat"], "semantic_vector": vec,
                "created_at": doc["validated_at"],
            })

            title, summary_card, playbook = CARD_TITLES_PLAYBOOKS[i]
            patterns = []
            if SWARM_VERIFIED_FLAGS[i]:
                patterns = [
                    f"Vahvistettu 7 vastaavassa organisaatiossa — {tenant['sector']} -sektori",
                    "Mediaaniaikataulu 35 päivää, onnistumisaste 78%",
                    "Top success factor: nopea omistajuusnimitys (<3 vk)",
                ]
            card_id = str(uuid.uuid4())
            await db.action_cards.insert_one({
                "id": card_id, "tenant_id": s["t"], "signal_id": sid,
                "title": title, "summary": summary_card, "playbook": playbook,
                "rag_context_used": ["Strategia 2026"],
                "swarm_patterns_used": patterns,
                "impact_score": IMPACT_SCORES[i],
                "swarm_verified": SWARM_VERIFIED_FLAGS[i],
                "swarm_verified_count": 7 if SWARM_VERIFIED_FLAGS[i] else 0,
                "status": CARD_STATUSES[i], "facilitator": facilitator,
                "created_at": doc["validated_at"] + timedelta(minutes=1),
            })
            await db.signals.update_one({"id": sid}, {"$set": {"swarm_fragment_id": frag_id, "action_card_id": card_id}})

        # Pending signal for Decision Hub demo
        pending_sid = str(uuid.uuid4())
        pending_content = "Q3-julkaisuaikataulu vaarassa: kahden senior-insinöörin lähtö ei näy kapasiteettisuunnittelussa, ja korvaava rekrytointi on 8 viikkoa myöhässä."
        vec = semantic_embed(pending_content)
        await db.signals.insert_one({
            "id": pending_sid, "tenant_id": "default-tenant",
            "content": pending_content, "source": "howspace",
            "business_unit": "Engineering", "author": "Anonymous",
            "submitted_at": datetime.now(timezone.utc) - timedelta(minutes=14),
            "status": SignalStatus.PENDING.value,
            "risk_level": "HIGH", "confidence": 0.84,
            "summary": "Q3-julkaisuaikataulu vaarassa kapasiteettivajeen ja viivästyneen rekrytoinnin takia.",
            "execution_gaps": ["Kapasiteettisuunnittelu ei reagoinut lähtöihin", "Rekrytointiprosessi ei skaalaudu kriittiseen tarpeeseen", "Asiakasviestintä ei proaktiivista"],
            "hidden_assumptions": ["Oletettu, että lähtevien tilalle saadaan korvaajat 4 vk:n sisällä"],
            "facilitator_questions": ["Onko Q3-aikataulu uudelleenneuvoteltavissa?", "Voiko ulkoinen kumppani siltarata kapasiteetin?"],
            "category": "resources", "semantic_vector": vec,
            "validated_by": None, "validated_at": None, "validation_note": None,
            "override_risk_level": None, "swarm_fragment_id": None, "action_card_id": None,
        })

        await update_clusters()

    logger.info("Seed complete (rich data)")
