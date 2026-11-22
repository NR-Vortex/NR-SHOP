(() => {
  const cacheKey="nr-tg-session";
  function initialData(){
    const launch=new URLSearchParams(location.hash.slice(1));
    const signed=launch.get("tgWebAppData")||window.Telegram?.WebApp?.initData;
    if(signed){
      try{sessionStorage.setItem(cacheKey,signed)}catch{}
      return signed;
    }
    try{return sessionStorage.getItem(cacheKey)||""}catch{return ""}
  }
  function loadSDK(){
    if(window.Telegram?.WebApp||location.protocol==="file:")return Promise.resolve();
    return new Promise(resolve=>{
      const script=document.createElement("script");
      script.src="https://telegram.org/js/telegram-web-app.js";
      const timeout=setTimeout(resolve,2300);
      script.onload=script.onerror=()=>{clearTimeout(timeout);resolve()};
      document.head.append(script);
    });
  }
  window.nrTelegram=async()=>{
    let initData=initialData();
    await loadSDK();
    initData=window.Telegram?.WebApp?.initData||initData||initialData();
    if(initData){
      try{sessionStorage.setItem(cacheKey,initData)}catch{}
      window.Telegram?.WebApp?.ready();
      window.Telegram?.WebApp?.expand();
    }
    return {initData,sdk:window.Telegram?.WebApp,clear(){
      try{sessionStorage.removeItem(cacheKey)}catch{}
    }};
  };
})();
