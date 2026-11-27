interface ScheduledController {
  cron: string;
  scheduledTime: number;
}

export interface Env {
  GITHUB_TOKEN: string;
  TRIGGER_SECRET?: string;
}

const CHECK_CRON = "* * * * *"; // Every minute; decide tasks using Asia/Shanghai time.
const TIME_ZONE = "Asia/Shanghai";
function getBeijingHourMinute(timestamp: number): { hour: string; minute: string } {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: TIME_ZONE,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(timestamp));
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return { hour: values.hour, minute: values.minute };
}
const GITHUB_API_VERSION = "2022-11-28";

async function dispatchWorkflow(
  env: Env,
  workflowFile: string,
  inputs?: Record<string, string | boolean>,
): Promise<void> {
  // Repository coordinates are fixed in code; no Cloudflare Text vars are required.
  const owner = "694340796";
  const repo = "TheDivision2-Daily-Loot";
  const ref = "main";
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
    .task.fetch{--glow:var(--cyan)}.task.push{--glow:var(--violet)}.task.xmaint{--glow:var(--green)}
    .task-head{display:flex;align-items:center;justify-content:space-between;gap:12px;position:relative;z-index:1}
    .task-name{display:flex;align-items:center;gap:10px;font-size:16px;font-weight:700}.task-icon{width:34px;height:34px;border-radius:11px;display:grid;place-items:center;background:rgba(255,255,255,.06);font-size:17px}
    .tag{font-size:11px;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:5px 9px}
    .time{font-size:28px;font-weight:750;margin:22px 0 3px;font-variant-numeric:tabular-nums;position:relative;z-index:1}.timezone{font-size:12px;color:var(--muted)}
    .count-label{margin-top:22px;color:var(--muted);font-size:12px}.count{font-size:clamp(23px,4vw,30px);font-weight:750;letter-spacing:.4px;margin-top:5px;font-variant-numeric:tabular-nums;position:relative;z-index:1}
    .foot{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:22px;padding-top:15px;border-top:1px solid var(--line);font-size:12px;color:var(--muted)}
    .status{color:#9fe5c0}.note{margin-top:18px;border:1px solid var(--line);border-radius:16px;padding:16px 18px;color:var(--muted);font-size:12px;line-height:1.8;background:rgba(17,26,45,.62)}
    .note strong{color:#dbeafe}
    .test-panel{margin-top:18px;border:1px solid rgba(84,214,232,.22);border-radius:20px;padding:22px;background:linear-gradient(145deg,rgba(17,29,49,.96),rgba(13,21,37,.96))}
    .test-title{font-size:16px;font-weight:750}.test-title span{font-size:10px;letter-spacing:1.5px;color:var(--cyan);margin-left:8px}
    .test-panel p{font-size:12px;line-height:1.7;color:var(--muted);margin:9px 0 16px}
    .test-panel label{display:block;font-size:12px;color:#cbd5e1;margin-bottom:7px}
    .test-panel input{width:100%;max-width:480px;padding:12px 13px;border-radius:11px;border:1px solid var(--line);background:#080f1e;color:var(--text);outline:none}
    .test-panel input:focus{border-color:var(--cyan)}
    .test-actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}
    .test-btn{border:0;border-radius:11px;padding:12px 16px;font-weight:700;color:#07111e;cursor:pointer;transition:filter .15s,transform .15s}
    .test-btn:hover{filter:brightness(1.12);transform:translateY(-1px)}.test-btn:disabled{opacity:.55;cursor:wait;transform:none}
    .fetch-btn{background:linear-gradient(135deg,#58d9e8,#7de2c4)}.push-btn{background:linear-gradient(135deg,#a99aff,#d0a5ff)}
    #trigger-result{font-size:12px;line-height:1.7;margin-top:12px;color:#a9b7ce;min-height:18px}
    #trigger-result.ok{color:#8ce8b8}#trigger-result.error{color:#ff9b9b}
    .bottom{text-align:center;color:#64748b;font-size:11px;margin-top:24px}
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
      <article class="task xmaint">
        <div class="task-head"><div class="task-name"><span class="task-icon">𝕏</span>X 服务器维护监测</div><span class="tag">X MONITOR</span></div>
        <div class="time">每小时 :05</div><div class="timezone">每小时一次 · 北京时间 UTC+8（如 09:05、10:05、11:05）</div>
        <div class="count-label">距离下次执行还有</div><div class="count" id="xmaint-count">计算中…</div>
        <div class="foot"><span>GitHub Actions · Hourly X Maintenance Alert</span><span class="status">● 已配置</span></div>
      </article>
    </section>
    <section class="note"><strong>运行说明</strong><br>① 每天 16:01 触发每日掉落数据获取。<br>② 每天 16:02 触发订阅推送工作流，等待当天获取任务成功后再发送，避免推送旧数据。<br>③ 每小时 :05 触发 X 服务器维护公告检查（例如 09:05、10:05、11:05）。<br>以上时间均为北京时间。Cloudflare Worker 每分钟检查一次计划任务，实际触发可能有少量延迟。</section>

    <section class="test-panel">
      <div class="test-title">手动触发测试 <span>MANUAL TEST</span></div>
      <p>用于验证 Cloudflare Worker 是否能够成功调用 GitHub Actions。请输入你设置的测试密钥，再选择要触发的工作流。</p>
      <label for="trigger-key">测试密钥</label>
      <input id="trigger-key" type="password" autocomplete="off" placeholder="输入 Cloudflare Secret：TRIGGER_SECRET">
      <div class="test-actions">
        <button class="test-btn fetch-btn" data-workflow="fetch">测试触发每日掉落获取</button>
        <button class="test-btn push-btn" data-workflow="push">测试触发每日订阅推送</button>
      </div>
      <div id="trigger-result" role="status" aria-live="polite"></div>
    </section>
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
    function nextHourlyRun(minute) {
      const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA",{timeZone:zone,year:"numeric",month:"numeric",day:"numeric",hour:"numeric",hourCycle:"h23"}).formatToParts(new Date()).filter(p=>p.type!=="literal").map(p=>[p.type,Number(p.value)]));
      let target = Date.UTC(parts.year,parts.month-1,parts.day,parts.hour-8,minute,0);
      if (target <= Date.now()) target += 3600000;
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
      document.getElementById("xmaint-count").textContent=countdown(nextHourlyRun(5));
    }

    document.querySelectorAll(".test-btn").forEach(button => {
      button.addEventListener("click", async () => {
        const key = document.getElementById("trigger-key").value.trim();
        const result = document.getElementById("trigger-result");
        if (!key) { result.className = "error"; result.textContent = "请先输入测试密钥。"; return; }
        const workflow = button.dataset.workflow;
        document.querySelectorAll(".test-btn").forEach(item => item.disabled = true);
        result.className = ""; result.textContent = "正在请求 Cloudflare Worker…";
        try {
          const response = await fetch("/api/trigger", {
            method: "POST",
            headers: {"Content-Type":"application/json","X-Trigger-Key":key},
            body: JSON.stringify({workflow})
          });
          const data = await response.json().catch(() => ({}));
          if (!response.ok) throw new Error(data.error || ("HTTP " + response.status));
          result.className = "ok";
          result.textContent = "✓ GitHub 已接受工作流触发请求：" + data.workflow + "。请到仓库 Actions 页面查看运行状态。";
        } catch (error) {
          result.className = "error";
          result.textContent = "触发失败：" + (error.message || String(error));
        } finally {
          document.querySelectorAll(".test-btn").forEach(item => item.disabled = false);
        }
      });
    });
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

    if (controller.cron !== CHECK_CRON) {
      console.log(JSON.stringify({ event: "ignored_cron", cron: controller.cron }));
      return;
    }

    // Use the scheduled instant, not the Cloudflare data-center's local timezone.
    const beijing = getBeijingHourMinute(controller.scheduledTime);
    console.log(JSON.stringify({
      event: "beijing_time_checked",
      timezone: TIME_ZONE,
      hour: beijing.hour,
      minute: beijing.minute,
      scheduledTime: new Date(controller.scheduledTime).toISOString(),
    }));

    if (beijing.hour === "16" && beijing.minute === "01") {
      await dispatchWorkflow(env, "daily-loot-fetch.yml");
      return;
    }

    // 每小时北京时间第 05 分钟，由 Worker 触发 X 维护公告检查工作流。
    if (beijing.minute === "05") {
      await dispatchWorkflow(env, "hourly-x-maintenance-alert.yml");
      return;
    }

    if (beijing.hour === "16" && beijing.minute === "02") {
      const fetchNotBefore = new Date(
        controller.scheduledTime - 3 * 60 * 1000,
      ).toISOString();

      await dispatchWorkflow(env, "daily-loot-push.yml", {
        wait_for_fetch: "true",
        fetch_not_before: fetchNotBefore,
      });
      return;
    }

    console.log(JSON.stringify({
      event: "no_workflow_due",
      timezone: TIME_ZONE,
      hour: beijing.hour,
      minute: beijing.minute,
    }));
  },

  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/api/trigger") {
      if (request.method !== "POST") {
        return Response.json({ error: "Method Not Allowed" }, { status: 405, headers: { Allow: "POST" } });
      }
      if (!env.TRIGGER_SECRET) {
        return Response.json({ error: "Worker 尚未配置 TRIGGER_SECRET" }, { status: 503 });
      }
      const supplied = request.headers.get("X-Trigger-Key") || "";
      let mismatch = supplied.length ^ env.TRIGGER_SECRET.length;
      const max = Math.max(supplied.length, env.TRIGGER_SECRET.length);
      for (let i = 0; i < max; i++) {
        mismatch |= (supplied.charCodeAt(i) || 0) ^ (env.TRIGGER_SECRET.charCodeAt(i) || 0);
      }
      if (mismatch !== 0) {
        return Response.json({ error: "测试密钥错误" }, { status: 401 });
      }
      let body: { workflow?: string };
      try {
        body = await request.json() as { workflow?: string };
      } catch {
        return Response.json({ error: "请求内容不是有效 JSON" }, { status: 400 });
      }
      const workflows: Record<string, string> = {
        fetch: "daily-loot-fetch.yml",
        push: "daily-loot-push.yml",
      };
      const workflowFile = body.workflow ? workflows[body.workflow] : undefined;
      if (!workflowFile) {
        return Response.json({ error: "不支持的工作流类型" }, { status: 400 });
      }
      try {
        await dispatchWorkflow(env, workflowFile);
        return Response.json({ ok: true, workflow: workflowFile, message: "GitHub 已接受 workflow_dispatch 请求" }, { status: 202 });
      } catch (error) {
        console.error("Manual workflow trigger failed:", error);
        return Response.json({ error: error instanceof Error ? error.message : "GitHub API 调用失败" }, { status: 502 });
      }
    }

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
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'",
      },
    });
  },
};
