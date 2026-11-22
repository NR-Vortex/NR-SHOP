const $ = id => document.getElementById(id);
const clone = value => JSON.parse(JSON.stringify(value));
const DEFAULT = {
  primary: "#e9c88e", secondary: "#252335", background: "#101019", surface: "#191927",
  native: "default", layout: "tiles", chat_layout: "tiles", buttons: {}
};
const COLORS = ["primary", "secondary", "background", "surface"];
const LAYOUTS = [["tiles", "کارت‌های دوتایی"], ["list", "فهرست تمام‌عرض"], ["compact", "شبکهٔ فشرده"], ["feature", "دکمهٔ اول برجسته"]];
const TELEGRAM_COLORS = {primary:"#2f72c9",success:"#2c8c62",danger:"#c23f51"};
const TELEGRAM = [["default", "پیش‌فرض تلگرام"], ["primary", "آبی"], ["success", "سبز"], ["danger", "قرمز"]];
const NAME_BY_ACTION = {
  "admin:finance:payments": "رسیدهای پرداخت", "admin:reports:sales": "گزارش فروش",
  "admin:section:users": "کاربران", "support:admin:menu": "پشتیبانی مدیریت",
  "admin:section:finance": "امور مالی", "admin:hub:shop": "کاتالوگ و فروش",
  "admin:hub:agency": "نمایندگی", "admin:hub:content": "محتوا و ارتباطات",
  "admin:hub:system": "تنظیمات و نگهداری", "admin:section:ai": "هوش مصنوعی مدیر",
  "admin:vpn": "مدیریت VPN", "admin:section:gifts": "تخفیف و هدیه",
  "admin:section:reports": "گزارش‌ها", "admin:section:representatives": "مدیریت نمایندگان",
  "admin:section:agency_panel": "مدیریت پنل نمایندگی", "admin:section:agency_bot": "مدیریت ربات نمایندگی",
  "admin:section:broadcast": "پیام همگانی", "admin:section:ads": "تبلیغات و عضویت",
  "admin:section:texts": "متن‌های ربات", "admin:section:guides": "راهنماها",
  "admin:section:settings": "تنظیمات ربات", "admin:section:database": "دیتابیس و بکاپ",
  "updates:menu": "به‌روزرسانی", "webapp:/admin.html": "باز کردن مینی‌اپ مدیریت",
  "webapp:/shop.html": "ورود به مینی‌اپ فروشگاه", "webapp:/representative.html": "مینی‌اپ نمایندگی",
  "shop:category:vpn": "خرید VPN", "shop:category:ai": "اشتراک هوش مصنوعی",
  "shop:category:telegram": "خدمات تلگرام", "shop:orders": "محصولات من",
  "agency:bot": "ربات فروش نماینده", "agency:panel": "پنل نمایندگی",
  "support:menu": "پشتیبانی مشتری", "shop:home": "بازگشت به فروشگاه",
  "panel:buy": "خرید حجم نمایندگی", "panel:issue": "ساخت کانفیگ",
  "miniapp:home": "تب داشبورد", "miniapp:services": "تب سرویس‌ها",
  "miniapp:account": "تب حساب", "miniapp:appearance": "تب ظاهر",
  "miniapp:save": "ذخیرهٔ تم", "miniapp:submit": "ارسال فرم", "miniapp:back": "بازگشت"
};
const shop = location.pathname === "/" || location.pathname.endsWith("/shop.html") || new URLSearchParams(location.search).has("shop");
const mode = shop ? "shop" : "admin";
const preview = location.protocol === "file:";
const route = "api/" + mode + "/";
const heading = shop ? "فروشگاه NR SHOP" : "داشبورد مدیریت";
const description = shop ? "اشتراک بخر، سفارش را پیگیری کن یا از پشتیبانی کمک بگیر." : "فروش، مشتری‌ها و نمایندگی را از همین‌جا مدیریت کن.";
const buttonNames = new Map(Object.entries(NAME_BY_ACTION));
const adminRoots = ["admin:finance:payments","admin:reports:sales","admin:section:users","support:admin:menu","admin:section:finance","admin:hub:shop","admin:hub:agency","admin:hub:content","admin:hub:system"];
const shopRoots = ["shop:category:vpn","shop:category:ai","shop:orders","support:menu"];
const layoutSample = ["admin:finance:payments","admin:section:users","admin:hub:agency","admin:hub:shop"];
let telegram, auth, screen, busy = false, blob, selectedKey;
let saved = {...DEFAULT}, draft = {...DEFAULT};

function options(node, values, current) {
  node.replaceChildren(...values.map(([value, label]) => new Option(label, value, false, value === current)));
}

function ink(color) {
  const rgb = color.slice(1).match(/../g).map(x => parseInt(x,16)/255)
    .map(x => x <= .04045 ? x/12.92 : ((x+.055)/1.055)**2.4);
  return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722 > .179 ? "#14111d" : "#fff";
}

function paintButton(node, key, settings) {
  const custom = settings.buttons[key]?.web;
  node.style.backgroundColor = custom || "";
  node.style.color = custom ? ink(custom) : "";
}

function makeCard(key, name, click, settings = draft) {
  const button = document.createElement("button");
  button.type = "button";
  const icon = document.createElement("span");
  icon.className = "action-icon";
  icon.ariaHidden = "true";
  icon.textContent = "↖";
  const label = document.createElement("span");
  label.textContent = name;
  button.append(icon,label);
  if (click) button.onclick = click;
  paintButton(button,key,settings);
  return button;
}

function updatePreviews() {
  const active = draft.buttons[selectedKey] || {};
  $("buttonColor").value = active.web || draft.secondary;
  $("buttonNative").value = active.native ?? "inherit";
  $("buttonPreview").textContent = buttonNames.get(selectedKey) || "پیش‌نمایش دکمه";
  paintButton($("buttonPreview"),selectedKey,draft);
  for (const [host, layout] of [["layoutPreview",draft.layout],["chatPreview",draft.chat_layout]]) {
    const list = $(host);
    list.dataset.layout = layout;
    list.replaceChildren(...layoutSample.map(key => {
      const card = makeCard(key,buttonNames.get(key));
      if (host === "chatPreview") {
        const color = TELEGRAM_COLORS[draft.buttons[key]?.native ?? draft.native];
        card.style.backgroundColor = color || "";
        card.style.color = color ? ink(color) : "";
      }
      return card;
    }));
  }
}

function apply(settings) {
  for (const [field, variable, text] of [
    ["primary","--primary","--ptext"], ["secondary","--secondary","--stext"],
    ["background","--bg","--fg"], ["surface","--surface","--card-fg"]
  ]) {
    const color = settings[field];
    document.documentElement.style.setProperty(variable,color);
    document.documentElement.style.setProperty(text,ink(color));
    $(field).value = color;
  }
  for (const key of ["native","layout","chat_layout"]) $(key).value = settings[key];
  $("buttons").dataset.layout = settings.layout;
  for (const [id, key] of [
    ["home","miniapp:home"], ["palette","miniapp:appearance"], ["save","miniapp:save"],
    ["cancelForm","miniapp:back"], ["shortcut","miniapp:appearance"]
  ]) paintButton($(id),key,settings);
  paintButton($("form").querySelector(".primary"),"miniapp:submit",settings);
  drawButtons();
  updatePreviews();
}

function populateButtons() {
  const search = $("buttonSearch").value.trim().toLocaleLowerCase("fa");
  const values = [...buttonNames].filter(([key,name]) => !search || name.toLocaleLowerCase("fa").includes(search) || key.includes(search));
  const current = values.some(([key]) => key === selectedKey) ? selectedKey : values[0]?.[0];
  selectedKey = current;
  options($("targetButton"),values,current);
  for (const id of ["buttonColor","buttonNative","clearButton"]) $(id).disabled = !current;
  updatePreviews();
}

function drawButtons() {
  if (!screen) return;
  $("buttons").replaceChildren();
  for (const item of screen.rows.flat()) {
    $("buttons").append(makeCard(item.key || item.action,item.text,() => {
      if (item.url) {
        if (new URL(item.url).origin === location.origin) location.assign(item.url);
        else if (telegram?.openLink) telegram.openLink(item.url);
        else window.open(item.url,"_blank","noopener");
      } else sendEvent(item.action);
    }));
  }
}

function themeTab(show) {
  $("operations").hidden = show;
  $("appearance").hidden = !show;
  $("title").textContent = show ? "ظاهر و چیدمان" : heading;
  $("summary").textContent = show ? "مدل منو، تم و رنگ تک‌تک دکمه‌ها را تنظیم کن." : description;
  $("eyebrow").textContent = show ? "NR SHOP / STYLE" : shop ? "NR SHOP / STORE" : "NR SHOP / ADMIN";
  $("home").setAttribute("aria-current",show ? "false" : "page");
  $("palette").setAttribute("aria-current",show ? "page" : "false");
}

async function request(url, opts = {}) {
  const res = await fetch(url,{...opts,headers:{Authorization:"tma "+auth.initData,...opts.headers},cache:"no-store"});
  if (!res.ok) {
    const error = Error({
    403:"این بخش برای حساب شما در دسترس نیست.",
    401:"مینی‌اپ را دوباره از منوی ربات باز کن.",
    409:"صفحه تغییر کرده. گزینه را دوباره انتخاب کن."
  }[res.status] || "عملیات کامل نشد. دوباره امتحان کن.");
    error.status=res.status;
    throw error;
  }
  return res;
}

async function render(view) {
  screen = view;
  for (const item of view.rows.flat()) {
    if (item.key) buttonNames.set(item.key,item.text);
  }
  themeTab(false);
  $("notice").textContent = view.notice || "";
  $("productNav").hidden = !view.shortcuts?.["shop:orders"];
  $("supportNav").hidden = !view.shortcuts?.["support:menu"];
  $("caption").hidden = !!view.is_home;
  $("caption").textContent = view.caption || "";
  $("sectionTitle").textContent = view.is_home ? (shop ? "بخش‌های فروشگاه" : "دسترسی سریع") : "عملیات این بخش";
  $("form").hidden = !view.input;
  $("value").hidden = !!view.password;
  $("secret").hidden = !view.password;
  $("upload").hidden = !view.upload;
  $("value").placeholder = view.upload ? "متن همراه پیوست (اختیاری)" : "پاسخ را وارد کن";
  for (const id of ["value","secret","upload"]) $(id).value = "";
  $("media").replaceChildren();
  if (blob) URL.revokeObjectURL(blob);
  apply(draft);
  if (view.media) {
    const response = await request(route + "media/" + view.media.key);
    blob = URL.createObjectURL(await response.blob());
    const node = document.createElement(view.media.photo ? "img" : "a");
    if (view.media.photo) { node.src = blob; node.alt = "تصویر پیوست"; }
    else { node.href = blob; node.download = "receipt"; node.textContent = "دریافت پیوست"; node.className = "btn"; }
    $("media").append(node);
  }
}

async function refresh() {
  const payload = await (await request(route+"screen")).json();
  saved = {...DEFAULT,...payload.theme}; draft = clone(saved);
  await render(payload);
}

async function sendEvent(action) {
  if (busy || !screen) return;
  if (preview) {
    $("notice").textContent = shop ? "خرید از داخل تلگرام فعال می‌شود." : "برای اجرای عملیات، مینی‌اپ را از منوی ادمین ربات باز کن.";
    return;
  }
  busy = true;
  try {
    const body = new FormData();
    body.set("revision",screen.revision);
    body.set("action",action);
    if (action === "input") {
      body.set("value",screen.password ? $("secret").value : $("value").value);
      if ($("upload").files[0]) body.set("file",$("upload").files[0]);
    }
    await render(await (await request(route+"event",{method:"POST",body})).json());
  } catch (error) {
    if (error.status===401) {
      auth.clear();
      await recovery(error.message);
    } else {
      try { await refresh(); } catch {}
      $("notice").textContent = error.message;
    }
  } finally { busy = false; }
}

function changeButton(rule,value) {
  if (!selectedKey) return;
  const rules = {...draft.buttons[selectedKey]};
  if (value) rules[rule] = value;
  else delete rules[rule];
  if (Object.keys(rules).length) draft.buttons[selectedKey] = rules;
  else delete draft.buttons[selectedKey];
  apply(draft);
}

options($("layout"),LAYOUTS,DEFAULT.layout);
options($("chat_layout"),LAYOUTS,DEFAULT.chat_layout);
options($("native"),TELEGRAM,DEFAULT.native);
options($("buttonNative"),[["inherit","پیروی از تنظیمات عمومی"],...TELEGRAM],"inherit");
for (const [name,palette] of Object.entries({
  "طلایی": ["#e9c88e","#252335","#101019","#191927"],
  "یاقوت": ["#ff9cae","#4f2a40","#1b101a","#2c1728"],
  "یخی": ["#9cd8ff","#273e59","#101924","#172738"],
  "زمرد": ["#9de4c7","#234739","#101c18","#183029"]
})) {
  const button = document.createElement("button");
  button.type = "button";
  const dot = document.createElement("span");
  dot.className = "preset-dot"; dot.style.background = palette[0];
  button.append(dot,name);
  button.onclick = () => { COLORS.forEach((key,index) => draft[key]=palette[index]); apply(draft); };
  $("presets").append(button);
}
for (const key of [...COLORS,"layout","chat_layout","native"]) $(key).oninput=()=>{ draft[key]=$(key).value; apply(draft); };
$("buttonSearch").oninput = populateButtons;
$("targetButton").onchange = () => { selectedKey=$("targetButton").value; updatePreviews(); };
$("buttonColor").oninput = () => changeButton("web",$("buttonColor").value);
$("buttonNative").onchange = () => changeButton("native",$("buttonNative").value === "inherit" ? null : $("buttonNative").value);
$("clearButton").onclick = () => { delete draft.buttons[selectedKey]; apply(draft); };
$("reset").onclick = () => { draft=clone(DEFAULT); apply(draft); };
$("palette").onclick = $("shortcut").onclick = () => { themeTab(true);populateButtons();apply(draft); };
$("home").onclick = () => { themeTab(false); draft=clone(saved); apply(draft); if (!preview) sendEvent("home"); };
$("cancelForm").onclick = () => sendEvent("home");
$("productNav").onclick = () => sendEvent("shop:orders");
$("supportNav").onclick = () => sendEvent("support:menu");
$("retry").onclick = () => location.reload();
$("openSidebar").onclick = () => $("sidebar").showModal();
$("closeSidebar").onclick = () => $("sidebar").close();
$("sidebar").addEventListener("click",event=>{
  if(event.target===$("sidebar")) $("sidebar").close();
  const action=event.target.closest("[data-screen]")?.dataset.screen;
  if(action){
    $("sidebar").close();
    $(action==="appearance"?"palette":"home").click();
  }
});
for (const link of document.querySelectorAll("[data-jump]")) {
  link.onclick=event=>{
    event.preventDefault();
    $(link.dataset.jump).scrollIntoView({behavior:"smooth",block:"start"});
  };
}
$("form").onsubmit = event => { event.preventDefault(); sendEvent("input"); };
$("save").onclick = async () => {
  try {
    if (preview) localStorage.setItem("nr-preview-theme",JSON.stringify(draft));
    else {
      const response = await request("api/admin/theme",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(draft)});
      draft = await response.json();
    }
    saved=clone(draft);
    apply(draft);
    $("notice").textContent=preview ? "چیدمان و رنگ‌ها برای پیش‌نمایش ذخیره شدند." : "چیدمان و رنگ‌ها ذخیره شدند. منوهای تلگرام با پیام جدید به‌روز می‌شوند.";
    $("notice").scrollIntoView({block:"nearest"});
  } catch(error) { $("notice").textContent=error.message; }
};

async function recovery(message) {
  $("operations").hidden=true;
  $("appearance").hidden=true;
  $("dock").hidden=true;
  $("recoveryText").textContent=message;
  $("recovery").hidden=false;
  try {
    const response=await fetch("api/bot-link");
    const {url}=await response.json();
    if(/^https:\/\/t\.me\/[A-Za-z0-9_]+$/.test(url)){
      $("botLink").href=url;
      $("botLink").hidden=false;
    }
  } catch {}
}

async function start() {
  $("title").textContent=heading;
  $("summary").textContent=description;
  if (shop) {
    for (const id of ["palette","shortcut"]) $(id).hidden=true;
    $("home").textContent="خانهٔ فروشگاه";
    $("sideAppearance").hidden=true;
    $("sideShop").hidden=true;
  }
  if (preview) {
    document.querySelector(".brand").href="index.html";
    $("sideShop").href="admin.html?shop";
    $("sideRep").href="index.html";
    try { saved={...DEFAULT,...JSON.parse(localStorage.getItem("nr-preview-theme")||"{}")}; } catch {}
    draft=clone(saved);
    $("session").textContent="پیش‌نمایش";
    const roots=shop?shopRoots:adminRoots;
    await render({is_home:true,rows:[roots.map(key=>({key,text:NAME_BY_ACTION[key],action:key}))]});
    return;
  }
  try {
    auth=await window.nrTelegram();
    telegram=auth.sdk;
    if(!auth.initData) throw Error(shop?"برای خرید، ربات را در تلگرام باز کن و «ورود به فروشگاه» را بزن.":"برای مدیریت، در تلگرام /admin را بفرست و «باز کردن مینی‌اپ مدیریت» را بزن.");
    await refresh();
    if (shop) request("api/access").then(r=>r.json()).then(role=>{$("sideAdmin").hidden=!role.admin}).catch(()=>{});
    $("session").textContent=shop?"فروشگاه مشتری":"پنل ادمین";
    if (!shop && new URLSearchParams(location.search).get("view")==="appearance") $("palette").click();
    telegram?.BackButton?.show();
    telegram?.BackButton?.onClick(()=>$("home").click());
  } catch(error) {
    if(error.status===401) auth?.clear();
    await recovery(error.message);
  }
}
start();
