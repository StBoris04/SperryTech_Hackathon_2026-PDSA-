import { useEffect, useMemo, useState } from "react";

const fallbackProjects = [
  { id:"DESC_2", utility:"Dominion Energy SC", short:"DESC", name:"Hooks – Thurmond 115kV Tie: Rebuild", location:"Hooks – Thurmond, SC", type:"Transmission line", milestone:"In service Dec 2024", window:"Construction window unavailable", quality:"Approximate", review:"Validated", description:"Rebuild a section of the 115 kV line between Hooks and Thurmond.", source:"Dominion project listing · PDF page 3", x:40, y:32 },
  { id:"DESC_3", utility:"Dominion Energy SC", short:"DESC", name:"Jasper – Okatie 230kV #2: Construct", location:"Jasper – Yemassee, SC", type:"Transmission line", milestone:"In service Dec 2024", window:"Construction window unavailable", quality:"Approximate", review:"Validated", description:"Expand the Okatie transmission area and add a 230–115 kV connection.", source:"Dominion project listing · PDF page 3", x:68, y:70 },
  { id:"GPC_1", utility:"Georgia Power", short:"GPC", name:"Evans Primary – Thurmond Dam #5 115kV Rebuild", location:"Evans – Thurmond Dam, GA", type:"Transmission line", milestone:"Start Jun 2029", window:"End date unavailable", quality:"Unknown", review:"Needs review", description:"Planning record for a 115 kV rebuild. Location and schedule require source review.", source:"Georgia Power public disclosure · review pending", x:31, y:39 },
];

const opportunities = [
  { id:"opp-1", a:"DESC_2", b:"GPC_1", distance:"4.1 mi", timeline:"Unknown timing", label:"Thurmond corridor review", status:"Provisional", reason:"The representative points suggest a nearby cross-utility corridor worth validating.", actions:["Confirm both project locations", "Verify construction windows", "Request a joint planning review"] },
  { id:"opp-2", a:"DESC_3", b:"GPC_1", distance:"—", timeline:"Missing location", label:"Evidence required", status:"Not ranked", reason:"Keep the records visible, but do not calculate a match until both locations are validated.", actions:["Open the source record", "Validate coordinates", "Run the distance calculation again"] },
];

const tone = (utility) => utility.startsWith("Dominion") ? "green" : "orange";

const positionProject = (project) => {
  if (project.latitude == null || project.longitude == null) return { x:null, y:null };
  const x=Math.max(8,Math.min(92,8+((project.longitude+82.5)/3.1)*84));
  const y=Math.max(8,Math.min(92,8+((34.5-project.latitude)/2.7)*84));
  return {x,y};
};

const normalizeProject = (project) => {
  const isDominion=project.utility_id==="dominion_sc";
  const position=positionProject(project);
  const milestone=project.in_service_date?`In service ${project.in_service_date}`:project.construction_start?`Starts ${project.construction_start}`:"Schedule unknown";
  const window=project.construction_start&&project.construction_end?`${project.construction_start} – ${project.construction_end}`:project.construction_start?"Construction end unavailable":"Construction window unavailable";
  return {id:project.project_id,utility:isDominion?"Dominion Energy SC":"Georgia Power",short:isDominion?"DESC":"GPC",name:project.project_name,location:project.location_text?`${project.location_text}${project.state?`, ${project.state}`:""}`:"Location not yet validated",type:project.project_type?.replaceAll("_"," ")??"Unknown",milestone,window,quality:project.location_quality??"Unknown",review:project.review_status==="validated"?"Validated":"Needs review",description:project.description??"No source-backed description available.",source:project.sources?.[0]?`${project.sources[0].reference} · ${project.sources[0].locator}`:"Source unavailable",latitude:project.latitude,longitude:project.longitude,...position};
};

const distanceMiles=(a,b)=>{if(a?.latitude==null||a?.longitude==null||b?.latitude==null||b?.longitude==null)return null;const rad=value=>value*Math.PI/180;const dLat=rad(b.latitude-a.latitude);const dLon=rad(b.longitude-a.longitude);const h=Math.sin(dLat/2)**2+Math.cos(rad(a.latitude))*Math.cos(rad(b.latitude))*Math.sin(dLon/2)**2;return 3958.8*2*Math.asin(Math.sqrt(h))};

export default function App(){
  const [projects,setProjects]=useState(fallbackProjects);
  const [dataState,setDataState]=useState("loading");
  const [selectedId,setSelectedId]=useState("DESC_2");
  const [selectedOpp,setSelectedOpp]=useState(opportunities[0]);
  const [query,setQuery]=useState("");
  const [utility,setUtility]=useState("All");
  const [layer,setLayer]=useState("Projects");
  const [panel,setPanel]=useState("project");
  const [compareIds,setCompareIds]=useState([]);
  const [activeSection,setActiveSection]=useState("top");
  const [page,setPage]=useState("workspace");
  const [toast,setToast]=useState("");
  useEffect(()=>{fetch("/master_projects.json").then(response=>{if(!response.ok)throw new Error("Dataset unavailable");return response.json()}).then(payload=>{setProjects(payload.projects.map(normalizeProject));setDataState("ready")}).catch(()=>setDataState("fallback"))},[]);
  useEffect(()=>{if(page!=="workspace")return;const updateSection=()=>{const sections=["directory","recommendations","top"];const current=sections.find(id=>{const element=document.getElementById(id);return element&&element.getBoundingClientRect().top<=150});setActiveSection(current??"top")};window.addEventListener("scroll",updateSection,{passive:true});updateSection();return()=>window.removeEventListener("scroll",updateSection)},[page]);
  const selected=projects.find(p=>p.id===selectedId)??projects[0];
  const compared=compareIds.map(id=>projects.find(p=>p.id===id)).filter(Boolean);
  const comparedDistance=compared.length===2?distanceMiles(compared[0],compared[1]):null;
  const mappedComparison=compared.length===2&&compared.every(project=>project.x!=null&&project.y!=null)?compared:null;
  const filtered=useMemo(()=>projects.filter(p=>(utility==="All"||p.short===utility)&&`${p.id} ${p.name} ${p.location}`.toLowerCase().includes(query.toLowerCase())),[query,utility]);
  const chooseProject=(id)=>{setSelectedId(id);setPanel("project")};
  const chooseOpp=(opp)=>{setSelectedOpp(opp);setSelectedId(opp.a);setPanel("opportunity")};
  const toggleCompare=(id)=>{setCompareIds(current=>{if(current.includes(id))return current.filter(item=>item!==id);const next=current.length>=2?[current[1],id]:[...current,id];if(next.length===2){setPanel("compare");window.setTimeout(()=>navigateTo("top"),0)}return next})};
  const navigateTo=(id)=>{setActiveSection(id);document.getElementById(id)?.scrollIntoView({behavior:"smooth",block:"start"})};
  const openWorkspace=(id="top")=>{setPage("workspace");setActiveSection(id);window.setTimeout(()=>document.getElementById(id)?.scrollIntoView({behavior:"smooth",block:"start"}),0)};
  const openAbout=()=>{setPage("about");setActiveSection("about");window.scrollTo({top:0,behavior:"smooth"})};
  const exportReview=()=>{
    const text=["GRIDLOCK COORDINATION REVIEW","Prototype — awaiting deterministic API results","",`${selectedOpp.a} ↔ ${selectedOpp.b}`,`Distance: ${selectedOpp.distance}`,`Timeline: ${selectedOpp.timeline}`,`Status: ${selectedOpp.status}`,"",selectedOpp.reason,"",...selectedOpp.actions.map(x=>`- ${x}`)].join("\n");
    const url=URL.createObjectURL(new Blob([text],{type:"text/plain"}));const a=document.createElement("a");a.href=url;a.download=`gridlock-${selectedOpp.a}-${selectedOpp.b}.txt`;a.click();URL.revokeObjectURL(url);setToast("Review exported");setTimeout(()=>setToast(""),1800)
  };
  return <div className="shell">
    <header className="header">
      <button className="logo logo-button" onClick={()=>openWorkspace("top")}><span className="logo-grid"><i/><i/><i/><i/></span><b>GridLock</b><em>by Sperry Tech</em></button>
      <nav className="main-nav"><button className={page==="workspace"&&activeSection==="top"?"active":""} onClick={()=>openWorkspace("top")}>Explore</button><button className={page==="workspace"&&activeSection==="directory"?"active":""} onClick={()=>openWorkspace("directory")}>Projects</button><button className={page==="workspace"&&activeSection==="recommendations"?"active":""} onClick={()=>openWorkspace("recommendations")}>Recommendations</button><button className={page==="about"?"active":""} onClick={openAbout}>About</button></nav>
      <div className="header-actions"><span className="api-state"><i/> API preview</span><button onClick={exportReview} className="outline-button">Export review ↗</button></div>
    </header>

    {page==="workspace"?<main id="top">
      <section className="intro">
        <div><p className="kicker"><span>01</span> Cross-utility intelligence</p><h1>See where the grid<br/><em>can work together.</em></h1></div>
        <div className="intro-copy"><p>Find nearby transmission projects, understand timing, and turn public planning data into an evidence-backed coordination review.</p><div className="quick-stats"><span><b>166</b> projects</span><span><b>2</b> utilities</span><span><b>25 mi</b> radius</span></div></div>
      </section>

      <section className="explorer">
          <div className="map-stage">
          <div className="map-noise"/><div className="contour c1"/><div className="contour c2"/><div className="contour c3"/><div className="route r1"/><div className="route r2"/><div className="water"/>
          <span className="map-place augusta">AUGUSTA</span><span className="map-place columbia">COLUMBIA</span><span className="map-place savannah">SAVANNAH</span><span className="map-place charleston">CHARLESTON</span><span className="map-state ga">GEORGIA</span><span className="map-state sc">SOUTH CAROLINA</span>
          {mappedComparison&&<svg className="connection active-connection" viewBox="0 0 100 100" preserveAspectRatio="none"><line x1={mappedComparison[0].x} y1={mappedComparison[0].y} x2={mappedComparison[1].x} y2={mappedComparison[1].y}/></svg>}
          {projects.filter(p=>p.x!=null&&p.y!=null).map(p=><button key={p.id} style={{left:`${p.x}%`,top:`${p.y}%`}} onClick={()=>chooseProject(p.id)} className={`project-marker ${tone(p.utility)} ${selectedId===p.id?"selected":""} ${compareIds.includes(p.id)?"comparing":""}`}><span>{p.short}</span><small>{p.id}</small></button>)}
          {mappedComparison&&<div className="distance-chip" style={{left:`${(mappedComparison[0].x+mappedComparison[1].x)/2}%`,top:`${(mappedComparison[0].y+mappedComparison[1].y)/2}%`}}>{comparedDistance?.toFixed(2)} mi <small>selected pair</small></div>}
          {!mappedComparison&&compareIds.length===2&&<div className="map-data-warning">A map line requires coordinates for both selected projects.</div>}
          <div className="map-toolbar"><button>＋</button><button>－</button><button>⌖</button></div>
          <div className="layer-switch">{["Projects","Opportunities"].map(x=><button onClick={()=>setLayer(x)} className={layer===x?"active":""} key={x}>{x}</button>)}</div>
          <div className="map-caption"><span><i className="dot green"/> Dominion</span><span><i className="dot orange"/> Georgia Power</span><b>{projects.filter(p=>p.x!=null).length} located · {projects.length-projects.filter(p=>p.x!=null).length} location unknown</b></div>
        </div>

        <aside className="control-panel">
          <div className="search"><span>⌕</span><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Find a project or place"/><kbd>⌘ K</kbd></div>
          <div className="utility-tabs">{["All","DESC","GPC"].map(x=><button key={x} onClick={()=>setUtility(x)} className={utility===x?"active":""}>{x}</button>)}</div>
          <div className="project-jump"><div><small>Project directory</small><b>{filtered.length} matching records</b><span>{dataState==="ready"?"Real dataset loaded":"Loading local preview"}</span></div><button onClick={()=>navigateTo("directory")}>Open list ↓</button></div>
          {compareIds.length>0&&<div className="compare-tray"><div><small>Compare queue · {compareIds.length}/2</small><span>{compared.map(p=><button key={p.id} onClick={()=>toggleCompare(p.id)}>{p.id} ×</button>)}</span></div><button disabled={compareIds.length<2} onClick={()=>setPanel("compare")}>Compare now →</button></div>}
          <div className="panel-divider"/>
          {panel==="project"?<div className="selection-detail"><div className="detail-label"><span>Selected project</span><em className={selected.review==="Validated"?"valid":"review"}>{selected.review}</em></div><h2>{selected.name}</h2><p>{selected.description}</p><div className="detail-facts"><span><small>Milestone</small><b>{selected.milestone}</b></span><span><small>Location</small><b>{selected.quality}</b></span></div><button onClick={()=>toggleCompare(selected.id)} className="cta">{compareIds.includes(selected.id)?"Remove from comparison":"Add to comparison"} <span>＋</span></button></div>:panel==="compare"?<div className="selection-detail comparison-detail"><div className="detail-label"><span>Project comparison</span><em>{compared.length===2?"Ready":"Select two"}</em></div>{compared.length<2?<div className="compare-empty"><b>Choose one more project</b><p>Use the ＋ buttons above to build a side-by-side comparison.</p></div>:<><div className="compare-head"><div><small>{compared[0].short}</small><b>{compared[0].id}</b></div><span>↔</span><div><small>{compared[1].short}</small><b>{compared[1].id}</b></div></div><div className="comparison-metric"><small>Point-to-point distance</small><b>{comparedDistance==null?"Unavailable":`${comparedDistance.toFixed(2)} mi`}</b><em>{comparedDistance!=null&&comparedDistance<=25?"Within 25-mile review radius":comparedDistance==null?"Coordinates required":"Outside review radius"}</em></div><div className="compare-table"><span><small>Utility</small><b>{compared[0].short}</b><b>{compared[1].short}</b></span><span><small>Schedule</small><b>{compared[0].milestone}</b><b>{compared[1].milestone}</b></span><span><small>Location</small><b>{compared[0].quality}</b><b>{compared[1].quality}</b></span><span><small>Review</small><b>{compared[0].review}</b><b>{compared[1].review}</b></span></div><button onClick={()=>setPanel("opportunity")} className="cta lime">Review coordination potential <span>→</span></button></>}</div>:<div className="selection-detail opportunity-detail"><div className="detail-label"><span>Decision path</span><em>{selectedOpp.status}</em></div><p className="pair">{selectedOpp.a}<i/> {selectedOpp.b}</p><h2>{selectedOpp.label}</h2><p>{selectedOpp.reason}</p><div className="op-facts"><span><small>Distance</small><b>{selectedOpp.distance}</b></span><span><small>Timeline</small><b>{selectedOpp.timeline}</b></span></div><button onClick={exportReview} className="cta lime">Open full review <span>→</span></button></div>}
        </aside>
      </section>

      <section className="recommendation-workspace" id="recommendations">
        <div className="recommendation-heading"><div><p className="kicker"><span>02</span> Recommendations</p><h2>Know what deserves<br/><em>attention next.</em></h2></div><p>GridLock turns verified proximity and schedule evidence into a focused coordination review. Unknown data remains visible and is never treated as a match.</p></div>
        <div className="recommendation-board">
          <div className="recommendation-status"><span className="status-orbit"><i/><i/><i/></span><small>Current review</small><h3>{compared.length===2?`${compared[0].id} ↔ ${compared[1].id}`:"Select two projects to begin"}</h3><p>{compared.length<2?"Build a comparison from the project directory to see evidence-backed guidance here.":comparedDistance==null?"This pair cannot be ranked yet because at least one location is missing.":comparedDistance<=25?"These projects fall within the 25-mile review radius and are ready for schedule review.":"These projects are outside the 25-mile coordination radius."}</p><button onClick={()=>openWorkspace(compared.length===2?"top":"directory")}>{compared.length===2?"Review comparison":"Choose projects"} <span>→</span></button></div>
          <div className="recommendation-evidence">
            <div className="evidence-title"><span>Decision evidence</span><em>{compared.length===2&&comparedDistance!=null?"Distance calculated":"Evidence incomplete"}</em></div>
            <div className="evidence-metrics"><span><small>Distance</small><b>{comparedDistance==null?"—":`${comparedDistance.toFixed(2)} mi`}</b></span><span><small>Review radius</small><b>25 mi</b></span><span><small>Projects selected</small><b>{compared.length}/2</b></span></div>
            <div className="evidence-next"><small>Recommended next step</small><b>{compared.length<2?"Select a cross-utility pair":comparedDistance==null?"Validate both project locations":comparedDistance<=25?"Review known construction timing":"Return to the project directory"}</b><p>{compared.length===2?"Open the comparison to inspect source-backed project fields and any remaining uncertainty.":"Recommendations appear only after a project pair has been selected."}</p></div>
          </div>
        </div>
        <div className="recommendation-principle"><span>Verified inputs</span><i/> <span>Deterministic distance</span><i/> <span>Transparent uncertainty</span><i/> <b>No manufactured matches</b></div>
      </section>

      <section className="directory" id="directory">
        <div className="section-head compact"><div><p className="kicker"><span>03</span> Project directory</p><h2>Every project.<br/><em>One separate list.</em></h2></div><p>This list has its own navigation. Search, filter, select, or add any two records to the comparison queue.</p></div>
        <div className="directory-tools"><div className="directory-search"><span>⌕</span><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search name, ID or location"/></div><div className="directory-filter">{["All","DESC","GPC"].map(x=><button key={x} onClick={()=>setUtility(x)} className={utility===x?"active":""}>{x}</button>)}</div><span>{filtered.length} results</span></div>
        <div className="directory-list"><div className="directory-header"><span>Project</span><span>Utility</span><span>Schedule</span><span>Evidence</span><span>Compare</span></div><div className="directory-scroll">{filtered.map(p=><div className={`directory-row ${selectedId===p.id?"active":""}`} key={p.id}><button onClick={()=>{chooseProject(p.id);navigateTo("top")}}><span><i className={`dot ${tone(p.utility)}`}/><b>{p.name}</b><small>{p.id} · {p.location}</small></span><span>{p.utility}</span><span>{p.milestone}<small>{p.window}</small></span><span><em>{p.review}</em> ↗</span></button><button onClick={()=>toggleCompare(p.id)} className={`directory-compare ${compareIds.includes(p.id)?"added":""}`}>{compareIds.includes(p.id)?"✓ Added":"＋ Add"}</button></div>)}{!filtered.length&&<p className="empty directory-empty">No projects match the current search.</p>}</div></div>
      </section>

    </main>:<main className="about-page" id="about">
      <div className="about-page-hero"><button onClick={()=>openWorkspace("top")}>← Back to workspace</button><p className="kicker"><span>01</span> About GridLock</p><h1>Coordination begins with<br/><em>a shared view.</em></h1><p>GridLock helps neighboring utilities discover where public transmission plans may deserve a closer, evidence-backed review.</p></div>
      <section className="method" id="method"><div><p className="kicker"><span>02</span> Method</p><h2>Built to show its work.</h2></div><div className="method-steps"><span><b>01</b> Compare different utilities</span><span><b>02</b> Filter to ≤25 miles</span><span><b>03</b> Evaluate known timing</span><span><b>04</b> Preserve uncertainty</span></div></section>

      <section className="about">
        <div className="about-intro">
          <div><p className="kicker"><span>03</span> The challenge</p><h2>Built for the <em>ShellHacks 2026</em><br/>Sperry Tech Challenge.</h2></div>
          <p>GridLock turns fragmented public transmission plans into a shared view where neighboring utilities can identify opportunities worth investigating.</p>
        </div>
        <div className="about-story">
          <article><span className="story-index">A</span><small>The problem</small><h3>Planning stops at the utility boundary.</h3><p>Neighboring utilities plan independently, making it difficult to notice nearby work, aligned schedules, or infrastructure that deserves a joint review.</p></article>
          <article className="solution"><span className="story-index">B</span><small>Our solution</small><h3>One evidence-backed coordination view.</h3><p>GridLock compares projects across utilities, applies the 25-mile rule, preserves timing uncertainty, and explains why each candidate was flagged.</p></article>
        </div>
        <div className="about-grid">
          <div className="about-block">
            <div className="about-block-title"><span>How it works</span><small>Four-step pipeline</small></div>
            <ol className="pipeline">
              <li><b>01</b><span><strong>Extract</strong><small>Parse public utility filings with Gemini.</small></span></li>
              <li><b>02</b><span><strong>Validate</strong><small>Keep source evidence, nulls, and location quality.</small></span></li>
              <li><b>03</b><span><strong>Compare</strong><small>Calculate cross-utility geodesic distance.</small></span></li>
              <li><b>04</b><span><strong>Explain</strong><small>Rank candidates and expose uncertainty.</small></span></li>
            </ol>
          </div>
          <div className="about-block sources-block">
            <div className="about-block-title"><span>Public data sources</span><small>No CEII</small></div>
            <ul>
              <li><i className="dot green"/><span><b>Dominion Energy South Carolina</b><small>2024–2028 projects of $2M and above</small></span></li>
              <li><i className="dot orange"/><span><b>Georgia Power</b><small>2025 IRP Volume 3 public disclosure</small></span></li>
              <li><i className="source-symbol">＋</i><span><b>Sperry challenge workbook</b><small>Project mapping and supplied reference data</small></span></li>
            </ul>
          </div>
        </div>
        <div className="team-head"><div><p className="kicker">The team</p><h2>Four disciplines.<br/><em>One working demo.</em></h2></div><p>Designed and built during ShellHacks by a team spanning data, infrastructure, backend, and product experience.</p></div>
        <div className="team-grid">
          {[['PE','Piero Espinoza','Data Science','Extract · normalize · validate'],['BM','Boris Steeven Mino','Data Engineering','Tiger Data · PostGIS · import'],['AP','Adrian Perez','Backend / API','FastAPI · analysis · endpoints'],['DR','Diego Rios','Frontend','Interface · map · experience']].map(([initials,name,role,focus],index)=><article key={name}><span className={`avatar avatar-${index+1}`}>{initials}</span><div><small>0{index+1}</small><h3>{name}</h3><b>{role}</b><p>{focus}</p></div></article>)}
        </div>
      </section>
    </main>}
    <footer><b>GRIDLOCK</b><span>Public sources only · Missing data remains unknown · No manufactured matches</span><em>ShellHacks 2026</em></footer>
    {toast&&<div className="toast">✓ {toast}</div>}
  </div>
}
