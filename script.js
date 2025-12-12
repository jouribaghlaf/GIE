"use strict";

window.addEventListener("DOMContentLoaded", () => {
  const API_BASE = "http://127.0.0.1:5000";

  const searchInput  = document.getElementById("searchInput");
  const searchBtn    = document.getElementById("searchBtn");
  const backendPill  = document.getElementById("backendPill");
  const errorBox     = document.getElementById("errorBox");

  const favoritesGrid = document.getElementById("favoritesGrid");
  const suggestedGrid = document.getElementById("suggestedGrid");

  const modal      = document.getElementById("modal");
  const modalBg    = document.getElementById("modalBg");
  const modalBody  = document.getElementById("modalBody");
  const modalClose = document.getElementById("modalClose");
  const modalGo    = document.getElementById("modalGo");

  // ✅ فحص IDs بعد ما العناصر تكون موجودة
  if (!searchInput || !searchBtn) {
    console.error("IDs mismatch: تأكدي أن searchInput و searchBtn موجودين في HTML");
    return; // لا نكمل لأن الصفحة ناقصة عناصر
  }

  let lastSuggestedTargets = null; // Set([...targets]) بعد البحث
  let lastNavTarget = null;

  // خدمات مفضلة ثابتة
  const FAVORITES = [
    { id:"payments", title:"المدفوعات الحكومية", description:"سداد الرسوم الحكومية (محاكاة).", action:{type:"navigate", target:"payments"} },
    { id:"appointments", title:"إدارة المواعيد", description:"حجز/تعديل/إلغاء موعد (محاكاة).", action:{type:"navigate", target:"appointments"} },
    { id:"documents_delivery", title:"توصيل الوثائق", description:"طلب توصيل الوثائق (محاكاة).", action:{type:"navigate", target:"documents-delivery"} },
    { id:"delegation", title:"إدارة التفويض", description:"إنشاء/إلغاء تفويض (محاكاة).", action:{type:"navigate", target:"delegation"} }
  ];

  function showError(msg){
    if(!msg){
      errorBox.classList.add("hidden");
      errorBox.textContent = "";
      return;
    }
    errorBox.textContent = msg;
    errorBox.classList.remove("hidden");
  }

  function setBackend(ok){
    backendPill.textContent = ok ? "Backend: OK" : "Backend: Down";
    backendPill.classList.toggle("ok", !!ok);
    backendPill.classList.toggle("down", !ok);
  }

  async function pingBackend(){
    try{
      const res = await fetch(`${API_BASE}/api/health`, { method:"GET" });
      setBackend(res.ok);
    }catch(e){
      setBackend(false);
    }
  }

  function isArabicText(text){
    const t = (text || "").trim();
    if(t.length < 4) return false;

    const arabic = (t.match(/[\u0600-\u06FF]/g) || []).length;
    if(arabic < 3) return false;

    const low = t.replace(/[أإآ]/g,"ا").toLowerCase();
    const bad = ["اتروش","استحم","شاور","انام","أكل","اكل","العب","ابا اروح","ابي اروح"];
    if(bad.some(x => low.includes(x))) return false;

    const hints = ["ابغى","ابي","ابا","احتاج","كيف","تجديد","اصدار","حجز","موعد","سداد","مدفوعات","تفويض","وثائق","توصيل","اقامه","جواز","هوية","سفر","اسافر","بلاغ","تأشيرة","مخالفات"];
    if(!hints.some(h => low.includes(h)) && !low.includes("اسافر") && !low.includes("سافر")) return false;

    return true;
  }

  function openModal(service){
    const title  = service?.title || "خدمة";
    const desc   = service?.description || "";
    const target = service?.action?.target || "unknown";
    lastNavTarget = target;

    modalBody.innerHTML = `
      <div style="font-weight:900; margin-bottom:6px;">${title}</div>
      <div style="opacity:0.9; margin-bottom:8px;">${desc}</div>
      <div style="opacity:0.8;">سيتم الانتقال إلى: <b>${target}</b> (محاكاة)</div>
    `;
    modal.classList.remove("hidden");
  }

  function closeModal(){
    modal.classList.add("hidden");
  }

  modalBg.addEventListener("click", closeModal);
  modalClose.addEventListener("click", closeModal);
  modalGo.addEventListener("click", ()=>{
    if(lastNavTarget){
      window.location.hash = `#service=${encodeURIComponent(lastNavTarget)}`;
    }
    closeModal();
  });

  function cardEl(service){
    const card = document.createElement("div");
    card.className = "service-card";
    card.innerHTML = `
      <div>
        <div class="service-title">${service.title || "—"}</div>
        <div class="service-desc">${service.description || ""}</div>
      </div>
      <div class="service-actions">
        <button class="go-btn" type="button">الانتقال للخدمة</button>
      </div>
    `;

    card.querySelector(".go-btn").addEventListener("click", ()=> openModal(service));
    card.addEventListener("click", (e)=>{
      if(e.target?.classList?.contains("go-btn")) return;
      openModal(service);
    });

    return card;
  }

  function renderFavorites(){
    favoritesGrid.innerHTML = "";
    let items = FAVORITES;

    if(lastSuggestedTargets && lastSuggestedTargets.size > 0){
      items = FAVORITES.filter(f => lastSuggestedTargets.has(f.action.target));
    }

    if(items.length === 0){
      const empty = document.createElement("div");
      empty.style.opacity = "0.9";
      empty.textContent = "لا توجد خدمات مفضلة مطابقة لنتائج البحث.";
      favoritesGrid.appendChild(empty);
      return;
    }

    items.forEach(s => favoritesGrid.appendChild(cardEl(s)));
  }

  function renderSuggested(services){
    suggestedGrid.innerHTML = "";

    if(!Array.isArray(services) || services.length === 0){
      const empty = document.createElement("div");
      empty.style.opacity = "0.9";
      empty.textContent = "لا توجد خدمات مقترحة حالياً.";
      suggestedGrid.appendChild(empty);
      return;
    }

    services.forEach(s => suggestedGrid.appendChild(cardEl(s)));
  }

  async function analyze(){
    const text = (searchInput.value || "").trim();
    showError("");

    if(!text){
      showError("الرجاء إدخال نص صحيح وواضح.");
      return;
    }

    // ✅ فلترة النص غير المفهوم
    if(!isArabicText(text)){
      lastSuggestedTargets = null;
      renderFavorites();
      renderSuggested([]);
      showError("الرجاء إدخال طلب واضح يتعلق بخدمات أبشر.");
      return;
    }

    try{
      const response = await fetch(`${API_BASE}/api/gie`, {
        method: "POST",
        headers: { "Content-Type":"application/json" },
        body: JSON.stringify({ text })
      });

      const data = await response.json().catch(()=> ({}));

      if(!response.ok){
        throw new Error(data?.message || ("HTTP " + response.status));
      }

      const services = Array.isArray(data.services) ? data.services : [];
      lastSuggestedTargets = new Set(
        services.map(s => s?.action?.target).filter(Boolean)
      );

      renderSuggested(services);
      renderFavorites();

    }catch(err){
      console.error(err);
      showError("صار خطأ أثناء الاتصال بالمحرك. تأكدي أن app.py شغال وأن المنفذ 5000 مفتوح.");
    }
  }

  // زر بحث
  searchBtn.addEventListener("click", analyze);

  // Enter يشتغل
  searchInput.addEventListener("keydown", (e)=>{
    if(e.key === "Enter"){
      e.preventDefault();
      analyze();
    }
  });

  // أول تحميل
  renderFavorites();
  renderSuggested([]);
  pingBackend();
  setInterval(pingBackend, 3000);
});
