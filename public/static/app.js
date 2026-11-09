/* GeoDEM Explorer browser interface. The OpenTopography API key never enters this file. */
const $ = id => document.getElementById(id);
const state = {aoi:null, area:0, config:null, chosen:new Set(["COP30","AW3D30","SRTMGL1","NASADEM","COP90"]), timer:null};
const fmt = new Intl.NumberFormat("en-IN",{maximumFractionDigits:1});
const map = L.map("map",{zoomControl:false,worldCopyJump:true}).setView([22.5,80],5);
L.control.zoom({position:"bottomright"}).addTo(map);
L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",{maxZoom:19,attribution:"&copy; OpenStreetMap contributors &copy; CARTO"}).addTo(map);
const areaLayer = new L.FeatureGroup().addTo(map);
const drawing = new L.Control.Draw({draw:{polyline:false,polygon:{allowIntersection:false,showArea:true,shapeOptions:{color:"#a9dc64"}},rectangle:{shapeOptions:{color:"#a9dc64"}},circle:false,circlemarker:false,marker:false},edit:{featureGroup:areaLayer}});
map.addControl(drawing);
function toast(message) {const e=$("toast"); e.textContent=message; e.hidden=false; clearTimeout(window.toastTimeout); window.toastTimeout=setTimeout(()=>e.hidden=true,6500);}
function updateRun() {$("selectedCount").textContent=state.chosen.size; $("areaStat").textContent=state.aoi?fmt.format(state.area)+" km²":"—"; $("runBtn").disabled=true;}
function selectAOI(feature) {
  state.aoi=feature; state.area=Number(feature.area_km2||0);
  areaLayer.clearLayers(); const layer=L.geoJSON(feature,{style:{color:"#7eaf37",weight:3,fillColor:"#abdc63",fillOpacity:0.20}}).addTo(areaLayer);
  map.fitBounds(layer.getBounds(),{padding:[35,35],maxZoom:13});
  $("aoiInfo").classList.add("active"); $("aoiText").textContent="Area selected · "+fmt.format(state.area)+" km²";
  $("clearBtn").hidden=false; updateRun();
}
function clearArea(){state.aoi=null;state.area=0;areaLayer.clearLayers();$("aoiInfo").classList.remove("active");$("aoiText").textContent="No study area selected";$("clearBtn").hidden=true;updateRun();}
async function upload(file) {
  try {
    let feature;
    if (file.name.toLowerCase().endsWith(".zip")) {
      if (!window.shp) throw Error("Shapefile parser unavailable");
      const parsed=await window.shp(await file.arrayBuffer());
      feature=Array.isArray(parsed)?{type:"FeatureCollection",features:parsed.flatMap(x=>x.features||[])}:parsed;
    } else {
      feature=JSON.parse(await file.text());
    }
    const geo=(feature.type==="Feature"||feature.type==="FeatureCollection")?feature:{type:"Feature",properties:{},geometry:feature};
    const layer=L.geoJSON(geo);
    if(!layer.getLayers().length)throw Error("No geometry found");
    const merged=layer.toGeoJSON();
    const features=merged.type==="FeatureCollection"?merged.features:[merged];
    if(features.some(f=>!["Polygon","MultiPolygon"].includes(f.geometry?.type)))throw Error("Select a polygon boundary");
    const area=window.turf?window.turf.area(merged)/1000000:0;
    selectAOI({...merged,area_km2:area});
    toast("Study area loaded. DEM downloads require a separate processing server.");
  } catch(e){toast("Could not read boundary: "+e.message);}
}
$("aoiFile").addEventListener("change",e=>{if(e.target.files[0])upload(e.target.files[0]);});
for (const event of ["dragenter","dragover"]) $("dropzone").addEventListener(event,e=>{e.preventDefault();$("dropzone").classList.add("drag");});
for (const event of ["dragleave","drop"]) $("dropzone").addEventListener(event,e=>{e.preventDefault();$("dropzone").classList.remove("drag");});
$("dropzone").addEventListener("drop",e=>{if(e.dataTransfer.files[0])upload(e.dataTransfer.files[0]);});
$("clearBtn").onclick=clearArea;
$("drawBtn").onclick=()=>new L.Draw.Polygon(map,drawing.options.draw.polygon).enable();
$("bboxBtn").onclick=()=>new L.Draw.Rectangle(map,drawing.options.draw.rectangle).enable();
map.on(L.Draw.Event.CREATED,evt=>{
  const feature=evt.layer.toGeoJSON();
  const area=window.turf?window.turf.area(feature)/1000000:0;
  selectAOI({...feature,area_km2:area});
});
$("indiaBtn").onclick=()=>map.setView([22.5,80],5);
$("worldBtn").onclick=()=>map.setView([12,5],2);
map.on("mousemove",e=>{$("coords").textContent=e.latlng.lat.toFixed(5)+"°, "+e.latlng.lng.toFixed(5)+"°";});
$("searchForm").onsubmit=async e=>{
  e.preventDefault();const query=$("locationInput").value.trim();if(!query)return;
  try {const r=await fetch("https://nominatim.openstreetmap.org/search?format=json&limit=1&q="+encodeURIComponent(query));
    if(!r.ok)throw Error("Search service unavailable");const results=await r.json();if(!results.length)throw Error("Location not found");
    const p=results[0];map.setView([Number(p.lat),Number(p.lon)],10);
  }catch(error){toast(error.message);}
};
function showDatasets() {
  $("datasetList").replaceChildren();
  Object.entries(state.config.datasets).forEach(([id,data])=>{
    const row=document.createElement("label");row.className="dataset";
    const check=document.createElement("input");check.type="checkbox";check.checked=state.chosen.has(id);
    check.addEventListener("change",()=>{check.checked?state.chosen.add(id):state.chosen.delete(id);updateRun();});
    const names=document.createElement("span");names.className="dataset-info";
    const title=document.createElement("strong");title.textContent=data.name; const sub=document.createElement("small");sub.textContent=data.description;
    names.append(title,sub);const res=document.createElement("span");res.className="resolution";res.textContent=data.resolution;
    row.append(check,names,res);$("datasetList").append(row);
  });updateRun();
}
async function pollJob(id) {
  try {const r=await fetch("/api/jobs/"+encodeURIComponent(id));const job=await r.json();if(!r.ok)throw Error(job.detail||"Job unavailable");
    $("jobStatus").textContent=job.status==="completed"?"✓ Download ready":job.status==="failed"?"✕ Processing failed":"● "+job.status.toUpperCase();
    $("progressBar").style.width=job.progress+"%";$("progressLabel").textContent=Math.round(job.progress)+"%";
    $("jobMessage").textContent=job.message;
    if(["failed","completed"].includes(job.status)) {
      clearInterval(state.timer);state.timer=null;updateRun();
      if(job.errors?.length)toast(job.errors.join(" | "));
      if(job.status==="completed") {
        const target=$("downloads");target.replaceChildren();const root="/api/jobs/"+encodeURIComponent(id)+"/download/";
        job.files.forEach(file=>{const a=document.createElement("a");a.className="download";a.href=root+encodeURIComponent(file.filename);
          a.textContent="↓ "+file.dataset+" · "+(file.size_bytes/1048576).toFixed(1)+" MB";target.append(a);});
        const all=document.createElement("a");all.className="download download-all";all.href=root+"GeoDEM_Explorer_outputs.zip";all.textContent="↓ Download all (ZIP)";target.append(all);
      }
    }
  } catch(error) {toast("Status error: "+error.message);clearInterval(state.timer);state.timer=null;updateRun();}
}
$("runBtn").onclick=async()=>{
  if(!state.aoi||!state.chosen.size)return;
  $("runBtn").disabled=true;$("jobPanel").hidden=false;$("downloads").replaceChildren();$("jobStatus").textContent="● SUBMITTING";
  $("progressBar").style.width="0%";$("progressLabel").textContent="0%";
  try {const r=await fetch("/api/jobs",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({aoi:state.aoi,datasets:[...state.chosen]})});
    const data=await r.json();if(!r.ok)throw Error(data.detail||"Could not submit");
    if(state.timer)clearInterval(state.timer);state.timer=setInterval(()=>pollJob(data.id),2500);await pollJob(data.id);
  } catch(error){$("jobStatus").textContent="Could not start";$("jobMessage").textContent=error.message;toast(error.message);updateRun();}
};
state.config={key_configured:false,datasets:{
 "COP30":{name:"Copernicus GLO-30",description:"Digital Surface Model",resolution:"~30 m"},
 "AW3D30":{name:"ALOS AW3D30",description:"Digital Surface Model",resolution:"~30 m"},
 "SRTMGL1":{name:"NASA SRTM GL1",description:"Radar DEM",resolution:"~30 m"},
 "NASADEM":{name:"NASADEM",description:"Reprocessed SRTM",resolution:"~30 m"},
 "COP90":{name:"Copernicus GLO-90",description:"Digital Surface Model",resolution:"~90 m"}
}};
showDatasets();
$("runBtn").textContent="Processing server not connected";
$("keyWarning").hidden=false;
$("keyWarning").textContent="This Vercel deployment supports map selection and uploads in your browser. DEM mosaicking and downloads require a separate GDAL backend; no downloads are performed here.";
