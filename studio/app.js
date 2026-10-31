const $ = (id) => document.getElementById(id);
let currentProject = null;
const statusBox = $("system-status");
function setStatus(text, state) {
  statusBox.innerHTML = '<span class="dot '+(state||'')+'"></span><span></span>';
  statusBox.querySelector("span:last-child").textContent = text;
}
async function checkStatus() {
  try {
    const r = await fetch("/api/status");
    const data = await r.json();
    const missing = Object.entries(data.tools).filter(([,ok]) => !ok).map(([name]) => name);
    if (data.ready) setStatus("Outils prêts · Python "+data.python, "good");
    else setStatus("Installation requise : "+missing.join(", "), "bad");
  } catch { setStatus("Serveur local indisponible", "bad"); }
}
checkStatus();
$("manuscript").addEventListener("change", () => {
  const f = $("manuscript").files[0];
  $("file-name").textContent = f ? f.name+" · "+(f.size/1024/1024).toFixed(2)+" Mo" : "Aucun fichier sélectionné";
});
const drop = $("drop-zone");
drop.addEventListener("dragover", e => {e.preventDefault();drop.classList.add("drag")});
drop.addEventListener("dragleave", () => drop.classList.remove("drag"));
drop.addEventListener("drop", e => {
  e.preventDefault();drop.classList.remove("drag");
  const f=e.dataTransfer.files[0];
  if(f){$("manuscript").files=e.dataTransfer.files;$("manuscript").dispatchEvent(new Event("change"));}
});
function encodeBase64(buffer) {
  let binary = "";
  const bytes = new Uint8Array(buffer);
  const chunk = 0x8000;
  for(let i=0;i<bytes.length;i+=chunk) binary += String.fromCharCode(...bytes.subarray(i,i+chunk));
  return btoa(binary);
}
$("book-form").addEventListener("submit", async e => {
  e.preventDefault();
  const file = $("manuscript").files[0];
  if(!file){alert("Choisissez votre manuscrit.");return;}
  if(file.size>35*1024*1024){alert("Le fichier dépasse 35 Mo.");return;}
  const button=$("create-btn");button.disabled=true;button.textContent="Création du projet…";
  try {
    const buffer=await file.arrayBuffer();
    const payload={
      title:$("title").value,author:$("author").value,subtitle:$("subtitle").value,
      trim:$("trim").value,paper:$("paper").value,bleed:$("bleed").value==="true",
      toc:$("toc").checked,description:$("description").value,
      filename:file.name,file_base64:encodeBase64(buffer)
    };
    const response=await fetch("/api/create",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
    const data=await response.json();
    if(!response.ok) throw new Error(data.error||"Impossible de créer le projet.");
    currentProject=data.project;
    $("project-path").textContent=data.project+" · "+data.paragraphs+" paragraphes importés";
    $("project-panel").classList.remove("hidden");
    $("project-panel").scrollIntoView({behavior:"smooth",block:"start"});
    $("build-btn").disabled=false;
  } catch(err){alert(err.message);}
  finally{button.disabled=false;button.innerHTML='Créer le projet <span>→</span>';}
});
$("build-btn").addEventListener("click", async () => {
  if(!currentProject)return;
  const button=$("build-btn"),output=$("build-output");
  button.disabled=true;button.textContent="Génération en cours…";
  output.classList.remove("hidden");output.innerHTML="<p>Préparation des fichiers. Cette opération peut prendre quelques minutes…</p>";
  try{
    const response=await fetch("/api/build",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({project:currentProject})});
    const data=await response.json();
    if(data.logs){
      output.innerHTML="";
      const summary=document.createElement("div");
      summary.className=data.ok?"success-message":"error-message";
      summary.textContent=data.ok?"Génération terminée. Vérifiez les fichiers ci-dessous.":(data.message||"La génération a échoué.");
      output.append(summary);
      for(const log of data.logs){
        const section=document.createElement("div");section.className="log-step";
        const title=document.createElement("strong");title.textContent=(log.returncode===0?"✓ ":"✕ ")+log.step;
        const pre=document.createElement("pre");pre.textContent=log.output||"Terminé sans message.";
        section.append(title,pre);output.append(section);
      }
      if(data.ok){
        const done=document.createElement("p");done.className="success-message";done.textContent="Dossier final : "+data.package+" · "+data.files.join(", ");output.append(done);
      }
    } else throw new Error(data.error||"Erreur pendant la génération.");
  }catch(err){output.textContent=err.message;}
  finally{button.disabled=false;button.innerHTML='Relancer la génération <span>↻</span>';}
});
