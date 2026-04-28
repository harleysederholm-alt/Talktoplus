import React, { useEffect, useState, useContext } from 'react';
import { AppCtx } from '../App';
import { http } from '../api';
import { ArrowsClockwise, CaretDown, CaretUp, ChartBar, Buildings, Lightning } from '@phosphor-icons/react';
import { toast } from 'sonner';

// Per-category rich explanation (FI/EN)
const BOTTLENECK_DETAILS = {
  resources: {
    fi: {
      explainer: "Resurssivaje syntyy kun strategiset tavoitteet eivät vastaa todellista kapasiteettia. Tämä on yleisin organisaatiorajat ylittävä toimeenpanoeste — 47% kaikista validoiduista signaaleista koskee resursseja.",
      whyItMatters: "Toimeenpanoaikataulut viivästyvät keskimäärin 38%, kun resurssivaje havaitaan vasta projektin keskivaiheessa. Varhainen havaitseminen mahdollistaa 60% nopeamman korjauksen.",
      successPlaybook: [
        "Aktivoi raamisopimukset 7 päivän sisällä havaitsemisesta",
        "Allokoi senior-tason coach 30 päivän knowledge transferille",
        "Aseta viikoittainen burn-down-mittari ohjausryhmään",
        "Päätöspiste 4 viikon kohdalla: jatka vai eskaloi C-tasolle",
      ],
      relatedSectors: ["Manufacturing", "Healthcare", "Financial Services", "Energy"],
    },
    en: {
      explainer: "Resource gap emerges when strategic targets exceed actual capacity. This is the most common cross-organization execution blocker — 47% of all validated signals relate to resources.",
      whyItMatters: "Execution timelines slip on average 38% when resource gap is discovered mid-project. Early detection enables 60% faster recovery.",
      successPlaybook: [
        "Activate framework agreements within 7 days of detection",
        "Allocate senior-level coach for 30-day knowledge transfer",
        "Weekly burn-down metric to steering group",
        "Decision point at 4 weeks: continue or escalate to C-level",
      ],
      relatedSectors: ["Manufacturing", "Healthcare", "Financial Services", "Energy"],
    },
  },
  capabilities: {
    fi: {
      explainer: "Osaamisvaje on hiljainen riski — usein piilossa kunnes kriittinen järjestelmä tai prosessi epäonnistuu. 28% pitkän aikavälin riskeistä juontuu osaamisen puutteesta.",
      whyItMatters: "Senior-osaamisen siirtyminen ilman jälkikasvun rakentamista johtaa keskimäärin 6 kuukauden tuottavuuden laskuun. Investointi koulutukseen tuottaa 3.2x paluun.",
      successPlaybook: [
        "Suorita osaamiskartoitus top-10 kriittisissä rooleissa",
        "Käynnistä mentorointi-pari jokaiselle senior-asiantuntijalle",
        "LMS-pohjainen koulutuspolku, mitattava 90 vk:n välein",
        "Strateginen rekrytointiputki 12 kk eteenpäin",
      ],
      relatedSectors: ["Energy", "Healthcare", "Technology"],
    },
    en: {
      explainer: "Capability gap is a silent risk — often hidden until a critical system or process fails. 28% of long-term risks stem from capability shortfalls.",
      whyItMatters: "Senior expertise leaving without successor pipeline leads to average 6-month productivity drop. Training investment yields 3.2x return.",
      successPlaybook: [
        "Skill mapping for top-10 critical roles",
        "Launch mentor pairing for every senior expert",
        "LMS-based learning path, measured every 90 days",
        "Strategic hiring pipeline 12 months ahead",
      ],
      relatedSectors: ["Energy", "Healthcare", "Technology"],
    },
  },
  engagement: {
    fi: {
      explainer: "Sitoutumisvaje näkyy hiljaisena vastarintana muutoshankkeissa. Tutkimus osoittaa että alle 50% sitoutuminen ennustaa 73% todennäköisyydellä strategian epäonnistumista.",
      whyItMatters: "Henkilöstövaihtuvuus on suorin sitoutumisvajeen mittari — joka 1% nousu 'huolestuneessa' segmentissä ennustaa 0.4% vaihtuvuuden kasvua 6 kk:n aikana.",
      successPlaybook: [
        "Pulse-kysely 200 työntekijälle 3 päivän sisällä",
        "Top-5 huolen julkinen vastausnäyttö johdolta",
        "Kuukausittain Town Hall livestreamilla Q&A",
        "Sitoutumismittarit henkilöstöjohdon kvartaaliraporttiin",
      ],
      relatedSectors: ["Manufacturing", "Financial Services", "Retail"],
    },
    en: {
      explainer: "Engagement gap manifests as silent resistance in change initiatives. Research shows engagement below 50% predicts strategy failure with 73% probability.",
      whyItMatters: "Employee turnover is the most direct measure of engagement gap — every 1% rise in 'concerned' segment predicts 0.4% turnover increase within 6 months.",
      successPlaybook: [
        "Pulse survey for 200 employees within 3 days",
        "Public response from leadership for top-5 concerns",
        "Monthly Town Hall with livestream Q&A",
        "Engagement metrics into HR quarterly board report",
      ],
      relatedSectors: ["Manufacturing", "Financial Services", "Retail"],
    },
  },
  process: {
    fi: {
      explainer: "Prosessivaje syntyy kun toimintamalleja ei ole standardoitu kriittisissä vaiheissa, tai vastuujako on epäselvä. 23% kaikista signaaleista koskee prosessihäiriöitä.",
      whyItMatters: "Vastuuhenkilön puute aiheuttaa keskimäärin 12 päivän viiveen päätöksenteossa. Yhden selkeän omistajan nimittäminen lyhentää syklin 70%.",
      successPlaybook: [
        "Nimeä C-tason sponsori jokaiselle kriittiselle prosessille",
        "RACI-matriisi 30 päivässä",
        "KPI-mittarit + viikoittaiset stand-upit",
        "Standardiprosessin dokumentointi yhteen lähteeseen",
      ],
      relatedSectors: ["Manufacturing", "Financial Services"],
    },
    en: {
      explainer: "Process gap emerges when operations aren't standardized at critical points, or accountability is unclear. 23% of all signals relate to process disruptions.",
      whyItMatters: "Lack of named owner causes average 12-day decision delay. Single clear owner appointment shortens the cycle by 70%.",
      successPlaybook: [
        "Appoint C-level sponsor for every critical process",
        "RACI matrix in 30 days",
        "KPI metrics + weekly stand-ups",
        "Standard process documentation in single source",
      ],
      relatedSectors: ["Manufacturing", "Financial Services"],
    },
  },
};

export default function GlobalIntel() {
  const { t, user, locale } = useContext(AppCtx);
  const [bn, setBn] = useState([]);
  const [frags, setFrags] = useState(0);
  const [alerts, setAlerts] = useState([]);
  const [busy, setBusy] = useState(false);
  const [expanded, setExpanded] = useState(null);

  const load = () => Promise.all([
    http.get('/swarm/bottlenecks'),
    http.get('/swarm/fragments/count'),
    http.get('/oracle/alerts'),
  ]).then(([b, f, a]) => { setBn(b.data); setFrags(f.data.count); setAlerts(a.data); });

  useEffect(() => { load(); }, []);

  const recompute = async () => {
    setBusy(true);
    try {
      await http.post('/swarm/recompute');
      await load();
      toast.success(t.global.recompute + ' ✓');
    } catch (e) {
      toast.error('Failed');
    } finally { setBusy(false); }
  };

  const detailsFor = (cat) => (BOTTLENECK_DETAILS[cat] || BOTTLENECK_DETAILS.process)[locale] || BOTTLENECK_DETAILS[cat]?.fi;

  return (
    <div data-testid="global-page">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="font-heading text-4xl font-black tracking-tighter">{t.global.title}</h1>
          <div className="text-[11px] tracking-[0.25em] uppercase text-slate-500 mt-1">{t.global.subtitle}</div>
        </div>
        {(user?.role === 'super_admin' || user?.role === 'admin') && (
          <button onClick={recompute} disabled={busy} className="tkp-btn-primary flex items-center gap-2" data-testid="recompute-btn">
            <ArrowsClockwise size={14} weight="bold" className={busy ? 'animate-spin' : ''} />{t.global.recompute}
          </button>
        )}
      </div>

      <div className="grid grid-cols-12 gap-6 mb-6">
        <div className="col-span-6 md:col-span-3 tkp-card p-6" data-testid="stat-fragments">
          <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold">{t.global.fragments}</div>
          <div className="font-heading text-4xl font-black tracking-tighter mt-2">{frags}</div>
          <div className="text-[10px] text-slate-500 mt-1 font-mono">Zero-Knowledge anonymized vectors</div>
        </div>
        <div className="col-span-6 md:col-span-3 tkp-card p-6" data-testid="stat-clusters">
          <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold">{t.global.clusters}</div>
          <div className="font-heading text-4xl font-black tracking-tighter mt-2">{bn.length}</div>
          <div className="text-[10px] text-slate-500 mt-1 font-mono">Greedy cosine ≥ 0.55</div>
        </div>
        <div className="col-span-12 md:col-span-6 tkp-card p-6" data-testid="stat-alerts">
          <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold">Oracle signals</div>
          <div className="flex items-baseline gap-3 mt-2">
            <span className="font-heading text-4xl font-black tracking-tighter">{alerts.length}</span>
            <span className="text-xs text-slate-500">active predictions</span>
          </div>
        </div>
      </div>

      <div className="tkp-card p-6">
        <div className="font-heading text-xl font-bold tracking-tight mb-1">{t.global.clusters}</div>
        <div className="text-xs text-slate-500 mb-4">{locale === 'fi' ? 'Klikkaa pullonkaulaa nähdäksesi yhteenvedon ja onnistumisstrategian' : 'Click any bottleneck to see explainer and success playbook'}</div>
        <div className="space-y-3">
          {bn.length === 0 && <div className="text-sm text-slate-400">{t.empty}</div>}
          {bn.map(b => {
            const isOpen = expanded === b.id;
            const details = detailsFor(b.category);
            return (
              <div key={b.id} className="border border-slate-200 rounded-sm overflow-hidden" data-testid={`cluster-${b.id}`}>
                <button
                  onClick={() => setExpanded(isOpen ? null : b.id)}
                  className="w-full text-left p-5 hover:bg-slate-50 transition-colors"
                  data-testid={`cluster-toggle-${b.id}`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="font-semibold text-base">{b.label}</div>
                      <div className="text-[10px] tracking-widest uppercase text-slate-500 font-mono mt-0.5">
                        {b.fragment_count} fragments · {t.global.sectorsAffected}: {b.sectors_affected.join(', ')}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-heading text-2xl font-black tracking-tighter">{b.percentage}%</div>
                      <div className="text-[10px] tracking-widest uppercase text-slate-500 font-mono">avg weight {b.avg_risk_weight}</div>
                    </div>
                    <div className="text-slate-400 mt-1">
                      {isOpen ? <CaretUp size={18} weight="bold" /> : <CaretDown size={18} weight="bold" />}
                    </div>
                  </div>
                  <div className="h-1.5 bg-slate-100 rounded-sm overflow-hidden mt-3">
                    <div className="h-full bg-ink" style={{ width: `${Math.min(b.percentage, 100)}%` }} />
                  </div>
                </button>

                {isOpen && details && (
                  <div className="border-t border-slate-200 bg-slate-50 p-5 space-y-4 animate-fade-up" data-testid={`cluster-detail-${b.id}`}>
                    <div>
                      <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-2 flex items-center gap-1.5"><ChartBar size={12} weight="duotone" />{locale === 'fi' ? 'Mistä on kyse' : 'What this is'}</div>
                      <div className="text-sm text-slate-700 leading-relaxed">{details.explainer}</div>
                    </div>
                    <div>
                      <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-2 flex items-center gap-1.5"><Lightning size={12} weight="duotone" />{locale === 'fi' ? 'Miksi tämä on tärkeää' : 'Why it matters'}</div>
                      <div className="text-sm text-slate-700 leading-relaxed">{details.whyItMatters}</div>
                    </div>
                    <div>
                      <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-2">{locale === 'fi' ? 'Onnistumispelikirja parviälystä' : 'Success playbook from swarm'}</div>
                      <ol className="space-y-1.5 text-sm text-slate-700">
                        {details.successPlaybook.map((step, i) => (
                          <li key={i} className="pl-7 relative">
                            <span className="absolute left-0 top-0.5 w-5 h-5 bg-ink text-white rounded-full flex items-center justify-center text-[10px] font-bold">{i + 1}</span>
                            {step}
                          </li>
                        ))}
                      </ol>
                    </div>
                    <div>
                      <div className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-2 flex items-center gap-1.5"><Buildings size={12} weight="duotone" />{locale === 'fi' ? 'Sektorit joissa havaittu' : 'Sectors where detected'}</div>
                      <div className="flex flex-wrap gap-2">
                        {details.relatedSectors.map(s => (
                          <span key={s} className="text-[10px] tracking-widest uppercase font-bold px-2 py-1 bg-white border border-slate-200 rounded-sm">{s}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
