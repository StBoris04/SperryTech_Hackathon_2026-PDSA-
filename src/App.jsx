import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const fallbackProjects = [
  { id:"DESC_2", utility:"Dominion Energy SC", short:"DESC", name:"Hooks – Thurmond 115kV Tie: Rebuild", location:"Hooks – Thurmond, SC", type:"Transmission line", milestone:"In service Dec 2024", window:"Construction window unavailable", quality:"Approximate", review:"Validated", description:"Rebuild a section of the 115 kV line between Hooks and Thurmond.", source:"Dominion project listing · PDF page 3", x:40, y:32 },
  { id:"DESC_3", utility:"Dominion Energy SC", short:"DESC", name:"Jasper – Okatie 230kV #2: Construct", location:"Jasper – Yemassee, SC", type:"Transmission line", milestone:"In service Dec 2024", window:"Construction window unavailable", quality:"Approximate", review:"Validated", description:"Expand the Okatie transmission area and add a 230–115 kV connection.", source:"Dominion project listing · PDF page 3", x:68, y:70 },
  { id:"GPC_1", utility:"Georgia Power", short:"GPC", name:"Evans Primary – Thurmond Dam #5 115kV Rebuild", location:"Evans – Thurmond Dam, GA", type:"Transmission line", milestone:"Start Jun 2029", window:"End date unavailable", quality:"Unknown", review:"Needs review", description:"Planning record for a 115 kV rebuild. Location and schedule require source review.", source:"Georgia Power public disclosure · review pending", x:31, y:39 },
];

const API_BASE=(import.meta.env.VITE_API_URL||"/api").replace(/\/$/,"");
const pairKey=(a,b)=>[a,b].sort().join("::");
const fetchJson=async(path)=>{const response=await fetch(`${API_BASE}${path}`);if(!response.ok)throw new Error(`${path} returned ${response.status}`);return response.json()};

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

function ProjectMap({projects,terminalRoutes,selectedId,compareIds,layer,onSelect}){
  const containerRef=useRef(null);
  const mapRef=useRef(null);
  const projectLayerRef=useRef(null);

  useEffect(()=>{
    if(!containerRef.current||mapRef.current)return;
    const map=L.map(containerRef.current,{zoomControl:false,minZoom:5,maxZoom:17}).setView([32.65,-81.35],7);
    L.control.zoom({position:"topright"}).addTo(map);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{
      attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom:19,
    }).addTo(map);
    projectLayerRef.current=L.layerGroup().addTo(map);
    mapRef.current=map;
    window.setTimeout(()=>map.invalidateSize(),0);
    return()=>{map.remove();mapRef.current=null;projectLayerRef.current=null};
  },[]);

  useEffect(()=>{
    const map=mapRef.current;
    const group=projectLayerRef.current;
    if(!map||!group)return;
    group.clearLayers();
    const located=projects.filter(project=>project.latitude!=null&&project.longitude!=null);
    const visibleIds=layer==="Opportunities"&&compareIds.length===2?new Set(compareIds):null;
    terminalRoutes.filter(route=>route.terminals.length===2).forEach(route=>{
      const project=projects.find(item=>item.id===route.project_id);
      if(!project||(visibleIds&&!visibleIds.has(project.id)))return;
      const active=selectedId===project.id||compareIds.includes(project.id);
      const color=tone(project.utility)==="green"?"#24714a":"#dd8735";
      const points=route.terminals.map(terminal=>[terminal.latitude,terminal.longitude]);
      L.polyline(points,{color,weight:active?6:3,opacity:active?.95:.45}).bindTooltip(`${route.terminals[0].name} ↔ ${route.terminals[1].name}`).addTo(group);
      route.terminals.forEach(terminal=>L.circleMarker([terminal.latitude,terminal.longitude],{radius:active?6:4,color:"#fff",weight:2,fillColor:color,fillOpacity:1}).bindTooltip(terminal.name).addTo(group));
    });
    located.forEach(project=>{
      if(visibleIds&&!visibleIds.has(project.id))return;
      const color=tone(project.utility)==="green"?"#24714a":"#dd8735";
      const active=selectedId===project.id||compareIds.includes(project.id);
      const icon=L.divIcon({
        className:"gridlock-marker-shell",
        html:`<span class="gridlock-marker ${active?"active":""}" style="--marker-color:${color}"><b>${project.short}</b><small>${project.id}</small></span>`,
        iconSize:[48,48],iconAnchor:[24,24],popupAnchor:[0,-22],
      });
      const marker=L.marker([project.latitude,project.longitude],{icon}).addTo(group);
      marker.bindPopup(`<strong>${project.name}</strong><br><span>${project.id} · ${project.utility}</span><br><small>${project.quality} location</small>`);
      marker.on("click",()=>onSelect(project.id));
    });

    const compared=compareIds.map(id=>located.find(project=>project.id===id)).filter(Boolean);
    if(compared.length===2){
      const points=compared.map(project=>[project.latitude,project.longitude]);
      const distance=distanceMiles(compared[0],compared[1]);
      L.polyline(points,{color:"#173923",weight:4,dashArray:"9 7",opacity:.9}).bindTooltip(`${distance.toFixed(2)} mi`,{permanent:true,direction:"center",className:"distance-tooltip"}).addTo(group);
      map.fitBounds(L.latLngBounds(points),{padding:[70,70],maxZoom:11});
    }else{
      const selected=located.find(project=>project.id===selectedId);
      if(selected)map.flyTo([selected.latitude,selected.longitude],Math.max(map.getZoom(),9),{duration:.55});
      else if(located.length)map.fitBounds(L.latLngBounds(located.map(project=>[project.latitude,project.longitude])),{padding:[35,35],maxZoom:8});
    }
  },[projects,terminalRoutes,selectedId,compareIds,layer,onSelect]);

  return <div ref={containerRef} className="leaflet-map" aria-label="Interactive map of utility projects"/>;
}

export default function App(){
  const [projects,setProjects]=useState(fallbackProjects);
  const [apiOpportunities,setApiOpportunities]=useState([]);
  const [terminalRoutes,setTerminalRoutes]=useState([]);
  const [recommendationData,setRecommendationData]=useState({status:"loading",summary:"Loading recommendations…",recommendations:[]});
  const [dataState,setDataState]=useState("loading");
  const [selectedId,setSelectedId]=useState("DESC_2");
  const [query,setQuery]=useState("");
  const [utility,setUtility]=useState("All");
  const [layer,setLayer]=useState("Projects");
  const [panel,setPanel]=useState("project");
  const [compareIds,setCompareIds]=useState([]);
  const [activeSection,setActiveSection]=useState("top");
  const [page,setPage]=useState("workspace");
  const [toast,setToast]=useState("");
  useEffect(()=>{fetch("/terminal_routes.json").then(response=>response.json()).then(payload=>setTerminalRoutes(payload.routes??[])).catch(()=>setTerminalRoutes([]))},[]);
  useEffect(()=>{
    Promise.all([fetchJson("/projects"),fetchJson("/opportunities"),fetchJson("/recommendations")])
      .then(([projectPayload,opportunityPayload,recommendationPayload])=>{
        setProjects(projectPayload.projects.map(normalizeProject));
        setApiOpportunities(opportunityPayload.opportunities);
        setRecommendationData(recommendationPayload);
        setDataState("api");
      })
      .catch(()=>Promise.all([fetch("/master_projects.json").then(response=>{if(!response.ok)throw new Error("Dataset unavailable");return response.json()}),fetch("/recommendations.json").then(response=>{if(!response.ok)throw new Error("Recommendation snapshot unavailable");return response.json()})])
        .then(([payload,recommendations])=>{setProjects(payload.projects.map(normalizeProject));setApiOpportunities([]);setRecommendationData(recommendations);setDataState("local")})
        .catch(()=>{setDataState("fallback");setRecommendationData({status:"offline",summary:"Recommendation API unavailable.",recommendations:[]})}));
  },[]);
  useEffect(()=>{if(page!=="workspace")return;const updateSection=()=>{const sections=["directory","recommendations","top"];const current=sections.find(id=>{const element=document.getElementById(id);return element&&element.getBoundingClientRect().top<=150});setActiveSection(current??"top")};window.addEventListener("scroll",updateSection,{passive:true});updateSection();return()=>window.removeEventListener("scroll",updateSection)},[page]);
  useEffect(()=>{if(compareIds.length===2){setPanel("compare");window.setTimeout(()=>navigateTo("top"),0)}},[compareIds]);
  const selected=projects.find(p=>p.id===selectedId)??projects[0];
  const selectedRoute=terminalRoutes.find(route=>route.project_id===selected?.id);
  const compared=compareIds.map(id=>projects.find(p=>p.id===id)).filter(Boolean);
  const comparedDistance=compared.length===2?distanceMiles(compared[0],compared[1]):null;
  const mappedComparison=compared.length===2&&compared.every(project=>project.latitude!=null&&project.longitude!=null)?compared:null;
  const comparedKey=compared.length===2?pairKey(compared[0].id,compared[1].id):null;
  const isCrossUtility=compared.length===2&&compared[0].short!==compared[1].short;
  const isEligible=isCrossUtility&&comparedDistance!=null&&comparedDistance<=25;
  const activeRecommendation=recommendationData.recommendations.find(item=>pairKey(item.project_id_a,item.project_id_b)===comparedKey);
  const backendOpportunity=apiOpportunities.find(item=>pairKey(item.project_id_a,item.project_id_b)===comparedKey);
  const recommendationView=compared.length<2?{
    badge:"Evidence incomplete",title:"Select a cross-utility pair",description:"Build a comparison from the project directory to see evidence-backed guidance here.",next:"Select one Dominion and one Georgia Power project",detail:"Recommendations appear only after two projects have been selected.",
  }:!isCrossUtility?{
    badge:"Not eligible",title:"Same-utility pair",description:"Coordination recommendations compare projects from different utilities. Select one Dominion project and one Georgia Power project.",next:"Replace one selected project",detail:"This comparison remains visible, but it is never sent to the recommendation agent.",
  }:comparedDistance==null?{
    badge:"Not eligible",title:"Location evidence required",description:"This pair cannot be ranked because at least one project has no validated coordinates.",next:"Validate both project locations",detail:"Missing coordinates remain unknown; GridLock does not invent a map position.",
  }:comparedDistance>25?{
    badge:"Not eligible",title:"Outside the review radius",description:`These representative points are ${comparedDistance.toFixed(2)} miles apart, outside the inclusive 25-mile threshold.`,next:"Select another cross-utility pair",detail:"The comparison is valid to inspect, but it is not a coordination recommendation.",
  }:activeRecommendation?{
    badge:activeRecommendation.category,title:activeRecommendation.category,description:activeRecommendation.why_flagged,next:activeRecommendation.next_step,detail:activeRecommendation.uncertainties.join(" "),
  }:dataState==="api"?{
    badge:"Not ranked",title:"Not returned by the backend",description:"This pair was not included in the authoritative opportunity results.",next:"Review validation and evidence",detail:"Only deterministic backend opportunities may receive an agent recommendation.",
  }:{
    badge:"API unavailable",title:"Recommendation unavailable",description:recommendationData.summary,next:"Reconnect the recommendation API",detail:"The local dataset remains available for project browsing and comparison.",
  };
  const filtered=useMemo(()=>projects.filter(p=>(utility==="All"||p.short===utility)&&`${p.id} ${p.name} ${p.location}`.toLowerCase().includes(query.toLowerCase())),[projects,query,utility]);
  const chooseProject=useCallback((id)=>{setSelectedId(id);setPanel("project")},[]);
  const toggleCompare=(id)=>{setCompareIds(current=>current.includes(id)?current.filter(item=>item!==id):current.length>=2?[current[1],id]:[...current,id])};
  const chooseRecommendation=(item)=>{setCompareIds([item.project_id_a,item.project_id_b]);setSelectedId(item.project_id_a);setPanel("opportunity");window.setTimeout(()=>navigateTo("recommendations"),0)};
  const navigateTo=(id)=>{setActiveSection(id);document.getElementById(id)?.scrollIntoView({behavior:"smooth",block:"start"})};
  const openWorkspace=(id="top")=>{setPage("workspace");setActiveSection(id);window.setTimeout(()=>document.getElementById(id)?.scrollIntoView({behavior:"smooth",block:"start"}),0)};
  const openAbout=()=>{setPage("about");setActiveSection("about");window.scrollTo({top:0,behavior:"smooth"})};
  const exportReview=()=>{
    if(!activeRecommendation){setToast("Select an eligible recommended pair");setTimeout(()=>setToast(""),1800);return}
    const text=["GRIDLOCK COORDINATION REVIEW","Deterministic backend result explained by the recommendation agent","",`${activeRecommendation.project_id_a} ↔ ${activeRecommendation.project_id_b}`,`Distance: ${activeRecommendation.distance_miles} mi`,`Timeline: ${activeRecommendation.timeline_status}`,`Category: ${activeRecommendation.category}`,"",activeRecommendation.why_flagged,"","NEXT STEP",activeRecommendation.next_step,"","UNCERTAINTIES",...activeRecommendation.uncertainties.map(item=>`- ${item}`)].join("\n");
    const url=URL.createObjectURL(new Blob([text],{type:"text/plain"}));const a=document.createElement("a");a.href=url;a.download=`gridlock-${activeRecommendation.project_id_a}-${activeRecommendation.project_id_b}.txt`;a.click();URL.revokeObjectURL(url);setToast("Review exported");setTimeout(()=>setToast(""),1800)
  };
  return <div className="shell">
    <header className="header">
      <button className="logo logo-button" onClick={()=>openWorkspace("top")}><span className="logo-grid"><i/><i/><i/><i/></span><b>GridLock</b><em>by Sperry Tech</em></button>
      <nav className="main-nav"><button className={page==="workspace"&&activeSection==="top"?"active":""} onClick={()=>openWorkspace("top")}>Explore</button><button className={page==="workspace"&&activeSection==="directory"?"active":""} onClick={()=>openWorkspace("directory")}>Projects</button><button className={page==="workspace"&&activeSection==="recommendations"?"active":""} onClick={()=>openWorkspace("recommendations")}>Recommendations</button><button className={page==="about"?"active":""} onClick={openAbout}>About</button></nav>
      <div className="header-actions"><span className="api-state"><i/> {dataState==="api"?"Live API":"Local preview"}</span><button onClick={exportReview} className="outline-button">Export review ↗</button></div>
    </header>

    {page==="workspace"?<main id="top">
      <section className="intro">
        <div><p className="kicker"><span>01</span> Cross-utility intelligence</p><h1>See where the grid<br/><em>can work together.</em></h1></div>
        <div className="intro-copy"><p>Find nearby transmission projects, understand timing, and turn public planning data into an evidence-backed coordination review.</p><div className="quick-stats"><span><b>{projects.length}</b> projects</span><span><b>{new Set(projects.map(project=>project.utility)).size}</b> utilities</span><span><b>25 mi</b> radius</span></div></div>
      </section>

      <section className="explorer">
          <div className="map-stage">
          <ProjectMap projects={projects} terminalRoutes={terminalRoutes} selectedId={selectedId} compareIds={compareIds} layer={layer} onSelect={chooseProject}/>
          {!mappedComparison&&compareIds.length===2&&<div className="map-data-warning">A map line requires coordinates for both selected projects.</div>}
          <div className="layer-switch">{["Projects","Opportunities"].map(x=><button onClick={()=>setLayer(x)} className={layer===x?"active":""} key={x}>{x}</button>)}</div>
          <div className="map-caption"><span><i className="dot green"/> Dominion</span><span><i className="dot orange"/> Georgia Power</span><b>{selectedRoute?.terminals.length===2?`${selectedRoute.terminals[0].name} ↔ ${selectedRoute.terminals[1].name} · verified terminals`:`${projects.filter(p=>p.x!=null).length} located · ${projects.length-projects.filter(p=>p.x!=null).length} location unknown`}</b></div>
        </div>

        <aside className="control-panel">
          <div className="search"><span>⌕</span><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Find a project or place"/><kbd>⌘ K</kbd></div>
          <div className="utility-tabs">{["All","DESC","GPC"].map(x=><button key={x} onClick={()=>setUtility(x)} className={utility===x?"active":""}>{x}</button>)}</div>
          <div className="project-jump"><div><small>Project directory</small><b>{filtered.length} matching records</b><span>{dataState==="api"?"Live API connected":dataState==="local"?"Local dataset · API offline":"Loading data"}</span></div><button onClick={()=>navigateTo("directory")}>Open list ↓</button></div>
          {compareIds.length>0&&<div className="compare-tray"><div><small>Compare queue · {compareIds.length}/2</small><span>{compared.map(p=><button key={p.id} onClick={()=>toggleCompare(p.id)}>{p.id} ×</button>)}</span></div><button disabled={compareIds.length<2} onClick={()=>setPanel("compare")}>Compare now →</button></div>}
          <div className="panel-divider"/>
          {panel==="project"?<div className="selection-detail"><div className="detail-label"><span>Selected project</span><em className={selected.review==="Validated"?"valid":"review"}>{selected.review}</em></div><h2>{selected.name}</h2><p>{selected.description}</p><div className="detail-facts"><span><small>Milestone</small><b>{selected.milestone}</b></span><span><small>Location</small><b>{selected.quality}</b></span></div><button onClick={()=>toggleCompare(selected.id)} className="cta">{compareIds.includes(selected.id)?"Remove from comparison":"Add to comparison"} <span>＋</span></button></div>:panel==="compare"?<div className="selection-detail comparison-detail"><div className="detail-label"><span>Project comparison</span><em>{compared.length===2?"Ready":"Select two"}</em></div>{compared.length<2?<div className="compare-empty"><b>Choose one more project</b><p>Use the ＋ buttons above to build a side-by-side comparison.</p></div>:<><div className="compare-head"><div><small>{compared[0].short}</small><b>{compared[0].id}</b></div><span>↔</span><div><small>{compared[1].short}</small><b>{compared[1].id}</b></div></div><div className="comparison-metric"><small>Point-to-point distance</small><b>{comparedDistance==null?"Unavailable":`${comparedDistance.toFixed(2)} mi`}</b><em>{!isCrossUtility?"Same utility · not eligible":comparedDistance==null?"Coordinates required":comparedDistance<=25?"Within 25-mile review radius":"Outside review radius"}</em></div><div className="compare-table"><span><small>Utility</small><b>{compared[0].short}</b><b>{compared[1].short}</b></span><span><small>Schedule</small><b>{compared[0].milestone}</b><b>{compared[1].milestone}</b></span><span><small>Location</small><b>{compared[0].quality}</b><b>{compared[1].quality}</b></span><span><small>Review</small><b>{compared[0].review}</b><b>{compared[1].review}</b></span></div><button onClick={()=>setPanel("opportunity")} className="cta lime">{isEligible?"Review recommendation":"Review eligibility"} <span>→</span></button></>}</div>:<div className="selection-detail opportunity-detail"><div className="detail-label"><span>Decision path</span><em>{recommendationView.badge}</em></div><p className="pair">{compared.map(project=>project.id).join(" ↔ ")}</p><h2>{recommendationView.title}</h2><p>{recommendationView.description}</p><div className="op-facts"><span><small>Distance</small><b>{comparedDistance==null?"Unavailable":`${comparedDistance.toFixed(2)} mi`}</b></span><span><small>Timeline</small><b>{activeRecommendation?.timeline_status??backendOpportunity?.timeline_status??"Not ranked"}</b></span></div><button disabled={!activeRecommendation} onClick={exportReview} className="cta lime">{activeRecommendation?"Export agent review":"No review to export"} <span>→</span></button></div>}
        </aside>
      </section>

      <section className="recommendation-workspace" id="recommendations">
        <div className="recommendation-heading"><div><p className="kicker"><span>02</span> Recommendations</p><h2>Know what deserves<br/><em>attention next.</em></h2></div><p>GridLock turns verified proximity and schedule evidence into a focused coordination review. Unknown data remains visible and is never treated as a match.</p></div>
        <div className="recommendation-list">
          {recommendationData.recommendations.length?recommendationData.recommendations.map((item,index)=><button key={pairKey(item.project_id_a,item.project_id_b)} onClick={()=>chooseRecommendation(item)}><span>{String(index+1).padStart(2,"0")}</span><div><small>{item.project_id_a} ↔ {item.project_id_b}</small><b>{item.category}</b><p>{item.why_flagged}</p></div><em>{Number(item.distance_miles).toFixed(2)} mi →</em></button>):<div className="recommendation-empty"><b>{dataState==="api"?"No ranked opportunities returned":"Recommendation API is not connected"}</b><p>{recommendationData.summary}</p></div>}
        </div>
        {compared.length===2&&<div className="selected-projects"><div className="selected-projects-title"><span>Selected project information</span><b>{compared[0].id} ↔ {compared[1].id}</b></div><div className="selected-projects-grid">{compared.map(project=><article key={project.id}><div><span className={`dot ${tone(project.utility)}`}/><small>{project.utility}</small><em>{project.review}</em></div><h3>{project.name}</h3><p>{project.description}</p><dl><div><dt>Project ID</dt><dd>{project.id}</dd></div><div><dt>Type</dt><dd>{project.type}</dd></div><div><dt>Schedule</dt><dd>{project.milestone}</dd></div><div><dt>Location</dt><dd>{project.location}</dd></div><div><dt>Location quality</dt><dd>{project.quality}</dd></div><div><dt>Source evidence</dt><dd>{project.source}</dd></div></dl></article>)}</div></div>}
        <div className="recommendation-board">
          <div className="recommendation-status"><span className="status-orbit"><i/><i/><i/></span><small>Current review</small><h3>{compared.length===2?`${compared[0].id} ↔ ${compared[1].id}`:"Select two projects to begin"}</h3><p>{recommendationView.description}</p><button onClick={()=>openWorkspace(compared.length===2?"top":"directory")}>{compared.length===2?"Review comparison":"Choose projects"} <span>→</span></button></div>
          <div className="recommendation-evidence">
            <div className="evidence-title"><span>Decision evidence</span><em>{recommendationView.badge}</em></div>
            <div className="evidence-metrics"><span><small>Distance</small><b>{comparedDistance==null?"—":`${comparedDistance.toFixed(2)} mi`}</b></span><span><small>Review radius</small><b>25 mi</b></span><span><small>Projects selected</small><b>{compared.length}/2</b></span></div>
            <div className="evidence-next"><small>{activeRecommendation?"Agent-recommended next step":"Next step"}</small><b>{recommendationView.next}</b><p>{recommendationView.detail}</p></div>
          </div>
        </div>
        <div className="recommendation-principle"><span>Verified inputs</span><i/> <span>Deterministic distance</span><i/> <span>Transparent uncertainty</span><i/> <b>No manufactured matches</b></div>
      </section>

      <section className="directory" id="directory">
        <div className="section-head compact"><div><p className="kicker"><span>03</span> Project directory</p><h2>Every project.<br/><em>One separate list.</em></h2></div><p>This list has its own navigation. Search, filter, select, or add any two records to the comparison queue.</p></div>
        <div className="directory-tools"><div className="directory-search"><span>⌕</span><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search name, ID or location"/></div><div className="directory-filter">{["All","DESC","GPC"].map(x=><button key={x} onClick={()=>setUtility(x)} className={utility===x?"active":""}>{x}</button>)}</div><span>{filtered.length} results</span></div>
        <div className="directory-list"><div className="directory-header"><span>Project</span><span>Utility</span><span>Schedule</span><span>Evidence</span><span>Compare</span></div><div className="directory-scroll">{filtered.map(p=><div className={`directory-row ${selectedId===p.id?"active":""}`} key={p.id}><button onClick={()=>{chooseProject(p.id);navigateTo("top")}}><span><i className={`dot ${tone(p.utility)}`}/><b>{p.name}</b><small>{p.id} · {p.location}</small></span><span>{p.utility}</span><span>{p.milestone}<small>{p.window}</small></span><span><em>{p.review}</em> ↗</span></button><div role="button" tabIndex="0" onClick={()=>toggleCompare(p.id)} onKeyDown={event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();toggleCompare(p.id)}}} className={`directory-compare ${compareIds.includes(p.id)?"added":""}`}>{compareIds.includes(p.id)?"✓ Added":"＋ Add"}</div></div>)}{!filtered.length&&<p className="empty directory-empty">No projects match the current search.</p>}</div></div>
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
