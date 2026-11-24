interface ScheduledController {
  cron: string;
  scheduledTime: number;
}

export interface Env {
  GITHUB_TOKEN: string;
  GITHUB_OWNER?: string;
  GITHUB_REPO?: string;
  GITHUB_REF?: string;
}

const FETCH_CRON = "1 8 * * *"; // Beijing 16:01
const PUSH_CRON = "2 8 * * *";  // Beijing 16:02
const GITHUB_API_VERSION = "2022-11-28";

async function dispatchWorkflow(
  env: Env,
  workflowFile: string,
  inputs?: Record<string, string | boolean>,
): Promise<void> {
  const owner = env.GITHUB_OWNER || "694340796";
  const repo = env.GITHUB_REPO || "TheDivision2-Daily-Loot";
  const ref = env.GITHUB_REF || "main";
  const url = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflowFile}/dispatches`;

  const response = await fetch(url, {
    method: "POST",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      "X-GitHub-Api-Version": GITHUB_API_VERSION,
      "Content-Type": "application/json",
      "User-Agent": "thedivision2-daily-loot-cloudflare-worker",
    },
    body: JSON.stringify({ ref, ...(inputs ? { inputs } : {}) }),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(
      `GitHub workflow dispatch failed (${response.status}) for ${workflowFile}: ${detail}`,
    );
  }

  console.log(
    JSON.stringify({
      event: "workflow_dispatched",
      workflow: workflowFile,
      ref,
      scheduledAt: new Date().toISOString(),
      status: response.status,
    }),
  );
}

const DASHBOARD_HTML = String.raw`<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#0b1020">
  <title>全境封锁2 · 每日掉落任务调度</title>
  <style>
    :root{color-scheme:dark;--bg:#080d19;--panel:#111a2d;--panel2:#151f35;--line:rgba(148,163,184,.16);--muted:#94a3b8;--text:#edf4ff;--cyan:#54d6e8;--violet:#9b8cff;--green:#59d69a}
    *{box-sizing:border-box}
    body{margin:0;min-height:100vh;background:radial-gradient(ellipse at 12% 0%,rgba(49,93,166,.24),transparent 42%),radial-gradient(ellipse at 92% 15%,rgba(104,74,180,.2),transparent 36%),var(--bg);color:var(--text);font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif}
    .wrap{width:min(1040px,calc(100% - 36px));margin:0 auto;padding:48px 0 36px}
    .top{display:flex;align-items:center;justify-content:space-between;gap:18px;margin-bottom:30px}
    .brand{display:flex;align-items:center;gap:14px}.logo{width:46px;height:46px;border-radius:15px;display:grid;place-items:center;background:linear-gradient(135deg,#47cce0,#7165e8);box-shadow:0 8px 28px rgba(72,190,221,.22);font-size:22px;font-weight:900;color:#07111e}
    .eyebrow{font-size:11px;letter-spacing:2px;color:var(--cyan);font-weight:800;text-transform:uppercase}
    h1{font-size:clamp(22px,4vw,30px);margin:4px 0 0;letter-spacing:.3px}
    .live{border:1px solid rgba(89,214,154,.28);background:rgba(89,214,154,.08);color:#8ce8b8;padding:8px 12px;border-radius:999px;font-size:12px;white-space:nowrap}
    .live i{display:inline-block;width:7px;height:7px;background:var(--green);border-radius:50%;margin-right:7px;box-shadow:0 0 10px var(--green)}
    .hero{border:1px solid var(--line);border-radius:24px;padding:26px 28px;background:linear-gradient(120deg,rgba(23,39,66,.94),rgba(18,25,46,.94));box-shadow:0 20px 70px rgba(0,0,0,.2);margin-bottom:18px}
    .hero-label{color:var(--muted);font-size:13px}.clock{font-size:clamp(34px,7vw,54px);font-weight:750;letter-spacing:1px;margin:8px 0 5px;font-variant-numeric:tabular-nums}.date{color:#a9b7ce;font-size:14px}
    .grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
    .task{position:relative;overflow:hidden;border:1px solid var(--line);border-radius:22px;padding:23px;background:linear-gradient(145deg,rgba(20,31,53,.98),rgba(14,22,39,.98));min-height:248px}
    .task:after{content:"";position:absolute;width:170px;height:170px;border-radius:50%;right:-70px;top:-82px;background:var(--glow);filter:blur(3px);opacity:.13}
    .task.fetch{--glow:var(--cyan)}.task.push{--glow:var(--violet)}
    .task-head{display:flex;align-items:center;justify-content:space-between;gap:12px;position:relative;z-index:1}
    .task-name{display:flex;align-items:center;gap:10px;font-size:16px;font-weight:700}.task-icon{width:34px;height:34px;border-radius:11px;display:grid;place-items:center;background:rgba(255,255,255,.06);font-size:17px}
    .tag{font-size:11px;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:5px 9px}
    .time{font-size:28px;font-weight:750;margin:22px 0 3px;font-variant-numeric:tabular-nums;position:relative;z-index:1}.timezone{font-size:12px;color:var(--muted)}
    .count-label{margin-top:22px;color:var(--muted);font-size:12px}.count{font-size:clamp(23px,4vw,30px);font-weight:750;letter-spacing:.4px;margin-top:5px;font-variant-numeric:tabular-nums;position:relative;z-index:1}
    .foot{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:22px;padding-top:15px;border-top:1px solid var(--line);font-size:12px;color:var(--muted)}
    .status{color:#9fe5c0}.note{margin-top:18px;border:1px solid var(--line);border-radius:16px;padding:16px 18px;color:var(--muted);font-size:12px;line-height:1.8;background:rgba(17,26,45,.62)}
    .note strong{color:#dbeafe}.bottom{text-align:center;color:#64748b;font-size:11px;margin-top:24px}
    @media(max-width:680px){.wrap{padding-top:28px}.top{align-items:flex-start}.live{font-size:0;padding:9px}.live i{margin:0}.hero{padding:22px}.grid{grid-template-columns:1fr}.task{min-height:230px}.foot{flex-wrap:wrap}}
  </style>
</head>
<body>
  <main class="wrap">
    <header class="top">
      <div class="brand"><div class="logo">D2</div><div><div class="eyebrow">DAILY LOOT AUTOMATION</div><h1>每日任务调度中心</h1></div></div>
      <div class="live"><i></i>调度服务已部署</div>
    </header>
    <section class="hero">
      <div class="hero-label">当前北京时间 · Asia/Shanghai</div>
      <div class="clock" id="clock">--:--:--</div>
      <div class="date" id="date">正在读取时间…</div>
    </section>
    <section class="grid">
      <article class="task fetch">
        <div class="task-head"><div class="task-name"><span class="task-icon">↻</span>每日掉落获取</div><span class="tag">FETCH</span></div>
        <div class="time">16:01</div><div class="timezone">每天 · 北京时间 UTC+8</div>
        <div class="count-label">距离下次执行还有</div><div class="count" id="fetch-count">计算中…</div>
        <div class="foot"><span>GitHub Actions · Daily Loot Fetch</span><span class="status">● 已配置</span></div>
      </article>
      <article class="task push">
        <div class="task-head"><div class="task-name"><span class="task-icon">➤</span>每日订阅推送</div><span class="tag">PUSH</span></div>
        <div class="time">16:02</div><div class="timezone">每天 · 北京时间 UTC+8</div>
        <div class="count-label">距离下次执行还有</div><div class="count" id="push-count">计算中…</div>
        <div class="foot"><span>GitHub Actions · Daily Loot Push</span><span class="status">● 已配置</span></div>
      </article>
    </section>
    <section class="note"><strong>运行说明</strong><br>① 16:01 触发每日掉落数据获取。<br>② 16:02 触发订阅推送工作流，等待当天获取任务成功后再发送，避免推送旧数据。<br>倒计时根据浏览器当前时间实时计算；Cloudflare Cron 使用 UTC，实际触发可能有少量延迟，不保证秒级准点。</section>
    <footer class="bottom">THE DIVISION 2 · DAILY LOOT SCHEDULER</footer>
  </main>
  <script>
    const zone = "Asia/Shanghai";
    const fmt = new Intl.DateTimeFormat("zh-CN", {timeZone:zone,year:"numeric",month:"2-digit",day:"2-digit",weekday:"long"});
    const timeFmt = new Intl.DateTimeFormat("zh-CN", {timeZone:zone,hour:"2-digit",minute:"2-digit",second:"2-digit",hourCycle:"h23"});
    function nextRun(hour, minute) {
      const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA",{timeZone:zone,year:"numeric",month:"numeric",day:"numeric"}).formatToParts(new Date()).filter(p=>p.type!=="literal").map(p=>[p.type,Number(p.value)]));
      let target = Date.UTC(parts.year,parts.month-1,parts.day,hour-8,minute,0);
      if (target <= Date.now()) target += 86400000;
      return target;
    }
    function pad(n){return String(n).padStart(2,"0")}
    function countdown(target){
      let seconds=Math.max(0,Math.floor((target-Date.now())/1000));
      const days=Math.floor(seconds/86400);seconds%=86400;
      const hours=Math.floor(seconds/3600);seconds%=3600;
      const minutes=Math.floor(seconds/60);seconds%=60;
      return (days>0?days+"天 ":"")+pad(hours)+"时 "+pad(minutes)+"分 "+pad(seconds)+"秒";
    }
    function tick(){
      const now=new Date();
      document.getElementById("clock").textContent=timeFmt.format(now);
      document.getElementById("date").textContent=fmt.format(now);
      document.getElementById("fetch-count").textContent=countdown(nextRun(16,1));
      document.getElementById("push-count").textContent=countdown(nextRun(16,2));
    }
    tick();setInterval(tick,1000);
  </script>
</body>
</html>`;

export default {
  async scheduled(
    controller: ScheduledController,
    env: Env,
    _ctx: unknown,
  ): Promise<void> {
    if (!env.GITHUB_TOKEN) {
      throw new Error("Missing Cloudflare Worker secret: GITHUB_TOKEN");
    }

    console.log(
      JSON.stringify({
        event: "cron_started",
        cron: controller.cron,
        scheduledTime: new Date(controller.scheduledTime).toISOString(),
      }),
    );

    if (controller.cron === FETCH_CRON) {
      await dispatchWorkflow(env, "daily-loot-fetch.yml");
      return;
    }

    if (controller.cron === PUSH_CRON) {
      const fetchNotBefore = new Date(
        controller.scheduledTime - 3 * 60 * 1000,
      ).toISOString();

      await dispatchWorkflow(env, "daily-loot-push.yml", {
        wait_for_fetch: "true",
        fetch_not_before: fetchNotBefore,
      });
      return;
    }

    console.log(JSON.stringify({ event: "ignored_cron", cron: controller.cron }));
  },

  async fetch(request: Request): Promise<Response> {
    if (request.method !== "GET") {
      return new Response("Method Not Allowed", {
        status: 405,
        headers: { Allow: "GET" },
      });
    }

    return new Response(DASHBOARD_HTML, {
      headers: {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "no-store, max-age=0",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'",
      },
    });
  },
};
