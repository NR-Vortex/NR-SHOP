document.addEventListener("DOMContentLoaded", async () => {
  const el = id => document.getElementById(id);
  const auth = await window.nrTelegram();
  const preview = location.protocol === "file:";
  const format = value => new Intl.NumberFormat("fa-IR").format(value);
  const sections = {home:"میز کار نماینده", services:"تاریخچهٔ سرویس‌ها", account:"حساب من"};
  let data, cursor, filter = "all", action;
  const digits = value => value.replace(/[۰-۹]/g, c => "۰۱۲۳۴۵۶۷۸۹".indexOf(c)).replace(/[٠-٩]/g, c => "٠١٢٣٤٥٦٧٨٩".indexOf(c));
  function section(key) {
    for (const id of Object.keys(sections)) el(id).hidden = id !== key;
    el("heading").textContent = sections[key];
    for (const button of document.querySelectorAll("nav button")) {
      if (button.dataset.tab === key) button.setAttribute("aria-current","page");
      else button.removeAttribute("aria-current");
    }
    el("drawer").close();
    if (key === "home") auth.sdk?.BackButton?.hide();
    else auth.sdk?.BackButton?.show();
    window.scrollTo(0,0);
  }
  function rows(id, items, empty) {
    const host = el(id);
    host.replaceChildren();
    if (!items.length) host.textContent = empty;
    for (const service of items) {
      const row = document.createElement("div");
      row.className = "item";
      row.innerHTML = '<div><b></b><small></small></div><span class="status"></span>';
      row.querySelector("b").textContent = format(service.gb) + " گیگابایت";
      row.querySelector("small").textContent = "سرویس " + service.id + " · مشتری " + service.customer;
      row.querySelector(".status").textContent = service.delivered ? "✓ تحویل‌شده" : "◷ در انتظار";
      host.append(row);
    }
  }
  function history() {
    const query = digits(el("search").value.trim());
    const items = (data?.services || []).filter(s =>
      (filter === "all" || s.delivered === (filter === "done")) &&
      (String(s.id).includes(query) || String(s.customer).includes(query)));
    rows("list",items,query || filter !== "all" ? "سرویسی با این مشخصات پیدا نشد." : "هنوز سرویسی ثبت نشده است.");
    for (const b of document.querySelectorAll("[data-filter]")) b.setAttribute("aria-pressed",String(filter === b.dataset.filter));
    el("more").hidden = !cursor;
  }
  function render() {
    el("volume").textContent = format(data.volume);
    el("wallet").textContent = format(data.wallet) + " تومان";
    el("rate").textContent = data.price ? format(data.price) + " تومان" : "تعریف نشده";
    el("accountBot").textContent = data.bot;
    if (data.name) el("hello").textContent = "سلام، " + data.name;
    rows("recent",data.services.slice(0,3),"اولین کانفیگ شما اینجا نمایش داده می‌شود.");
    history();
  }
  async function api(path, method = "GET") {
    const response = await fetch("api/" + path,{method,headers:{Authorization:"tma " + auth.initData},cache:"no-store"});
    if (!response.ok) throw new Error(String(response.status));
    return response.json();
  }
  function estimate() {
    const gb = Number(el("gb").value);
    el("total").textContent = !data.price ? "تعرفه هنوز ثبت نشده است." :
      Number.isInteger(gb) && gb > 0 && gb <= 999999 ? "هزینهٔ برآوردی " + format(gb * data.price) + " تومان" : "حجم را به گیگابایت وارد کن.";
  }
  function openAction(key) {
    if (!data) return;
    action = key;
    el("dialogTitle").textContent = key === "buy" ? "خرید حجم نمایندگی" : "ساخت کانفیگ روی پنل مرکزی";
    el("estimate").hidden = key !== "buy";
    el("details").textContent = preview ? "پیش‌نمایش با دادهٔ نمونه" : key === "buy" ? "حجم نهایی را در گفت‌وگوی ربات انتخاب و تأیید کن." : "حجم و مدت سرویس را در گفت‌وگوی ربات وارد کن.";
    el("continue").hidden = preview;
    estimate();
    el("confirm").showModal();
  }
  document.addEventListener("click", event => {
    const b = event.target.closest("button");
    if (!b) return;
    if (b.dataset.tab) section(b.dataset.tab);
    if (b.dataset.act) openAction(b.dataset.act);
    if (b.dataset.filter) {filter = b.dataset.filter; history();}
    if (b.hasAttribute("data-close")) b.closest("dialog").close();
  });
  el("menu").onclick = () => el("drawer").showModal();
  el("gb").oninput = estimate;
  el("search").oninput = history;
  el("more").onclick = async () => {
    el("more").disabled = true;
    try {
      const page = await api("dashboard?before=" + encodeURIComponent(cursor));
      data.services.push(...page.services);
      cursor = page.next;
      history();
      el("notice").textContent = "";
    } catch {el("notice").textContent = "دریافت ادامهٔ تاریخچه ناموفق بود. دوباره تلاش کن.";}
    finally {el("more").disabled = false;}
  };
  el("continue").onclick = async () => {
    el("continue").disabled = true;
    try {
      await api("action/" + action,"POST");
      el("confirm").close();
      el("notice").textContent = "دکمهٔ ادامه به گفت‌وگوی ربات ارسال شد.";
      auth.sdk?.close?.();
    } catch {el("details").textContent = "ارسال درخواست ناموفق بود. دوباره تلاش کن.";}
    finally {el("continue").disabled = false;}
  };
  function paint(color, apply) {
    if (!/^#[0-9a-f]{6}$/i.test(color)) return;
    const [r,g,b] = color.slice(1).match(/../g).map(c => parseInt(c,16)/255).map(c => c <= .04045 ? c/12.92 : ((c+.055)/1.055)**2.4);
    apply(color,.2126*r+.7152*g+.0722*b > .179 ? "#14111d" : "#fff");
  }
  async function theme() {
    const style = preview ? JSON.parse(localStorage.getItem("nr-preview-theme") || "{}") : await (await fetch("api/theme")).json();
    const root = document.documentElement.style;
    for (const [key,fill,ink] of [["primary","accent","on-accent"],["secondary","secondary","on-secondary"],["background","bg","fg"],["surface","surface","on-surface"]]) {
      paint(style[key],(color,text) => {root.setProperty("--"+fill,color);root.setProperty("--"+ink,text);});
    }
    document.body.dataset.layout = style.layout || "tiles";
    for (const [selector,key] of [['[data-act="buy"]',"panel:buy"],['[data-act="connect"]',"panel:issue"],["#continue","miniapp:submit"],["#dismiss","miniapp:back"],...Object.keys(sections).map(k => ['[data-tab="'+k+'"]',"miniapp:"+k])]) {
      paint(style.buttons?.[key]?.web,(color,text) => document.querySelectorAll(selector).forEach(b => {b.style.backgroundColor=color;b.style.color=text;}));
    }
  }
  theme().catch(() => {});
  section("home");
  auth.sdk?.BackButton?.onClick(() => section("home"));
  try {
    if (preview) {
      data = {name:"",bot:"پنل نمایندگی",volume:185,wallet:2450000,price:12000,services:[{id:"103",customer:"24780",gb:20,delivered:true},{id:"102",customer:"24779",gb:10,delivered:false}]};
      el("mode").textContent = "پیش‌نمایش";
      el("shopEntry").href = "admin.html?shop";
      el("adminEntry").hidden = false;
    } else {
      if (!auth.initData) throw new Error("401");
      api("access").then(a => {el("adminEntry").hidden = !a.admin;}).catch(() => {});
      data = await api("dashboard");
      cursor = data.next;
    }
    render();
  } catch (error) {
    el("notice").textContent = error.message === "403" ? "نمایندگی برای این حساب فعال نیست." : error.message === "401" ? "برای ورود، پنل نمایندگی را از ربات تلگرام باز کن." : "اطلاعات نمایندگی بارگذاری نشد. صفحه را دوباره باز کن.";
  }
  for (const b of document.querySelectorAll("[data-act]")) b.disabled = !data;
});
